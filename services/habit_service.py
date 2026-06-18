"""
services/habit_service.py
Service métier pour les habitudes.
"""

from typing import Optional, Dict, List
from datetime import date, timedelta
from calendar import monthrange

from database.database import DatabaseManager


class HabitService:
    """Service métier pour la gestion des habitudes."""

    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    # ═══════════════════════════════════════════════════
    # CRUD
    # ═══════════════════════════════════════════════════

    def create_habit(self, **kwargs) -> int:
        return self.db.create_habit(**kwargs)

    def get_habit(self, habit_id: int) -> Optional[dict]:
        row = self.db.get_habit_by_id(habit_id)
        return dict(row) if row else None

    def update_habit(self, habit_id: int, **kwargs) -> bool:
        return self.db.update_habit(habit_id, **kwargs)

    def archive_habit(self, habit_id: int) -> bool:
        """Archive (soft delete) — l'habitude disparaît de la vue principale."""
        return self.db.archive_habit(habit_id)

    def restore_habit(self, habit_id: int) -> bool:
        """Restaure une habitude archivée."""
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE habits SET archived_at = NULL WHERE id = ?",
                (habit_id,)
            )
            return cursor.rowcount > 0

    def delete_habit_permanently(self, habit_id: int) -> bool:
        """Suppression définitive — TOUT est effacé (habitude + logs)."""
        return self.db.delete_habit(habit_id)

    def list_habits(self, include_archived: bool = False) -> List[dict]:
        """Liste les habitudes. Par défaut, exclut les archivées."""
        rows = self.db.get_all_habits(include_archived=include_archived)
        return [dict(row) for row in rows]

    # ═══════════════════════════════════════════════════
    # LOGS
    # ═══════════════════════════════════════════════════

    def toggle_log(self, habit_id: int, date_iso: str, status: str) -> int:
        return self.db.create_or_update_habit_log(habit_id, date_iso, status)

    def delete_log(self, habit_id: int, date_iso: str) -> bool:
        return self.db.delete_habit_log(habit_id, date_iso)

    def get_logs_for_month(self, year: int, month: int) -> Dict[int, Dict[str, str]]:
        """Récupère tous les logs du mois, groupés par habit_id."""
        _, num_days = monthrange(year, month)
        start = f"{year}-{month:02d}-01"
        end = f"{year}-{month:02d}-{num_days:02d}"

        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT habit_id, log_date, status 
                FROM habit_logs 
                WHERE log_date >= ? AND log_date <= ?
            """, (start, end))

            result: Dict[int, Dict[str, str]] = {}
            for row in cursor.fetchall():
                hid = row["habit_id"]
                if hid not in result:
                    result[hid] = {}
                result[hid][row["log_date"]] = row["status"]
            return result

    # ═══════════════════════════════════════════════════
    # STREAKS
    # ═══════════════════════════════════════════════════

    def get_current_streak(self, habit_id: int) -> int:
        """Calcule le streak actuel (jours consécutifs avec 'done')."""
        logs = self.db.get_habit_logs(habit_id)
        if not logs:
            return 0

        done_dates = set()
        for log in logs:
            if log["status"] == "done":
                done_dates.add(log["log_date"])

        if not done_dates:
            return 0

        today = date.today().isoformat()
        yesterday = (date.today() - timedelta(days=1)).isoformat()

        # Le streak est valide si on a fait aujourd'hui ou hier
        if today not in done_dates and yesterday not in done_dates:
            return 0

        streak = 0
        check_date = date.today()
        while True:
            iso = check_date.isoformat()
            if iso in done_dates:
                streak += 1
                check_date -= timedelta(days=1)
            else:
                # Tolérance : si c'est aujourd'hui et pas encore fait, on continue
                if iso == today:
                    check_date -= timedelta(days=1)
                    continue
                break

        return streak

    def get_best_streak(self, habit_id: int) -> int:
        """Meilleur streak historique."""
        logs = self.db.get_habit_logs(habit_id)
        done_dates = sorted([
            log["log_date"] for log in logs if log["status"] == "done"
        ])

        if not done_dates:
            return 0

        best = 1
        current = 1
        for i in range(1, len(done_dates)):
            prev = date.fromisoformat(done_dates[i - 1])
            curr = date.fromisoformat(done_dates[i])
            if (curr - prev).days == 1:
                current += 1
                best = max(best, current)
            else:
                current = 1

        return best

    # ═══════════════════════════════════════════════════
    # STATS
    # ═══════════════════════════════════════════════════

    def get_month_stats(self, habit_id: int, year: int, month: int) -> dict:
        return self.db.get_habit_month_stats(habit_id, year, month)

    def get_completion_rate(self, habit_id: int, days: int = 30) -> float:
        """Taux de complétion sur les N derniers jours."""
        end = date.today()
        start = end - timedelta(days=days - 1)
        logs = self.db.get_habit_logs(habit_id, start.isoformat(), end.isoformat())

        done = sum(1 for log in logs if log["status"] == "done")
        return round(done / days * 100, 1) if days > 0 else 0.0