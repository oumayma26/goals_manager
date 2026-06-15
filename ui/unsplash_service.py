"""
ui/unsplash_service.py
Service pour récupérer des images depuis Unsplash/Pexels.
"""

import os
import json
import urllib.request
import urllib.parse
from pathlib import Path
from typing import List, Optional, Dict
from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib

# Charger les variables d'environnement depuis .env si python-dotenv est installé
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv non installé, utiliser les variables système


@dataclass
class UnsplashImage:
    """Représente une image récupérée."""
    id: str
    url_small: str
    url_regular: str
    url_full: str
    width: int
    height: int
    description: Optional[str]
    author: str
    author_url: str
    keywords: List[str]
    local_path: Optional[str] = None


class UnsplashService:
    """
    Service pour interagir avec l'API Unsplash.
    Nécessite une clé API (gratuite sur unsplash.com/developers).
    """

    BASE_URL = "https://api.unsplash.com"
    CACHE_DIR = Path("assets/unsplash_cache")
    CACHE_DURATION = timedelta(days=7)

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("UNSPLASH_API_KEY", "")
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def is_available(self) -> bool:
        """Vérifie si le service est configuré."""
        return bool(self.api_key)

    def search_images(
        self,
        query: str,
        per_page: int = 10,
        orientation: Optional[str] = None
    ) -> List[UnsplashImage]:
        """
        Cherche des images sur Unsplash.

        Args:
            query: Mots-clés de recherche
            per_page: Nombre d'images (max 30)
            orientation: 'landscape', 'portrait', 'squarish' ou None
        """
        if not self.is_available():
            return self._get_demo_images(query, per_page)

        # Vérifier le cache
        cache_key = hashlib.md5(f"{query}_{per_page}_{orientation}".encode()).hexdigest()
        cache_file = self.CACHE_DIR / f"{cache_key}.json"

        if cache_file.exists():
            cache_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
            if cache_age < self.CACHE_DURATION:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    return [UnsplashImage(**img) for img in data]

        # Appel API
        params = {
            "query": query,
            "per_page": min(per_page, 30),
            "client_id": self.api_key
        }
        if orientation:
            params["orientation"] = orientation

        url = f"{self.BASE_URL}/search/photos?{urllib.parse.urlencode(params)}"

        try:
            req = urllib.request.Request(url, headers={"Accept-Version": "v1"})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
        except Exception as e:
            print(f"Erreur API Unsplash: {e}")
            return self._get_demo_images(query, per_page)

        images = []
        for result in data.get("results", []):
            img = UnsplashImage(
                id=result["id"],
                url_small=result["urls"]["small"],
                url_regular=result["urls"]["regular"],
                url_full=result["urls"]["full"],
                width=result["width"],
                height=result["height"],
                description=result.get("description") or result.get("alt_description"),
                author=result["user"]["name"],
                author_url=result["user"]["links"]["html"],
                keywords=[query]
            )
            images.append(img)

        # Sauvegarder en cache
        with open(cache_file, 'w') as f:
            json.dump([{
                "id": img.id,
                "url_small": img.url_small,
                "url_regular": img.url_regular,
                "url_full": img.url_full,
                "width": img.width,
                "height": img.height,
                "description": img.description,
                "author": img.author,
                "author_url": img.author_url,
                "keywords": img.keywords
            } for img in images], f)

        return images

    def download_image(self, image: UnsplashImage, size: str = "regular") -> Optional[str]:
        """
        Télécharge une image localement.

        Returns:
            Chemin local de l'image téléchargée
        """
        if image.local_path and os.path.exists(image.local_path):
            return image.local_path

        url = getattr(image, f"url_{size}", image.url_regular)
        ext = ".jpg"
        filename = f"unsplash_{image.id}{ext}"
        local_path = self.CACHE_DIR / filename

        if local_path.exists():
            image.local_path = str(local_path)
            return str(local_path)

        try:
            req = urllib.request.Request(url, headers={
                "Authorization": f"Client-ID {self.api_key}"
            } if self.api_key else {})

            with urllib.request.urlopen(req, timeout=15) as response:
                with open(local_path, 'wb') as f:
                    f.write(response.read())

            image.local_path = str(local_path)
            return str(local_path)
        except Exception as e:
            print(f"Erreur téléchargement: {e}")
            return None

    def _get_demo_images(self, query: str, count: int) -> List[UnsplashImage]:
        """Images de démo si pas d'API key."""
        # Retourne des placeholders colorés basés sur le hash du query
        demo_images = []
        colors = ["#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#EC4899", "#06B6D4", "#84CC16"]

        for i in range(min(count, 8)):
            color = colors[i % len(colors)]
            demo_images.append(UnsplashImage(
                id=f"demo_{i}",
                url_small=f"https://via.placeholder.com/400x300/{color[1:]}/FFFFFF?text={urllib.parse.quote(query)}",
                url_regular=f"https://via.placeholder.com/800x600/{color[1:]}/FFFFFF?text={urllib.parse.quote(query)}",
                url_full=f"https://via.placeholder.com/1200x900/{color[1:]}/FFFFFF?text={urllib.parse.quote(query)}",
                width=800,
                height=600,
                description=f"Image de démo pour '{query}'",
                author="Demo",
                author_url="",
                keywords=[query]
            ))
        return demo_images


class PexelsService:
    """Alternative avec Pexels API."""

    BASE_URL = "https://api.pexels.com/v1"
    CACHE_DIR = Path("assets/pexels_cache")

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("PEXELS_API_KEY", "")
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def is_available(self) -> bool:
        return bool(self.api_key)

    def search_images(self, query: str, per_page: int = 10) -> List[UnsplashImage]:
        """Cherche sur Pexels."""
        if not self.is_available():
            return []

        cache_key = hashlib.md5(f"pexels_{query}_{per_page}".encode()).hexdigest()
        cache_file = self.CACHE_DIR / f"{cache_key}.json"

        if cache_file.exists():
            with open(cache_file, 'r') as f:
                data = json.load(f)
                return [UnsplashImage(**img) for img in data]

        url = f"{self.BASE_URL}/search?query={urllib.parse.quote(query)}&per_page={per_page}"

        try:
            req = urllib.request.Request(url, headers={
                "Authorization": self.api_key
            })
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
        except Exception as e:
            print(f"Erreur API Pexels: {e}")
            return []

        images = []
        for photo in data.get("photos", []):
            img = UnsplashImage(
                id=str(photo["id"]),
                url_small=photo["src"]["medium"],
                url_regular=photo["src"]["large"],
                url_full=photo["src"]["original"],
                width=photo["width"],
                height=photo["height"],
                description=photo.get("alt"),
                author=photo["photographer"],
                author_url=photo["photographer_url"],
                keywords=[query]
            )
            images.append(img)

        with open(cache_file, 'w') as f:
            json.dump([{
                "id": img.id,
                "url_small": img.url_small,
                "url_regular": img.url_regular,
                "url_full": img.url_full,
                "width": img.width,
                "height": img.height,
                "description": img.description,
                "author": img.author,
                "author_url": img.author_url,
                "keywords": img.keywords
            } for img in images], f)

        return images