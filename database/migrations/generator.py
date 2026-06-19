"""
database/migrations/generator.py
Générateur de migrations et runner.
"""

import sqlite3
import os
import re
from pathlib import Path
from typing import Callable, List, Optional
from datetime import datetime


# ───────────────────────────────────────────────────
# REGISTRY DES MIGRATIONS
# ───────────────────────────────────────────────────

_migration_registry: dict[int, Callable[[sqlite3.Cursor], None]] = {}


def migration(version: int, description: str):
    """Décorateur pour enregistrer une migration."""
    def decorator(func: Callable[[sqlite3.Cursor], None]):
        _migration_registry[version] = func
        func._version = version          # type: ignore
        func._description = description  # type: ignore
        return func
    return decorator


def get_registered_migrations() -> dict[int, Callable[[sqlite3.Cursor], None]]:
    """Retourne toutes les migrations enregistrées."""
    return dict(_migration_registry)


# ───────────────────────────────────────────────────
# UTILITAIRES
# ───────────────────────────────────────────────────

def get_next_version(migrations_dir: Path) -> int:
    """Trouve le prochain numéro de version disponible."""
    if not migrations_dir.exists():
        return 1
    
    versions = []
    for f in migrations_dir.glob("*_*.py"):
        match = re.match(r"(\d{3})_", f.name)
        if match:
            versions.append(int(match.group(1)))
    
    return max(versions, default=0) + 1


def get_applied_versions(db_path: str) -> set[int]:
    """Récupère les versions déjà appliquées."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL,
            description TEXT
        )
    """)
    conn.commit()
    
    cursor.execute("SELECT version FROM schema_migrations")
    versions = {row[0] for row in cursor.fetchall()}
    conn.close()
    return versions


def record_migration(cursor: sqlite3.Cursor, version: int, description: str) -> None:
    """Enregistre qu'une migration a été appliquée."""
    now = datetime.now().isoformat()
    cursor.execute(
        "INSERT INTO schema_migrations (version, applied_at, description) VALUES (?, ?, ?)",
        (version, now, description)
    )


# ───────────────────────────────────────────────────
# RUNNER
# ───────────────────────────────────────────────────

def run_migrations(db_path: str = "database.db") -> None:
    """Exécute toutes les migrations en attente."""
    # Import dynamique pour charger tous les modules de migration
    migrations_dir = Path(__file__).parent
    if migrations_dir.exists():
        for f in sorted(migrations_dir.glob("*_*.py")):
            if f.name not in ("__init__.py", "generator.py", "schema_detector.py"):
                module_name = f"database.migrations.{f.stem}"
                try:
                    __import__(module_name)
                except ImportError:
                    # Fallback: import via exec
                    spec = __import__("importlib.util").util.spec_from_file_location(
                        f"migration_{f.stem}", f
                    )
                    if spec and spec.loader:
                        module = __import__("importlib.util").util.module_from_spec(spec)
                        spec.loader.exec_module(module)

    applied = get_applied_versions(db_path)
    pending = sorted(v for v in _migration_registry if v not in applied)

    if not pending:
        print("✅ Aucune migration en attente.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        for version in pending:
            func = _migration_registry[version]
            desc = getattr(func, '_description', 'Unknown')
            print(f"⬆️  Migration {version:03d}: {desc}")
            func(cursor)
            record_migration(cursor, version, desc)
        
        conn.commit()
        print(f"✅ {len(pending)} migration(s) appliquée(s).")
    except Exception as e:
        conn.rollback()
        print(f"❌ Erreur migration: {e}")
        raise
    finally:
        conn.close()


# ───────────────────────────────────────────────────
# GÉNÉRATEUR DE MIGRATION (template)
# ───────────────────────────────────────────────────

def generate_migration_template(version: int, description: str) -> str:
    """Génère un template de fichier de migration."""
    lines = [
        '"""',
        f'database/migrations/{version:03d}_{description.lower().replace(" ", "_")}.py',
        f'Migration {version} : {description}',
        '"""',
        '',
        'import sqlite3',
        'from database.migrations.generator import migration',
        '',
        '',
        f'@migration({version}, "{description}")',
        f'def migration_{version:03d}(cursor: sqlite3.Cursor) -> None:',
        '    """',
        '    TODO: Implémenter la migration ici.',
        '    Exemple:',
        '        cursor.execute("ALTER TABLE goals ADD COLUMN new_field TEXT")',
        '    """',
        '    pass',
        ''
    ]
    return "\n".join(lines)


def create_migration_file(description: str, migrations_dir: Optional[Path] = None) -> Path:
    """Crée un nouveau fichier de migration vide."""
    if migrations_dir is None:
        migrations_dir = Path(__file__).parent
    
    migrations_dir.mkdir(parents=True, exist_ok=True)
    version = get_next_version(migrations_dir)
    
    filename = f"{version:03d}_{description.lower().replace(' ', '_')}.py"
    filepath = migrations_dir / filename
    
    filepath.write_text(generate_migration_template(version, description), encoding="utf-8")
    print(f"📝 Fichier créé: {filepath}")
    return filepath


# ───────────────────────────────────────────────────
# CLI
# ───────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python -m database.migrations.generator [run|create <description>]")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "run":
        run_migrations()
    elif cmd == "create" and len(sys.argv) >= 3:
        desc = " ".join(sys.argv[2:])
        create_migration_file(desc)
    else:
        print("Usage: python -m database.migrations.generator [run|create <description>]")