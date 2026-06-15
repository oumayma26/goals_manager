"""
ui/main_window.py
Fenêtre principale avec Vision Board intégré.
"""

import os
import customtkinter as ctk
from typing import Optional
from services import GoalService
from database import DatabaseManager
from ui.theme_manager import ThemeManager
from ui.dashboard_view import DashboardView
from ui.goals_grid_view import GoalsGridView
from ui.goal_detail_view import GoalDetailView
from ui.dialogs import GoalDialog


class MainWindow(ctk.CTk):
    """
    Fenêtre principale - Design clair, épuré et professionnel.
    """

    def __init__(self) -> None:
        super().__init__()

        self.title("Goals Manager")
        self.geometry("1280x850")
        self.minsize(1000, 700)
        self.configure(fg_color="#F1F5F9")

        self.db = DatabaseManager()
        self.service = GoalService(self.db)

        self.selected_goal_id: Optional[int] = None
        self.current_view: Optional[ctk.CTkFrame] = None
        self.show_completed: bool = False

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_left_panel()
        self._build_right_panel()

        self._show_dashboard()

    def _build_left_panel(self) -> None:
        """Panneau gauche - Sidebar claire."""
        self.left_frame = ctk.CTkFrame(
            self,
            width=320,
            fg_color="#FFFFFF",
            corner_radius=0,
            border_width=0
        )
        self.left_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.left_frame.grid_rowconfigure(8, weight=1)
        self.left_frame.grid_propagate(False)

        # Logo / Titre
        header = ctk.CTkFrame(self.left_frame, fg_color="transparent", height=70)
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        header.grid_propagate(False)

        ctk.CTkLabel(header, text="🎯", font=ctk.CTkFont(size=28)).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(
            header,
            text="Goals Manager",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#1E293B"
        ).pack(side="left")

        # Navigation
        nav_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        nav_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=10)

        self.dashboard_btn = self._create_nav_button(
            nav_frame, "📊 Tableau de bord", self._show_dashboard, active=True
        )
        self.dashboard_btn.pack(fill="x", pady=3)

        self.goals_btn = self._create_nav_button(
            nav_frame, "🎯 Mes Objectifs", self._show_goals_view, active=False
        )
        self.goals_btn.pack(fill="x", pady=3)

        self.vision_btn = self._create_nav_button(
            nav_frame, "✨ Vision Board", self._show_vision_board, active=False
        )
        self.vision_btn.pack(fill="x", pady=3)

        # Séparateur
        ctk.CTkFrame(self.left_frame, height=1, fg_color="#E2E8F0").grid(
            row=2, column=0, sticky="ew", padx=20, pady=15
        )

        # Section Filtres
        filter_label = ctk.CTkLabel(
            self.left_frame,
            text="FILTRES",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#94A3B8"
        )
        filter_label.grid(row=3, column=0, padx=20, pady=(5, 10), sticky="w")

        # Recherche
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *args: self._on_filter_changed())

        search_frame = ctk.CTkFrame(self.left_frame, fg_color="#F1F5F9", corner_radius=10)
        search_frame.grid(row=4, column=0, padx=15, pady=5, sticky="ew")

        ctk.CTkEntry(
            search_frame,
            placeholder_text="🔍 Rechercher...",
            textvariable=self.search_var,
            fg_color="transparent",
            border_width=0,
            height=40
        ).pack(fill="x", padx=10, pady=5)

        # Filtres statut/priorité
        filters_row = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        filters_row.grid(row=5, column=0, padx=15, pady=5, sticky="ew")
        filters_row.grid_columnconfigure((0, 1), weight=1)

        self.status_filter = ctk.CTkOptionMenu(
            filters_row,
            values=["Tous", "Non commencé", "En cours", "Terminé"],
            command=lambda _: self._on_filter_changed(),
            width=130,
            fg_color="#F1F5F9",
            button_color="#E2E8F0",
            text_color="#475569",
            dropdown_fg_color="#FFFFFF",
            dropdown_text_color="#1E293B",
            dropdown_hover_color="#F1F5F9"
        )
        self.status_filter.set("Tous")
        self.status_filter.grid(row=0, column=0, padx=(0, 5), sticky="ew")

        self.priority_filter = ctk.CTkOptionMenu(
            filters_row,
            values=["Toutes", "Faible", "Moyenne", "Haute"],
            command=lambda _: self._on_filter_changed(),
            width=130,
            fg_color="#F1F5F9",
            button_color="#E2E8F0",
            text_color="#475569",
            dropdown_fg_color="#FFFFFF",
            dropdown_text_color="#1E293B",
            dropdown_hover_color="#F1F5F9"
        )
        self.priority_filter.set("Toutes")
        self.priority_filter.grid(row=0, column=1, padx=(5, 0), sticky="ew")

        # Toggle "Voir les terminés"
        self.toggle_completed_btn = ctk.CTkButton(
            self.left_frame,
            text="👁️ Voir les terminés",
            command=self._toggle_completed_filter,
            height=35,
            corner_radius=8,
            fg_color="#F1F5F9",
            hover_color="#E2E8F0",
            text_color="#475569",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.toggle_completed_btn.grid(row=6, column=0, padx=15, pady=10, sticky="ew")

        # Liste des goals (sidebar)
        self.goals_scroll = ctk.CTkScrollableFrame(
            self.left_frame,
            fg_color="transparent",
            label_text=""
        )
        self.goals_scroll.grid(row=8, column=0, sticky="nsew", padx=10, pady=10)

        # Bouton Nouveau Goal
        self.new_goal_btn = ctk.CTkButton(
            self.left_frame,
            text="➕ Nouvel objectif",
            command=self._open_new_goal_dialog,
            height=45,
            corner_radius=10,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#3B82F6",
            hover_color="#2563EB",
            text_color="#FFFFFF"
        )
        self.new_goal_btn.grid(row=9, column=0, padx=15, pady=(5, 20), sticky="ew")

    def _create_nav_button(self, parent, text, command, active=False):
        """Crée un bouton de navigation stylisé."""
        colors = {
            "active": {"fg": "#EFF6FF", "text": "#3B82F6", "hover": "#EFF6FF"},
            "inactive": {"fg": "transparent", "text": "#64748B", "hover": "#F1F5F9"}
        }
        state = "active" if active else "inactive"

        btn = ctk.CTkButton(
            parent,
            text=text,
            command=command,
            height=42,
            corner_radius=8,
            font=ctk.CTkFont(size=13, weight="bold" if active else "normal"),
            fg_color=colors[state]["fg"],
            hover_color=colors[state]["hover"],
            text_color=colors[state]["text"],
            anchor="w",
            text_color_disabled=colors[state]["text"]
        )
        return btn

    def _build_right_panel(self) -> None:
        """Panneau droit."""
        self.right_frame = ctk.CTkFrame(
            self,
            fg_color="#F1F5F9",
            corner_radius=0,
            border_width=0
        )
        self.right_frame.grid(row=0, column=1, sticky="nsew", padx=15, pady=15)
        self.right_frame.grid_columnconfigure(0, weight=1)
        self.right_frame.grid_rowconfigure(0, weight=1)

    def _clear_right_panel(self) -> None:
        for widget in self.right_frame.winfo_children():
            widget.destroy()

    def _show_dashboard(self) -> None:
        self._clear_right_panel()
        self._set_nav_active("dashboard")

        self.current_view = DashboardView(
            self.right_frame,
            service=self.service,
            on_navigate_goals=self._show_goals_view
        )
        self.current_view.grid(row=0, column=0, sticky="nsew")

    def _show_goals_view(self) -> None:
        """Affiche la grille de goals."""
        self._clear_right_panel()
        self._set_nav_active("goals")
        self.selected_goal_id = None

        goals = self._get_filtered_goals()

        self.current_view = GoalsGridView(
            self.right_frame,
            service=self.service,
            goals=goals,
            on_select_goal=self._on_goal_selected
        )
        self.current_view.grid(row=0, column=0, sticky="nsew")

        self._refresh_sidebar_only()

    def _show_vision_board(self) -> None:
        """Affiche le Vision Board."""
        self._clear_right_panel()
        self._set_nav_active("vision")

        from ui.vision_board_view import VisionBoardView

        self.current_view = VisionBoardView(
            self.right_frame,
            service=self.service,
            db_manager=self.db
        )
        self.current_view.grid(row=0, column=0, sticky="nsew")

    def _get_filtered_goals(self) -> list:
        """Récupère les goals filtrés et triés par progression."""
        status = self.status_filter.get()
        priority = self.priority_filter.get()
        search = self.search_var.get() or None

        if status == "Tous":
            status = None
        if priority == "Toutes":
            priority = None

        if self.show_completed:
            goals = self.service.list_goals(status="Terminé")
        else:
            goals = self.service.list_goals(exclude_status="Terminé")

        if status and status != "Terminé":
            goals = [g for g in goals if g.status == status]
        if priority:
            goals = [g for g in goals if g.priority == priority]
        if search:
            goals = [g for g in goals if search.lower() in g.title.lower()
                     or search.lower() in g.description.lower()]

        goals_with_progress = []
        for goal in goals:
            prog = self.service.get_goal_progress(goal.id)
            goals_with_progress.append((goal, prog["percentage"]))

        goals_with_progress.sort(key=lambda x: x[1], reverse=True)
        return [g for g, _ in goals_with_progress]

    def _on_goal_selected(self, goal_id: int) -> None:
        """Callback quand un goal est sélectionné."""
        self.selected_goal_id = goal_id
        self._show_goal_details(goal_id)

    def _show_goal_details(self, goal_id: int) -> None:
        """Affiche les détails d'un goal."""
        goal = self.service.get_goal(goal_id)
        if not goal:
            return

        self._clear_right_panel()

        self.current_view = GoalDetailView(
            self.right_frame,
            goal=goal,
            service=self.service,
            on_update=self._on_goal_updated
        )
        self.current_view.grid(row=0, column=0, sticky="nsew")

    def _toggle_completed_filter(self) -> None:
        """Bascule entre goals non terminés et terminés."""
        self.show_completed = not self.show_completed

        if self.show_completed:
            self.toggle_completed_btn.configure(
                text="👁️ Voir les non terminés",
                fg_color="#D1FAE5",
                hover_color="#A7F3D0",
                text_color="#059669"
            )
        else:
            self.toggle_completed_btn.configure(
                text="👁️ Voir les terminés",
                fg_color="#F1F5F9",
                hover_color="#E2E8F0",
                text_color="#475569"
            )

        self._show_goals_view()

    def _on_filter_changed(self) -> None:
        """Appelé quand un filtre change."""
        self._refresh_sidebar_only()
        if isinstance(self.current_view, GoalsGridView):
            self._refresh_grid_only()

    def _on_goal_updated(self) -> None:
        """Appelé quand un goal est modifié."""
        self._refresh_sidebar_only()
        if isinstance(self.current_view, GoalsGridView):
            self._refresh_grid_only()

    def _refresh_sidebar_only(self) -> None:
        """Recharge UNIQUEMENT la sidebar."""
        for widget in self.goals_scroll.winfo_children():
            widget.destroy()

        status = self.status_filter.get()
        priority = self.priority_filter.get()
        search = self.search_var.get() or None

        if status == "Tous":
            status = None
        if priority == "Toutes":
            priority = None

        if self.show_completed:
            goals = self.service.list_goals(status="Terminé")
        else:
            goals = self.service.list_goals(exclude_status="Terminé")

        if status and status != "Terminé":
            goals = [g for g in goals if g.status == status]
        if priority:
            goals = [g for g in goals if g.priority == priority]
        if search:
            goals = [g for g in goals if search.lower() in g.title.lower()
                     or search.lower() in g.description.lower()]

        if not goals:
            ctk.CTkLabel(
                self.goals_scroll,
                text="Aucun objectif",
                text_color="#94A3B8",
                font=ctk.CTkFont(size=13)
            ).pack(pady=30)
            return

        for goal in goals:
            self._create_sidebar_goal_item(goal)

    def _refresh_grid_only(self) -> None:
        """Recharge UNIQUEMENT la grille."""
        if not isinstance(self.current_view, GoalsGridView):
            return

        for widget in self.current_view.scroll.winfo_children():
            widget.destroy()

        goals = self._get_filtered_goals()

        for widget in self.current_view.winfo_children():
            if isinstance(widget, ctk.CTkFrame) and widget != self.current_view.scroll:
                for child in widget.winfo_children():
                    if isinstance(child, ctk.CTkLabel) and "Objectifs" in child.cget("text"):
                        child.configure(text=f"🎯 Objectifs ({len(goals)})")

        if not goals:
            self.current_view._build_empty_state()
            return

        for idx, goal in enumerate(goals):
            self.current_view._create_goal_card(goal, idx)

    def _create_sidebar_goal_item(self, goal) -> None:
        """Item compact dans la sidebar."""
        progress = self.service.get_goal_progress(goal.id)
        percentage = progress["percentage"]
        goal_color = goal.color if hasattr(goal, 'color') and goal.color else "#3B82F6"

        item = ctk.CTkFrame(
            self.goals_scroll,
            fg_color="#FFFFFF",
            corner_radius=10,
            border_width=1,
            border_color="#E2E8F0",
            height=60
        )
        item.pack(fill="x", padx=2, pady=2)
        item.pack_propagate(False)
        item.bind("<Button-1>", lambda e, gid=goal.id: self._on_goal_selected(gid))
        item.configure(cursor="hand2")

        item.bind("<Enter>", lambda e, it=item, gc=goal_color: it.configure(border_color=gc, border_width=2))
        item.bind("<Leave>", lambda e, it=item: it.configure(border_color="#E2E8F0", border_width=1))

        inner = ctk.CTkFrame(item, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=10, pady=8)
        inner.bind("<Button-1>", lambda e, gid=goal.id: self._on_goal_selected(gid))

        top = ctk.CTkFrame(inner, fg_color="transparent")
        top.pack(fill="x")
        top.bind("<Button-1>", lambda e, gid=goal.id: self._on_goal_selected(gid))

        ctk.CTkLabel(
            top,
            text=goal.title,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#1E293B",
            anchor="w"
        ).pack(side="left", fill="x", expand=True)

        percent_color = "#10B981" if percentage >= 100 else goal_color
        ctk.CTkLabel(
            top,
            text=f"{percentage:.0f}%",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=percent_color
        ).pack(side="right")

        bar_bg = ctk.CTkFrame(inner, height=3, corner_radius=2, fg_color="#E2E8F0")
        bar_bg.pack(fill="x", pady=(4, 0))
        bar_bg.pack_propagate(False)

        fill_width = max(1, int(200 * (percentage / 100))) if percentage > 0 else 1
        bar_fill = ctk.CTkFrame(bar_bg, height=3, corner_radius=2, fg_color=percent_color, width=fill_width)
        bar_fill.pack(side="left", fill="y")

    def _set_nav_active(self, view: str) -> None:
        """Met à jour l'état des boutons de navigation."""
        buttons = {
            "dashboard": self.dashboard_btn,
            "goals": self.goals_btn,
            "vision": self.vision_btn
        }

        for key, btn in buttons.items():
            if key == view:
                btn.configure(
                    fg_color="#EFF6FF", text_color="#3B82F6",
                    font=ctk.CTkFont(size=13, weight="bold")
                )
            else:
                btn.configure(
                    fg_color="transparent", text_color="#64748B",
                    font=ctk.CTkFont(size=13, weight="normal")
                )

    def _open_new_goal_dialog(self) -> None:
        dialog = GoalDialog(self, service=self.service, on_save=self._on_filter_changed)
        dialog.grab_set()

    def run(self) -> None:
        self.mainloop()