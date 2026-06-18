"""
ui/habits/habit_calendar_grid.py
Grille calendrier avec actions d'archivage, restauration et suppression.
"""

import calendar
from datetime import date
from typing import Callable, Dict, List, Optional

import customtkinter as ctk
import tkinter as tk


class HabitCalendarGrid(ctk.CTkFrame):
    """
    Grille mois × habits.
    Header : jours 1-31
    Rows : une par habitude avec nom + cases à cocher + actions
    """

    def __init__(
        self,
        master,
        year: int,
        month: int,
        habits: List[dict],
        logs_by_habit: Dict[int, Dict[str, str]],
        on_toggle: Callable[[int, str, Optional[str]], None],
        on_archive: Optional[Callable[[int], None]] = None,
        on_restore: Optional[Callable[[int], None]] = None,
        on_delete: Optional[Callable[[int], None]] = None,
        streaks_by_habit: Optional[Dict[int, int]] = None,
        best_streaks_by_habit: Optional[Dict[int, int]] = None,
        is_archived_view: bool = False,
        **kwargs
    ):
        super().__init__(master, fg_color="transparent", **kwargs)

        self.year = year
        self.month = month
        self.habits = habits
        self.logs_by_habit = logs_by_habit
        self.on_toggle = on_toggle
        self.on_archive = on_archive
        self.on_restore = on_restore
        self.on_delete = on_delete
        self.streaks_by_habit = streaks_by_habit or {}
        self.best_streaks_by_habit = best_streaks_by_habit or {}
        self.is_archived_view = is_archived_view

        self._day_cells: Dict[tuple, ctk.CTkButton] = {}
        self._streak_frames: Dict[int, ctk.CTkFrame] = {}
        self._build_grid()

    def _build_grid(self) -> None:
        """Construit la grille entière."""
        _, num_days = calendar.monthrange(self.year, self.month)

        # Colonne 0 = nom + actions, colonnes 1-31 = jours
        self.grid_columnconfigure(0, minsize=220)  # Plus large pour les boutons
        for day in range(1, num_days + 1):
            self.grid_columnconfigure(day, minsize=36)

        self._build_header(num_days)

        for row_idx, habit in enumerate(self.habits, start=1):
            self._build_habit_row(habit, row_idx, num_days)

    def _build_header(self, num_days: int) -> None:
        corner = ctk.CTkFrame(self, fg_color="transparent", height=36)
        corner.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)

        for day in range(1, num_days + 1):
            is_today = self._is_today(day)
            bg = "#3B82F6" if is_today else "#F1F5F9"
            fg = "#FFFFFF" if is_today else "#64748B"

            cell = ctk.CTkFrame(self, fg_color=bg, corner_radius=4, height=32, width=34)
            cell.grid(row=0, column=day, sticky="nsew", padx=1, pady=2)

            label = ctk.CTkLabel(
                cell, text=str(day),
                font=ctk.CTkFont(size=10, weight="bold" if is_today else "normal"),
                text_color=fg, width=28
            )
            label.place(relx=0.5, rely=0.5, anchor="center")

    def _build_habit_row(self, habit: dict, row: int, num_days: int) -> None:
        habit_id = habit["id"]
        color = habit.get("color", "#3B82F6")
        icon = habit.get("icon", "•")
        title = habit["title"]
        streak = self.streaks_by_habit.get(habit_id, 0)
        best = self.best_streaks_by_habit.get(habit_id, 0)
        is_archived = habit.get("archived_at") is not None

        name_cell = ctk.CTkFrame(self, fg_color="#FFFFFF", corner_radius=6, height=50)
        name_cell.grid(row=row, column=0, sticky="nsew", padx=2, pady=1)

        # ─── Gauche : info habit ───
        left = ctk.CTkFrame(name_cell, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True, padx=10)

        indicator = ctk.CTkFrame(left, fg_color=color, corner_radius=3, width=4, height=20)
        indicator.pack(side="left", padx=(0, 8))

        ctk.CTkLabel(
            left,
            text=f"{icon} {title}",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#1E293B" if not is_archived else "#94A3B8",
            anchor="w"
        ).pack(side="left")

        # Badge "ARCHIVÉ"
        if is_archived:
            ctk.CTkLabel(
                left, text="📦",
                font=ctk.CTkFont(size=10), text_color="#94A3B8"
            ).pack(side="left", padx=(4, 0))

        linked_text = self._get_linked_text(habit)
        if linked_text:
            ctk.CTkLabel(
                left,
                text=linked_text,
                font=ctk.CTkFont(size=9),
                text_color="#94A3B8",
                anchor="w"
            ).pack(side="left", padx=(8, 0))

        # ─── Droite : streak + actions ───
        right = ctk.CTkFrame(name_cell, fg_color="transparent")
        right.pack(side="right", padx=(0, 10))

        # Streak
        self._streak_frames[habit_id] = right
        self._render_streak(right, streak, best)

        # ─── Boutons d'action ───
        actions = ctk.CTkFrame(name_cell, fg_color="transparent")
        actions.pack(side="right", padx=(0, 5))

        if self.is_archived_view:
            # Mode archivé : Restaurer + Supprimer
            ctk.CTkButton(
                actions, text="↩️", width=28, height=28, corner_radius=4,
                fg_color="#D1FAE5", hover_color="#A7F3D0",
                text_color="#059669", font=ctk.CTkFont(size=12),
                command=lambda hid=habit_id: self._on_restore(hid) if self.on_restore else None
            ).pack(side="left", padx=1)

            ctk.CTkButton(
                actions, text="🗑️", width=28, height=28, corner_radius=4,
                fg_color="#FEE2E2", hover_color="#FECACA",
                text_color="#DC2626", font=ctk.CTkFont(size=12),
                command=lambda hid=habit_id: self._on_delete(hid) if self.on_delete else None
            ).pack(side="left", padx=1)
        else:
            # Mode actif : Archiver + Supprimer
            ctk.CTkButton(
                actions, text="📦", width=28, height=28, corner_radius=4,
                fg_color="#F1F5F9", hover_color="#E2E8F0",
                text_color="#64748B", font=ctk.CTkFont(size=12),
                command=lambda hid=habit_id: self._on_archive(hid) if self.on_archive else None
            ).pack(side="left", padx=1)

            ctk.CTkButton(
                actions, text="🗑️", width=28, height=28, corner_radius=4,
                fg_color="#FEE2E2", hover_color="#FECACA",
                text_color="#DC2626", font=ctk.CTkFont(size=12),
                command=lambda hid=habit_id: self._on_delete(hid) if self.on_delete else None
            ).pack(side="left", padx=1)

        # ─── Cases jours ───
        for day in range(1, num_days + 1):
            self._build_day_cell(habit_id, day, row, color, is_archived)

    def _build_day_cell(self, habit_id: int, day: int, row: int, habit_color: str, is_archived: bool = False) -> None:
        """Une case jour individuelle."""
        date_iso = f"{self.year}-{self.month:02d}-{day:02d}"
        status = self._get_status(habit_id, date_iso)
        is_today = self._is_today(day)

        if is_archived:
            # Grisé pour les archivées
            bg = "#F1F5F9"
            fg = "#CBD5E1"
            text = "✓" if status == "done" else "✗" if status == "missed" else "~" if status == "partial" else ""
            state = "disabled"
        else:
            if status == "done":
                bg = habit_color
                fg = "#FFFFFF"
                text = "✓"
            elif status == "missed":
                bg = "#FEE2E2"
                fg = "#DC2626"
                text = "✗"
            elif status == "partial":
                bg = "#FEF3C7"
                fg = "#D97706"
                text = "~"
            else:
                bg = "#F8FAFC" if not is_today else "#EFF6FF"
                fg = "#CBD5E1"
                text = ""
            state = "normal"

        cell = ctk.CTkButton(
            self,
            text=text,
            width=36,
            height=32,
            corner_radius=4,
            fg_color=bg,
            hover_color=bg,
            text_color=fg,
            font=ctk.CTkFont(size=12, weight="bold"),
            border_width=1 if is_today else 0,
            border_color="#3B82F6",
            state=state,
            command=lambda hid=habit_id, d=date_iso, s=status: self._on_cell_click(hid, d, s)
        )
        cell.grid(row=row, column=day, sticky="nsew", padx=1, pady=1)

        self._day_cells[(habit_id, day)] = cell

    def _on_cell_click(self, habit_id: int, date_iso: str, current_status: Optional[str]) -> None:
        """Cycle : None → done → missed → partial → None."""
        cycle = {None: "done", "done": "missed", "missed": "partial", "partial": None}
        new_status = cycle.get(current_status, "done")

        self._update_cell_visual(habit_id, date_iso, new_status)
        self.on_toggle(habit_id, date_iso, new_status)

    def _update_cell_visual(self, habit_id: int, date_iso: str, status: Optional[str]) -> None:
        """Met à jour une cellule sans reconstruire toute la grille."""
        day = int(date_iso.split("-")[2])
        cell = self._day_cells.get((habit_id, day))
        if not cell:
            return

        habit = next((h for h in self.habits if h["id"] == habit_id), None)
        habit_color = habit.get("color", "#3B82F6") if habit else "#3B82F6"

        if status == "done":
            bg = habit_color
            fg = "#FFFFFF"
            text = "✓"
        elif status == "missed":
            bg = "#FEE2E2"
            fg = "#DC2626"
            text = "✗"
        elif status == "partial":
            bg = "#FEF3C7"
            fg = "#D97706"
            text = "~"
        else:
            is_today = self._is_today(day)
            bg = "#F8FAFC" if not is_today else "#EFF6FF"
            fg = "#CBD5E1"
            text = ""

        cell.configure(
            text=text,
            fg_color=bg,
            hover_color=bg,
            text_color=fg,
            command=lambda hid=habit_id, d=date_iso, s=status: self._on_cell_click(hid, d, s)
        )

        if habit_id not in self.logs_by_habit:
            self.logs_by_habit[habit_id] = {}
        if status:
            self.logs_by_habit[habit_id][date_iso] = status
        else:
            self.logs_by_habit[habit_id].pop(date_iso, None)

    def _on_archive(self, habit_id: int) -> None:
        if self.on_archive:
            self.on_archive(habit_id)

    def _on_restore(self, habit_id: int) -> None:
        if self.on_restore:
            self.on_restore(habit_id)

    def _on_delete(self, habit_id: int) -> None:
        if self.on_delete:
            self.on_delete(habit_id)

    def _get_status(self, habit_id: int, date_iso: str) -> Optional[str]:
        return self.logs_by_habit.get(habit_id, {}).get(date_iso)

    def _is_today(self, day: int) -> bool:
        today = date.today()
        return today.year == self.year and today.month == self.month and today.day == day

    def refresh_logs(self, new_logs: Dict[int, Dict[str, str]]) -> None:
        self.logs_by_habit = new_logs
        for (habit_id, day), cell in self._day_cells.items():
            date_iso = f"{self.year}-{self.month:02d}-{day:02d}"
            status = self._get_status(habit_id, date_iso)
            self._update_cell_visual(habit_id, date_iso, status)

    def _get_linked_text(self, habit: dict) -> str:
        goal_title = habit.get("goal_title")
        task_name = habit.get("task_name")

        if task_name and goal_title:
            return f"↳ {goal_title} › {task_name}"
        elif goal_title:
            return f"↳ {goal_title}"
        return ""

    def _render_streak(self, parent: ctk.CTkFrame, streak: int, best: int) -> None:
        """Affiche le streak dans le frame donné."""
        for widget in parent.winfo_children():
            widget.destroy()

        if streak > 0:
            streak_color = "#EF4444" if streak >= 7 else "#F59E0B" if streak >= 3 else "#94A3B8"
            ctk.CTkLabel(
                parent,
                text=f"🔥 {streak}",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=streak_color
            ).pack(side="right")
        elif best > 0:
            ctk.CTkLabel(
                parent,
                text=f"🏆 {best}",
                font=ctk.CTkFont(size=10),
                text_color="#94A3B8"
            ).pack(side="right")

    def update_streak(self, habit_id: int, streak: int, best: int) -> None:
        """Met à jour l'affichage du streak en temps réel."""
        frame = self._streak_frames.get(habit_id)
        if frame:
            self._render_streak(frame, streak, best)