#!/bin/bash
# ============================================================
#  Dimitri — Full Deployment Script
#  Deploys PentAGI + Telegram Bot + LLM Router + Local Models
# ============================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DIMITRI_DIR="${REPO_ROOT}/dimitri"

echo "═══════════════════════════════════════════"
echo "  DIMITRI — Autonomous Pentest Platform"
echo "  Full Deployment"
echo "═══════════════════════════════════════════"
echo ""

# --- Pre-checks ---
echo "[PRE] Checking requirements..."
command -v docker >/dev/null 2>&1 || { echo "ERROR: docker not found. Install Docker first."; exit 1; }
command -v docker compose >/dev/null 2>&1 || { echo "ERROR: docker compose not found."; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 not found."; exit 1; }
command -v nvidia-smi >/dev/null 2>&1 || echo "WARNING: nvidia-smi not found. GPU acceleration may not work."

GPU_MEM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>/dev/null | head -1 || echo "0")
RAM_GB=$(free -g | awk '/^Mem:/{print $2}')
echo "  GPU VRAM: ${GPU_MEM} MB"
echo "  System RAM: ${RAM_GB} GB"
echo ""

# --- 1. Bot venv + deps ---
echo "[1/6] Setting up Telegram bot..."
python3 -m venv /opt/pentagi-telegram
/opt/pentagi-telegram/bin/pip install --quiet -r "${DIMITRI_DIR}/requirements.txt"
cp -v "${DIMITRI_DIR}/bot/"*.py /opt/pentagi-telegram/
echo "  ✓ Bot installed"

# --- 2. LLM Router ---
echo "[2/6] Installing LLM Router..."
cp -v "${DIMITRI_DIR}/router/llm-router.py" /opt/llm-router.py
/opt/pentagi-telegram/bin/pip install --quiet aiohttp
echo "  ✓ Router installed"

# --- 3. Systemd units ---
echo "[3/6] Installing systemd services..."
cp -v "${DIMITRI_DIR}/systemd/"*.service /etc/systemd/system/
systemctl daemon-reload
echo "  ✓ Services registered"

# --- 4. PentAGI provider config ---
echo "[4/6] Configuring PentAGI provider..."
cp -v "${DIMITRI_DIR}/deepseek-hybrid.provider.yml" "${REPO_ROOT}/deepseek-hybrid.provider.yml"
echo "  ✓ Hybrid provider config installed"

# --- 5. Models directory ---
echo "[5/6] Preparing models directory..."
mkdir -p /opt/models
echo "  Models directory: /opt/models/"
echo "  Download required models:"
echo "    → Qwen3-Coder-30B-A3B-abliterated-Q4_K_S.gguf (~17 GB)"
echo "    → Qwen3-1.7B-Q8_0.gguf (~1.8 GB)"

# --- 6. Docker SSL certs ---
echo "[6/6] Checking SSL certs..."
if [ ! -d "${REPO_ROOT}/docker-ssl" ]; then
  mkdir -p "${REPO_ROOT}/docker-ssl"
  openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
    -keyout "${REPO_ROOT}/docker-ssl/key.pem" \
    -out "${REPO_ROOT}/docker-ssl/cert.pem" \
    -subj "/CN=localhost" 2>/dev/null
  echo "  ✓ Self-signed SSL certs generated"
else
  echo "  ✓ SSL certs already exist"
fi

echo ""
echo "═══════════════════════════════════════════"
echo "  SETUP COMPLETE"
echo "═══════════════════════════════════════════"
echo ""
echo "Next steps:"
echo ""
echo "  1. Configure secrets:"
echo "     cp dimitri/.env.example /opt/pentagi-telegram/start.sh"
echo "     nano /opt/pentagi-telegram/start.sh"
echo "     chmod 700 /opt/pentagi-telegram/start.sh"
echo ""
echo "  2. Set DeepSeek API key in systemd:"
echo "     sudo systemctl edit llm-router"
echo "     [Service]"
echo "     Environment=DEEPSEEK_API_KEY=sk-your-key"
echo ""
echo "  3. Configure PentAGI .env:"
echo "     cp .env.example .env"
echo "     nano .env"
echo ""
echo "  4. Download models to /opt/models/"
echo ""
echo "  5. Start everything:"
echo "     sudo systemctl start llama-server llama-router llm-router"
echo "     docker compose up -d"
echo "     sudo systemctl start pentagi-telegram"
echo ""
