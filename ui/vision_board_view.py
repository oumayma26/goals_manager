"""
ui/vision_board_view.py
Vision Board avec Mood Board intégré - Collage automatique Unsplash.
"""

import os
import sys
import sqlite3
import tkinter as tk
from tkinter import colorchooser
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, field

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFilter, ImageTk, ImageFont

# Ajouter la racine du projet au path pour les imports absolus
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from database import DatabaseManager
from services import GoalService
from ui.collage_engine import CollageEngine, CollageConfig, LayoutType, CollageItem


# ═══════════════════════════════════════════════════
# MODÈLES
# ═══════════════════════════════════════════════════

@dataclass
class TextStyle:
    font_family: str = "Arial"
    font_size: int = 16
    bold: bool = False
    italic: bool = False
    color: str = "#1E293B"
    background: Optional[str] = None
    opacity: int = 0


@dataclass
class FloatingText:
    id: int
    text: str
    x: float
    y: float
    style: TextStyle = field(default_factory=TextStyle)
    canvas_id: Optional[int] = None
    bg_id: Optional[int] = None
    tk_image: Optional[ImageTk.PhotoImage] = None


@dataclass
class VisionItem:
    goal_id: int
    image_path: str
    title: str
    x: float = 0
    y: float = 0
    width: float = 280
    height: float = 190
    color: str = "#3B82F6"
    rotation: float = 0.0
    canvas_id: Optional[int] = None
    shadow_id: Optional[int] = None
    tk_image: Optional[ImageTk.PhotoImage] = None
    is_mood_item: bool = False  # Nouveau : item généré par mood board


# ═══════════════════════════════════════════════════
# DIALOG AVEC SCROLLBAR
# ═══════════════════════════════════════════════════

class FloatingTextDialog(ctk.CTkToplevel):
    def __init__(self, master, text_obj: Optional[FloatingText] = None):
        super().__init__(master)
        self.title("✏️ Texte libre")
        self.geometry("450x580")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        self.configure(fg_color="#FFFFFF")

        self.result = None
        self.text_obj = text_obj

        self.update_idletasks()
        x = master.winfo_x() + (master.winfo_width() - 450) // 2
        y = master.winfo_y() + (master.winfo_height() - 580) // 2
        self.geometry(f"+{x}+{y}")

        self._build_ui()

    def _build_ui(self):
        self.scroll_frame = ctk.CTkScrollableFrame(
            self,
            fg_color="#FFFFFF",
            corner_radius=0,
            scrollbar_fg_color="#E2E8F0",
            scrollbar_button_color="#CBD5E1",
            scrollbar_button_hover_color="#94A3B8"
        )
        self.scroll_frame.pack(fill="both", expand=True, padx=0, pady=0)

        content = ctk.CTkFrame(self.scroll_frame, fg_color="#FFFFFF")
        content.pack(fill="x", expand=True)

        ctk.CTkLabel(
            content,
            text="✨ Texte libre",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#1E293B"
        ).pack(pady=(15, 10), padx=20, anchor="w")

        # TEXTE
        ctk.CTkLabel(content, text="Contenu:", font=ctk.CTkFont(size=12, weight="bold"), text_color="#475569").pack(padx=20, anchor="w", pady=(10, 5))

        self.text_entry = ctk.CTkTextbox(
            content, height=60, wrap="word",
            corner_radius=8, border_width=1, border_color="#E2E8F0",
            fg_color="#F8FAFC", text_color="#1E293B",
            font=ctk.CTkFont(size=13)
        )
        self.text_entry.pack(fill="x", padx=20, pady=5)
        self.text_entry.insert("0.0", self.text_obj.text if self.text_obj else "Votre texte ici")

        # POLICE
        font_frame = ctk.CTkFrame(content, fg_color="#F8FAFC", corner_radius=10)
        font_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(font_frame, text="📝 Police", font=ctk.CTkFont(size=13, weight="bold"), text_color="#1E293B").pack(anchor="w", padx=12, pady=(10, 5))

        row1 = ctk.CTkFrame(font_frame, fg_color="transparent")
        row1.pack(fill="x", padx=12, pady=5)
        ctk.CTkLabel(row1, text="Police:", font=ctk.CTkFont(size=11), text_color="#475569").pack(side="left", padx=(0, 8))

        fonts = ["Arial", "Times New Roman", "Courier New", "Georgia", "Verdana", "Helvetica", "Impact", "Comic Sans MS", "Segoe UI", "Tahoma"]
        self.font_var = ctk.StringVar(value=self.text_obj.style.font_family if self.text_obj else "Arial")
        ctk.CTkOptionMenu(row1, values=fonts, variable=self.font_var, width=180, height=28, fg_color="#FFFFFF", button_color="#E2E8F0", text_color="#1E293B", font=ctk.CTkFont(size=11)).pack(side="left")

        row2 = ctk.CTkFrame(font_frame, fg_color="transparent")
        row2.pack(fill="x", padx=12, pady=5)
        ctk.CTkLabel(row2, text="Taille:", font=ctk.CTkFont(size=11), text_color="#475569").pack(side="left", padx=(0, 8))

        self.size_slider = ctk.CTkSlider(row2, from_=8, to=72, number_of_steps=64, width=100)
        self.size_slider.set(self.text_obj.style.font_size if self.text_obj else 16)
        self.size_slider.pack(side="left")
        self.size_label = ctk.CTkLabel(row2, text=str(self.text_obj.style.font_size if self.text_obj else 16), width=30, font=ctk.CTkFont(size=11))
        self.size_label.pack(side="left", padx=5)
        self.size_slider.configure(command=lambda v: self.size_label.configure(text=f"{int(v)}"))

        row3 = ctk.CTkFrame(font_frame, fg_color="transparent")
        row3.pack(fill="x", padx=12, pady=(5, 10))
        self.bold_var = ctk.BooleanVar(value=self.text_obj.style.bold if self.text_obj else False)
        ctk.CTkCheckBox(row3, text="Gras", variable=self.bold_var, font=ctk.CTkFont(size=11)).pack(side="left", padx=8)
        self.italic_var = ctk.BooleanVar(value=self.text_obj.style.italic if self.text_obj else False)
        ctk.CTkCheckBox(row3, text="Italique", variable=self.italic_var, font=ctk.CTkFont(size=11)).pack(side="left", padx=8)

        # COULEURS
        color_frame = ctk.CTkFrame(content, fg_color="#F8FAFC", corner_radius=10)
        color_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(color_frame, text="🎨 Couleurs", font=ctk.CTkFont(size=13, weight="bold"), text_color="#1E293B").pack(anchor="w", padx=12, pady=(10, 5))

        row_c1 = ctk.CTkFrame(color_frame, fg_color="transparent")
        row_c1.pack(fill="x", padx=12, pady=5)
        ctk.CTkLabel(row_c1, text="Texte:", font=ctk.CTkFont(size=11), text_color="#475569").pack(side="left", padx=(0, 10))

        self.text_color = self.text_obj.style.color if self.text_obj else "#1E293B"
        self.text_color_preview = ctk.CTkFrame(row_c1, width=28, height=28, corner_radius=6, fg_color=self.text_color, border_width=2, border_color="#E2E8F0")
        self.text_color_preview.pack(side="left")
        ctk.CTkButton(row_c1, text="Choisir", width=80, height=26, corner_radius=6, fg_color="#FFFFFF", hover_color="#F1F5F9", text_color="#475569", border_width=1, border_color="#E2E8F0", font=ctk.CTkFont(size=11), command=lambda: self._pick_color("text")).pack(side="left", padx=10)

        row_c2 = ctk.CTkFrame(color_frame, fg_color="transparent")
        row_c2.pack(fill="x", padx=12, pady=5)
        ctk.CTkLabel(row_c2, text="Fond:", font=ctk.CTkFont(size=11), text_color="#475569").pack(side="left", padx=(0, 10))

        self.bg_color = self.text_obj.style.background if self.text_obj else None
        bg_hex = self.bg_color if self.bg_color else "#FFFFFF"
        self.bg_color_preview = ctk.CTkFrame(row_c2, width=28, height=28, corner_radius=6, fg_color=bg_hex, border_width=2, border_color="#E2E8F0")
        self.bg_color_preview.pack(side="left")
        ctk.CTkButton(row_c2, text="Choisir", width=80, height=26, corner_radius=6, fg_color="#FFFFFF", hover_color="#F1F5F9", text_color="#475569", border_width=1, border_color="#E2E8F0", font=ctk.CTkFont(size=11), command=lambda: self._pick_color("bg")).pack(side="left", padx=10)
        ctk.CTkButton(row_c2, text="Aucun", width=60, height=26, corner_radius=6, fg_color="#FEE2E2", hover_color="#FECACA", text_color="#DC2626", font=ctk.CTkFont(size=11), command=self._clear_bg).pack(side="left", padx=5)

        row_c3 = ctk.CTkFrame(color_frame, fg_color="transparent")
        row_c3.pack(fill="x", padx=12, pady=(5, 10))
        ctk.CTkLabel(row_c3, text="Opacité:", font=ctk.CTkFont(size=11), text_color="#475569").pack(side="left", padx=(0, 8))
        self.opacity_slider = ctk.CTkSlider(row_c3, from_=0, to=255, number_of_steps=51, width=100)
        self.opacity_slider.set(self.text_obj.style.opacity if self.text_obj else 0)
        self.opacity_slider.pack(side="left")
        self.opacity_label = ctk.CTkLabel(row_c3, text=str(self.text_obj.style.opacity if self.text_obj else 0), width=30, font=ctk.CTkFont(size=11))
        self.opacity_label.pack(side="left", padx=5)
        self.opacity_slider.configure(command=lambda v: self.opacity_label.configure(text=f"{int(v)}"))

        # BOUTONS
        ctk.CTkFrame(content, height=1, fg_color="#E2E8F0").pack(fill="x", padx=20, pady=10)

        btn_frame = ctk.CTkFrame(content, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(5, 20))

        if self.text_obj:
            ctk.CTkButton(btn_frame, text="🗑️ Supprimer", width=100, fg_color="#FEE2E2", hover_color="#FECACA", text_color="#DC2626", font=ctk.CTkFont(size=12, weight="bold"), command=self._on_delete).pack(side="left", padx=5)

        ctk.CTkButton(btn_frame, text="Annuler", width=90, fg_color="#F1F5F9", hover_color="#E2E8F0", text_color="#475569", font=ctk.CTkFont(size=12, weight="bold"), command=self.destroy).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="💾 Appliquer", width=120, fg_color="#3B82F6", hover_color="#2563EB", text_color="#FFFFFF", font=ctk.CTkFont(size=12, weight="bold"), command=self._on_save).pack(side="right", padx=5)

    def _pick_color(self, which: str):
        current = self.text_color if which == "text" else (self.bg_color or "#FFFFFF")
        color = colorchooser.askcolor(color=current, title="Couleur")
        if color[1]:
            if which == "text":
                self.text_color = color[1]
                self.text_color_preview.configure(fg_color=color[1])
            else:
                self.bg_color = color[1]
                self.bg_color_preview.configure(fg_color=color[1])

    def _clear_bg(self):
        self.bg_color = None
        self.bg_color_preview.configure(fg_color="#FFFFFF")

    def _on_save(self):
        self.result = {
            "text": self.text_entry.get("0.0", "end").strip(),
            "style": TextStyle(
                font_family=self.font_var.get(),
                font_size=int(self.size_slider.get()),
                bold=self.bold_var.get(),
                italic=self.italic_var.get(),
                color=self.text_color,
                background=self.bg_color,
                opacity=int(self.opacity_slider.get())
            )
        }
        self.destroy()

    def _on_delete(self):
        self.result = {"delete": True}
        self.destroy()


# ═══════════════════════════════════════════════════
# VISION BOARD
# ═══════════════════════════════════════════════════

class VisionBoardView(ctk.CTkFrame):
    CARD_W = 280
    CARD_H = 190
    CANVAS_W = 2000
    CANVAS_H = 1400

    def __init__(self, master, service: GoalService, db_manager: DatabaseManager, **kwargs):
        super().__init__(master, fg_color="#F8FAFC", **kwargs)
        self.service = service
        self.db = db_manager
        self.items: Dict[int, VisionItem] = {}
        self.texts: Dict[int, FloatingText] = {}
        self._next_text_id = 1
        self._next_mood_id = -1  # IDs négatifs pour les items mood
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build_header()
        self._build_canvas()
        self._load_all()

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent", height=55)
        header.grid(row=0, column=0, sticky="ew", padx=25, pady=(15, 5))
        header.grid_propagate(False)

        left = ctk.CTkFrame(header, fg_color="transparent")
        left.pack(side="left", pady=8)

        ctk.CTkLabel(left, text="✨ Mon Vision Board", font=ctk.CTkFont(size=20, weight="bold"), text_color="#1E293B").pack(side="left")
        ctk.CTkLabel(left, text="Double-clic = éditer  |  Drag = déplacer", font=ctk.CTkFont(size=11), text_color="#94A3B8").pack(side="left", padx=(12, 0))

        right = ctk.CTkFrame(header, fg_color="transparent")
        right.pack(side="right", pady=8)


        # Bouton Ajouter image
        ctk.CTkButton(
            right, text="➕ Ajouter image", width=130, height=32, corner_radius=8,
            fg_color="#10B981", hover_color="#059669", text_color="#FFFFFF",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._open_add_image_dialog
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            right, text="➕ Ajouter texte", width=130, height=32, corner_radius=8,
            fg_color="#3B82F6", hover_color="#2563EB", text_color="#FFFFFF",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._add_floating_text
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            right, text="💾", width=36, height=32, corner_radius=8,
            fg_color="#FFFFFF", hover_color="#F1F5F9", text_color="#3B82F6",
            border_width=1, border_color="#E2E8F0", font=ctk.CTkFont(size=14),
            command=self._save
        ).pack(side="left", padx=4)

    def _build_canvas(self):
        container = ctk.CTkFrame(self, fg_color="#FFFFFF", corner_radius=16, border_width=1, border_color="#E2E8F0")
        container.grid(row=1, column=0, sticky="nsew", padx=20, pady=(5, 20))
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(container, bg="#FAFBFC", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)

        h_scroll = ctk.CTkScrollbar(container, orientation="horizontal", command=self.canvas.xview)
        h_scroll.grid(row=1, column=0, sticky="ew")
        v_scroll = ctk.CTkScrollbar(container, orientation="vertical", command=self.canvas.yview)
        v_scroll.grid(row=0, column=1, sticky="ns")

        self.canvas.configure(
            xscrollcommand=h_scroll.set, yscrollcommand=v_scroll.set,
            scrollregion=(0, 0, self.CANVAS_W, self.CANVAS_H)
        )

        self.canvas.bind("<ButtonPress-1>", self._on_drag_start)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_drag_stop)
        self.canvas.bind("<Double-Button-1>", self._on_double_click)
        self.canvas.bind("<Button-3>", self._on_right_click)

    def _load_all(self):
        self._load_items()
        self._load_texts()
        self._load_mood_items()

    def _load_items(self):
        goals = self.service.list_goals()
        goals_with_images = [g for g in goals if g.image_path and os.path.exists(g.image_path)]

        if not goals_with_images and not self.texts and not any(i.is_mood_item for i in self.items.values()):
            self._show_empty()
            return

        saved = self._get_saved_items()
        for idx, goal in enumerate(goals_with_images):
            s = saved.get(goal.id, {})
            item = VisionItem(
                goal_id=goal.id,
                image_path=goal.image_path,
                title=goal.title,
                x=s.get("pos_x", 40 + (idx % 3) * 320),
                y=s.get("pos_y", 40 + (idx // 3) * 250),
                color=goal.color if hasattr(goal, 'color') and goal.color else "#3B82F6",
                width=s.get("width", self.CARD_W),
                height=s.get("height", self.CARD_H)
            )
            self.items[goal.id] = item
            self._draw_item(item)

    def _load_texts(self):
        saved_texts = self._get_saved_texts()
        for st in saved_texts:
            text_obj = FloatingText(
                id=st["id"],
                text=st["text"],
                x=st["x"],
                y=st["y"],
                style=TextStyle(
                    font_family=st.get("font_family", "Arial"),
                    font_size=st.get("font_size", 16),
                    bold=st.get("bold", False),
                    italic=st.get("italic", False),
                    color=st.get("color", "#1E293B"),
                    background=st.get("background"),
                    opacity=st.get("opacity", 0)
                )
            )
            self.texts[text_obj.id] = text_obj
            self._next_text_id = max(self._next_text_id, text_obj.id + 1)
            self._draw_text(text_obj)

    def _load_mood_items(self):
        """Charge les items mood board sauvegardés."""
        mood_items = self._get_saved_mood_items()
        loaded = 0
        skipped = 0

        for mi in mood_items:
            # Convertir en path absolu si relatif
            image_path = mi["image_path"]
            if not os.path.isabs(image_path):
                image_path = os.path.abspath(image_path)

            if not os.path.exists(image_path):
                print(f"⚠️ Image mood introuvable: {image_path}")
                skipped += 1
                continue

            item = VisionItem(
                goal_id=mi["id"],
                image_path=image_path,
                title=mi.get("title", ""),
                x=mi["x"],
                y=mi["y"],
                width=mi.get("width", 280),
                height=mi.get("height", 190),
                color=mi.get("color", "#3B82F6"),
                rotation=mi.get("rotation", 0.0),
                is_mood_item=True
            )
            self.items[mi["id"]] = item
            self._next_mood_id = min(self._next_mood_id, mi["id"] - 1)
            self._draw_item(item)
            loaded += 1

        if loaded > 0 or skipped > 0:
            print(f"📊 Mood items: {loaded} chargés, {skipped} manquants")

    def _get_saved_items(self) -> dict:
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS vision_board (
                        goal_id INTEGER PRIMARY KEY,
                        motivation_text TEXT DEFAULT '',
                        pos_x REAL DEFAULT 0,
                        pos_y REAL DEFAULT 0,
                        width REAL DEFAULT 280,
                        height REAL DEFAULT 190,
                        FOREIGN KEY (goal_id) REFERENCES goals(id) ON DELETE CASCADE
                    )
                """)
                cursor.execute("SELECT goal_id, pos_x, pos_y, width, height FROM vision_board")
                return {
                    row[0]: {"pos_x": row[1] or 0, "pos_y": row[2] or 0, "width": row[3] or self.CARD_W, "height": row[4] or self.CARD_H}
                    for row in cursor.fetchall()
                }
        except:
            return {}

    def _get_saved_texts(self) -> list:
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS vision_board_texts (
                        id INTEGER PRIMARY KEY,
                        text TEXT NOT NULL,
                        x REAL DEFAULT 100,
                        y REAL DEFAULT 100,
                        font_family TEXT DEFAULT 'Arial',
                        font_size INTEGER DEFAULT 16,
                        bold INTEGER DEFAULT 0,
                        italic INTEGER DEFAULT 0,
                        color TEXT DEFAULT '#1E293B',
                        background TEXT,
                        opacity INTEGER DEFAULT 0
                    )
                """)
                cursor.execute("SELECT * FROM vision_board_texts")
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Erreur chargement textes: {e}")
            return []

    def _get_saved_mood_items(self) -> list:
        """Récupère les items mood board de la DB."""
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS vision_board_mood (
                        id INTEGER PRIMARY KEY,
                        image_path TEXT NOT NULL,
                        title TEXT DEFAULT '',
                        x REAL DEFAULT 100,
                        y REAL DEFAULT 100,
                        width REAL DEFAULT 280,
                        height REAL DEFAULT 190,
                        color TEXT DEFAULT '#3B82F6',
                        rotation REAL DEFAULT 0,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cursor.execute("SELECT * FROM vision_board_mood")
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Erreur chargement mood items: {e}")
            return []

    def _show_empty(self):
        self.canvas.create_text(
            self.CANVAS_W // 2, self.CANVAS_H // 2,
            text="📸 Ajoutez des images à vos goals\nou générez un Mood Board automatique !",
            font=("Segoe UI", 16), fill="#94A3B8", justify="center"
        )

    def _draw_item(self, item: VisionItem):
        """Dessine un item (goal ou mood) sur le canvas."""
        w, h = item.width, item.height

        # Ombre
        shadow = self._make_shadow(int(w), int(h))
        item.shadow_id = self.canvas.create_image(
            item.x + 5, item.y + 5,
            image=shadow, anchor="nw"
        )

        # Image principale
        img = self._make_card_image(item)
        item.tk_image = img
        item.canvas_id = self.canvas.create_image(
            item.x, item.y,
            image=img, anchor="nw"
        )

        # Bordure
        self.canvas.create_rectangle(
            item.x - 2, item.y - 2,
            item.x + w + 2, item.y + h + 2,
            outline=item.color, width=2,
            state="hidden", tags=f"border_{item.goal_id}"
        )

        # Handles de redimensionnement pour tous les items
        self._draw_resize_handles(item)

        self.canvas.tag_raise(item.canvas_id)

    def _draw_resize_handles(self, item: VisionItem):
        """Dessine les handles de redimensionnement aux coins."""
        w, h = item.width, item.height
        handle_size = 8
        handles = [
            (item.x + w, item.y + h, "se"),  # Sud-Est (coin bas-droite)
        ]

        item.resize_handles = []
        for hx, hy, direction in handles:
            handle_id = self.canvas.create_rectangle(
                hx - handle_size//2, hy - handle_size//2,
                hx + handle_size//2, hy + handle_size//2,
                fill="#3B82F6", outline="#FFFFFF", width=2,
                tags=f"resize_handle_{item.goal_id}_{direction}",
                state="hidden"
            )
            item.resize_handles.append(handle_id)

    def _show_resize_handles(self, item: VisionItem):
        """Affiche les handles de redimensionnement."""
        if hasattr(item, 'resize_handles'):
            for handle_id in item.resize_handles:
                self.canvas.itemconfig(handle_id, state="normal")

    def _hide_resize_handles(self, item: VisionItem):
        """Cache les handles de redimensionnement."""
        if hasattr(item, 'resize_handles'):
            for handle_id in item.resize_handles:
                self.canvas.itemconfig(handle_id, state="hidden")

    def _draw_text(self, text_obj: FloatingText):
        img = self._render_text_image(text_obj)
        text_obj.tk_image = img
        if text_obj.canvas_id:
            self.canvas.delete(text_obj.canvas_id)
        if text_obj.bg_id:
            self.canvas.delete(text_obj.bg_id)

        text_obj.canvas_id = self.canvas.create_image(
            text_obj.x, text_obj.y,
            image=img, anchor="nw",
            tags=f"text_{text_obj.id}"
        )

        bbox = self.canvas.bbox(text_obj.canvas_id)
        if bbox:
            text_obj.bg_id = self.canvas.create_rectangle(
                bbox[0]-2, bbox[1]-2, bbox[2]+2, bbox[3]+2,
                outline="#3B82F6", width=2,
                state="hidden", tags=f"text_border_{text_obj.id}"
            )

    def _render_text_image(self, text_obj: FloatingText) -> ImageTk.PhotoImage:
        style = text_obj.style
        try:
            font = ImageFont.truetype(f"{style.font_family}.ttf", style.font_size)
        except:
            try:
                font = ImageFont.truetype("arial.ttf", style.font_size)
            except:
                font = ImageFont.load_default()

        dummy = Image.new("RGBA", (1, 1))
        draw = ImageDraw.Draw(dummy)
        lines = text_obj.text.split("\n")
        max_w = 0
        total_h = 0
        line_heights = []

        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            lw = bbox[2] - bbox[0]
            lh = bbox[3] - bbox[1]
            max_w = max(max_w, lw)
            line_heights.append(lh)
            total_h += lh + 4

        total_h += 8
        max_w += 20

        img = Image.new("RGBA", (max_w, total_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        if style.background and style.opacity > 0:
            r, g, b = self._hex_to_rgb(style.background)
            draw.rounded_rectangle((0, 0, max_w, total_h), radius=6, fill=(r, g, b, style.opacity))

        y = 6
        for i, line in enumerate(lines):
            lh = line_heights[i]
            draw.text((10, y), line, fill=style.color, font=font)
            y += lh + 4

        return ImageTk.PhotoImage(img)

    def _hex_to_rgb(self, hex_color: str) -> tuple:
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def _make_shadow(self, w: int, h: int) -> ImageTk.PhotoImage:
        pad = 14
        img = Image.new("RGBA", (w + pad, h + pad), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        for i in range(6):
            alpha = 20 - i * 3
            offset = 3 + i
            draw.rounded_rectangle(
                (offset, offset + 1, offset + w, offset + h + 1),
                radius=10, fill=(0, 0, 0, alpha)
            )
        final = Image.new("RGB", img.size, (250, 250, 250))
        final.paste(img, mask=img.split()[3])
        return ImageTk.PhotoImage(final)

    def _make_card_image(self, item: VisionItem) -> ImageTk.PhotoImage:
        """Crée l'image d'une card avec effets."""
        w, h = int(item.width), int(item.height)

        try:
            img = Image.open(item.image_path).convert("RGB")
        except Exception:
            # Fallback: placeholder coloré
            img = Image.new("RGB", (w, h), self._hex_to_rgb(item.color))

        img = self._crop_center(img, w, h)
        img = img.resize((w, h), Image.Resampling.LANCZOS)

        # Rotation si mood item
        if item.rotation != 0 and item.is_mood_item:
            img = img.rotate(item.rotation, expand=True, resample=Image.Resampling.BICUBIC)
            # Recadrer au centre pour garder la taille cible
            new_w, new_h = img.size
            if new_w > w or new_h > h:
                left = (new_w - w) // 2
                top = (new_h - h) // 2
                img = img.crop((left, top, left + w, top + h))

        # Overlay dégradé pour le titre
        overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        for i in range(50):
            alpha = int(140 * (i / 50))
            draw.rectangle((0, h - 50 + i, w, h - 50 + i + 1), fill=(0, 0, 0, alpha))

        # Titre
        try:
            font = ImageFont.truetype("segoeui.ttf", 13) or ImageFont.truetype("arial.ttf", 13)
        except:
            font = ImageFont.load_default()

        if item.title:
            bbox = draw.textbbox((0, 0), item.title, font=font)
            tw = bbox[2] - bbox[0]
            draw.text(((w - tw) // 2, h - 30), item.title, fill="#FFFFFF", font=font)

        rgba = img.convert("RGBA")
        result = Image.alpha_composite(rgba, overlay)
        result = self._round_corners(result, 10)

        final = Image.new("RGB", result.size, (255, 255, 255))
        final.paste(result, mask=result.split()[3])

        return ImageTk.PhotoImage(final)

    def _crop_center(self, img: Image.Image, tw: int, th: int) -> Image.Image:
        w, h = img.size
        ratio = tw / th
        curr = w / h
        if curr > ratio:
            nw = int(h * ratio)
            left = (w - nw) // 2
            return img.crop((left, 0, left + nw, h))
        else:
            nh = int(w / ratio)
            top = (h - nh) // 2
            return img.crop((0, top, w, top + nh))

    def _round_corners(self, img: Image.Image, r: int) -> Image.Image:
        mask = Image.new("L", img.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle((0, 0, img.size[0], img.size[1]), radius=r, fill=255)
        out = Image.new("RGBA", img.size, (0, 0, 0, 0))
        out.paste(img, (0, 0))
        out.putalpha(mask)
        return out

    # ─── MOOD BOARD ───

    def _open_mood_board_dialog(self):
        """Ouvre le dialogue de génération de mood board."""
        goals = self.service.list_goals()

        dialog = MoodBoardDialog(self, service=self.service, goals=goals)
        self.wait_window(dialog)

        if dialog.result_items:
            self._apply_mood_board(dialog.result_items)

    def _open_add_image_dialog(self):
        """Ouvre le dialogue pour ajouter une image (Unsplash ou Upload)."""
        from ui.add_mood_image_dialog import AddMoodImageDialog

        def on_image_selected(path: str, title: str):
            """Callback quand une image est sélectionnée."""
            mood_id = self._next_mood_id
            self._next_mood_id -= 1

            # Position au centre du canvas visible
            x = self.canvas.canvasx(self.canvas.winfo_width() / 2) - 140
            y = self.canvas.canvasy(self.canvas.winfo_height() / 2) - 95

            vision_item = VisionItem(
                goal_id=mood_id,
                image_path=path,
                title=title,
                x=max(10, x),
                y=max(10, y),
                width=280,
                height=190,
                color="#3B82F6",
                rotation=0.0,
                is_mood_item=True
            )

            self.items[mood_id] = vision_item
            self._draw_item(vision_item)
            self._save()

            # Notification
            saved = ctk.CTkLabel(
                self, text=f"✓ Image ajoutée",
                font=ctk.CTkFont(size=11), text_color="#10B981",
                fg_color="#FFFFFF", corner_radius=6,
                width=120, height=26
            )
            saved.place(relx=0.5, rely=0.95, anchor="center")
            self.after(1500, saved.destroy)

        dialog = AddMoodImageDialog(self, on_image_selected=on_image_selected)
        self.wait_window(dialog)

    def _apply_mood_board(self, items: List[CollageItem]):
        """Applique les items générés au vision board."""
        # Supprimer les anciens mood items
        mood_ids = [k for k, v in self.items.items() if v.is_mood_item]
        for mid in mood_ids:
            item = self.items[mid]
            if item.canvas_id:
                self.canvas.delete(item.canvas_id)
            if item.shadow_id:
                self.canvas.delete(item.shadow_id)
            del self.items[mid]

        # Ajouter les nouveaux
        for collage_item in items:
            mood_id = self._next_mood_id
            self._next_mood_id -= 1

            vision_item = VisionItem(
                goal_id=mood_id,
                image_path=collage_item.image_path,
                title=collage_item.title,
                x=collage_item.x,
                y=collage_item.y,
                width=collage_item.width,
                height=collage_item.height,
                color=collage_item.color,
                rotation=collage_item.rotation,
                is_mood_item=True
            )

            self.items[mood_id] = vision_item
            self._draw_item(vision_item)

        # Sauvegarder
        self._save()

        # Notification
        saved = ctk.CTkLabel(
            self, text=f"✓ {len(items)} images générées",
            font=ctk.CTkFont(size=11), text_color="#10B981",
            fg_color="#FFFFFF", corner_radius=6,
            width=150, height=26
        )
        saved.place(relx=0.5, rely=0.95, anchor="center")
        self.after(2000, saved.destroy)

    def _add_floating_text(self):
        dialog = FloatingTextDialog(self)
        self.wait_window(dialog)

        if dialog.result is not None and "delete" not in dialog.result:
            x = self.canvas.canvasx(self.canvas.winfo_width() / 2) - 50
            y = self.canvas.canvasy(self.canvas.winfo_height() / 2) - 20

            text_obj = FloatingText(
                id=self._next_text_id,
                text=dialog.result["text"],
                x=x, y=y,
                style=dialog.result["style"]
            )
            self._next_text_id += 1
            self.texts[text_obj.id] = text_obj
            self._draw_text(text_obj)

    def _on_drag_start(self, event):
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        clicked = self.canvas.find_closest(cx, cy)
        if not clicked:
            return

        # Vérifier si on a cliqué sur un handle de redimensionnement
        for item in self.items.values():
            if item.is_mood_item and hasattr(item, 'resize_handles'):
                if clicked[0] in item.resize_handles:
                    self._resizing_item = item
                    self._resize_start_x = cx
                    self._resize_start_y = cy
                    self._resize_start_w = item.width
                    self._resize_start_h = item.height
                    return

        for text_obj in self.texts.values():
            if text_obj.canvas_id == clicked[0]:
                self._dragged_text = text_obj
                self._drag_offx = cx - text_obj.x
                self._drag_offy = cy - text_obj.y
                if text_obj.bg_id:
                    self.canvas.itemconfig(text_obj.bg_id, state="normal")
                return

        for item in self.items.values():
            if item.canvas_id == clicked[0]:
                self._dragged_item = item
                self._drag_offx = cx - item.x
                self._drag_offy = cy - item.y
                self.canvas.itemconfig(f"border_{item.goal_id}", state="normal")
                self.canvas.tag_raise(item.canvas_id)
                # Afficher les handles pour les mood items
                if item.is_mood_item:
                    self._show_resize_handles(item)
                return

    def _on_drag(self, event):
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)

        # Redimensionnement
        if hasattr(self, '_resizing_item') and self._resizing_item:
            item = self._resizing_item
            dx = cx - self._resize_start_x
            dy = cy - self._resize_start_y

            new_w = max(100, min(self._resize_start_w + dx, 600))
            new_h = max(80, min(self._resize_start_h + dy, 450))

            item.width = new_w
            item.height = new_h

            # Redessiner l'item
            self._redraw_item(item)
            return

        if hasattr(self, '_dragged_text') and self._dragged_text:
            text_obj = self._dragged_text
            new_x = max(0, min(cx - self._drag_offx, self.CANVAS_W - 50))
            new_y = max(0, min(cy - self._drag_offy, self.CANVAS_H - 30))
            dx = new_x - text_obj.x
            dy = new_y - text_obj.y
            self.canvas.move(text_obj.canvas_id, dx, dy)
            if text_obj.bg_id:
                self.canvas.move(text_obj.bg_id, dx, dy)
            text_obj.x = new_x
            text_obj.y = new_y
            return

        if hasattr(self, '_dragged_item') and self._dragged_item:
            item = self._dragged_item
            new_x = max(10, min(cx - self._drag_offx, self.CANVAS_W - item.width - 10))
            new_y = max(10, min(cy - self._drag_offy, self.CANVAS_H - item.height - 10))
            new_x = round(new_x / 50) * 50
            new_y = round(new_y / 50) * 50
            dx = new_x - item.x
            dy = new_y - item.y

            for tag in [item.shadow_id, item.canvas_id]:
                if tag:
                    self.canvas.move(tag, dx, dy)
            self.canvas.move(f"border_{item.goal_id}", dx, dy)

            # Déplacer aussi les handles
            if hasattr(item, 'resize_handles'):
                for handle_id in item.resize_handles:
                    self.canvas.move(handle_id, dx, dy)

            item.x = new_x
            item.y = new_y

    def _on_drag_stop(self, event):
        if hasattr(self, '_resizing_item') and self._resizing_item:
            self._hide_resize_handles(self._resizing_item)
            self._resizing_item = None

        if hasattr(self, '_dragged_text') and self._dragged_text:
            if self._dragged_text.bg_id:
                self.canvas.itemconfig(self._dragged_text.bg_id, state="hidden")
            self._dragged_text = None
        if hasattr(self, '_dragged_item') and self._dragged_item:
            self.canvas.itemconfig(f"border_{self._dragged_item.goal_id}", state="hidden")
            # Cacher les handles
            self._hide_resize_handles(self._dragged_item)
            self._dragged_item = None

    def _on_double_click(self, event):
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        clicked = self.canvas.find_closest(cx, cy)
        if not clicked:
            return

        for text_obj in self.texts.values():
            if text_obj.canvas_id == clicked[0]:
                self._edit_text(text_obj)
                return

        for item in self.items.values():
            if item.canvas_id == clicked[0]:
                if item.is_mood_item:
                    # Pour les mood items, on peut éditer le titre
                    self._edit_mood_item(item)
                else:
                    self._edit_image_text(item)
                return


    def _redraw_item(self, item: VisionItem):
        """Redessine un item après redimensionnement."""
        # Supprimer l'ancien rendu
        if item.canvas_id:
            self.canvas.delete(item.canvas_id)
        if item.shadow_id:
            self.canvas.delete(item.shadow_id)
        if hasattr(item, 'resize_handles'):
            for handle_id in item.resize_handles:
                self.canvas.delete(handle_id)

        # Supprimer la bordure
        self.canvas.delete(f"border_{item.goal_id}")

        # Redessiner
        self._draw_item(item)

        # Afficher les handles
        self._show_resize_handles(item)

    def _on_right_click(self, event):
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        clicked = self.canvas.find_closest(cx, cy)
        if not clicked:
            return

        for text_obj in self.texts.values():
            if text_obj.canvas_id == clicked[0]:
                menu = tk.Menu(self, tearoff=0, bg="#FFFFFF", fg="#1E293B",
                              activebackground="#EFF6FF", activeforeground="#3B82F6",
                              font=("Segoe UI", 11))
                menu.add_command(label="✏️ Éditer", command=lambda: self._edit_text(text_obj))
                menu.add_command(label="🗑️ Supprimer", command=lambda: self._delete_text(text_obj))
                menu.tk_popup(event.x_root, event.y_root)
                return

        for item in self.items.values():
            if item.canvas_id == clicked[0]:
                menu = tk.Menu(self, tearoff=0, bg="#FFFFFF", fg="#1E293B",
                              activebackground="#EFF6FF", activeforeground="#3B82F6",
                              font=("Segoe UI", 11))

                if item.is_mood_item:
                    menu.add_command(label="✏️ Renommer", command=lambda: self._edit_mood_item(item))
                    menu.add_command(label="↔️ Redimensionner", command=lambda: self._start_resize_mode(item))
                    menu.add_separator()
                    menu.add_command(label="🗑️ Supprimer", command=lambda: self._delete_item(item))
                else:
                    # Goal items : redimensionnable mais pas supprimable depuis ici
                    menu.add_command(label="✏️ Texte motivant", command=lambda: self._edit_image_text(item))
                    menu.add_command(label="↔️ Redimensionner", command=lambda: self._start_resize_mode(item))
                    menu.add_command(label="👁️ Voir le détail", command=lambda: self._show_goal_detail(item.goal_id))

                menu.tk_popup(event.x_root, event.y_root)
                return

    def _start_resize_mode(self, item: VisionItem):
        """Active le mode redimensionnement pour un mood item."""
        self._show_resize_handles(item)
        # Message temporaire
        hint = ctk.CTkLabel(
            self, 
            text="🖱️ Drag le coin bleu pour redimensionner",
            font=ctk.CTkFont(size=11), 
            text_color="#3B82F6",
            fg_color="#EFF6FF", 
            corner_radius=6,
            width=280, 
            height=28
        )
        hint.place(relx=0.5, rely=0.05, anchor="center")
        self.after(2500, hint.destroy)

    def _edit_text(self, text_obj: FloatingText):
        dialog = FloatingTextDialog(self, text_obj)
        self.wait_window(dialog)

        if dialog.result is None:
            return
        if "delete" in dialog.result:
            self._delete_text(text_obj)
            return

        text_obj.text = dialog.result["text"]
        text_obj.style = dialog.result["style"]
        self._draw_text(text_obj)

    def _delete_text(self, text_obj: FloatingText):
        if text_obj.canvas_id:
            self.canvas.delete(text_obj.canvas_id)
        if text_obj.bg_id:
            self.canvas.delete(text_obj.bg_id)
        del self.texts[text_obj.id]

    def _edit_mood_item(self, item: VisionItem):
        """Édite un item mood (titre simple)."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("✏️ Éditer")
        dialog.geometry("350x150")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        dialog.configure(fg_color="#FFFFFF")

        ctk.CTkLabel(dialog, text="Titre:", font=ctk.CTkFont(size=12, weight="bold")).pack(padx=20, pady=(15, 5), anchor="w")
        entry = ctk.CTkEntry(dialog, height=35)
        entry.pack(fill="x", padx=20, pady=5)
        entry.insert(0, item.title)

        def save():
            item.title = entry.get().strip()
            self._draw_item(item)
            dialog.destroy()

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=10)
        ctk.CTkButton(btn_frame, text="Annuler", command=dialog.destroy, width=90).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Sauvegarder", command=save, width=120, fg_color="#3B82F6").pack(side="right", padx=5)

    def _delete_item(self, item: VisionItem):
        """Supprime un item. Seuls les mood items peuvent être supprimés."""
        # 🛡️ PROTECTION : empêcher la suppression des goals
        if not item.is_mood_item:
            error = ctk.CTkLabel(
                self,
                text="⚠️ Les goals se suppriment depuis la vue détail",
                font=ctk.CTkFont(size=12),
                text_color="#DC2626",
                fg_color="#FEE2E2",
                corner_radius=8,
                width=350,
                height=32
            )
            error.place(relx=0.5, rely=0.95, anchor="center")
            self.after(2000, error.destroy)
            return

        # 🗑️ SUPPRESSION PHYSIQUE DU FICHIER
        file_deleted = False
        if item.image_path and os.path.exists(item.image_path):
            try:
                os.remove(item.image_path)
                file_deleted = True
            except Exception as e:
                print(f"⚠️ Impossible de supprimer le fichier: {e}")

        # Supprimer les éléments canvas
        if item.canvas_id:
            self.canvas.delete(item.canvas_id)
        if item.shadow_id:
            self.canvas.delete(item.shadow_id)
        if hasattr(item, 'resize_handles'):
            for handle_id in item.resize_handles:
                self.canvas.delete(handle_id)

        # Supprimer de la DB
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM vision_board_mood WHERE id = ?", (item.goal_id,))
                conn.commit()
        except Exception as e:
            print(f"Erreur suppression DB: {e}")

        # Supprimer de la mémoire
        if item.goal_id in self.items:
            del self.items[item.goal_id]

        # Notification
        msg = "✓ Image supprimée" if file_deleted else "✓ Image retirée (fichier conservé)"
        saved = ctk.CTkLabel(
            self, text=msg,
            font=ctk.CTkFont(size=11), text_color="#10B981",
            fg_color="#FFFFFF", corner_radius=6,
            width=250, height=26
        )
        saved.place(relx=0.5, rely=0.95, anchor="center")
        self.after(1500, saved.destroy)

    def _edit_image_text(self, item: VisionItem):
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"📝 {item.title}")
        dialog.geometry("400x180")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        dialog.configure(fg_color="#FFFFFF")

        ctk.CTkLabel(dialog, text="Texte motivant:", font=ctk.CTkFont(size=12, weight="bold"), text_color="#475569").pack(padx=20, pady=(15, 5), anchor="w")
        entry = ctk.CTkTextbox(dialog, height=50, wrap="word", corner_radius=8, border_width=1, border_color="#E2E8F0", fg_color="#F8FAFC", text_color="#1E293B", font=ctk.CTkFont(size=12))
        entry.pack(fill="x", padx=20, pady=5)
        entry.insert("0.0", getattr(item, 'motivation', ""))

        def save():
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO vision_board (goal_id, motivation_text)
                    VALUES (?, ?)
                    ON CONFLICT(goal_id) DO UPDATE SET motivation_text = excluded.motivation_text
                """, (item.goal_id, entry.get("0.0", "end").strip()))
                conn.commit()
            dialog.destroy()

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=10)
        ctk.CTkButton(btn_frame, text="Annuler", command=dialog.destroy, width=90, fg_color="#F1F5F9", hover_color="#E2E8F0", text_color="#475569").pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="💾 Sauvegarder", command=save, width=120, fg_color="#3B82F6", hover_color="#2563EB", text_color="#FFFFFF", font=ctk.CTkFont(size=12, weight="bold")).pack(side="right", padx=5)

    def _save(self):
        with self.db._get_connection() as conn:
            cursor = conn.cursor()

            # Goals
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vision_board (
                    goal_id INTEGER PRIMARY KEY,
                    motivation_text TEXT DEFAULT '',
                    pos_x REAL DEFAULT 0,
                    pos_y REAL DEFAULT 0,
                    width REAL DEFAULT 280,
                    height REAL DEFAULT 190,
                    FOREIGN KEY (goal_id) REFERENCES goals(id) ON DELETE CASCADE
                )
            """)
            for item in self.items.values():
                if not item.is_mood_item:
                    cursor.execute("""
                        INSERT INTO vision_board (goal_id, pos_x, pos_y, width, height)
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT(goal_id) DO UPDATE SET
                            pos_x = excluded.pos_x,
                            pos_y = excluded.pos_y,
                            width = excluded.width,
                            height = excluded.height
                    """, (item.goal_id, item.x, item.y, item.width, item.height))

            # Mood items
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vision_board_mood (
                    id INTEGER PRIMARY KEY,
                    image_path TEXT NOT NULL,
                    title TEXT DEFAULT '',
                    x REAL DEFAULT 100,
                    y REAL DEFAULT 100,
                    width REAL DEFAULT 280,
                    height REAL DEFAULT 190,
                    color TEXT DEFAULT '#3B82F6',
                    rotation REAL DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("DELETE FROM vision_board_mood")
            for item in self.items.values():
                if item.is_mood_item:
                    cursor.execute("""
                        INSERT INTO vision_board_mood (id, image_path, title, x, y, width, height, color, rotation)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (item.goal_id, item.image_path, item.title, item.x, item.y,
                          item.width, item.height, item.color, item.rotation))

            # Textes
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vision_board_texts (
                    id INTEGER PRIMARY KEY,
                    text TEXT NOT NULL,
                    x REAL DEFAULT 100,
                    y REAL DEFAULT 100,
                    font_family TEXT DEFAULT 'Arial',
                    font_size INTEGER DEFAULT 16,
                    bold INTEGER DEFAULT 0,
                    italic INTEGER DEFAULT 0,
                    color TEXT DEFAULT '#1E293B',
                    background TEXT,
                    opacity INTEGER DEFAULT 0
                )
            """)
            cursor.execute("DELETE FROM vision_board_texts")
            for text_obj in self.texts.values():
                cursor.execute("""
                    INSERT INTO vision_board_texts (id, text, x, y, font_family, font_size, bold, italic, color, background, opacity)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (text_obj.id, text_obj.text, text_obj.x, text_obj.y,
                      text_obj.style.font_family, text_obj.style.font_size,
                      int(text_obj.style.bold), int(text_obj.style.italic),
                      text_obj.style.color, text_obj.style.background, text_obj.style.opacity))

            conn.commit()

        saved = ctk.CTkLabel(
            self, text="✓ Sauvegardé",
            font=ctk.CTkFont(size=11), text_color="#10B981",
            fg_color="#FFFFFF", corner_radius=6,
            width=90, height=26
        )
        saved.place(relx=0.5, rely=0.95, anchor="center")
        self.after(1500, saved.destroy)