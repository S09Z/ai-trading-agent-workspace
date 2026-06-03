# AlphaOps — Murff Alpha

An AI-native multi-agent trading intelligence platform. Continuously collects, analyzes, and monitors financial market information in real-time. Runs autonomously on Docker + VPS so it keeps working when you're offline.

## What it does

| Agent | Responsibility | Schedule |
| --- | --- | --- |
| **Orchestrator** | Coordinates all agents, routes tasks | Always-on |
| **NewsHunter** | Scrapes financial news from multiple sources | Every 5 min |
| **MarketWatch** | Monitors price data, volume spikes, unusual moves | Every 1 min |
| **SentimentAnalyst** | Classifies news sentiment via Claude | On new data |
| **ResearchAnalyst** | Deep-dives on specific tickers on demand | On trigger |
| **RiskMonitor** | Tracks macro events, earnings calendar, volatility | Every 15 min |
| **ReportWriter** | Generates structured daily/weekly summaries | Daily |

## Architecture

```
Agents (Orchestrator, NewsHunter, MarketWatch, Sentiment, Research, Risk, Reporter)
    │
    ├── Intelligence: Claude API (analysis) + Qdrant (RAG memory)
    ├── Storage:      PostgreSQL/TimescaleDB (structured) · Redis (cache + queue)
    └── Presentation: FastAPI + WebSocket · Agent Cockpit (Next.js) · Virtual Office
```

## Stack

| Layer | Technology |
| --- | --- |
| Language | Python 3.12 |
| LLM | Claude (Anthropic API) |
| Vector DB | Qdrant |
| Database | PostgreSQL + TimescaleDB |
| Cache / Queue | Redis + Celery |
| API | FastAPI + WebSocket |
| Agent Cockpit | Next.js + Tailwind |
| Infrastructure | Docker Compose |

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) — Python package manager
- Docker + Docker Compose
- Anthropic API key

## Quick start

```bash
# 1. Clone and enter the project
git clone <repo-url>
cd ai-trading-agent-workspace

# 2. Copy env template and fill in your secrets
cp .env.example .env
# Required: POSTGRES_PASSWORD, ANTHROPIC_API_KEY

# 3. Install dependencies
make install

# 4. Start backing services (PostgreSQL, Qdrant, Redis)
make up

# 5. Verify all services connect
make start
```

## Environment variables

Copy `.env.example` to `.env` and set the following:

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `POSTGRES_PASSWORD` | Yes | — | PostgreSQL password |
| `ANTHROPIC_API_KEY` | Yes | — | Claude API key |
| `POSTGRES_HOST` | No | `localhost` | PostgreSQL host |
| `POSTGRES_PORT` | No | `5432` | PostgreSQL port |
| `POSTGRES_DB` | No | `alphaops` | Database name |
| `POSTGRES_USER` | No | `alphaops` | Database user |
| `QDRANT_HOST` | No | `localhost` | Qdrant host |
| `QDRANT_PORT` | No | `6333` | Qdrant REST port |
| `REDIS_URL` | No | `redis://localhost:6379/0` | Redis connection URL |
| `CLAUDE_MODEL` | No | `claude-sonnet-4-6` | Claude model ID |
| `NEWS_API_KEY` | No | — | NewsAPI key (falls back to RSS) |
| `NEWS_POLL_INTERVAL` | No | `300` | News fetch interval (seconds) |
| `MARKET_POLL_INTERVAL` | No | `60` | Market data interval (seconds) |
| `RISK_POLL_INTERVAL` | No | `900` | Risk monitor interval (seconds) |
| `API_PORT` | No | `8000` | FastAPI server port |
| `DEBUG` | No | `false` | Enable SQLAlchemy query logging |

## Commands

### Setup

| Command | Description |
| --- | --- |
| `make install` | Install all dependencies including dev tools |

### Docker services

| Command | Description |
| --- | --- |
| `make up` | Start PostgreSQL, Qdrant, and Redis (detached) |
| `make down` | Stop all services |
| `make restart` | Restart all services |
| `make logs` | Follow logs for all services (Ctrl+C to stop) |
| `make ps` | Show service status and health checks |
| `make reset` | Destroy all volumes and restart fresh — **wipes all data** |

### App

| Command | Description |
| --- | --- |
| `make start` | Run startup health check (DB + Qdrant + Claude API) |

### Code quality

| Command | Description |
| --- | --- |
| `make test` | Run full test suite |
| `make test-cov` | Run tests with coverage report |
| `make lint` | Lint with ruff |
| `make fmt` | Format with ruff |
| `make check` | Run lint + tests in sequence |
| `make clean` | Remove `__pycache__`, `.pytest_cache`, `.ruff_cache` |

### Poe tasks (alternative, requires activated venv)

```bash
uv run poe start       # startup health check
uv run poe test        # run tests
uv run poe test:cov    # tests + coverage
uv run poe lint        # ruff check
uv run poe fmt         # ruff format
uv run poe check       # lint → test
```

## Project structure

```
.
├── agents/              # Agent implementations (orchestrator, news hunter, etc.)
├── collectors/          # Data collectors (news, market data)
├── config/
│   └── settings.py      # Pydantic settings — single source of truth for all config
├── intelligence/
│   └── claude_client.py # Anthropic SDK wrapper (chat, analyze)
├── memory/
│   ├── database.py      # SQLAlchemy models + async engine (Article, Signal, AgentLog)
│   └── vector_store.py  # Qdrant RAG (upsert, upsert_batch, search)
├── api/                 # FastAPI app + WebSocket (Phase 4)
├── scheduler/           # Celery task definitions (Phase 2)
├── cockpit/             # Agent Cockpit — Next.js frontend (Phase 4)
├── tests/               # Test suite
├── docker-compose.yml   # PostgreSQL/TimescaleDB · Qdrant · Redis
├── Makefile             # Dev commands
├── main.py              # Startup health check
└── pyproject.toml       # Dependencies + Poe tasks + tool config
```

## Services

| Service | Port | UI |
| --- | --- | --- |
| PostgreSQL (TimescaleDB) | `5432` | — |
| Qdrant | `6333` (REST) · `6334` (gRPC) | http://localhost:6333/dashboard |
| Redis | `6379` | — |
| FastAPI | `8000` | http://localhost:8000/docs |
| Agent Cockpit | `3000` | <http://localhost:3000> |

## Build phases

- **Phase 1** — Foundation: Docker services, config, database models, vector store, Claude client ✅
- **Phase 2** — Data collection: NewsHunter, MarketWatch collectors, Celery scheduler
- **Phase 3** — AI intelligence: SentimentAnalyst, ResearchAnalyst, RAG pipeline
- **Phase 4** — Agent Cockpit: FastAPI + WebSocket, Next.js UI, Virtual Office
- **Phase 5** — Deployment: VPS setup, Nginx, health checks
