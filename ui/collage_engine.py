"""
ui/collage_engine.py
Algorithme de génération de collage esthétique.
Implémente plusieurs layouts : grid, masonry, polaroid, wheel.
"""

import random
import math
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
from enum import Enum


class LayoutType(Enum):
    GRID = "grid"           # Grille régulière
    MASONRY = "masonry"     # Pinterest-style
    POLAROID = "polaroid"   # Photos avec rotation
    WHEEL = "wheel"         # Roue de la vie
    FREEFORM = "freeform"   # Placement aléatoire organique
    SPIRAL = "spiral"       # Spirale dorée


@dataclass
class CollageItem:
    """Item positionné dans le collage."""
    image_path: str
    x: float
    y: float
    width: float
    height: float
    rotation: float = 0.0
    z_index: int = 0
    title: str = ""
    color: str = "#3B82F6"


@dataclass
class CollageConfig:
    """Configuration du collage."""
    layout: LayoutType = LayoutType.MASONRY
    canvas_width: float = 2000
    canvas_height: float = 1400
    padding: float = 20
    item_min_width: float = 200
    item_max_width: float = 400
    item_aspect_ratio: float = 4/3  # width/height
    random_seed: Optional[int] = None
    shuffle: bool = True
    add_shadows: bool = True
    add_borders: bool = True
    border_width: float = 8
    polaroid_caption: bool = True


class CollageEngine:
    """
    Moteur de génération de collage esthétique.
    """

    def __init__(self, config: Optional[CollageConfig] = None):
        self.config = config or CollageConfig()
        if self.config.random_seed is not None:
            random.seed(self.config.random_seed)

    def generate(
        self,
        image_paths: List[str],
        titles: Optional[List[str]] = None,
        colors: Optional[List[str]] = None
    ) -> List[CollageItem]:
        """
        Génère un collage à partir d'une liste d'images.

        Args:
            image_paths: Chemins des images
            titles: Titres optionnels pour chaque image
            colors: Couleurs optionnelles pour chaque image

        Returns:
            Liste des items positionnés
        """
        if not image_paths:
            return []

        titles = titles or [""] * len(image_paths)
        colors = colors or ["#3B82F6"] * len(image_paths)

        if self.config.shuffle:
            combined = list(zip(image_paths, titles, colors))
            random.shuffle(combined)
            image_paths, titles, colors = zip(*combined) if combined else ([], [], [])
            image_paths, titles, colors = list(image_paths), list(titles), list(colors)

        layout_method = {
            LayoutType.GRID: self._layout_grid,
            LayoutType.MASONRY: self._layout_masonry,
            LayoutType.POLAROID: self._layout_polaroid,
            LayoutType.WHEEL: self._layout_wheel,
            LayoutType.FREEFORM: self._layout_freeform,
            LayoutType.SPIRAL: self._layout_spiral,
        }

        method = layout_method.get(self.config.layout, self._layout_masonry)
        return method(image_paths, titles, colors)

    def _layout_grid(
        self,
        image_paths: List[str],
        titles: List[str],
        colors: List[str]
    ) -> List[CollageItem]:
        """Layout en grille régulière."""
        n = len(image_paths)
        cols = math.ceil(math.sqrt(n * 1.4))  # Ratio 1.4 pour un rectangle plutôt que carré
        rows = math.ceil(n / cols)

        available_w = self.config.canvas_width - 2 * self.config.padding
        available_h = self.config.canvas_height - 2 * self.config.padding

        cell_w = (available_w - (cols - 1) * self.config.padding) / cols
        cell_h = (available_h - (rows - 1) * self.config.padding) / rows

        items = []
        for i, (path, title, color) in enumerate(zip(image_paths, titles, colors)):
            row = i // cols
            col = i % cols

            x = self.config.padding + col * (cell_w + self.config.padding)
            y = self.config.padding + row * (cell_h + self.config.padding)

            # Ajuster la taille pour garder le ratio
            item_w = cell_w
            item_h = item_w / self.config.item_aspect_ratio

            if item_h > cell_h:
                item_h = cell_h
                item_w = item_h * self.config.item_aspect_ratio

            # Centrer dans la cellule
            x += (cell_w - item_w) / 2
            y += (cell_h - item_h) / 2

            items.append(CollageItem(
                image_path=path,
                x=x, y=y,
                width=item_w, height=item_h,
                title=title, color=color,
                z_index=i
            ))

        return items

    def _layout_masonry(
        self,
        image_paths: List[str],
        titles: List[str],
        colors: List[str]
    ) -> List[CollageItem]:
        """Layout Pinterest-style avec colonnes de hauteurs variables."""
        n = len(image_paths)
        cols = max(3, min(5, n // 2 + 1))  # 3-5 colonnes selon le nombre d'images

        available_w = self.config.canvas_width - 2 * self.config.padding
        col_width = (available_w - (cols - 1) * self.config.padding) / cols

        col_heights = [self.config.padding] * cols
        items = []

        for i, (path, title, color) in enumerate(zip(image_paths, titles, colors)):
            # Choisir la colonne la plus courte
            min_col = col_heights.index(min(col_heights))

            # Hauteur variable pour l'effet masonry
            base_height = col_width / self.config.item_aspect_ratio
            height_variation = random.uniform(0.7, 1.3)
            item_h = base_height * height_variation
            item_w = col_width

            x = self.config.padding + min_col * (col_width + self.config.padding)
            y = col_heights[min_col]

            col_heights[min_col] += item_h + self.config.padding

            items.append(CollageItem(
                image_path=path,
                x=x, y=y,
                width=item_w, height=item_h,
                title=title, color=color,
                z_index=i
            ))

        return items

    def _layout_polaroid(
        self,
        image_paths: List[str],
        titles: List[str],
        colors: List[str]
    ) -> List[CollageItem]:
        """Layout style Polaroid avec rotation aléatoire."""
        n = len(image_paths)

        # Taille fixe des polaroids
        polaroid_w = 280
        polaroid_h = 340  # + espace pour la légende
        photo_h = 260

        items = []

        # Disposition en grille légèrement désorganisée
        cols = max(3, math.ceil(math.sqrt(n * 1.5)))
        available_w = self.config.canvas_width - 2 * self.config.padding
        start_x = self.config.padding + (available_w - cols * polaroid_w) / 2

        for i, (path, title, color) in enumerate(zip(image_paths, titles, colors)):
            row = i // cols
            col = i % cols

            # Position de base avec offset aléatoire
            base_x = start_x + col * (polaroid_w + 30)
            base_y = self.config.padding + row * (polaroid_h + 40)

            # Rotation aléatoire subtile (-8° à +8°)
            rotation = random.uniform(-8, 8)

            # Légère translation aléatoire
            offset_x = random.uniform(-15, 15)
            offset_y = random.uniform(-10, 10)

            x = base_x + offset_x
            y = base_y + offset_y

            items.append(CollageItem(
                image_path=path,
                x=x, y=y,
                width=polaroid_w, height=photo_h,
                rotation=rotation,
                title=title, color=color,
                z_index=i
            ))

        return items

    def _layout_wheel(
        self,
        image_paths: List[str],
        titles: List[str],
        colors: List[str]
    ) -> List[CollageItem]:
        """Layout en roue de la vie (cercle)."""
        n = len(image_paths)
        center_x = self.config.canvas_width / 2
        center_y = self.config.canvas_height / 2

        # Rayon du cercle
        radius = min(self.config.canvas_width, self.config.canvas_height) * 0.35

        item_size = min(200, radius * 0.5)

        items = []
        for i, (path, title, color) in enumerate(zip(image_paths, titles, colors)):
            angle = (2 * math.pi * i) / n - math.pi / 2  # Commencer en haut

            x = center_x + radius * math.cos(angle) - item_size / 2
            y = center_y + radius * math.sin(angle) - item_size / 2

            items.append(CollageItem(
                image_path=path,
                x=x, y=y,
                width=item_size, height=item_size,
                title=title, color=color,
                z_index=i
            ))

        return items

    def _layout_freeform(
        self,
        image_paths: List[str],
        titles: List[str],
        colors: List[str]
    ) -> List[CollageItem]:
        """Placement organique aléatoire avec évitement de collision."""
        items = []
        placed_rects = []

        for i, (path, title, color) in enumerate(zip(image_paths, titles, colors)):
            item_w = random.uniform(self.config.item_min_width, self.config.item_max_width)
            item_h = item_w / random.uniform(1.2, 1.8)  # Ratio variable

            max_attempts = 100
            placed = False

            for _ in range(max_attempts):
                x = random.uniform(
                    self.config.padding,
                    self.config.canvas_width - item_w - self.config.padding
                )
                y = random.uniform(
                    self.config.padding,
                    self.config.canvas_height - item_h - self.config.padding
                )

                # Vérifier collision
                new_rect = (x, y, x + item_w, y + item_h)
                collision = False

                for rect in placed_rects:
                    if self._rects_overlap(new_rect, rect, margin=20):
                        collision = True
                        break

                if not collision:
                    placed_rects.append(new_rect)
                    items.append(CollageItem(
                        image_path=path,
                        x=x, y=y,
                        width=item_w, height=item_h,
                        rotation=random.uniform(-5, 5),
                        title=title, color=color,
                        z_index=i
                    ))
                    placed = True
                    break

            if not placed:
                # Fallback : placement en grille si collision impossible
                cols = 4
                col = i % cols
                row = i // cols
                x = self.config.padding + col * (self.config.canvas_width - 2 * self.config.padding) / cols
                y = self.config.padding + row * 300
                items.append(CollageItem(
                    image_path=path,
                    x=x, y=y,
                    width=item_w, height=item_h,
                    title=title, color=color,
                    z_index=i
                ))

        return items

    def _layout_spiral(
        self,
        image_paths: List[str],
        titles: List[str],
        colors: List[str]
    ) -> List[CollageItem]:
        """Spirale dorée (Fibonacci)."""
        n = len(image_paths)
        center_x = self.config.canvas_width / 2
        center_y = self.config.canvas_height / 2

        golden_angle = math.pi * (3 - math.sqrt(5))  # ~137.5°

        items = []
        for i, (path, title, color) in enumerate(zip(image_paths, titles, colors)):
            # Distance croissante avec la racine carrée pour uniformité
            radius = 30 * math.sqrt(i + 1)
            angle = i * golden_angle

            # Taille décroissante vers l'extérieur
            size = max(150, 300 - i * 8)

            x = center_x + radius * math.cos(angle) - size / 2
            y = center_y + radius * math.sin(angle) - size / 2

            items.append(CollageItem(
                image_path=path,
                x=x, y=y,
                width=size, height=size,
                title=title, color=color,
                z_index=n - i  # Centre au-dessus
            ))

        return items

    @staticmethod
    def _rects_overlap(
        rect1: Tuple[float, float, float, float],
        rect2: Tuple[float, float, float, float],
        margin: float = 0
    ) -> bool:
        """Vérifie si deux rectangles se chevauchent."""
        x1_min, y1_min, x1_max, y1_max = rect1
        x2_min, y2_min, x2_max, y2_max = rect2

        return not (
            x1_max + margin < x2_min or
            x2_max + margin < x1_min or
            y1_max + margin < y2_min or
            y2_max + margin < y1_min
        )


class MoodBoardGenerator:
    """
    Générateur de mood board complet avec images Unsplash + goals existants.
    """

    def __init__(self, unsplash_service, collage_engine: CollageEngine):
        self.unsplash = unsplash_service
        self.engine = collage_engine

    def generate_from_goals(
        self,
        goals,
        images_per_goal: int = 2,
        layout: LayoutType = LayoutType.MASONRY
    ) -> Tuple[List[CollageItem], List[str]]:
        """
        Génère un mood board à partir des goals existants.

        Returns:
            (items, warnings)
        """
        all_images = []
        all_titles = []
        all_colors = []
        warnings = []

        for goal in goals:
            # Images existantes du goal
            if hasattr(goal, 'image_path') and goal.image_path:
                all_images.append(goal.image_path)
                all_titles.append(goal.title)
                all_colors.append(getattr(goal, 'color', '#3B82F6'))

            # Images Unsplash basées sur le titre
            try:
                keywords = goal.title.split()[:3]  # 3 premiers mots
                query = " ".join(keywords)
                unsplash_images = self.unsplash.search_images(query, per_page=images_per_goal)

                for img in unsplash_images:
                    local_path = self.unsplash.download_image(img, size="regular")
                    if local_path:
                        all_images.append(local_path)
                        all_titles.append(goal.title)
                        all_colors.append(getattr(goal, 'color', '#3B82F6'))
            except Exception as e:
                warnings.append(f"Erreur recherche pour '{goal.title}': {e}")

        if not all_images:
            warnings.append("Aucune image trouvée. Vérifiez votre connexion ou clé API.")
            return [], warnings

        self.engine.config.layout = layout
        items = self.engine.generate(all_images, all_titles, all_colors)

        return items, warnings