# Smart Career Roadmap Generator

A full-stack web application that helps users plan career transitions through AI-powered skill gap analysis and personalized learning roadmaps.

## Project Structure

```
.
├── backend/          # Python/FastAPI backend
│   ├── alembic/      # Database migrations
│   ├── app/
│   │   ├── ai/       # AI provider abstraction
│   │   ├── api/      # FastAPI routers & dependencies
│   │   ├── core/     # Config, DB, security, exceptions
│   │   ├── models/   # SQLAlchemy ORM models
│   │   ├── schemas/  # Pydantic request/response models
│   │   └── services/ # Domain service implementations
│   └── tests/        # pytest + Hypothesis test suite
└── frontend/         # Next.js / TypeScript frontend
```

## Quick Start

### Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file and fill in values
cp .env.example .env

# Run development server
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Running Tests

```bash
cd backend
pytest
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15, React 19, TypeScript, ESLint, Prettier |
| Backend | Python 3.11, FastAPI, Uvicorn |
| Database | PostgreSQL 16, SQLAlchemy (async), asyncpg, Alembic |
| Auth | JWT (python-jose), bcrypt (passlib) |
| Testing | pytest, Hypothesis (property-based) |
| AI | Provider-agnostic abstraction (OpenAI default) |
