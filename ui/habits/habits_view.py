"""
ui/habits/habits_view.py
Vue principale du tracker d'habitudes avec support arabe RTL,
archivage, suppression définitive et vue des archivées.
"""

import calendar
from datetime import date
from typing import Dict, List, Optional

import customtkinter as ctk
import tkinter as tk

from utils.arabic_text import (
    prepare_for_display,
    ArabicCTkLabel,
    ArabicCTkButton,
)

from database.database import DatabaseManager
from services.habit_service import HabitService
from services.goal_service import GoalService
from .habit_calendar_grid import HabitCalendarGrid
from .habit_dialog import HabitDialog


class HabitsView(ctk.CTkFrame):
    """Vue tracker d'habitudes avec archivage, suppression et support arabe."""

    def __init__(self, master, db: DatabaseManager, **kwargs):
        super().__init__(master, fg_color="#F8FAFC", **kwargs)

        self.db = db
        self.service = HabitService(db)

        self.current_year = date.today().year
        self.current_month = date.today().month
        self.show_archived = False  # Toggle vue archivées

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_header()
        self._build_toolbar()
        self._build_calendar_container()

        self._load_habits()

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent", height=55)
        header.grid(row=0, column=0, sticky="ew", padx=25, pady=(15, 5))
        header.grid_propagate(False)

        left = ctk.CTkFrame(header, fg_color="transparent")
        left.pack(side="left", pady=8)

        # Titre dynamique selon le mode
        self.title_label = ArabicCTkLabel(
            left, text=prepare_for_display("📅 Habitudes"),
            font=ctk.CTkFont(size=20, weight="bold"), text_color="#1E293B"
        )
        self.title_label.pack(side="left")

        self.month_label = ArabicCTkLabel(
            left,
            text=self._format_month_year(self.current_year, self.current_month),
            font=ctk.CTkFont(size=14), text_color="#64748B"
        )
        self.month_label.pack(side="left", padx=(12, 0))

    def _build_toolbar(self) -> None:
        toolbar = ctk.CTkFrame(self, fg_color="transparent", height=45)
        toolbar.grid(row=1, column=0, sticky="ew", padx=25, pady=5)
        toolbar.grid_propagate(False)

        left = ctk.CTkFrame(toolbar, fg_color="transparent")
        left.pack(side="left")

        ArabicCTkButton(
            left, text="◀", width=32, height=32, corner_radius=6,
            fg_color="#F1F5F9", hover_color="#E2E8F0", text_color="#475569",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._prev_month
        ).pack(side="left", padx=2)

        ArabicCTkButton(
            left, text=prepare_for_display("Aujourd'hui"), width=80, height=32, corner_radius=6,
            fg_color="#F1F5F9", hover_color="#E2E8F0", text_color="#475569",
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._go_to_today
        ).pack(side="left", padx=2)

        ArabicCTkButton(
            left, text="▶", width=32, height=32, corner_radius=6,
            fg_color="#F1F5F9", hover_color="#E2E8F0", text_color="#475569",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._next_month
        ).pack(side="left", padx=2)

        right = ctk.CTkFrame(toolbar, fg_color="transparent")
        right.pack(side="right")

        # Toggle "Voir archivées"
        self.archive_toggle_btn = ArabicCTkButton(
            right,
            text=prepare_for_display("📦 Voir archivées"),
            width=130, height=32, corner_radius=8,
            fg_color="#F1F5F9", hover_color="#E2E8F0",
            text_color="#64748B",
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._toggle_archived_view
        )
        self.archive_toggle_btn.pack(side="right", padx=5)

        # Nouvelle habitude (caché en mode archivées)
        self.new_habit_btn = ArabicCTkButton(
            right, text=prepare_for_display("➕ Nouvelle habitude"), width=140, height=32, corner_radius=8,
            fg_color="#3B82F6", hover_color="#2563EB", text_color="#FFFFFF",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._open_new_habit_dialog
        )
        self.new_habit_btn.pack(side="right", padx=2)

    def _build_calendar_container(self) -> None:
        """Conteneur scrollable HORIZONTAL pour la grille."""
        self.calendar_wrapper = ctk.CTkFrame(self, fg_color="transparent")
        self.calendar_wrapper.grid(row=2, column=0, sticky="nsew", padx=20, pady=5)
        self.calendar_wrapper.grid_columnconfigure(0, weight=1)
        self.calendar_wrapper.grid_rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(
            self.calendar_wrapper,
            bg="#F8FAFC",
            highlightthickness=0
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")

        self.h_scroll = tk.Scrollbar(
            self.calendar_wrapper,
            orient="horizontal",
            command=self.canvas.xview
        )
        self.h_scroll.grid(row=1, column=0, sticky="ew")

        self.canvas.configure(xscrollcommand=self.h_scroll.set)

        self.scroll_inner = ctk.CTkFrame(self.canvas, fg_color="transparent")
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scroll_inner, anchor="nw")

        self.scroll_inner.bind("<Configure>", self._on_inner_configure)

        self.calendar_frame: Optional[HabitCalendarGrid] = None

    def _on_inner_configure(self, event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        bbox = self.canvas.bbox("all")
        if bbox:
            content_width = bbox[2] - bbox[0]
            canvas_width = self.canvas.winfo_width()
            if content_width <= canvas_width:
                self.h_scroll.grid_remove()
            else:
                self.h_scroll.grid()

    def _load_habits(self) -> None:
        habits = self.service.list_habits(include_archived=self.show_archived)
        logs = self.service.get_logs_for_month(self.current_year, self.current_month)

        habits_data = [
            {
                "id": h["id"],
                "title": prepare_for_display(h["title"]),
                "color": h.get("color", "#3B82F6"),
                "icon": h.get("icon", "•"),
                "goal_title": prepare_for_display(h.get("goal_title", "")),
                "task_name": prepare_for_display(h.get("task_name", "")),
                "archived_at": h.get("archived_at"),
            }
            for h in habits
        ]

        streaks = {}
        best_streaks = {}
        for h in habits:
            streaks[h["id"]] = self.service.get_current_streak(h["id"])
            best_streaks[h["id"]] = self.service.get_best_streak(h["id"])

        if self.calendar_frame:
            self.calendar_frame.destroy()

        for widget in self.scroll_inner.winfo_children():
            widget.destroy()

        if not habits_data:
            self._show_empty_state()
            return

        self.calendar_frame = HabitCalendarGrid(
            self.scroll_inner,
            year=self.current_year,
            month=self.current_month,
            habits=habits_data,
            logs_by_habit=logs,
            streaks_by_habit=streaks,
            best_streaks_by_habit=best_streaks,
            on_toggle=self._on_habit_toggle,
            on_archive=self._on_archive_habit if not self.show_archived else None,
            on_restore=self._on_restore_habit if self.show_archived else None,
            on_delete=self._on_delete_habit_permanently,
            is_archived_view=self.show_archived,
        )
        self.calendar_frame.pack(fill="both", expand=True)

    def _show_empty_state(self) -> None:
        for widget in self.scroll_inner.winfo_children():
            widget.destroy()

        msg = ("Aucune habitude archivée" if self.show_archived 
               else "Aucune habitude\nCréez votre première habitude !")
        ArabicCTkLabel(
            self.scroll_inner,
            text=prepare_for_display(msg),
            font=ctk.CTkFont(size=14), text_color="#94A3B8",
            justify="center"
        ).pack(pady=100)

    def _on_habit_toggle(self, habit_id: int, date_iso: str, new_status: Optional[str]) -> None:
        if new_status:
            self.service.toggle_log(habit_id, date_iso, new_status)
        else:
            self.service.delete_log(habit_id, date_iso)

        if self.calendar_frame:
            new_streak = self.service.get_current_streak(habit_id)
            new_best = self.service.get_best_streak(habit_id)
            self.calendar_frame.update_streak(habit_id, new_streak, new_best)

    def _on_archive_habit(self, habit_id: int) -> None:
        """Archive une habitude active."""
        if self.service.archive_habit(habit_id):
            self._load_habits()

    def _on_restore_habit(self, habit_id: int) -> None:
        """Restaure une habitude archivée."""
        if self.service.restore_habit(habit_id):
            self._load_habits()

    def _on_delete_habit_permanently(self, habit_id: int) -> None:
        """Suppression définitive avec confirmation."""
        self._show_delete_confirm(habit_id)

    def _show_delete_confirm(self, habit_id: int) -> None:
        """Dialog de confirmation pour suppression définitive."""
        confirm = ctk.CTkToplevel(self)
        confirm.title("⚠️ Suppression définitive")
        confirm.geometry("360x180")
        confirm.transient(self)
        confirm.grab_set()
        confirm.configure(fg_color="#FFFFFF")

        # Centrer
        self.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 360) // 2
        y = self.winfo_y() + (self.winfo_height() - 180) // 2
        confirm.geometry(f"+{x}+{y}")

        # Icône warning
        ctk.CTkLabel(
            confirm, text="🗑️",
            font=ctk.CTkFont(size=32), text_color="#EF4444"
        ).pack(pady=(15, 5))

        ctk.CTkLabel(
            confirm,
            text="Supprimer définitivement ?",
            font=ctk.CTkFont(size=14, weight="bold"), text_color="#1E293B"
        ).pack()

        ctk.CTkLabel(
            confirm,
            text="Cette action est irréversible.\nTous les logs seront perdus.",
            font=ctk.CTkFont(size=11), text_color="#94A3B8"
        ).pack(pady=5)

        btn_frame = ctk.CTkFrame(confirm, fg_color="transparent")
        btn_frame.pack(pady=15)

        ctk.CTkButton(
            btn_frame, text="Annuler", width=100, height=32,
            fg_color="#F1F5F9", hover_color="#E2E8F0",
            text_color="#475569", font=ctk.CTkFont(size=12, weight="bold"),
            command=confirm.destroy
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame, text="Supprimer", width=100, height=32,
            fg_color="#EF4444", hover_color="#DC2626",
            text_color="#FFFFFF", font=ctk.CTkFont(size=12, weight="bold"),
            command=lambda: [
                self.service.delete_habit_permanently(habit_id),
                confirm.destroy(),
                self._load_habits()
            ]
        ).pack(side="left", padx=5)

    def _toggle_archived_view(self) -> None:
        """Bascule entre vue active et vue archivée."""
        self.show_archived = not self.show_archived

        if self.show_archived:
            self.title_label.configure(text=prepare_for_display("📦 Habitudes archivées"))
            self.archive_toggle_btn.configure(
                text=prepare_for_display("📅 Voir actives"),
                fg_color="#EFF6FF", text_color="#3B82F6",
                hover_color="#DBEAFE"
            )
            self.new_habit_btn.pack_forget()
        else:
            self.title_label.configure(text=prepare_for_display("📅 Habitudes"))
            self.archive_toggle_btn.configure(
                text=prepare_for_display("📦 Voir archivées"),
                fg_color="#F1F5F9", text_color="#64748B",
                hover_color="#E2E8F0"
            )
            self.new_habit_btn.pack(side="right", padx=2)

        self._load_habits()

    def _prev_month(self) -> None:
        self.current_month -= 1
        if self.current_month < 1:
            self.current_month = 12
            self.current_year -= 1
        self._refresh()

    def _next_month(self) -> None:
        self.current_month += 1
        if self.current_month > 12:
            self.current_month = 1
            self.current_year += 1
        self._refresh()

    def _go_to_today(self) -> None:
        today = date.today()
        self.current_year = today.year
        self.current_month = today.month
        self._refresh()

    def _refresh(self) -> None:
        self.month_label.configure(
            text=self._format_month_year(self.current_year, self.current_month)
        )
        self._load_habits()

    @staticmethod
    def _format_month_year(year: int, month: int) -> str:
        months = ["", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
                  "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
        return f"{months[month]} {year}"

    def _open_new_habit_dialog(self) -> None:
        dialog = HabitDialog(
            self,
            db=self.db,
            goal_service=GoalService(self.db),
            on_save=self._refresh
        )
        dialog.grab_set()