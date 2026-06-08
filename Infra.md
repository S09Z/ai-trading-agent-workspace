# Infrastructure

## Dev services

Managed by `docker-compose.yml` — PostgreSQL/TimescaleDB, Qdrant, Redis.

| Command | Description |
| --- | --- |
| `make up` | Start all dev services (detached) |
| `make down` | Stop all services |
| `make restart` | Restart all services |
| `make logs` | Follow logs (Ctrl+C to stop) |
| `make ps` | Show service status and health checks |
| `make reset` | ⚠ Destroy all volumes and restart — **wipes all data** |
| `make discord-bot` | Start Discord bot (listens for `!commands`) |
| `make celery-worker` | Start Celery worker (processes queued tasks) |

## Service ports

| Service | Port | UI |
| --- | --- | --- |
| PostgreSQL (TimescaleDB) | `5432` | — |
| Qdrant | `6333` (REST) · `6334` (gRPC) | <http://localhost:6333/dashboard> |
| Redis | `6780` | — |
| Cockpit API | `8000` | <http://localhost:8000/docs> |
| Cockpit UI (Next.js) | `3000` | <http://localhost:3000> |

---

## Production deployment

Managed by `docker-compose.prod.yml` — 9 services: postgres, qdrant, redis, cockpit, celery-worker, celery-beat, frontend, nginx, discord-bot.

### Setup

1. Copy the env template and fill in your secrets:
   ```bash
   cp .env.prod.example .env.prod
   ```

2. Required variables in `.env.prod`:
   ```
   APP_ENV=production
   DOMAIN=your.domain.com
   POSTGRES_PASSWORD=<strong password>
   ANTHROPIC_API_KEY=sk-ant-...
   NEXT_PUBLIC_API_URL=https://your.domain.com/api
   NEXT_PUBLIC_WS_URL=wss://your.domain.com/ws
   ```

### Deploy commands

| Command | Description |
| --- | --- |
| `make deploy` | Pull latest, rebuild containers, restart production stack |
| `make ssl-init` | Obtain Let's Encrypt cert and enable HTTPS (reads `DOMAIN` from `.env.prod`) |
| `make ssl-renew` | Renew certificates and reload nginx |

### Deploy flow

```bash
# First deploy (HTTP)
make deploy

# Enable HTTPS — requires APP_ENV=production and DOMAIN= in .env.prod
make ssl-init

# Rebuild frontend with https:// URLs, then restart
# (update NEXT_PUBLIC_API_URL and NEXT_PUBLIC_WS_URL in .env.prod first)
make deploy
```

### How nginx picks the config

| `APP_ENV` | Nginx config | Behaviour |
| --- | --- | --- |
| `development` | `nginx/nginx.conf` | HTTP proxy only |
| `production` | `nginx/nginx-ssl.conf` | HTTP → HTTPS redirect + TLS 1.2/1.3 |

### SSL certificate renewal (crontab on VPS)

```
0 3 * * * cd /path/to/repo && make ssl-renew >> /var/log/certbot-renew.log 2>&1
```

---

## Oracle Cloud (OCI) Free Tier Setup

**Recommended shape:** VM.Standard.A1.Flex — 4 OCPU / 24 GB RAM (always free). ARM architecture; Docker pulls ARM variants automatically.

### One-time instance setup (SSH in manually)

```bash
sudo apt update && sudo apt install -y docker.io docker-compose-plugin git make
sudo usermod -aG docker ubuntu && newgrp docker

# Clone repo
git clone https://github.com/<your-org>/ai-trading-agent-workspace.git
cd ai-trading-agent-workspace

# Fill in secrets
cp .env.prod.example .env.prod
nano .env.prod   # set DOMAIN, POSTGRES_PASSWORD, ANTHROPIC_API_KEY, etc.

make deploy
```

**OCI Security List** — open inbound TCP ports in VCN → Subnet → Security List:

- 22 (SSH), 80 (HTTP), 443 (HTTPS)

**SSL note:** Let's Encrypt (`make ssl-init`) requires a real domain name — it won't issue certs for bare IPs. Use `APP_ENV=development` (HTTP) if you don't have a domain yet.

---

## GitHub Actions — Automated Deploy

Push to `main` triggers `.github/workflows/deploy.yml`, which SSH-deploys to the OCI instance.

### Required GitHub Secrets

Add under repo **Settings → Secrets and variables → Actions**:

| Secret | Value |
|---|---|
| `OCI_HOST` | OCI instance public IP |
| `OCI_USER` | `ubuntu` (OCI default for Ubuntu images) |
| `OCI_SSH_KEY` | Private SSH key (matching the public key in `~/.ssh/authorized_keys` on the instance) |

### Manual trigger

The workflow supports `workflow_dispatch` — you can also trigger it from the Actions tab without pushing.

### Local equivalent

```bash
make deploy-ci   # same as deploy but skips git pull (GitHub Actions already checked out the code)
```

---

## VPS Resource Requirements
Minimum VPS: 2 vCPU / 4 GB RAM / 40 GB SSD
แนะนำ: 4 vCPU / 8 GB RAM / 80 GB SSD (รองรับ corpus growth 12 เดือน)

### Per-service breakdown

| Service | CPU (idle/peak) | RAM | Disk |
|---|---|---|---|
| **postgres** (TimescaleDB) | 0.05 / 0.3 vCPU | 256 – 512 MB | grows ~50 MB/month (logs + signals) |
| **qdrant** | 0.05 / 0.5 vCPU | 300 – 600 MB | grows ~200 MB/month (news embeddings) |
| **redis** | 0.02 / 0.1 vCPU | ≤ 512 MB (hard cap in config) | ≤ 512 MB (AOF) |
| **cockpit** (FastAPI/uvicorn) | 0.02 / 0.1 vCPU | 100 – 200 MB | — |
| **celery-worker** | 0.1 / **1.5 vCPU** | **600 MB – 1.2 GB** | — |
| **celery-beat** | 0.01 vCPU | 80 – 120 MB | — |
| **frontend** (Next.js standalone) | 0.02 / 0.1 vCPU | 150 – 250 MB | — |
| **nginx** | 0.01 vCPU | 30 – 50 MB | — |
| **discord-bot** | 0.01 / 0.05 vCPU | 80 – 150 MB | — |
| OS + Docker daemon | — | ~300 MB | — |

> **celery-worker** is the heaviest service. It loads a sentence-transformers embedding model (~400 MB) on startup and runs CPU-bound inference during each agent cycle. Peak CPU spikes to ~1.5 vCPU for 10–30 s per cycle.

### Aggregate totals

| Resource | Minimum (bare) | Recommended (headroom) |
|---|---|---|
| **vCPU** | 2 | 4 |
| **RAM** | 4 GB | 8 GB |
| **SSD** | 40 GB | 80 GB |
| **Bandwidth** | 1 TB/month | 2 TB/month |

### What's driving each number

**CPU — 4 vCPU recommended**
The agent cycle (NewsHunter → MarketWatch → SentimentAnalyst → RiskMonitor → ResearchAnalyst) runs every 1–5 minutes. Each cycle fires sentence-transformer inference + optional Claude API calls in the celery-worker. Running only 2 vCPU means the OS + DB + worker compete during peak, causing Celery task latency to creep up.

**RAM — 8 GB recommended**
The sentence-transformers model alone loads ~400 MB into the worker process. Add TimescaleDB shared_buffers (~256 MB default), Qdrant's in-memory vector index (grows with corpus), and Redis's 512 MB cap → you're at ~2.5 GB in steady state with 4 GB. 8 GB gives comfortable headroom for corpus growth and occasional OOM spikes during model inference.

**SSD — 80 GB recommended**
| Item | Size |
|---|---|
| Docker images (all services) | ~5 GB |
| Python deps + app code | ~2 GB |
| Next.js build artifacts | ~0.5 GB |
| postgres_data (12-month projection) | ~10 GB |
| qdrant_data (12-month projection) | ~5 GB |
| redis AOF | ≤ 0.5 GB |
| Logs + certbot certs | ~1 GB |
| **Total (12-month)** | **~24 GB** |

40 GB covers day-1 comfortably; 80 GB avoids a disk-resize operation at the 6-month mark.

### Minimum viable VPS spec

```
vCPU:  2 cores   (x86-64, single-threaded perf matters for Python)
RAM:   4 GB
SSD:   40 GB NVMe
OS:    Ubuntu 22.04 LTS / Debian 12
```

### Recommended production VPS spec

```
vCPU:  4 cores
RAM:   8 GB
SSD:   80 GB NVMe
OS:    Ubuntu 22.04 LTS / Debian 12
```

### If running local LLM (`USE_LOCAL_LLM=true` with Ollama + qwen3)

Ollama keeps the model in RAM. qwen3:latest (4-bit) requires an additional **~5–8 GB RAM** and benefits heavily from extra CPU cores. Minimum spec jumps to **16 GB RAM / 4–8 vCPU** — or a GPU-enabled VPS.
