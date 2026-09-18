# Fragrance Collection Tracker

Monorepo for a personal fragrance collection tracker.

## Projects

- `backend/`: async FastAPI API (Python 3.12+)
- `frontend/`: Next.js App Router web app (Node.js 22 LTS+)
- `docs/`: shared API, domain, and state-management contracts

Milestones 1 through 3 and Milestone 4 Google authentication are implemented: project foundations, SQLAlchemy/Pydantic domain definitions, Alembic migrations, private OIDC login attempts, revocable sessions, token rotation, and protected-user dependencies. Core CRUD, ranking, and scraping remain for later phases.

## Local setup

Copy each example environment file before starting a project. Never commit real secrets.

### Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.lock
Copy-Item .env.example .env
python -m alembic upgrade head
python -m uvicorn app.main:app --reload
```

The health endpoint is available at `http://localhost:8000/health`.
See [docs/database-migrations.md](docs/database-migrations.md) for migration commands and the schema-change workflow.

### Frontend

```powershell
cd frontend
npm ci
Copy-Item .env.example .env.local
npm run dev
```

The web app is available at `http://localhost:3000`.

## Quality checks

```powershell
cd backend
python -m ruff check .
python -m ruff format --check .
python -m mypy app
python -m pytest

cd ..\frontend
npm run lint
npm run typecheck
npm test
npm run build
```

See [docs/domain-contract.md](docs/domain-contract.md) for the shared API and domain conventions.
