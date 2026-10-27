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
        shutil.copytree(child, destination, dirs_exist_ok=True, ignore=shutil.ignore_patterns("migrations"))
    else:
        shutil.copy2(child, destination)
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
    exec python manage.py runserver 0.0.0.0:8000
fi

exec "$@"
