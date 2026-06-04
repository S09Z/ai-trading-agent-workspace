.DEFAULT_GOAL := help
.PHONY: help install up down restart logs ps start cockpit frontend discord-bot cycle sentiment digest digest-dry test test-cov lint fmt check clean reset deploy ssl-init ssl-renew

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

discord-bot: ## Start Discord bot (listens for !commands)
	$(UV) python -m intelligence.discord_bot

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
	docker compose -f docker-compose.prod.yml exec nginx nginx -s reload

# ── Cleanup ───────────────────────────────────────────────────────────────────
clean: ## Remove __pycache__, .pytest_cache, .ruff_cache
	@find . -type d -name __pycache__ -not -path './.venv/*' -exec rm -rf {} + 2>/dev/null || true
	@rm -rf .pytest_cache .ruff_cache htmlcov .coverage
	@echo "Cleaned."
