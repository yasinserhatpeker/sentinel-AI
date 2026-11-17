#!/bin/sh
set -eu

if [ "${1:-}" = "migrate-and-run" ]; then
    # Generated development migrations live in the named Docker volume, never in source.
    if ! python - <<'PY'
from pathlib import Path
import shutil

source = Path("/app")
target = Path("/app-local")
target.mkdir(parents=True, exist_ok=True)
persisted_migrations_exist = any((target / "demo" / "migrations").glob("0*.py"))

for path in sorted(target.rglob("*"), key=lambda item: len(item.parts), reverse=True):
    if "migrations" in path.parts:
        continue
    if path.is_file() or path.is_symlink():
        path.unlink()
    elif path.is_dir():
        try:
            path.rmdir()
        except OSError:
            pass

for child in source.iterdir():
    destination = target / child.name
    if child.is_dir():
        ignore = shutil.ignore_patterns("migrations") if persisted_migrations_exist else None
        shutil.copytree(child, destination, dirs_exist_ok=True, ignore=ignore)
    else:
        shutil.copy2(child, destination)

# Version-controlled baseline migrations may be added while the persistent
# runtime history already exists. Copy only missing baseline files; generated
# environment migrations remain untouched.
source_migrations = source / "demo" / "migrations"
target_migrations = target / "demo" / "migrations"
target_migrations.mkdir(parents=True, exist_ok=True)
for migration in source_migrations.glob("*.py"):
    destination = target_migrations / migration.name
    if not destination.exists():
        shutil.copy2(migration, destination)
PY
    then
        # A damaged local development copy must not make the authenticated API
        # unavailable. Keep the database and migration volume intact, and run
        # the current bind-mounted source until the local copy is repaired.
        cd /app
        python manage.py check
        exec python manage.py runserver 0.0.0.0:8000
    fi

    cd /app-local
    python manage.py check
    python manage.py makemigrations demo --noinput
    python manage.py migrate --noinput
    python manage.py ensure_local_additive_schema
    exec python manage.py runserver 0.0.0.0:8000
fi

# Repository policy keeps generated development migrations out of source.  Test
# containers still need a migration state matching the current models, so create
# it only inside the disposable container before Django creates its test database.
if [ "${1:-}" = "python" ] && [ "${2:-}" = "manage.py" ] && [ "${3:-}" = "test" ]; then
    python manage.py makemigrations demo --noinput
fi

exec "$@"
