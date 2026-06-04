.DEFAULT_GOAL := help
.PHONY: help install up down restart logs ps start cockpit frontend cycle sentiment digest digest-dry test test-cov lint fmt check clean reset

UV      := uv run
COMPOSE := docker compose

# ── Help ──────────────────────────────────────────────────────────────────────
help:
	@printf "\n\033[1mAlphaOps — dev commands\033[0m\n\n"
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*##/ \
	    {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""

# ── Setup ─────────────────────────────────────────────────────────────────────
install: ## Install all dependencies (including dev)
	uv sync --extra dev

# ── Docker ────────────────────────────────────────────────────────────────────
up: ## Start all Docker services (detached)
	$(COMPOSE) up -d

down: ## Stop all Docker services
	$(COMPOSE) down

restart: ## Restart all Docker services
	$(COMPOSE) restart

logs: ## Follow logs for all services (Ctrl+C to stop)
	$(COMPOSE) logs -f

ps: ## Show service status and health
	$(COMPOSE) ps

reset: ## ⚠ Destroy volumes and restart fresh (wipes all data)
	$(COMPOSE) down -v
	$(COMPOSE) up -d

# ── App ───────────────────────────────────────────────────────────────────────
start: ## Run startup health check (DB + Qdrant + LLM)
	$(UV) python main.py

cockpit: ## Start Agent Cockpit API server (port 8000)
	$(UV) uvicorn cockpit.app:app --reload --port 8000

frontend: ## Start Next.js frontend dev server (port 3000)
	cd frontend && npm run dev

# ── Agents ────────────────────────────────────────────────────────────────────
cycle: ## Run full agent cycle (NewsHunter → MarketWatch → Sentiment → Risk → Research)
	$(UV) python -m scripts.run_cycle

sentiment: ## Run SentimentAnalyst on unanalysed articles
	$(UV) python -c "import asyncio; from agents.sentiment_analyst import SentimentAnalystAgent; asyncio.run(SentimentAnalystAgent().run())"

# ── Digest ────────────────────────────────────────────────────────────────────
digest: ## Summarise recent news and post to Discord
	$(UV) python -m scripts.news_digest

digest-dry: ## Summarise recent news and print without posting
	$(UV) python -m scripts.news_digest --dry-run

# ── Quality ───────────────────────────────────────────────────────────────────
test: ## Run test suite
	$(UV) poe test

test-cov: ## Run tests with coverage report
	$(UV) poe test:cov

lint: ## Lint with ruff
	$(UV) poe lint

fmt: ## Format with ruff
	$(UV) poe fmt

check: ## Run lint + full test suite
	$(UV) poe check

# ── Cleanup ───────────────────────────────────────────────────────────────────
clean: ## Remove __pycache__, .pytest_cache, .ruff_cache
	@find . -type d -name __pycache__ -not -path './.venv/*' -exec rm -rf {} + 2>/dev/null || true
	@rm -rf .pytest_cache .ruff_cache htmlcov .coverage
	@echo "Cleaned."
