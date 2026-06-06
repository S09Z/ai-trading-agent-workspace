# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

---

## Project: AlphaOps — Build Roadmap

### Phases

| Phase | Status | Scope |
| --- | --- | --- |
| 1 | ✅ Done | Docker, config, DB models, vector store, Claude client, test suite |
| 2 | ✅ Done | NewsHunter, MarketWatch, BaseAgent, Celery scheduler, summarizer, Discord notifier |
| 3 | ✅ Done | SentimentAnalyst, ResearchAnalyst, RiskMonitor, RAG pipeline, Discord digest upgrade |
| 4A | ✅ Done | Cockpit backend — FastAPI REST + WebSocket (`make cockpit`, port 8000) |
| 4B | ✅ Done | Cockpit frontend — Next.js Market Dashboard + Virtual Office pixel-art (`make frontend`, port 3000) |
| 5 | ✅ Done | VPS deployment — Nginx, Celery Beat, production Docker Compose, `make deploy` |

### Dev Commands

```bash
make start        # health check (DB + Qdrant + LLM)
make cockpit      # start FastAPI backend (port 8000, --reload)
make frontend     # start Next.js frontend (port 3000)
make cycle        # full agent cycle: NewsHunter → MarketWatch → Sentiment → Risk → Research
make sentiment    # SentimentAnalyst only (after NewsHunter has run)
make digest       # generate + post Discord digest
make digest-dry   # preview digest without posting
make test         # run test suite
make check        # lint + test
```

### LLM Config (`.env`)

```
USE_LOCAL_LLM=true   # use Ollama (qwen3:latest) — no Claude credits needed
USE_LOCAL_LLM=false  # use Claude API (default)
```

### Phase 4A — Cockpit Backend ✅

- [x] `cockpit/app.py` — FastAPI app + CORS
- [x] `cockpit/schemas.py` — AgentStatus, LogEntry, SignalOut
- [x] `GET /agents` — list all agents with latest status
- [x] `GET /agents/{name}/logs` — per-agent log history
- [x] `GET /signals` — recent signals by confidence
- [x] `GET /logs` — activity log across all agents
- [x] `WS /logs/ws` — real-time stream (polls DB every 2s, pushes new rows)
- [x] 12 endpoint tests, 137 total passing

### Phase 4B — Cockpit Frontend ✅

- [x] `frontend/` — Next.js 16 + React 19 + Tailwind v4 (`make frontend`, port 3000)
- [x] `frontend/app/page.tsx` — Market Dashboard: signal cards, agent status badges, live activity log
- [x] `frontend/app/office/page.tsx` — Virtual Office: pixel-art Canvas room
- [x] `frontend/components/VirtualOffice.tsx` — HTML Canvas, one sprite per agent, RAF draw loop
- [x] `frontend/components/ActivityLog.tsx` — WebSocket consumer (`ws://localhost:8000/logs/ws`), auto-scrolling
- [x] `frontend/components/SignalCard.tsx` — ticker, BUY/SELL/HOLD badge, confidence bar, rationale
- [x] Agent sprites — idle / active (raises arms, monitor glows) / sleeping (dim + Z) / error (red flash)

### Phase 5 — Deployment ✅

- [x] Celery Beat — `run_digest` task added (every 6h), joins existing news/market/sentiment/risk/research schedule
- [x] `Dockerfile` — Python 3.12 image for cockpit + celery-worker + celery-beat
- [x] `frontend/Dockerfile` — multi-stage Next.js build (standalone output); `NEXT_PUBLIC_*` via build args
- [x] `docker-compose.prod.yml` — all 8 services: postgres, qdrant, redis, cockpit, celery-worker, celery-beat, frontend, nginx
- [x] `nginx/nginx.conf` — `/` → frontend:3000 · `/api/` → cockpit:8000 · `/ws/` → cockpit:8000 (WebSocket)
- [x] `.env.prod.example` — production env template (no secrets)
- [x] `make deploy` — pulls latest, rebuilds, restarts prod containers
- [x] `GET /health` — now checks DB + Qdrant connectivity, returns `{"status": "ok|degraded", "db": "ok|error", "qdrant": "ok|error"}`

### Phase 6 — In Progress

- [ ] SSL — run certbot on VPS, uncomment SSL server block in `nginx/nginx.conf`
- [x] Virtual Office 3D — Three.js isometric office, Lego minifigure agents, iframe in Next.js, WS bridge (`frontend/public/virtual-office/`)
- [x] Monitoring — `prometheus-fastapi-instrumentator` on cockpit → `GET /metrics`; Prometheus service in `docker-compose.prod.yml` (`monitoring/prometheus.yml`); `make monitoring`
- [x] Log shipping — Docker `json-file` log rotation (10 MB × 5 files) on all prod services via YAML anchor `x-logging`
