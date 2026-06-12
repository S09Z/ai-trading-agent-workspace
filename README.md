# AlphaOps — Murff Alpha

An AI-native multi-agent trading intelligence platform. Continuously collects, analyzes, and monitors financial market information in real-time. Runs autonomously on Docker + VPS so it keeps working when you're offline.

## What it does

| Agent | Responsibility | Schedule |
| --- | --- | --- |
| **Orchestrator** | Coordinates all agents, routes tasks in layers | Always-on |
| **NewsHunter** | Scrapes 8 RSS feeds + targeted small-cap feeds, deduplicates, embeds into RAG | Every 5 min |
| **MarketWatch** | Monitors OHLCV price data, detects ≥3% moves | Every 1 min |
| **SentimentAnalyst** | Classifies article sentiment via LLM → Signal + S/A/B/C grade | On new data |
| **ResearchAnalyst** | RAG + past outcome memory deep-dive on hot ticker → Signal + grades | Hourly |
| **RiskMonitor** | Aggregates price spikes, fires circuit breaker at >3 spikes / 15 min | Every 15 min |
| **MemoryAgent** | Evaluates past signal accuracy via yfinance, embeds outcomes into Qdrant | Daily |
| **FinancialAnalyst** | Fetches 17 financial metrics via yfinance + IC-scored alpha factors → LLM assessment → Signal + grades + composite score | Daily |
| **DiscoveryAgent** | Scans 199-ticker universe for news mention spikes outside watchlist → Signal + grades | Every 6h |

Results are pushed to Discord as a rich market digest every 6 hours, enriched with the Agent Intelligence section (signals, research thesis, risk status).

## Architecture

```text
Agents (Orchestrator → NewsHunter · MarketWatch → SentimentAnalyst · RiskMonitor → ResearchAnalyst)
    │
    ├── Intelligence:   Claude API or Ollama (local LLM) · Qdrant (RAG vector store)
    ├── Storage:        PostgreSQL/TimescaleDB · Redis (cache + task queue)
    ├── Notifications:  Discord webhook (market digest + Agent Intelligence)
    ├── Cockpit API:    FastAPI + WebSocket (port 8000)
    └── Cockpit UI:     Next.js Market Dashboard + Virtual Office pixel-art (port 3000)
```

## Stack

| Layer | Technology |
| --- | --- |
| Language | Python 3.12 |
| LLM | Claude (Anthropic API) or Ollama (local, e.g. qwen3) |
| Vector DB | Qdrant |
| Database | PostgreSQL + TimescaleDB |
| Cache / Queue | Redis + Celery |
| Cockpit API | FastAPI + WebSocket |
| Cockpit UI | Next.js 16 + React 19 + Tailwind v4 |
| Infrastructure | Docker Compose |

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) — Python package manager
- Docker + Docker Compose
- Anthropic API key **or** [Ollama](https://ollama.com/download) running locally

## Quick start

```bash
# 1. Clone and enter the project
git clone <repo-url>
cd ai-trading-agent-workspace

# 2. Copy env template and fill in your secrets
cp .env.example .env
# Required: POSTGRES_PASSWORD + (ANTHROPIC_API_KEY or USE_LOCAL_LLM=true)

# 3. Install dependencies
make install

# 4. Start backing services (PostgreSQL, Qdrant, Redis)
make up

# 5. Verify all services connect
make start

# 6. Run a full agent cycle (collect → analyse → research)
make cycle

# 7. Start the backend API
make cockpit   # → http://localhost:8000

# 8. Start the frontend dashboard
make frontend  # → http://localhost:3000

# 9. Post a digest to Discord
make digest
```

## Environment variables

Copy `.env.example` to `.env` and set the following:

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `POSTGRES_PASSWORD` | Yes | — | PostgreSQL password |
| `ANTHROPIC_API_KEY` | Yes* | — | Claude API key (*not needed when USE_LOCAL_LLM=true) |
| `DISCORD_WEBHOOK_URL` | No | — | Discord webhook for digest notifications |
| `USE_LOCAL_LLM` | No | `false` | Use Ollama instead of Claude API |
| `LOCAL_MODEL` | No | `qwen3:latest` | Ollama model name |
| `OLLAMA_URL` | No | `http://localhost:11434` | Ollama server URL |
| `POSTGRES_HOST` | No | `localhost` | PostgreSQL host |
| `POSTGRES_PORT` | No | `5432` | PostgreSQL port |
| `POSTGRES_DB` | No | `alphaops` | Database name |
| `POSTGRES_USER` | No | `alphaops` | Database user |
| `QDRANT_HOST` | No | `localhost` | Qdrant host |
| `QDRANT_PORT` | No | `6333` | Qdrant REST port |
| `REDIS_URL` | No | `redis://localhost:6379/0` | Redis connection URL |
| `CLAUDE_MODEL` | No | `claude-sonnet-4-6` | Claude model ID |
| `NEWS_API_KEY` | No | — | NewsAPI key (falls back to RSS feeds) |
| `DEBUG` | No | `false` | Enable SQLAlchemy query logging |

## Commands

> Docker service management and production deployment commands are in [Infra.md](Infra.md).

### Setup

| Command | Description |
| --- | --- |
| `make install` | Install all dependencies including dev tools |

### App & agents

| Command | Description |
| --- | --- |
| `make start` | Startup health check (DB + Qdrant + LLM) |
| `make status` | Color-coded health check for all 8 services |
| `make cockpit` | Start Agent Cockpit API server (port 8000, hot-reload) |
| `make frontend` | Start Next.js dashboard (port 3000) |
| `make discord-bot` | Start Discord bot (listens for `!` commands) |
| `make celery-worker` | Start Celery worker (processes queued tasks) |
| `make celery-beat` | Start Celery Beat scheduler (enqueues tasks on schedule) |
| `make cycle` | Full agent cycle: NewsHunter → MarketWatch → SentimentAnalyst → RiskMonitor → ResearchAnalyst |
| `make sentiment` | Run SentimentAnalyst only (use after NewsHunter has collected articles) |
| `make financial` | Run FinancialAnalystAgent (all watchlist tickers) |
| `make memory` | Run MemoryAgent (evaluate past signal outcomes) |
| `make discover` | Run DiscoveryAgent (surface universe tickers with strong news mentions) |
| `make digest` | Generate market digest and post to Discord |
| `make digest-dry` | Preview digest without posting to Discord |

### PM2 (background process management)

> Requires `npm install -g pm2` once.

| Command | Description |
| --- | --- |
| `make pm2-start` | Start cockpit + celery-worker + celery-beat + discord-bot as background processes |
| `make pm2-stop` | Stop all PM2-managed services |
| `make pm2-restart` | Restart all PM2-managed services |
| `make pm2-status` | Show PM2 process list with CPU/memory |
| `make pm2-logs` | Follow logs for all PM2 processes |

### Code quality

| Command | Description |
| --- | --- |
| `make test` | Run full test suite |
| `make test-cov` | Run tests with coverage report |
| `make lint` | Lint with ruff |
| `make fmt` | Format with ruff |
| `make check` | Run lint + tests in sequence |
| `make clean` | Remove `__pycache__`, `.pytest_cache`, `.ruff_cache` |

## Cockpit API

The Agent Cockpit exposes a REST + WebSocket API for the frontend.

```bash
make cockpit   # → http://localhost:8000
```

| Endpoint | Description |
| --- | --- |
| `GET /health` | Service health check (DB + Qdrant) |
| `GET /agents` | All agents with latest status (last action, last seen, level) |
| `GET /agents/{name}/logs` | Recent logs for a specific agent |
| `GET /signals?hours=6` | Recent trading signals ordered by confidence (includes S/A/B/C grades) |
| `GET /logs?hours=1` | Activity log across all agents |
| `GET /outcomes?ticker=` | Recent signal outcomes (price at signal vs actual) |
| `GET /outcomes/accuracy` | Per-agent accuracy stats (correct %, total evaluated) |
| `WS /logs/ws` | Real-time stream — pushes new `AgentLog` rows every 2s |

Interactive API docs: <http://localhost:8000/docs>

## Project structure

```text
.
├── agents/              # Agent implementations
│   ├── base.py               # BaseAgent with logging helper
│   ├── orchestrator.py       # Coordinates agents in three layers
│   ├── news_hunter.py        # RSS + NewsAPI + targeted feeds scraper with Qdrant embedding
│   ├── market_watch.py       # OHLCV polling + ≥3% spike detection
│   ├── sentiment_analyst.py  # LLM sentiment classification → Signal + S/A/B/C grades
│   ├── research_analyst.py   # RAG + memory deep-dive → Signal + grades
│   ├── risk_monitor.py       # Spike aggregation, circuit breaker
│   ├── memory_agent.py       # Past signal outcome evaluation + Qdrant embedding
│   ├── factor_library.py     # IC/IR alpha factor library (8 factors, 4 buckets) + get_factor_context()
│   ├── financial_analyst.py  # 17 yfinance metrics + factor context → LLM → Signal + grades + composite (daily)
│   └── discovery_agent.py    # Universe ticker mention scan → Signal + grades (every 6h)
├── cockpit/             # Agent Cockpit FastAPI backend
│   ├── app.py           # FastAPI app + CORS
│   ├── schemas.py       # Pydantic response models (includes grade fields + SignalOutcome)
│   └── routers/         # agents · signals · logs · outcomes (REST + WebSocket)
├── frontend/            # Next.js 16 dashboard (Market Dashboard + Virtual Office 3D)
│   ├── app/page.tsx     # Market Dashboard — signal cards with grade badges, agent status
│   ├── app/office/      # Virtual Office — Three.js 3D isometric office (iframe)
│   ├── components/      # SignalCard (with S/A/B/C grade row) · AgentStatusBadge · ActivityLog
│   ├── public/virtual-office/  # Three.js scene, Lego agents, WS bridge
│   └── lib/             # API client + TypeScript types
├── intelligence/
│   ├── claude_client.py      # Anthropic SDK wrapper
│   ├── local_client.py       # Ollama wrapper (local LLM)
│   ├── composite_scorer.py   # IC-weighted 0–100 composite score + S/A/B/C grade per ticker
│   ├── sentiment.py          # Sentiment analysis via LLM
│   ├── summarizer.py         # Market digest generation + signal/risk enrichment
│   └── discord_notifier.py   # Discord webhook embed + Agent Intelligence section
├── memory/
│   ├── database.py      # SQLAlchemy models: Article, Signal (+grades +composite), AgentLog, MarketSnapshot, SignalOutcome, FactorScore
│   ├── vector_store.py  # Qdrant RAG (upsert, search)
│   └── cache.py         # Redis cache helpers
├── config/
│   ├── settings.py      # Pydantic settings — single source of truth (watchlist: 35 tickers)
│   └── universe.py      # 199-ticker stock universe (21 sectors) for DiscoveryAgent
├── collectors/
│   ├── news.py          # RSS + NewsAPI + TARGETED_FEEDS (OKLO/SMR/TMDX) with macro aliases
│   └── market_data.py   # yfinance OHLCV fetcher
├── scheduler/
│   └── tasks.py         # Celery tasks (news/market/sentiment/risk/research/digest/memory/financial/factor-scoring)
├── scripts/
│   ├── news_digest.py   # CLI: generate + post Discord digest
│   └── run_cycle.py     # CLI: run full agent cycle
├── tests/               # 239 tests (pytest-asyncio)
├── docker-compose.yml   # PostgreSQL/TimescaleDB · Qdrant · Redis
├── docker-compose.prod.yml  # All 8 production services + Nginx + Prometheus
├── ecosystem.config.js  # PM2 process config (cockpit, workers, discord-bot)
├── Makefile             # Dev commands (make status / financial / celery-beat / pm2-*)
├── main.py              # Startup health check
└── pyproject.toml       # Dependencies + Poe tasks + tool config
```

## Build phases

| Phase | Status | Scope |
| --- | --- | --- |
| 1 | ✅ Done | Docker, config, DB models, vector store, Claude client, test suite |
| 2 | ✅ Done | NewsHunter, MarketWatch, Celery scheduler, summarizer, Discord notifier |
| 3 | ✅ Done | SentimentAnalyst, ResearchAnalyst, RiskMonitor, RAG pipeline, Discord digest upgrade |
| 4A | ✅ Done | Cockpit backend — FastAPI REST + WebSocket (`make cockpit`) |
| 4B | ✅ Done | Cockpit frontend — Next.js Market Dashboard + Virtual Office pixel-art (`make frontend`) |
| 5 | ✅ Done | VPS deployment — Nginx, Celery Beat, production Docker Compose, `make deploy` |
| 6 | ✅ Done* | Virtual Office 3D (Three.js), Prometheus monitoring, log rotation — *SSL pending VPS setup |
| 7 | ✅ Done | Signal memory — `SignalOutcome`, MemoryAgent, memory-augmented RAG, `GET /outcomes`, `GET /outcomes/accuracy` |
| 8 | 🔄 In Progress | Intelligence expansion — S/A/B/C grades, FinancialAnalystAgent (17 metrics + IC alpha factors), IC/IR factor library (`agents/factor_library.py`, 8 factors / 4 buckets), composite scorer (`intelligence/composite_scorer.py`, 0–100 score + grade, wired into FinancialAnalyst signals), expanded watchlist (35 tickers + macro), 199-ticker universe, PM2 process management |
| 9 | ✅ Done | DiscoveryAgent — news mention scan across 199-ticker universe, `make discover`, Celery every 6h |
| 10 | 🔜 Planned | Live execution — Alpaca paper/live trading, TradeExecutor, position management, P&L dashboard |
