"""
database.py
Couche d'accès aux données SQLite.
"""

import sqlite3
import os
from typing import Optional
from contextlib import contextmanager
from datetime import datetime, timedelta


class DatabaseManager:
    """
    Gestionnaire singleton de la base de données SQLite.
    """

    def __init__(self, db_path: str = "database.db") -> None:
        self.db_path: str = db_path
        self._init_database()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def _init_database(self) -> None:
        """Initialise le schéma de la base de données."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS goals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    target_date TEXT,
                    priority TEXT NOT NULL DEFAULT 'Moyenne' 
                        CHECK(priority IN ('Faible', 'Moyenne', 'Haute')),
                    status TEXT NOT NULL DEFAULT 'Non commencé'
                        CHECK(status IN ('Non commencé', 'En cours', 'Terminé')),
                    color TEXT DEFAULT '#3B82F6',
                    image_path TEXT,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    goal_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    status TEXT NOT NULL DEFAULT 'À faire'
                        CHECK(status IN ('À faire', 'En cours', 'Terminée')),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (goal_id) REFERENCES goals(id) ON DELETE CASCADE
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vision_board (
                    goal_id INTEGER PRIMARY KEY,
                    motivation_text TEXT DEFAULT '',
                    pos_x REAL DEFAULT 0,
                    pos_y REAL DEFAULT 0,
                    width INTEGER DEFAULT 300,
                    height INTEGER DEFAULT 220,
                    font_size INTEGER DEFAULT 13,
                    text_position TEXT DEFAULT 'bottom',
                    text_color TEXT DEFAULT '#FFFFFF',
                    text_bold INTEGER DEFAULT 1,
                    celebrated INTEGER DEFAULT 0,
                    FOREIGN KEY (goal_id) REFERENCES goals(id) ON DELETE CASCADE
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_goal_id ON tasks(goal_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_goals_status ON goals(status)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_goals_priority ON goals(priority)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_goals_created_at ON goals(created_at)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_updated_at ON tasks(updated_at)
            """)

            # Migration : ajouter colonne color si elle n'existe pas (pour DB existante)
            try:
                cursor.execute("SELECT color FROM goals LIMIT 1")
            except sqlite3.OperationalError:
                cursor.execute("ALTER TABLE goals ADD COLUMN color TEXT DEFAULT '#3B82F6'")
                cursor.execute("ALTER TABLE goals ADD COLUMN image_path TEXT")
                conn.commit()

            conn.commit()
            print(f"✅ Base de données initialisée : {self.db_path}")

    def create_goal(
        self,
        title: str,
        description: str = "",
        target_date: Optional[str] = None,
        priority: str = "Moyenne",
        status: str = "Non commencé",
        color: str = "#3B82F6",
        image_path: Optional[str] = None
    ) -> int:
        """Crée un nouveau goal et retourne son ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            cursor.execute("""
                INSERT INTO goals (title, description, target_date, priority, status, color, image_path, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (title, description, target_date, priority, status, color, image_path, now, now))
            return cursor.lastrowid

    def get_goal_by_id(self, goal_id: int) -> Optional[sqlite3.Row]:
        """Récupère un goal par son ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM goals WHERE id = ?", (goal_id,))
            return cursor.fetchone()

    def get_all_goals(
        self,
        status_filter: Optional[str] = None,
        priority_filter: Optional[str] = None,
        search_query: Optional[str] = None,
        exclude_status: Optional[str] = None
    ) -> list[sqlite3.Row]:
        """
        Récupère tous les goals avec filtres optionnels.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM goals WHERE 1=1"
            params: list = []

            if status_filter:
                query += " AND status = ?"
                params.append(status_filter)
            if exclude_status:
                query += " AND status != ?"
                params.append(exclude_status)
            if priority_filter:
                query += " AND priority = ?"
                params.append(priority_filter)
            if search_query:
                query += " AND (title LIKE ? OR description LIKE ?)"
                params.extend([f"%{search_query}%", f"%{search_query}%"])

            query += " ORDER BY created_at DESC"
            cursor.execute(query, params)
            return cursor.fetchall()

    def update_goal(
        self,
        goal_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        target_date: Optional[str] = None,
        priority: Optional[str] = None,
        status: Optional[str] = None,
        color: Optional[str] = None,
        image_path: Optional[str] = None
    ) -> bool:
        """Met à jour un goal existant."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            updates = []
            params = []

            if title is not None:
                updates.append("title = ?")
                params.append(title)
            if description is not None:
                updates.append("description = ?")
                params.append(description)
            if target_date is not None:
                updates.append("target_date = ?")
                params.append(target_date)
            if priority is not None:
                updates.append("priority = ?")
                params.append(priority)
            if status is not None:
                updates.append("status = ?")
                params.append(status)
            if color is not None:
                updates.append("color = ?")
                params.append(color)
            if image_path is not None:
                updates.append("image_path = ?")
                params.append(image_path)

            if not updates:
                return False

            updates.append("updated_at = ?")
            params.append(datetime.now().isoformat())
            params.append(goal_id)

            query = f"UPDATE goals SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, params)
            return cursor.rowcount > 0

    def delete_goal(self, goal_id: int) -> bool:
        """Supprime un goal et toutes ses tâches associées."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM goals WHERE id = ?", (goal_id,))
            return cursor.rowcount > 0

    def create_task(
        self,
        goal_id: int,
        name: str,
        description: str = "",
        status: str = "À faire"
    ) -> int:
        """Crée une nouvelle tâche."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            cursor.execute("""
                INSERT INTO tasks (goal_id, name, description, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (goal_id, name, description, status, now, now))
            return cursor.lastrowid

    def get_task_by_id(self, task_id: int) -> Optional[sqlite3.Row]:
        """Récupère une tâche par son ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            return cursor.fetchone()

    def get_tasks_by_goal_id(self, goal_id: int) -> list[sqlite3.Row]:
        """Récupère toutes les tâches d'un goal."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM tasks WHERE goal_id = ? ORDER BY created_at",
                (goal_id,)
            )
            return cursor.fetchall()

    def update_task(
        self,
        task_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None
    ) -> bool:
        """Met à jour une tâche."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            updates = []
            params = []

            if name is not None:
                updates.append("name = ?")
                params.append(name)
            if description is not None:
                updates.append("description = ?")
                params.append(description)
            if status is not None:
                updates.append("status = ?")
                params.append(status)

            if not updates:
                return False

            updates.append("updated_at = ?")
            params.append(datetime.now().isoformat())
            params.append(task_id)

            query = f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, params)
            return cursor.rowcount > 0

    def delete_task(self, task_id: int) -> bool:
        """Supprime une tâche."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            return cursor.rowcount > 0

    def get_dashboard_stats(self) -> dict:
        """Statistiques globales."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM goals")
            total_goals = cursor.fetchone()[0]

            cursor.execute("SELECT status, COUNT(*) FROM goals GROUP BY status")
            goals_by_status = {row[0]: row[1] for row in cursor.fetchall()}

            cursor.execute("SELECT COUNT(*) FROM tasks")
            total_tasks = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'Terminée'")
            completed_tasks = cursor.fetchone()[0]

            global_progress = 0
            if total_tasks > 0:
                global_progress = round((completed_tasks / total_tasks) * 100, 1)

            return {
                "total_goals": total_goals,
                "goals_completed": goals_by_status.get("Terminé", 0),
                "goals_in_progress": goals_by_status.get("En cours", 0),
                "goals_not_started": goals_by_status.get("Non commencé", 0),
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "global_progress": global_progress
            }

    def get_goal_progress(self, goal_id: int) -> dict:
        """Progression d'un goal."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM tasks WHERE goal_id = ?", (goal_id,))
            total = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(*) FROM tasks WHERE goal_id = ? AND status = 'Terminée'",
                (goal_id,)
            )
            completed = cursor.fetchone()[0]

            percentage = 0
            if total > 0:
                percentage = round((completed / total) * 100, 1)

            return {
                "total_tasks": total,
                "completed_tasks": completed,
                "percentage": percentage
            }

    def get_goals_by_year(self, year: int) -> dict:
        """Stats goals pour une année."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            year_start = f"{year}-01-01T00:00:00"
            year_end = f"{year + 1}-01-01T00:00:00"

            cursor.execute("""
                SELECT COUNT(*) FROM goals 
                WHERE created_at >= ? AND created_at < ?
            """, (year_start, year_end))
            created = cursor.fetchone()[0]

            cursor.execute("""
                SELECT COUNT(*) FROM goals 
                WHERE status = 'Terminé' 
                AND updated_at >= ? AND updated_at < ?
            """, (year_start, year_end))
            completed = cursor.fetchone()[0]

            cursor.execute("""
                SELECT COUNT(*) FROM goals 
                WHERE status = 'En cours' 
                AND created_at >= ? AND created_at < ?
            """, (year_start, year_end))
            in_progress = cursor.fetchone()[0]

            return {
                "created": created,
                "completed": completed,
                "in_progress": in_progress
            }

    def get_goals_by_month(self, year: int, month: int) -> dict:
        """Stats goals pour un mois."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            month_start = f"{year}-{month:02d}-01T00:00:00"
            if month == 12:
                month_end = f"{year + 1}-01-01T00:00:00"
            else:
                month_end = f"{year}-{month + 1:02d}-01T00:00:00"

            cursor.execute("""
                SELECT COUNT(*) FROM goals 
                WHERE status = 'En cours' 
                AND created_at >= ? AND created_at < ?
            """, (month_start, month_end))
            in_progress = cursor.fetchone()[0]

            cursor.execute("""
                SELECT COUNT(*) FROM goals 
                WHERE created_at >= ? AND created_at < ?
            """, (month_start, month_end))
            created = cursor.fetchone()[0]

            return {
                "in_progress": in_progress,
                "created": created
            }

    def get_daily_progress_last_30_days(self) -> list[dict]:
        """Tâches terminées par jour sur 30 jours."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            end_date = datetime.now()
            start_date = end_date - timedelta(days=29)

            results = []
            for i in range(30):
                current = start_date + timedelta(days=i)
                day_start = current.replace(hour=0, minute=0, second=0).isoformat()
                day_end = current.replace(hour=23, minute=59, second=59).isoformat()

                cursor.execute("""
                    SELECT COUNT(*) FROM tasks 
                    WHERE status = 'Terminée' 
                    AND updated_at >= ? AND updated_at <= ?
                """, (day_start, day_end))
                count = cursor.fetchone()[0]

                results.append({
                    "date": current.strftime("%d/%m"),
                    "full_date": current.strftime("%Y-%m-%d"),
                    "completed_tasks": count
                })

            return results

    def get_goals_distribution_by_status(self) -> dict:
        """Répartition par statut."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT status, COUNT(*) as count 
                FROM goals 
                GROUP BY status
            """)
            return {row[0]: row[1] for row in cursor.fetchall()}