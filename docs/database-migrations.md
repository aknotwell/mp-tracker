# Database migrations

Alembic is the only mechanism for creating and changing a persistent application database. The FastAPI process does not create tables automatically.

## First-time setup after cloning

From the repository root:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.lock
Copy-Item .env.example .env
python -m alembic upgrade head
```

With the default `.env`, the last command creates `backend/mp_tracker.sqlite3`. It also creates an `alembic_version` table that records the installed revision.

Run `upgrade head` again whenever a pull introduces new files in `migrations/versions/`. Alembic skips revisions already recorded in the database.

## Common commands

```powershell
# Show the revision installed in the configured database.
python -m alembic current

# Show all known revisions.
python -m alembic history

# Apply every unapplied revision.
python -m alembic upgrade head

# Reverse one revision. Back up real data before downgrading.
python -m alembic downgrade -1
```

## Changing the schema later

1. Change the SQLAlchemy models.
2. Generate a candidate revision:

   ```powershell
   python -m alembic revision --autogenerate -m "describe the change"
   ```

3. Read the generated file. Autogeneration is a starting point, not a substitute for review.
4. Run the backend test suite.
5. Apply the revision with `python -m alembic upgrade head`.

Alembic is configured with batch mode for SQLite. When SQLite cannot alter a constraint directly, batch mode creates a replacement table, copies the existing rows, and swaps the tables. Back up important databases before applying schema changes.

## Database location and overrides

The default connection URL is:

```text
sqlite+aiosqlite:///./mp_tracker.sqlite3
```

The relative path is resolved from the directory where the Alembic command runs, which is why commands should run from `backend/`. Set `APP_DATABASE_URL` in `backend/.env` to use another location.

Do not commit `.env` files or SQLite database files.
