"""
ui/add_mood_image_dialog.py
Dialogue pour ajouter une image au Mood Board.
2 options gratuites : Unsplash (recherche) ou Upload local.
"""

import os
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Optional, Callable, List
from tkinter import filedialog

import customtkinter as ctk
from PIL import Image, ImageTk

from ui.unsplash_service import UnsplashService


class AddMoodImageDialog(ctk.CTkToplevel):
    """
    Dialogue pour ajouter une image au Mood Board.
    Options gratuites : Unsplash ou Upload local.
    """

    def __init__(self, master, on_image_selected: Optional[Callable] = None):
        super().__init__(master)

        self.on_image_selected = on_image_selected
        self.selected_image_path: Optional[str] = None
        self.selected_title: str = ""

        self.title("✨ Ajouter une image")
        self.geometry("650x580")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        self.configure(fg_color="#FFFFFF")

        # Centrer
        self.update_idletasks()
        x = master.winfo_x() + (master.winfo_width() - 650) // 2
        y = master.winfo_y() + (master.winfo_height() - 580) // 2
        self.geometry(f"+{x}+{y}")

        self.unsplash = UnsplashService()
        self.search_results: List[dict] = []
        self._current_images: List[ImageTk.PhotoImage] = []
        self._downloaded_paths: List[str] = []  # Images téléchargées à nettoyer

        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # ─── HEADER ───
        header = ctk.CTkFrame(self, fg_color="transparent", height=60)
        header.grid(row=0, column=0, sticky="ew", padx=25, pady=(20, 10))
        header.grid_propagate(False)

        ctk.CTkLabel(
            header,
            text="✨ Ajouter une image au Mood Board",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#1E293B"
        ).pack(side="left")

        # ─── TABS ───
        self.tabview = ctk.CTkTabview(
            self,
            fg_color="#F8FAFC",
            segmented_button_fg_color="#F1F5F9",
            segmented_button_selected_color="#3B82F6",
            segmented_button_selected_hover_color="#2563EB",
            segmented_button_unselected_color="#FFFFFF",
            segmented_button_unselected_hover_color="#F1F5F9",
            text_color="#475569",
            command=self._on_tab_changed
        )
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=25, pady=(0, 10))

        # Tab 1 : Unsplash
        self.tab_unsplash = self.tabview.add("📷 Unsplash")
        self._build_unsplash_tab()

        # Tab 2 : Upload
        self.tab_upload = self.tabview.add("🖼️ Mon image")
        self._build_upload_tab()

        # ─── BOUTONS ───
        btn_frame = ctk.CTkFrame(self, fg_color="#FFFFFF", corner_radius=0, height=70)
        btn_frame.grid(row=2, column=0, sticky="ew", padx=25, pady=(0, 20))
        btn_frame.grid_propagate(False)
        btn_frame.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkFrame(btn_frame, height=1, fg_color="#E2E8F0").grid(
            row=0, column=0, columnspan=2, sticky="ew", pady=(0, 15)
        )

        ctk.CTkButton(
            btn_frame,
            text="Annuler",
            command=self.destroy,
            height=42,
            corner_radius=8,
            fg_color="#F1F5F9",
            hover_color="#E2E8F0",
            text_color="#475569",
            font=ctk.CTkFont(size=12, weight="bold")
        ).grid(row=1, column=0, sticky="ew", padx=(0, 8))

        self.add_btn = ctk.CTkButton(
            btn_frame,
            text="➕ Ajouter",
            command=self._on_add,
            height=42,
            corner_radius=8,
            fg_color="#3B82F6",
            hover_color="#2563EB",
            text_color="#FFFFFF",
            font=ctk.CTkFont(size=13, weight="bold"),
            state="disabled"
        )
        self.add_btn.grid(row=1, column=1, sticky="ew", padx=(8, 0))

    # ═══════════════════════════════════════════════════
    # TAB UNSPLASH
    # ═══════════════════════════════════════════════════

    def _build_unsplash_tab(self):
        self.tab_unsplash.grid_columnconfigure(0, weight=1)
        self.tab_unsplash.grid_rowconfigure(2, weight=1)

        # Barre de recherche
        search_frame = ctk.CTkFrame(self.tab_unsplash, fg_color="transparent")
        search_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 10))
        search_frame.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="🔍 Mots-clés (ex: fitness, nature, motivation...)",
            height=40,
            corner_radius=8,
            border_width=1,
            border_color="#E2E8F0",
            fg_color="#FFFFFF",
            text_color="#1E293B",
            font=ctk.CTkFont(size=12)
        )
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.search_entry.bind("<Return>", lambda e: self._search_unsplash())

        ctk.CTkButton(
            search_frame,
            text="🔍",
            width=40,
            height=40,
            corner_radius=8,
            fg_color="#3B82F6",
            hover_color="#2563EB",
            text_color="#FFFFFF",
            font=ctk.CTkFont(size=14),
            command=self._search_unsplash
        ).grid(row=0, column=1)

        # Message info
        self.unsplash_info = ctk.CTkLabel(
            self.tab_unsplash,
            text="Recherchez des images gratuites sur Unsplash\n(50 requêtes/heure)",
            font=ctk.CTkFont(size=11),
            text_color="#94A3B8"
        )
        self.unsplash_info.grid(row=1, column=0, pady=(0, 10))

        # Résultats
        self.results_scroll = ctk.CTkScrollableFrame(
            self.tab_unsplash,
            fg_color="transparent",
            label_text=""
        )
        self.results_scroll.grid(row=2, column=0, sticky="nsew", padx=15, pady=(0, 15))

        # Frame pour les résultats (grid 3 colonnes)
        self.results_grid = ctk.CTkFrame(self.results_scroll, fg_color="transparent")
        self.results_grid.pack(fill="both", expand=True)

    def _search_unsplash(self):
        """Recherche des images sur Unsplash."""
        query = self.search_entry.get().strip()
        if not query:
            self.unsplash_info.configure(text="❌ Veuillez entrer des mots-clés", text_color="#EF4444")
            return

        self.unsplash_info.configure(text="⏳ Recherche en cours...", text_color="#3B82F6")
        self.update()

        try:
            images = self.unsplash.search_images(query, per_page=9)
            self._display_results(images, query)
        except Exception as e:
            self.unsplash_info.configure(text=f"❌ Erreur: {str(e)[:50]}", text_color="#EF4444")

    def _display_results(self, images, query: str):
        """Affiche les résultats de recherche."""
        # 🧹 Nettoyer les anciennes images physiques
        self._cleanup_downloaded()

        # Vider les anciens résultats UI
        for widget in self.results_grid.winfo_children():
            widget.destroy()
        self._current_images.clear()
        self._downloaded_paths.clear()

        if not images:
            self.unsplash_info.configure(
                text="Aucun résultat. Essayez d'autres mots-clés.",
                text_color="#94A3B8"
            )
            return

        self.unsplash_info.configure(
            text=f"✅ {len(images)} images trouvées pour '{query}'",
            text_color="#10B981"
        )

        # Afficher en grille 3 colonnes
        for i, img_data in enumerate(images):
            row = i // 3
            col = i % 3

            self._create_result_card(img_data, row, col)

    def _create_result_card(self, img_data, row: int, col: int):
        """Crée une card de résultat cliquable."""
        card = ctk.CTkFrame(
            self.results_grid,
            fg_color="#FFFFFF",
            corner_radius=12,
            border_width=2,
            border_color="#E2E8F0",
            width=170,
            height=130
        )
        card.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
        card.grid_propagate(False)

        # Télécharger et afficher l'image
        try:
            local_path = self.unsplash.download_image(img_data, size="small")
            if local_path and os.path.exists(local_path):
                img = Image.open(local_path)
                img.thumbnail((160, 120))
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)

                label = ctk.CTkLabel(card, text="", image=ctk_img)
                label.pack(expand=True)
                self._current_images.append(ctk_img)

                # Tracker le path pour nettoyage futur
                if local_path and local_path not in self._downloaded_paths:
                    self._downloaded_paths.append(local_path)

                # Clic pour sélectionner
                card.bind("<Button-1>", lambda e, p=local_path, t=img_data.description or "Image": self._select_unsplash(p, t, card))
                label.bind("<Button-1>", lambda e, p=local_path, t=img_data.description or "Image": self._select_unsplash(p, t, card))
                card.configure(cursor="hand2")
        except Exception as e:
            ctk.CTkLabel(card, text=f"Erreur\n{str(e)[:20]}", font=ctk.CTkFont(size=9), text_color="#EF4444").pack(expand=True)

    def _select_unsplash(self, path: str, title: str, card):
        """Sélectionne une image Unsplash."""
        self.selected_image_path = path
        self.selected_title = title

        # Reset les bordures
        for widget in self.results_grid.winfo_children():
            widget.configure(border_color="#E2E8F0")

        # Highlight la sélection
        card.configure(border_color="#3B82F6", border_width=3)

        self.add_btn.configure(state="normal", text=f"➕ Ajouter '{title[:20]}...'")

        # 🧹 Supprimer les autres images physiques (garder seulement la sélection)
        self._cleanup_except_selected()

    # ═══════════════════════════════════════════════════
    # TAB UPLOAD
    # ═══════════════════════════════════════════════════

    def _build_upload_tab(self):
        self.tab_upload.grid_columnconfigure(0, weight=1)
        self.tab_upload.grid_rowconfigure(1, weight=1)

        # Bouton upload
        upload_btn = ctk.CTkButton(
            self.tab_upload,
            text="📁 Choisir une image",
            command=self._browse_image,
            height=45,
            corner_radius=10,
            fg_color="#3B82F6",
            hover_color="#2563EB",
            text_color="#FFFFFF",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        upload_btn.grid(row=0, column=0, pady=(20, 10))

        # Info
        self.upload_info = ctk.CTkLabel(
            self.tab_upload,
            text="Formats supportés : PNG, JPG, JPEG, GIF, BMP",
            font=ctk.CTkFont(size=11),
            text_color="#94A3B8"
        )
        self.upload_info.grid(row=1, column=0, pady=(0, 10))

        # Aperçu
        self.preview_frame = ctk.CTkFrame(
            self.tab_upload,
            fg_color="#F8FAFC",
            corner_radius=12,
            height=300
        )
        self.preview_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.preview_frame.grid_propagate(False)

        self.preview_label = ctk.CTkLabel(
            self.preview_frame,
            text="Aucune image sélectionnée",
            font=ctk.CTkFont(size=12),
            text_color="#94A3B8"
        )
        self.preview_label.pack(expand=True)

    def _browse_image(self):
        """Ouvre un sélecteur de fichier."""
        filetypes = [
            ("Images", "*.png *.jpg *.jpeg *.gif *.bmp"),
            ("PNG", "*.png"),
            ("JPEG", "*.jpg *.jpeg"),
            ("Tous fichiers", "*.*")
        ]
        path = filedialog.askopenfilename(
            title="Choisir une image",
            filetypes=filetypes
        )

        if path:
            self._load_preview(path)

    def _load_preview(self, path: str):
        """Charge l'aperçu de l'image."""
        try:
            img = Image.open(path)
            img.thumbnail((350, 280))
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)

            self.preview_label.configure(text="", image=ctk_img)
            self.preview_label.image = ctk_img  # Garder référence

            self.selected_image_path = path
            self.selected_title = Path(path).stem

            self.upload_info.configure(
                text=f"✅ {Path(path).name} ({img.size[0]}×{img.size[1]}px)",
                text_color="#10B981"
            )
            self.add_btn.configure(state="normal", text="➕ Ajouter mon image")

        except Exception as e:
            self.upload_info.configure(text=f"❌ Erreur: {str(e)[:50]}", text_color="#EF4444")

    # ═══════════════════════════════════════════════════
    # COMMUN
    # ═══════════════════════════════════════════════════

    def _on_tab_changed(self):
        """Appelé quand on change d'onglet."""
        self.selected_image_path = None
        self.selected_title = ""
        self.add_btn.configure(state="disabled", text="➕ Ajouter")

    def _on_add(self):
        """Ajoute l'image sélectionnée."""
        if self.selected_image_path and self.on_image_selected:
            # 📁 Copier l'image dans assets/mood_images/ avant de nettoyer
            final_path = self._copy_to_assets(self.selected_image_path)

            if final_path and os.path.exists(final_path):
                # ✅ Copie réussie, utiliser le nouveau path
                self.on_image_selected(final_path, self.selected_title)
                # 🧹 Nettoyer les temporaires (l'originale est dans assets/)
                self._cleanup_downloaded()
            else:
                # ⚠️ Copie échouée, garder l'original
                print("⚠️ Copie échouée, utilisation du path original")
                self.on_image_selected(self.selected_image_path, self.selected_title)
                # Ne pas nettoyer pour garder l'image
        else:
            # Pas de sélection, nettoyer tout
            self._cleanup_downloaded()

        self.destroy()

    def _copy_to_assets(self, source_path: str) -> Optional[str]:
        """Copie l'image dans assets/mood_images/ et retourne le path absolu."""
        try:
            import shutil
            from pathlib import Path

            # Créer le dossier s'il n'existe pas (path absolu)
            assets_dir = Path(os.getcwd()) / "assets" / "mood_images"
            assets_dir.mkdir(parents=True, exist_ok=True)

            # Générer un nom unique
            import uuid
            ext = Path(source_path).suffix or ".jpg"
            filename = f"mood_{uuid.uuid4().hex[:8]}{ext}"
            dest_path = assets_dir / filename

            # Copier
            shutil.copy2(source_path, dest_path)

            # Retourner le path absolu
            return str(dest_path.resolve())
        except Exception as e:
            print(f"⚠️ Erreur copie vers assets: {e}")
            return None

    def _cleanup_downloaded(self):
        """Supprime toutes les images téléchargées et leurs caches JSON."""
        deleted = 0
        for path in self._downloaded_paths:
            if os.path.exists(path):
                try:
                    os.remove(path)
                    deleted += 1
                except Exception as e:
                    print(f"⚠️ Impossible de supprimer {path}: {e}")

        # 🧹 Supprimer aussi les fichiers JSON de cache Unsplash
        try:
            import glob
            cache_dir = Path("assets/unsplash_cache")
            if cache_dir.exists():
                for json_file in cache_dir.glob("*.json"):
                    try:
                        json_file.unlink()
                    except:
                        pass
        except:
            pass

        if deleted > 0:
            print(f"🧹 {deleted} images temporaires supprimées")
        self._downloaded_paths.clear()

    def _cleanup_except_selected(self):
        """Supprime les images non sélectionnées, garde la sélection."""
        deleted = 0
        for path in self._downloaded_paths:
            if path != self.selected_image_path and os.path.exists(path):
                try:
                    os.remove(path)
                    deleted += 1
                except Exception as e:
                    print(f"⚠️ Impossible de supprimer {path}: {e}")
        if deleted > 0:
            print(f"🧹 {deleted} images non sélectionnées supprimées")
        # Garder seulement la sélection dans la liste
        self._downloaded_paths = [p for p in self._downloaded_paths if p == self.selected_image_path]