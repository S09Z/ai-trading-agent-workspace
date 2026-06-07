.DEFAULT_GOAL := help
.PHONY: help install up down restart logs ps start cockpit frontend discord-bot celery-worker celery-beat pm2-start pm2-stop pm2-restart pm2-status pm2-logs cycle sentiment digest digest-dry memory financial status test test-cov lint fmt check clean reset deploy ssl-init ssl-renew monitoring

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
status: ## Show status of all services (frontend optional)
	@printf "\n\033[1mAlphaOps — Service Status\033[0m\n\n"
	@printf "  \033[36m%-20s\033[0m" "postgres";      $(COMPOSE) ps --format "{{.Status}}" postgres    2>/dev/null | grep -q "healthy" && printf "\033[32m✓ healthy\033[0m\n" || printf "\033[31m✗ not running\033[0m\n"
	@printf "  \033[36m%-20s\033[0m" "qdrant";        $(COMPOSE) ps --format "{{.Status}}" qdrant      2>/dev/null | grep -q "healthy" && printf "\033[32m✓ healthy\033[0m\n" || printf "\033[31m✗ not running\033[0m\n"
	@printf "  \033[36m%-20s\033[0m" "redis";         $(COMPOSE) ps --format "{{.Status}}" redis       2>/dev/null | grep -q "healthy" && printf "\033[32m✓ healthy\033[0m\n" || printf "\033[31m✗ not running\033[0m\n"
	@printf "  \033[36m%-20s\033[0m" "cockpit :8000"; curl -sf http://localhost:8000/health 2>/dev/null | grep -q '"status"' && printf "\033[32m✓ ok\033[0m\n" || printf "\033[31m✗ not running\033[0m\n"
	@printf "  \033[36m%-20s\033[0m" "celery-worker"; pgrep -f "celery.*worker" > /dev/null 2>&1 && printf "\033[32m✓ running\033[0m\n" || printf "\033[31m✗ not running\033[0m\n"
	@printf "  \033[36m%-20s\033[0m" "discord-bot";   pgrep -f "discord_bot" > /dev/null 2>&1 && printf "\033[32m✓ running\033[0m\n" || printf "\033[31m✗ not running\033[0m\n"
	@printf "  \033[36m%-20s\033[0m" "ollama";        curl -sf http://localhost:11434/api/tags > /dev/null 2>&1 && printf "\033[32m✓ ok\033[0m\n" || printf "\033[33m~ not running\033[0m\n"
	@printf "  \033[36m%-20s\033[0m" "frontend :3000"; curl -sf --max-time 2 -o /dev/null http://localhost:3000 2>/dev/null && printf "\033[32m✓ running\033[0m\n" || printf "\033[90m- optional\033[0m\n"
	@echo ""

start: ## Run startup health check (DB + Qdrant + LLM)
	$(UV) python main.py

cockpit: ## Start Agent Cockpit API server (port 8000)
	-lsof -ti:8000 | xargs kill -9 2>/dev/null; $(UV) uvicorn cockpit.app:app --reload --port 8000

frontend: ## Start Next.js frontend dev server (port 3000)
	-lsof -ti:3000 | xargs kill -9 2>/dev/null; cd frontend && pnpm dev

discord-bot: ## Start Discord bot (listens for !commands)
	$(UV) python -m intelligence.discord_bot

celery-worker: ## Start Celery worker (processes queued tasks)
	PYTHONPATH=. $(UV) celery -A scheduler.tasks:celery_app worker --loglevel=info

celery-beat: ## Start Celery Beat scheduler (enqueues tasks on schedule)
	PYTHONPATH=. $(UV) celery -A scheduler.tasks:celery_app beat --loglevel=info

# ── PM2 ───────────────────────────────────────────────────────────────────────
pm2-start: ## Start all background services via PM2 (cockpit + workers + discord-bot)
	@mkdir -p logs/pm2
	-lsof -ti:8000 | xargs kill -9 2>/dev/null; pm2 start ecosystem.config.js

pm2-stop: ## Stop all PM2-managed services
	pm2 stop ecosystem.config.js

pm2-restart: ## Restart all PM2-managed services
	pm2 restart ecosystem.config.js

pm2-status: ## Show PM2 process list
	pm2 list

pm2-logs: ## Follow logs for all PM2 processes (Ctrl+C to stop)
	pm2 logs

# ── Agents ────────────────────────────────────────────────────────────────────
cycle: ## Run full agent cycle (NewsHunter → MarketWatch → Sentiment → Risk → Research)
	$(UV) python -m scripts.run_cycle

memory: ## Run MemoryAgent — evaluate past signal outcomes and embed into Qdrant
	$(UV) python -c "import asyncio; from agents.memory_agent import MemoryAgent; asyncio.run(MemoryAgent().run())"

financial: ## Run FinancialAnalystAgent — analyze financials for all watchlist tickers
	$(UV) python -c "import asyncio; from agents.financial_analyst import FinancialAnalystAgent; asyncio.run(FinancialAnalystAgent().run())"

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

# ── Production ────────────────────────────────────────────────────────────────
deploy: ## Pull latest, rebuild, and restart all production containers
	git pull
	docker compose -f docker-compose.prod.yml build --pull
	docker compose -f docker-compose.prod.yml up -d

ssl-init: ## Obtain Let's Encrypt cert (requires APP_ENV=production and DOMAIN= in .env.prod)
	@grep -q 'APP_ENV=production' .env.prod 2>/dev/null || \
		(echo "Error: set APP_ENV=production in .env.prod before running ssl-init" && exit 1)
	@grep -q 'DOMAIN=' .env.prod 2>/dev/null || \
		(echo "Error: set DOMAIN=your.domain in .env.prod before running ssl-init" && exit 1)
	$(eval DOMAIN := $(shell grep '^DOMAIN=' .env.prod | cut -d= -f2))
	docker compose -f docker-compose.prod.yml run --rm certbot certonly \
		--webroot --webroot-path /var/www/certbot \
		--email admin@$(DOMAIN) --agree-tos --no-eff-email \
		-d $(DOMAIN)
	docker compose -f docker-compose.prod.yml exec nginx nginx -s reload
	@echo "SSL enabled for $(DOMAIN). Update NEXT_PUBLIC_API_URL=https://$(DOMAIN)/api and NEXT_PUBLIC_WS_URL=wss://$(DOMAIN)/ws in .env.prod, then run: make deploy"

ssl-renew: ## Renew SSL certificates and reload nginx
	docker compose -f docker-compose.prod.yml run --rm certbot renew --quiet

monitoring: ## Open Prometheus UI (prod — port-forwards 9090)
	docker compose -f docker-compose.prod.yml exec prometheus wget -qO- http://localhost:9090/-/ready && \
		echo "Prometheus ready — visit http://localhost:9090" || echo "Start prod stack first: make deploy"
	docker compose -f docker-compose.prod.yml exec nginx nginx -s reload

# ── Cleanup ───────────────────────────────────────────────────────────────────
clean: ## Remove __pycache__, .pytest_cache, .ruff_cache
	@find . -type d -name __pycache__ -not -path './.venv/*' -exec rm -rf {} + 2>/dev/null || true
	@rm -rf .pytest_cache .ruff_cache htmlcov .coverage
	@echo "Cleaned."
