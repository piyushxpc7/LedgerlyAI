# Ledgerly

> **⚠️ Disclaimer**: Ledgerly is a preparation & workflow automation tool for CA firms. It does NOT file tax returns, certify documents, or provide legal opinions.

A SaaS platform that automates CA-firm back-office workflows using agentic AI:
- Document ingestion (bank statements, invoices, GST summaries, TDS challans)
- Automated reconciliation with issue detection
- Audit-ready working papers generation
- Multi-tenant dashboard for review & approval

## Tech Stack

- **Backend**: Python + FastAPI + SQLAlchemy + PostgreSQL (with pgvector)
- **Async Jobs**: Celery + Redis
- **LLM**: LangGraph with Mistral/Anthropic adapters
- **Frontend**: Next.js + TypeScript + Tailwind + shadcn/ui
- **Infrastructure**: Docker Compose

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Node.js 18+ (for local frontend dev)
- Python 3.11+ (for local backend dev)

### 1. Clone and Configure

```bash
cd /Users/Work/AICA
cp .env.example .env
# Edit .env and add your MISTRAL_API_KEY
```

### 2. Start with Docker Compose

```bash
cd infra
docker-compose up -d
```

### 3. Run Migrations

```bash
cd backend
alembic upgrade head
```

### 4. Seed Sample Data

```bash
cd backend
python scripts/seed.py
```

### 5. Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

### Demo Credentials
- Email: `admin@demo.com`
- Password: `password123`

## Demo Flow

1. Login with demo credentials
2. View the Dashboard with sample client
3. Upload sample documents from `/sample_data/`
4. Click "Run Ingestion" for each document
5. Start a reconciliation run
6. Review detected issues
7. View and download working papers

## Local Development

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Celery Worker

```bash
cd backend
celery -A app.tasks.celery_app worker --loglevel=info
```

## Project Structure

```
/
├── backend/          # FastAPI backend
│   ├── app/
│   │   ├── api/      # Route handlers
│   │   ├── auth/     # JWT authentication
│   │   ├── models/   # SQLAlchemy models
│   │   ├── schemas/  # Pydantic schemas
│   │   ├── services/ # Business logic
│   │   ├── tasks/    # Celery tasks
│   │   └── workflows/# LangGraph workflows
│   ├── alembic/      # Database migrations
│   └── tests/        # Unit tests
├── frontend/         # Next.js frontend
│   └── src/
│       ├── app/      # App router pages
│       ├── components/
│       └── lib/      # Utilities
├── infra/            # Docker Compose
└── sample_data/      # Demo documents
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `REDIS_URL` | Redis connection string | Yes |
| `JWT_SECRET` | Secret for JWT signing | Yes |
| `MISTRAL_API_KEY` | Mistral API key | Yes* |
| `ANTHROPIC_API_KEY` | Anthropic API key | Yes* |
| `LLM_PROVIDER` | `mistral` or `anthropic` | No (default: mistral) |

*At least one LLM provider key is required

## License

Proprietary - All rights reserved
