<div align="center">

# 🔴 DIMITRI

### Autonomous AI-Powered Penetration Testing Platform

*Multi-agent offensive security system with hybrid LLM architecture,*
*real-time Telegram interface, and professional-grade reporting.*

---

[![Python 3.13](https://img.shields.io/badge/Python-3.13-blue?logo=python&logoColor=white)](https://python.org)
[![PentAGI](https://img.shields.io/badge/Engine-PentAGI-red)](https://github.com/vxcontrol/pentagi)
[![DeepSeek](https://img.shields.io/badge/LLM-DeepSeek-purple)](https://deepseek.com)
[![Qwen3](https://img.shields.io/badge/LLM-Qwen3--30B-green)](https://huggingface.co/Qwen)
[![Kali Linux](https://img.shields.io/badge/OS-Kali%20Linux-557C94?logo=kalilinux)](https://kali.org)
[![License](https://img.shields.io/badge/License-Private-gray)]()

</div>

---

## Overview

Dimitri is a fully autonomous penetration testing platform that replaces a $140K+/year enterprise security stack with a single laptop running local AI models. It combines a multi-agent Go backend (PentAGI) with a custom Telegram bot interface, a hybrid LLM routing layer, and a professional PDF reporting engine — all orchestrated through natural language.

You message a Telegram bot. The bot dispatches specialized AI agents. The agents spawn Kali Linux containers, run real security tools (nmap, nuclei, nikto, sqlmap, ffuf), analyze the results, adapt their strategy, and deliver a professional pentest report — all without human intervention.

**This is not a wrapper around ChatGPT. This is a weapon.**

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        OPERATOR (Telegram)                         │
│                     Menu-driven + Natural Language                  │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                    ┌───────────▼───────────┐
                    │    TELEGRAM BOT (Py)   │
                    │  • Menu v2 (inline)    │
                    │  • Guided Scan Engine  │
                    │  • Report Generator    │
                    │  • Persistent Memory   │
                    │  • Access Control      │
                    └───────────┬───────────┘
                                │
                    ┌───────────▼───────────┐
                    │   PentAGI ENGINE (Go)  │
                    │  • 13 specialized      │
                    │    agent roles         │
                    │  • Flow orchestration  │
                    │  • Tool execution      │
                    │  • Vector memory       │
                    └──────┬────────┬───────┘
                           │        │
              ┌────────────▼─┐  ┌───▼────────────┐
              │  LLM ROUTER  │  │ KALI CONTAINER  │
              │  (Python)    │  │  (Docker)       │
              │  ┌─────────┐ │  │  • nmap         │
              │  │DeepSeek │ │  │  • nuclei       │
              │  │  (API)  │ │  │  • nikto        │
              │  │ Orchestr│ │  │  • sqlmap        │
              │  ├─────────┤ │  │  • ffuf          │
              │  │ Qwen 30B│ │  │  • subfinder     │
              │  │ (Local) │ │  │  • sslscan       │
              │  │ Execute │ │  │  • whatweb        │
              │  └─────────┘ │  │  • + 600 tools   │
              │  Auto-fallbk │  └──────────────────┘
              └──────────────┘
```

### The Hybrid Brain

Dimitri's intelligence comes from a dual-model architecture that optimizes for both quality and cost:

| Layer | Model | Location | Role | Latency |
|-------|-------|----------|------|---------|
| **Orchestration** | DeepSeek-Chat | Remote API | Strategy, planning, reflection, advising | ~2s |
| **Execution** | Qwen3-Coder-30B | Local GPU | Terminal commands, code, pentesting, searching | ~0.5s |
| **Embeddings** | Qwen3-1.7B | Local GPU | Vector memory, similarity search | ~0.1s |

The **LLM Router** sits between PentAGI and the models, routing each request by role:

- **Strategic roles** (primary_agent, adviser, reflector, generator, refiner) → DeepSeek API
- **Execution roles** (pentester, coder, installer, searcher, enricher) → Qwen local
- **Automatic fallback**: if DeepSeek fails (timeout, 5xx, rate limit), the router seamlessly degrades to Qwen local — reduced quality, zero downtime

This means the platform **never stops working**, even if the API goes down.

---

## Agent Roles

PentAGI orchestrates **13 specialized agents**, each with its own model, temperature, and token budget:

| Agent | Model | Function |
|-------|-------|----------|
| `primary_agent` | DeepSeek | Master orchestrator — decomposes tasks, assigns subtasks |
| `adviser` | DeepSeek | Reviews agent actions, suggests improvements |
| `reflector` | DeepSeek | Analyzes results, identifies patterns |
| `generator` | DeepSeek | Generates complex artifacts (reports, configs) |
| `refiner` | DeepSeek | Polishes outputs, ensures quality |
| `pentester` | Qwen 30B | Executes security tools via terminal |
| `coder` | Qwen 30B | Writes scripts, parses output, builds exploits |
| `installer` | Qwen 30B | Handles tool installation and environment setup |
| `searcher` | Qwen 30B | OSINT and web reconnaissance |
| `enricher` | Qwen 30B | Cross-references and enriches findings |
| `simple` | Qwen 30B | Quick tasks, classifications |
| `simple_json` | Qwen 30B | Structured JSON output |
| `A` | DeepSeek | Secondary orchestrator |

---

## Features

### 🎯 Telegram Bot — Menu v2

Full-featured Telegram interface with inline keyboard navigation:

| Command | Function |
|---------|----------|
| `/start` | Interactive menu with scan type selection |
| `/recon <target>` | DNS, subdomains, WHOIS, technology fingerprinting |
| `/scan <target>` | Port scanning (nmap -sV -sC, top 1000 ports) |
| `/vuln <target>` | Vulnerability scanning (Nuclei + Nikto) |
| `/web <target>` | Web application testing (headers, directory fuzzing, SQLi) |
| `/ssl <target>` | TLS/SSL audit (sslscan, cipher enumeration, cert analysis) |
| `/full <target>` | Complete 5-phase pentest + automatic PDF report |
| `/gscan <target>` | Guided scan — 5 phases with individual control |
| `/status` | Active flow status |
| `/stop` | Abort current operation |
| `/report` | Generate PDF report from last scan |
| `/nuke` | Nuclear reset — kill all flows, clear DB, restart engine |

**Flow**: Select scan type → Read description → Confirm → Enter target → Watch real-time progress → Receive report.

### 🔄 Guided Scan Engine

The `/gscan` command runs a structured 5-phase penetration test with intelligent phase gating:

```
Phase 1: Reconnaissance (nmap)
    ↓ findings feed into →
Phase 2: Web Fingerprinting (curl, headers)
    ↓ findings feed into →
Phase 3: Vulnerability Scanning (nuclei, nikto)
    ↓ IF vulns found →
Phase 4: Deep Probing (ffuf, sqlmap)
    ↓ all findings aggregate →
Phase 5: Report Assembly (from real data only)
```

Each phase has:
- **Hard timeout** — no infinite loops
- **Command limit** — prevents runaway execution
- **Stall detection** — auto-kills stuck flows
- **Phase gating** — Phase 4 only runs if Phase 3 found vulnerabilities (no wasted time)

### 📊 Professional PDF Reports

ReportLab-powered PDF generation with:
- Executive summary with risk scoring
- Findings categorized by severity (Critical/High/Medium/Low/Info)
- Pie charts and severity distribution tables
- Raw evidence from terminal output
- Remediation recommendations
- Professional dark-themed cover page
- Auto-generated from PentAGI flow data — zero manual work

### 🧠 Persistent Memory

SQLite-backed conversation and state management:
- Message history per user (last 20 messages, 50K char cap)
- Active flow tracking per user
- Scan notes and findings storage
- Cross-session state persistence

### 🔒 Access Control

Whitelist-based authorization via Telegram user IDs. Only authorized operators can interact with the bot. Configurable via `ALLOWED_USERS` environment variable.

---

## Cost Analysis

| Solution | Annual Cost | Notes |
|----------|-------------|-------|
| **Dimitri** | **~$600/yr** | DeepSeek API (~$50/mo), hardware amortized |
| Cobalt Strike | $5,900/user | License only, no AI |
| Nessus Professional | $4,236 | Scanner only, no exploitation |
| Burp Suite Pro | $2,999 | Web-only |
| Metasploit Pro | $15,000 | Manual operation required |
| Pentera | $100,000+ | Enterprise minimum |
| NodeZero | $100,000+ | Enterprise minimum |
| **Human pentest team** | **$140,000+** | 1 senior pentester salary |

Dimitri delivers **autonomous, multi-vector penetration testing** at **0.4% of the cost** of a human operator.

---

## Repository Structure

This repository is a **fork of [PentAGI](https://github.com/vxcontrol/pentagi)** (the multi-agent Go engine) with all Dimitri customizations integrated on top.

```
.
├── backend/                          # PentAGI — Multi-agent Go backend (upstream)
│   ├── pkg/                          #   Agent orchestration, LLM integration
│   ├── migrations/                   #   Database schemas
│   └── docs/                         #   Engine documentation
│
├── frontend/                         # PentAGI — React web UI (upstream)
│   └── src/                          #   Flow monitoring, settings
│
├── docker-compose.yml                # PentAGI containers (engine + pgvector + scraper)
├── Dockerfile                        # PentAGI image build
│
├── dimitri/                          # ── DIMITRI CUSTOM LAYER ──
│   ├── bot/                          # Telegram Bot (Python)
│   │   ├── bot.py                    #   Main bot — 1900 lines, menu v2, smart routing
│   │   ├── guided_scan.py            #   5-phase guided scan engine
│   │   ├── report.py                 #   Professional PDF report generator (ReportLab)
│   │   └── report_md2pdf.py          #   Markdown → PDF converter (WeasyPrint)
│   │
│   ├── router/                       # Hybrid LLM Router
│   │   └── llm-router.py            #   DeepSeek ↔ Qwen routing + auto-fallback
│   │
│   ├── systemd/                      # Service units
│   │   ├── llama-server.service      #   Qwen3-Coder-30B (execution model)
│   │   ├── llama-router.service      #   Qwen3-1.7B (embeddings)
│   │   ├── llm-router.service        #   Hybrid router
│   │   └── pentagi-telegram.service  #   Bot service
│   │
│   ├── extras/                       # Documentation generators
│   │   ├── dimitri_comparative.py    #   Cost comparison report
│   │   ├── dimitri_manual.py         #   Technical manual generator
│   │   ├── dimitri_strategic_manual.py #  Strategic operations manual
│   │   └── glousoft_report.py        #   Client-facing report template
│   │
│   ├── scripts/
│   │   └── setup.sh                  #   Full automated deployment
│   │
│   ├── deepseek-hybrid.provider.yml  # 13-role hybrid model config
│   ├── .env.example                  # Environment template (no secrets)
│   └── requirements.txt              # Python dependencies
│
├── observability/                    # Grafana + Prometheus + Loki (upstream)
├── examples/                         # PentAGI usage examples (upstream)
├── README.md                         # ← You are here
└── README-pentagi.md                 # Original PentAGI documentation
```

---

## Deployment

### Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 8 cores | 16+ cores |
| RAM | 32 GB | 64 GB |
| GPU | 8 GB VRAM (RTX 3070+) | 12+ GB VRAM |
| Storage | 100 GB | 500+ GB |
| OS | Kali Linux / Debian 12+ | Kali Linux |
| Network | Stable internet | Dedicated pentest VLAN |

### Required Models

Download from HuggingFace and place in `/opt/models/`:

| Model | File | Size | Purpose |
|-------|------|------|---------|
| Qwen3-Coder-30B-A3B-abliterated | `Qwen3-Coder-30B-A3B-abliterated-Q4_K_S.gguf` | ~17 GB | Execution (pentester, coder, installer) |
| Qwen3-1.7B | `Qwen3-1.7B-Q8_0.gguf` | ~1.8 GB | Embeddings + fallback |

### Step-by-Step Installation

#### 1. Clone the repository

```bash
git clone https://github.com/dimitriops/pentagi.git dimitri
cd dimitri
```

#### 2. Download models

```bash
sudo mkdir -p /opt/models
cd /opt/models

# Qwen3-Coder-30B (execution model)
huggingface-cli download bartowski/Qwen3-Coder-30B-A3B-abliterated-GGUF \
  Qwen3-Coder-30B-A3B-abliterated-Q4_K_S.gguf --local-dir .

# Qwen3-1.7B (embeddings)
huggingface-cli download bartowski/Qwen3-1.7B-GGUF \
  Qwen3-1.7B-Q8_0.gguf --local-dir .
```

#### 3. Run setup

```bash
sudo bash dimitri/scripts/setup.sh
```

#### 4. Configure secrets

**PentAGI environment** (`/opt/pentagi/.env`):
```env
# LLM Router (runs on host, containers access via Docker bridge IP)
LLM_SERVER_URL=http://172.17.0.1:8090/v1
LLM_SERVER_KEY=not-needed
LLM_SERVER_MODEL=qwen3-coder-30b
LLM_SERVER_PROVIDER=openai

# Embeddings (Qwen 1.7B on host)
EMBEDDING_URL=http://172.17.0.1:8081/v1
EMBEDDING_MODEL=Qwen3-1.7B-Q8_0.gguf

# Kali container image
DOCKER_DEFAULT_IMAGE=vxcontrol/kali-linux:latest
```

**LLM Router** — set DeepSeek API key in `/etc/systemd/system/llm-router.service`:
```ini
Environment=DEEPSEEK_API_KEY=sk-your-deepseek-api-key-here
```

> **Getting a DeepSeek API key:**
> 1. Go to [platform.deepseek.com](https://platform.deepseek.com)
> 2. Sign up / Sign in
> 3. Navigate to API Keys → Create new key
> 4. Fund your account (pay-as-you-go, ~$0.27/M input tokens)

**Telegram Bot** — create `/opt/pentagi-telegram/start.sh`:
```bash
#!/bin/bash
export TELEGRAM_TOKEN="your-bot-token-from-botfather"
export PENTAGI_TOKEN="your-pentagi-jwt-token"
export PENTAGI_URL="https://localhost:8443"
export LLM_URL="http://localhost:8080"
export ROUTER_URL="http://localhost:8081"
export ALLOWED_USERS="your-telegram-user-id"
exec /opt/pentagi-telegram/bin/python3 -u /opt/pentagi-telegram/bot.py
```

> **Getting a Telegram Bot token:**
> 1. Message [@BotFather](https://t.me/BotFather) on Telegram
> 2. `/newbot` → choose name and username
> 3. Copy the token
>
> **Getting your Telegram user ID:**
> Message [@userinfobot](https://t.me/userinfobot) and it will reply with your ID.

> **Getting the PentAGI JWT token:**
> After PentAGI is running, access `https://localhost:8443`, create an API token in the settings panel, and copy the JWT.

#### 5. Start everything

```bash
# Start LLM servers
sudo systemctl start llama-server    # Qwen 30B (takes ~30s to load)
sudo systemctl start llama-router    # Qwen 1.7B
sudo systemctl start llm-router      # Hybrid router

# Start PentAGI
cd /opt/pentagi && docker compose up -d

# Start Telegram bot
sudo systemctl start pentagi-telegram

# Enable on boot (optional)
sudo systemctl enable llama-server llama-router llm-router pentagi-telegram
```

#### 6. Verify

```bash
# Check all services
systemctl is-active llama-server llama-router llm-router pentagi-telegram

# Check LLM health
curl -s http://localhost:8080/health | jq .status    # Qwen 30B
curl -s http://localhost:8081/health | jq .status    # Qwen 1.7B
curl -s http://localhost:8090/health | jq .status    # Router

# Check containers
docker ps --format '{{.Names}} {{.Status}}'

# Check GPU
nvidia-smi --query-gpu=memory.used,memory.total --format=csv
```

---

## Operations

### Health Check

```bash
# All services at once
for svc in llama-server llama-router llm-router pentagi-telegram; do
  echo "$svc: $(systemctl is-active $svc)"
done

# Docker containers
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'

# GPU memory
nvidia-smi --query-gpu=memory.used,memory.total,utilization.gpu --format=csv
```

### Full Restart

```bash
sudo systemctl restart llama-server llama-router llm-router pentagi-telegram
cd /opt/pentagi && docker compose up -d
```

### Kill Zombie Flows

PentAGI sometimes leaves orphaned flows running. Nuclear cleanup:

```bash
# Mark all active flows as failed
docker exec pgvector psql -U postgres pentagidb \
  -c "UPDATE flows SET status='failed' WHERE status IN ('running','waiting','created');"

# Kill orphan containers
docker ps -q --filter "name=pentagi-terminal-" | xargs -r docker stop
docker ps -aq --filter "name=pentagi-terminal-" | xargs -r docker rm

# Restart PentAGI
cd /opt/pentagi && docker compose restart pentagi
```

### View Logs

```bash
journalctl -u pentagi-telegram -f           # Bot
journalctl -u llm-router -f                 # LLM Router
docker logs pentagi -f --since 5m           # PentAGI engine
journalctl -u llama-server --since "5m ago" # Qwen 30B
```

---

## Known Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| PentAGI loops researching instead of scanning | Vague prompts trigger searcher→reflector cycle | Use menu-driven scans (action-oriented prompts with explicit commands) |
| Zombie flows consuming LLM slots | `PUT /flows/{id} stop` doesn't kill goroutines | `/nuke` command: DB reset + container kill + engine restart |
| `docker restart pentagi` doesn't apply .env changes | Docker restart ≠ compose up (doesn't re-read .env) | Always use `docker compose up -d pentagi` |
| Context overflow (500K+ tokens) | Long-running flows accumulate history | Built-in summarizer + execution monitor + stall detector |
| DNS resolution fails in router | Tailscale DNS (100.100.100.100) incompatible with aiodns | ThreadedResolver (uses system `getaddrinfo`) |
| iptables stale after compose up | Docker bridge IPs change on each `compose up` | Use subnet ranges (172.16.0.0/12) in iptables rules |

---

## Security Considerations

- **Access control** — Telegram user ID whitelist. Unauthorized users are silently ignored.
- **No secrets in code** — All credentials via environment variables or start scripts (git-ignored).
- **Local execution** — Qwen models run 100% on-device. No data leaves the machine (except DeepSeek API calls for orchestration).
- **Container isolation** — Pentest tools run inside ephemeral Kali Docker containers, not on the host.
- **TLS** — PentAGI API served over HTTPS (self-signed cert, localhost only).

> ⚠️ **This is an offensive security tool.** Only use it against systems you own or have explicit written authorization to test. Unauthorized penetration testing is illegal.

---

## Technical Stats

| Metric | Value |
|--------|-------|
| Bot codebase | 1,900 lines |
| Guided scan engine | 626 lines |
| Report generator | 854 lines |
| LLM router | 329 lines |
| Total codebase | ~10,000 lines |
| Agent roles | 13 |
| Scan modes | 7 (recon, port, vuln, web, ssl, full, guided) |
| Supported tools | 600+ (Kali Linux toolset) |
| Bugs found & fixed | 54+ across 9 audit rounds |
| Test checks passed | 214+ |

---

<div align="center">

**Built for operators who want results, not dashboards.**

</div>
