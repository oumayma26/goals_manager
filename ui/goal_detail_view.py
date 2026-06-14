"""
ui/goal_detail_view.py
Panneau de détails affichant les informations d'un goal,
sa barre de progression et la liste de ses tâches.
"""

import customtkinter as ctk
from tkinter import messagebox
from typing import Callable
from models import Goal
from services import GoalService
from ui.dialogs import GoalDialog, TaskDialog


class GoalDetailView(ctk.CTkFrame):
    """Vue détaillée d'un goal - Design clair."""

    def __init__(
        self,
        master,
        goal: Goal,
        service: GoalService,
        on_update: Callable,
        **kwargs
    ) -> None:
        super().__init__(master, fg_color="#F1F5F9", **kwargs)
        
        self.goal = goal
        self.service = service
        self.on_update = on_update

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_header()
        self._build_progress_section()
        self._build_tasks_section()

    def _build_header(self) -> None:
        """En-tête épuré avec carte blanche."""
        # Carte principale
        card = ctk.CTkFrame(self, fg_color="#FFFFFF", corner_radius=16, border_width=1, border_color="#E2E8F0")
        card.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        card.grid_columnconfigure(0, weight=1)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=25, pady=20)

        # Ligne titre + badge
        title_row = ctk.CTkFrame(inner, fg_color="transparent")
        title_row.pack(fill="x")

        ctk.CTkLabel(
            title_row,
            text=self.goal.title,
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color="#1E293B"
        ).pack(side="left")

        priority_colors = {
            "Haute": ("#FEE2E2", "#DC2626"),
            "Moyenne": ("#FEF3C7", "#D97706"),
            "Faible": ("#D1FAE5", "#059669")
        }
        bg, fg = priority_colors.get(self.goal.priority, ("#F1F5F9", "#64748B"))

        ctk.CTkLabel(
            title_row,
            text=f"  {self.goal.priority}  ",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=bg,
            text_color=fg,
            corner_radius=8
        ).pack(side="right")

        # Description
        if self.goal.description:
            desc = ctk.CTkTextbox(
                inner,
                height=70,
                wrap="word",
                state="normal",
                fg_color="transparent",
                border_width=0,
                text_color="#475569",
                font=ctk.CTkFont(size=13)
            )
            desc.insert("0.0", self.goal.description)
            desc.configure(state="disabled")
            desc.pack(fill="x", pady=(10, 0))

        # Métadonnées
        meta = ctk.CTkFrame(inner, fg_color="transparent")
        meta.pack(fill="x", pady=(15, 0))

        ctk.CTkLabel(
            meta,
            text=f"📅 Créé le {self.goal.created_at.strftime('%d %B %Y')}",
            font=ctk.CTkFont(size=12),
            text_color="#94A3B8"
        ).pack(side="left")

        if self.goal.target_date:
            target_text = f"🎯 Échéance : {self.goal.target_date.strftime('%d %B %Y')}"
            target_color = "#EF4444" if self.goal.is_overdue else "#3B82F6"
            ctk.CTkLabel(
                meta,
                text=target_text,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=target_color
            ).pack(side="left", padx=20)

        # Boutons d'action
        actions = ctk.CTkFrame(inner, fg_color="transparent")
        actions.pack(fill="x", pady=(15, 0))

        ctk.CTkButton(
            actions,
            text="✏️ Modifier",
            command=self._edit_goal,
            width=120,
            height=35,
            corner_radius=8,
            fg_color="#F1F5F9",
            hover_color="#E2E8F0",
            text_color="#475569",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            actions,
            text="🗑️ Supprimer",
            command=self._delete_goal,
            width=120,
            height=35,
            corner_radius=8,
            fg_color="#FEE2E2",
            hover_color="#FECACA",
            text_color="#DC2626",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(side="left")

    def _build_progress_section(self) -> None:
        """Section progression avec carte - widgets stockés pour mise à jour."""
        card = ctk.CTkFrame(self, fg_color="#FFFFFF", corner_radius=16, border_width=1, border_color="#E2E8F0")
        card.grid(row=1, column=0, sticky="ew", pady=(0, 15))
        card.grid_columnconfigure(1, weight=1)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=25, pady=20)

        progress = self.service.get_goal_progress(self.goal.id)

        # Header progression
        header = ctk.CTkFrame(inner, fg_color="transparent")
        header.pack(fill="x")

        ctk.CTkLabel(
            header,
            text="📊 Progression",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#1E293B"
        ).pack(side="left")

        # Compteur de tâches (stocké pour mise à jour)
        self.tasks_counter_label = ctk.CTkLabel(
            header,
            text=f"{progress['completed_tasks']} / {progress['total_tasks']} tâches",
            font=ctk.CTkFont(size=13),
            text_color="#94A3B8"
        )
        self.tasks_counter_label.pack(side="right")

        # Barre de progression (stockée pour mise à jour)
        self.progress_bar = ctk.CTkFrame(inner, fg_color="#E2E8F0", corner_radius=10, height=12)
        self.progress_bar.pack(fill="x", pady=(15, 10))
        self.progress_bar.pack_propagate(False)

        fill_width_pct = progress["percentage"] / 100.0
        fill_width_pct = max(0.0, min(1.0, fill_width_pct))

        fill = ctk.CTkFrame(
            self.progress_bar,
            fg_color="#3B82F6" if progress["percentage"] < 100 else "#10B981",
            corner_radius=10
        )
        fill.place(x=0, y=0, relwidth=fill_width_pct, relheight=1.0)

        # Pourcentage (stocké pour mise à jour)
        percent_color = "#10B981" if progress["percentage"] == 100 else "#3B82F6"
        self.progress_label = ctk.CTkLabel(
            inner,
            text=f"{progress['percentage']:.0f}%",
            font=ctk.CTkFont(size=32, weight="bold"),
            text_color=percent_color
        )
        self.progress_label.pack(anchor="w")

    def _build_tasks_section(self) -> None:
        """Section tâches avec carte."""
        card = ctk.CTkFrame(self, fg_color="#FFFFFF", corner_radius=16, border_width=1, border_color="#E2E8F0")
        card.grid(row=2, column=0, sticky="nsew", pady=(0, 0))
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(1, weight=1)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=25, pady=20)

        # Header
        header = ctk.CTkFrame(inner, fg_color="transparent")
        header.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(
            header,
            text="✅ Tâches",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#1E293B"
        ).pack(side="left")

        ctk.CTkButton(
            header,
            text="➕ Ajouter",
            command=self._add_task,
            width=120,
            height=35,
            corner_radius=8,
            fg_color="#3B82F6",
            hover_color="#2563EB",
            text_color="#FFFFFF",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(side="right")

        # Liste des tâches
        self.tasks_scroll = ctk.CTkScrollableFrame(inner, fg_color="transparent", label_text="")
        self.tasks_scroll.pack(fill="both", expand=True)

        self._refresh_tasks_list()

    def _refresh_tasks_list(self) -> None:
        """Recharge la liste des tâches ET met à jour la progression en temps réel."""
        for widget in self.tasks_scroll.winfo_children():
            try:
                widget.destroy()
            except Exception:
                pass

        tasks = self.service.list_tasks(self.goal.id)

        if not tasks:
            empty = ctk.CTkFrame(self.tasks_scroll, fg_color="#F8FAFC", corner_radius=12)
            empty.pack(fill="x", pady=10)

            ctk.CTkLabel(
                empty,
                text="Aucune tâche pour le moment",
                font=ctk.CTkFont(size=13),
                text_color="#94A3B8"
            ).pack(pady=30)
            
            # Mettre à jour la progression à 0%
            self._update_progress_display({"percentage": 0, "completed_tasks": 0, "total_tasks": 0})
            return

        for task in tasks:
            self._create_task_row(task)

        # Mettre à jour la progression
        progress = self.service.get_goal_progress(self.goal.id)
        self._update_progress_display(progress)

    def _update_progress_display(self, progress: dict) -> None:
        """Met à jour l'affichage de progression en temps réel."""
        percentage = progress["percentage"]
        percent_color = "#10B981" if percentage >= 100 else "#3B82F6"
        
        # Mettre à jour le label de pourcentage
        if hasattr(self, 'progress_label'):
            self.progress_label.configure(text=f"{percentage:.0f}%", text_color=percent_color)
        
        # Mettre à jour la barre de progression
        if hasattr(self, 'progress_bar'):
            # Supprimer l'ancien fill
            for widget in self.progress_bar.winfo_children():
                widget.destroy()
            
            fill_width_pct = percentage / 100.0
            fill_width_pct = max(0.0, min(1.0, fill_width_pct))
            
            bar_fill = ctk.CTkFrame(
                self.progress_bar,
                height=12,
                corner_radius=10,
                fg_color=percent_color
            )
            bar_fill.place(x=0, y=0, relwidth=fill_width_pct, relheight=1.0)
        
        # Mettre à jour le compteur de tâches
        if hasattr(self, 'tasks_counter_label'):
            self.tasks_counter_label.configure(
                text=f"{progress['completed_tasks']} / {progress['total_tasks']} tâches"
            )

    def _create_task_row(self, task) -> None:
        """Ligne de tâche moderne avec bouton toggle."""
        row = ctk.CTkFrame(self.tasks_scroll, fg_color="#F8FAFC", corner_radius=10)
        row.pack(fill="x", pady=3)

        # Bouton toggle
        if task.is_completed:
            toggle_btn = ctk.CTkButton(
                row,
                text="✓",
                width=32,
                height=32,
                corner_radius=8,
                fg_color="#10B981",
                hover_color="#059669",
                text_color="#FFFFFF",
                font=ctk.CTkFont(size=14, weight="bold"),
                command=lambda t=task: self._toggle_task(t)
            )
        else:
            toggle_btn = ctk.CTkButton(
                row,
                text="○",
                width=32,
                height=32,
                corner_radius=8,
                fg_color="#E2E8F0",
                hover_color="#CBD5E1",
                text_color="#94A3B8",
                font=ctk.CTkFont(size=14, weight="bold"),
                command=lambda t=task: self._toggle_task(t)
            )
        toggle_btn.pack(side="left", padx=(15, 10), pady=10)

        # Texte
        text_frame = ctk.CTkFrame(row, fg_color="transparent")
        text_frame.pack(side="left", fill="both", expand=True, pady=10)

        name_color = "#94A3B8" if task.is_completed else "#1E293B"
        font = ctk.CTkFont(size=14, overstrike=task.is_completed)

        ctk.CTkLabel(
            text_frame,
            text=task.name,
            font=font,
            text_color=name_color,
            anchor="w"
        ).pack(fill="x")

        if task.description:
            ctk.CTkLabel(
                text_frame,
                text=task.description[:50] + "..." if len(task.description) > 50 else task.description,
                font=ctk.CTkFont(size=11),
                text_color="#94A3B8",
                anchor="w"
            ).pack(fill="x")

        # Boutons d'action
        if not task.is_completed:
            ctk.CTkButton(
                row,
                text="✏️",
                width=32,
                height=32,
                corner_radius=6,
                fg_color="transparent",
                hover_color="#E2E8F0",
                text_color="#64748B",
                command=lambda t=task: self._edit_task(t)
            ).pack(side="right", padx=(0, 5), pady=10)

        ctk.CTkButton(
            row,
            text="🗑️",
            width=32,
            height=32,
            corner_radius=6,
            fg_color="transparent",
            hover_color="#FEE2E2",
            text_color="#EF4444",
            command=lambda t=task: self._delete_task(t)
        ).pack(side="right", padx=(0, 15), pady=10)

    def _toggle_task(self, task) -> None:
        """Bascule le statut d'une tâche."""
        new_status = "Terminée" if task.status != "Terminée" else "À faire"
        self.service.update_task(task.id, status=new_status)
        self._refresh_tasks_list()
        self.on_update()

    def _add_task(self) -> None:
        """Ouvre le dialogue d'ajout de tâche."""
        dialog = TaskDialog(self, goal_id=self.goal.id, service=self.service, on_save=self._refresh_tasks_list)
        dialog.grab_set()

    def _edit_task(self, task) -> None:
        """Ouvre le dialogue d'édition de tâche."""
        dialog = TaskDialog(self, goal_id=self.goal.id, service=self.service, task=task, on_save=self._refresh_tasks_list)
        dialog.grab_set()

    def _delete_task(self, task) -> None:
        """Supprime une tâche avec confirmation."""
        if messagebox.askyesno("Confirmation", f"Supprimer la tâche '{task.name}' ?"):
            self.service.delete_task(task.id)
            self._refresh_tasks_list()
            self.on_update()

    def _edit_goal(self) -> None:
        """Ouvre le dialogue d'édition du goal."""
        dialog = GoalDialog(self, service=self.service, goal=self.goal, on_save=self.on_update)
        dialog.grab_set()

    def _delete_goal(self) -> None:
        """Supprime le goal avec confirmation."""
        if messagebox.askyesno(
            "Confirmation",
            f"Supprimer l'objectif '{self.goal.title}' ?\nToutes les tâches associées seront supprimées."
        ):
            self.service.delete_goal(self.goal.id)
            self.on_update()
            try:
                self.destroy()
            except Exception:
                pass