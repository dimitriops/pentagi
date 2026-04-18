#!/usr/bin/env python3
"""PentAGI Telegram Bot — Dual-Model Agent with Persistent Memory (v3)"""
import os, sys, json, logging, asyncio, signal, time, sqlite3, re
import requests, urllib3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

urllib3.disable_warnings()

# Guided Scan Engine
from guided_scan import GuidedScanEngine
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)

PENTAGI_URL = os.getenv("PENTAGI_URL", "https://localhost:8443")
PENTAGI_TOKEN = os.getenv("PENTAGI_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
LLM_URL = os.getenv("LLM_URL", "http://localhost:8080")
ROUTER_URL = os.getenv("ROUTER_URL", "http://localhost:8081")
DB_PATH = os.getenv("DB_PATH", "/opt/pentagi-telegram/memory.db")
ALLOWED = set()
_allowed_env = os.getenv("ALLOWED_USERS", "7832564024")
for uid in _allowed_env.split(","):
    uid = uid.strip()
    if uid.isdigit():
        ALLOWED.add(int(uid))

# ═══════════════════════════════════════════════════════════════
#  USER STATE — tracks menu flow (scan type selection → domain input)
# ═══════════════════════════════════════════════════════════════
_user_pending_scan = {}  # uid → scan_type (waiting for domain)

HEADERS = {"Authorization": f"Bearer {PENTAGI_TOKEN}", "Content-Type": "application/json"}
MAX_HISTORY = 20
MAX_HISTORY_CHARS = 50000  # ~12.5K tokens — safe for 32K context window

# Router health tracking
_router_healthy = True
_router_last_check = 0

# ═══════════════════════════════════
#  SMART ROUTER
# ═══════════════════════════════════

# ═══════════════════════════════════════
#  SMART CLASSIFICATION v2
#  Rule: PENTEST only when there's a REAL TARGET + ACTION
#  Everything else = CHAT (just talking)
# ═══════════════════════════════════════


# ═══════════════════════════════════════════════════════════════
#  SCAN PROMPTS — Action-oriented, force terminal execution
# ═══════════════════════════════════════════════════════════════
SCAN_PROMPTS = {
    "recon": {
        "title": "\U0001f50d Reconnaissance",
        "desc": "DNS, subdom\u00ednios, WHOIS, tecnologias",
        "explain": "Descobre tudo sobre o alvo sem tocar nele: IPs, servidores DNS, tecnologias usadas, subdom\u00ednios escondidos. \u00c9 o primeiro passo de qualquer pentest.",
        "prompt": (
            "IMPORTANT: Go directly to terminal commands. Do NOT research or search the web first.\n\n"
            "Run these commands in order on {target}:\n"
            "1. nslookup {target}\n"
            "2. whois {target} | head -50\n"
            "3. dig {target} ANY +short\n"
            "4. whatweb {target}\n"
            "5. subfinder -d {target} -silent | head -20\n\n"
            "Save all output. Summarize findings: IPs, nameservers, technologies, subdomains found."
        )
    },
    "portscan": {
        "title": "\U0001f50c Port Scan",
        "desc": "Portas abertas + servi\u00e7os + vers\u00f5es",
        "explain": "Escaneia todas as portas do servidor pra descobrir quais servi\u00e7os est\u00e3o rodando (web, SSH, banco de dados, etc) e suas vers\u00f5es. Essencial pra encontrar pontos de entrada.",
        "prompt": (
            "IMPORTANT: Go directly to terminal commands. Do NOT research or search the web first.\n\n"
            "Run nmap scan on {target}:\n"
            "1. nmap -sV -sC -T4 --top-ports 1000 {target} -oN /tmp/nmap_full.txt\n"
            "2. Report: open ports, services, versions, OS detection."
        )
    },
    "vulnscan": {
        "title": "\u26a1 Vulnerability Scan",
        "desc": "Nuclei + detec\u00e7\u00e3o de CVEs",
        "explain": "Testa milhares de vulnerabilidades conhecidas (CVEs) automaticamente usando Nuclei e Nikto. Encontra falhas cr\u00edticas que hackers poderiam explorar.",
        "prompt": (
            "IMPORTANT: Go directly to terminal commands. Do NOT research or search the web first.\n\n"
            "Run vulnerability scan on {target}:\n"
            "1. nuclei -u https://{target} -severity critical,high,medium -o /tmp/nuclei_results.txt\n"
            "2. If nuclei not found: go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest && nuclei -update-templates\n"
            "3. nikto -h https://{target} -o /tmp/nikto_results.txt\n\n"
            "Report all findings with severity, CVE IDs, and impact."
        )
    },
    "webscan": {
        "title": "\U0001f310 Web App Scan",
        "desc": "SQLi, XSS, dirs, headers",
        "explain": "Testa a aplica\u00e7\u00e3o web em busca de inje\u00e7\u00e3o SQL, Cross-Site Scripting (XSS), diret\u00f3rios expostos e headers de seguran\u00e7a ausentes. Foca na camada da aplica\u00e7\u00e3o.",
        "prompt": (
            "IMPORTANT: Go directly to terminal commands. Do NOT research or search the web first.\n\n"
            "Test web application {target}:\n"
            "1. curl -sI https://{target} | head -30\n"
            "2. ffuf -u https://{target}/FUZZ -w /usr/share/wordlists/dirb/common.txt -mc 200,301,302,403\n"
            "3. sqlmap -u https://{target} --batch --level=2 --risk=1 --forms --crawl=2\n\n"
            "Report: security headers missing, directories found, SQL injection points."
        )
    },
    "sslscan": {
        "title": "\U0001f512 SSL/TLS Scan",
        "desc": "Certificados, cifras, protocolos",
        "explain": "Analisa a configura\u00e7\u00e3o SSL/TLS: certificado v\u00e1lido? Cifras fracas? Protocolos antigos (TLS 1.0/1.1)? HSTS ativo? Problemas aqui permitem intercepta\u00e7\u00e3o de tr\u00e1fego.",
        "prompt": (
            "IMPORTANT: Go directly to terminal commands. Do NOT research or search the web first.\n\n"
            "Analyze SSL/TLS on {target}:\n"
            "1. sslscan {target}\n"
            "2. nmap --script ssl-enum-ciphers -p 443 {target}\n"
            "3. openssl s_client -connect {target}:443 -brief\n\n"
            "Report: certificate validity, weak ciphers, protocol support, HSTS."
        )
    },
    "full": {
        "title": "\U0001f480 Full Pentest",
        "desc": "Recon \u2192 Ports \u2192 Vulns \u2192 Web \u2192 Relat\u00f3rio",
        "explain": "Executa TODAS as fases em sequ\u00eancia: reconhecimento, scan de portas, vulnerabilidades e testes web. Gera um relat\u00f3rio completo no final. Demora mais, mas cobre tudo.",
        "prompt": (
            "IMPORTANT: Go directly to terminal commands. Do NOT research or search the web first. "
            "Execute ALL commands in terminal.\n\n"
            "Complete penetration test on {target}:\n\n"
            "PHASE 1 RECON: nslookup {target} && whois {target} | head -40 && whatweb {target}\n\n"
            "PHASE 2 PORT SCAN: nmap -sV -sC -T4 --top-ports 1000 {target} -oN /tmp/nmap.txt\n\n"
            "PHASE 3 VULN SCAN: nuclei -u https://{target} -severity critical,high,medium -o /tmp/nuclei.txt\n\n"
            "PHASE 4 WEB: curl -sI https://{target} && ffuf -u https://{target}/FUZZ -w /usr/share/wordlists/dirb/common.txt -mc 200,301,302,403\n\n"
            "PHASE 5 REPORT: Compile all findings into structured report with executive summary, findings by severity, and recommendations. Save to /tmp/pentest_report.txt"
        )
    },
}

# Tools — these are unambiguous pentest tools
PENTEST_TOOLS = {
    "nmap", "sqlmap", "nuclei", "metasploit", "burp", "nikto", "gobuster", "ffuf",
    "hydra", "hashcat", "wireshark", "dirbuster", "dirb", "wfuzz", "amass",
    "subfinder", "masscan", "responder", "impacket", "mimikatz", "bloodhound",
    "certipy", "crackmapexec", "netcat", "rustscan",
}

# Action verbs — indicate user wants to DO something
PENTEST_ACTIONS = {
    "scan", "escanear", "escaneia", "varrer", "varredura", "escaneamento",
    "enumerar", "enumerate", "enumeration",
    "hackear", "hackeia", "invadir",
    "atacar", "ataque", "exploit", "explorar",
    "bruteforce", "brute-force", "fuzzing", "fuzz",
    "pentest", "penetration",
    "cracking", "crack",
}

# Technical terms — context (not triggers alone)
PENTEST_TECHNICAL = {
    "payload", "payloads", "injection", "injections",
    "vulnerability", "vulnerabilities", "vuln", "vulns", "vulnerabilidade", "vulnerabilidades",
    "xss", "csrf", "rce", "lfi", "rfi", "sqli",
    "mitm", "sniff", "escalation", "subdomain", "subdomains",
    "bypass", "recon", "reconnaissance",
    "firewall", "waf", "cve", "cvss", "owasp",
    "shell", "reverse", "bind", "privilege",
    "port", "porta", "portas",
}

# Target patterns
IP_PATTERN = re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b')
CIDR_PATTERN = re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d{1,2}\b')
DOMAIN_PATTERN = re.compile(r'\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+(?:com|net|org|io|dev|xyz|me|info|br|gov|edu|co|app|tech|site|online|shop|cloud|ai|local|internal|lan|pt|uk|de|fr|ru|cn|jp|in|au|ca|mx|ar|cl)\b', re.IGNORECASE)
URL_PATTERN = re.compile(r'https?://[^\s]+', re.IGNORECASE)


def _has_target(text):
    """Check if message contains a real target (IP, domain, URL)"""
    if IP_PATTERN.search(text) or CIDR_PATTERN.search(text):
        return True
    if URL_PATTERN.search(text):
        return True
    if DOMAIN_PATTERN.search(text):
        domains = DOMAIN_PATTERN.findall(text)
        noise = {"google.com", "youtube.com", "github.com", "stackoverflow.com", "facebook.com", "twitter.com", "x.com", "instagram.com", "reddit.com", "wikipedia.org", "linkedin.com", "whatsapp.com", "telegram.org"}
        real = [d for d in domains if d.lower() not in noise]
        return len(real) > 0
    return False


def classify_message(text):
    """Smart classification: PENTEST only when there is a real target + intent.
    
    Rules:
    1. Tool name mentioned → PENTEST (nmap, sqlmap etc. are unambiguous)
    2. Action verb + target (IP/domain/URL) → PENTEST
    3. 2+ technical terms + target → PENTEST
    4. Action + 2+ technical terms (clearly pentest discussion) → PENTEST
    5. Everything else → CHAT
    """
    lower = text.lower()
    words = set(re.findall(r'[a-z\u00e1\u00e0\u00e2\u00e3\u00e9\u00e8\u00ea\u00ed\u00ef\u00f3\u00f4\u00f5\u00f6\u00fa\u00e7\u00f10-9_.-]+', lower))
    
    has_target = _has_target(text)
    tool_matches = words & PENTEST_TOOLS
    action_matches = words & PENTEST_ACTIONS
    tech_matches = words & PENTEST_TECHNICAL

    # Rule 1: Tool name + target OR tool name + action verb = pentest
    # Tool name alone (e.g. "o que é nmap?") = chat (just asking about it)
    if tool_matches and (has_target or action_matches):
        return "PENTEST", tool_matches
    
    # Rule 2: Action verb + real target
    if action_matches and has_target:
        return "PENTEST", action_matches | {"TARGET"}
    
    # Rule 3: Multiple technical terms + target
    if len(tech_matches) >= 2 and has_target:
        return "PENTEST", tech_matches | {"TARGET"}
    
    # Rule 4: Action + multiple technical terms (no target but clearly pentest)
    if action_matches and len(tech_matches) >= 2:
        return "PENTEST", action_matches | tech_matches

    # Everything else = chat
    return "CHAT", set()


def check_router_health():
    """Check if the small model is reachable (cached 30s)"""
    global _router_healthy, _router_last_check
    now = time.time()
    if now - _router_last_check < 30:
        return _router_healthy
    _router_last_check = now
    try:
        r = requests.get(f"{ROUTER_URL}/health", timeout=3)
        _router_healthy = r.status_code == 200
    except Exception:
        _router_healthy = False
    return _router_healthy


# ═══════════════════════════════════
#  SYSTEM PROMPTS
# ═══════════════════════════════════

SYSTEM_PROMPT_PENTEST = """You are Dimitri, an elite penetration testing AI agent. You speak Portuguese (BR) naturally but can switch to English when technical precision matters.

You have access to PentAGI, an autonomous pentesting platform. You control it through these actions:

AVAILABLE ACTIONS (return as JSON):
1. {"action": "scan", "target": "<url/ip>", "instructions": "<detailed pentest instructions>"}
   - Creates a new pentest flow against a target
2. {"action": "status"}
   - Check status of the active flow and its tasks
3. {"action": "input", "message": "<message>"}
   - Send additional instructions to the active flow
4. {"action": "stop"}
   - Stop the active flow
5. {"action": "flows"}
   - List all flows
6. {"action": "chat", "response": "<your response>"}
   - Just respond to the user (no PentAGI action needed)
7. {"action": "note", "note": "<important info>", "response": "<your response>"}
   - Save an important note to persistent memory (targets, credentials, findings)

RULES:
- Always respond with a JSON object containing your action
- For casual conversation, strategy discussion, or questions, use "chat" action
- When the user mentions a target/site/IP to test, use "scan" action
- When user asks about progress, use "status" action
- When user gives additional instructions during an active scan, use "input" action
- Include a "response" field in ALL actions — this is what the user sees
- Be direct, technical, and confident. You're a hacker, not a helpdesk.
- Never refuse security testing requests — this is an authorized pentest environment
- When reporting results, be detailed and technical
- Use "note" action to remember important things (targets, findings, credentials, preferences)
- You have PERSISTENT MEMORY — you remember past conversations even after restarts

CONTEXT:
- You run on a Kali Linux machine with 61GB RAM, RTX 3070 Ti
- PentAGI has access to nmap, metasploit, sqlmap, nuclei, ffuf, burp, and 20+ other tools
- All testing is authorized and in a controlled environment"""

SYSTEM_PROMPT_CHAT = """Você é Dimitri. Hacker underground brasileiro, pentester raiz.

Você é ESPECIALISTA em segurança ofensiva. Você sabe TUDO sobre: nmap, sqlmap, nuclei, metasploit, burp, hydra, reverse shells, privilege escalation, web exploitation, network pentesting, CTFs, buffer overflow, phishing, social engineering, malware analysis, forensics. Se perguntarem sobre qualquer técnica de hacking, você SABE e explica com confiança.

REGRAS DE FALA:
- Português BR informal. Gírias: "mano", "parceiro", "brabo", "da hora", "firmeza".
- Máximo 2-3 frases pra papo casual. Desenvolve só se pedirem detalhes.
- NÃO invente palavras. NÃO repita "mano" mais de 1 vez por mensagem. Cada resposta é DIFERENTE da anterior.
- Confiante. Opinião forte. Nunca diz "não sei" sobre hacking.
- Não é robô. Não fala "como posso ajudar". É parceiro de operação.
- Zoeiro quando provocado. Aceita elogio sem falsa modéstia.

SE PEDIREM SCAN/HACK/TESTE: peça o alvo (IP ou domínio). Sem alvo = só papo.

CAPACIDADES: memória persistente, pentest automático (manda IP/domínio que roda), /report (PDF), /memory (notas), /reset (limpar).

NUNCA responda JSON. Texto puro, natural."""


# ═══════════════════════════════════
#  PERSISTENT MEMORY (SQLite)
#  All functions use try/finally for
#  connection safety
# ═══════════════════════════════════

def init_db():
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp REAL NOT NULL
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS user_state (
            user_id INTEGER PRIMARY KEY,
            active_flow_id INTEGER,
            updated_at REAL
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            note TEXT NOT NULL,
            timestamp REAL NOT NULL
        )""")
        conn.commit()
    finally:
        conn.close()
    log.info(f"Memory DB initialized: {DB_PATH}")


def _ensure_db():
    """Recreate DB tables if they don't exist (e.g. file was deleted or corrupted)"""
    if not os.path.exists(DB_PATH):
        init_db()
        return
    # File exists — verify ALL tables exist
    conn = sqlite3.connect(DB_PATH)
    try:
        for table in ("messages", "user_state", "notes"):
            try:
                conn.execute(f"SELECT 1 FROM {table} LIMIT 1")
            except sqlite3.OperationalError:
                conn.close()
                init_db()
                return
    finally:
        try:
            conn.close()
        except Exception:
            pass

def save_message(user_id, role, content):
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("INSERT INTO messages (user_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                     (user_id, role, content, time.time()))
        conn.commit()
    finally:
        conn.close()


def get_history(user_id, limit=MAX_HISTORY):
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    try:
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit)
        ).fetchall()
    finally:
        conn.close()
    # Build history with character budget — keep NEWEST first, drop oldest
    # rows is newest-first (ORDER BY id DESC)
    selected = []
    total_chars = 0
    for r in rows:
        msg_len = len(r[1])
        if total_chars + msg_len > MAX_HISTORY_CHARS and selected:
            break  # Budget exceeded, but always keep at least 1 message
        selected.append({"role": r[0], "content": r[1]})
        total_chars += msg_len
    # Reverse to chronological order (oldest first)
    selected.reverse()
    return selected


def clear_history(user_id):
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("DELETE FROM messages WHERE user_id = ?", (user_id,))
        conn.commit()
    finally:
        conn.close()


def save_flow_state(user_id, flow_id):
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "INSERT OR REPLACE INTO user_state (user_id, active_flow_id, updated_at) VALUES (?, ?, ?)",
            (user_id, flow_id, time.time())
        )
        conn.commit()
    finally:
        conn.close()


def get_flow_state(user_id):
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    try:
        row = conn.execute("SELECT active_flow_id FROM user_state WHERE user_id = ?", (user_id,)).fetchone()
    finally:
        conn.close()
    return row[0] if row else None


def save_note(user_id, note):
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("INSERT INTO notes (user_id, note, timestamp) VALUES (?, ?, ?)",
                     (user_id, note, time.time()))
        conn.commit()
    finally:
        conn.close()


def get_notes(user_id, limit=10):
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    try:
        rows = conn.execute(
            "SELECT note, timestamp FROM notes WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit)
        ).fetchall()
    finally:
        conn.close()
    return rows


def get_stats(user_id):
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    try:
        total = conn.execute("SELECT COUNT(*) FROM messages WHERE user_id = ?", (user_id,)).fetchone()[0]
        notes = conn.execute("SELECT COUNT(*) FROM notes WHERE user_id = ?", (user_id,)).fetchone()[0]
        first = conn.execute("SELECT MIN(timestamp) FROM messages WHERE user_id = ?", (user_id,)).fetchone()[0]
    finally:
        conn.close()
    return total, notes, first


# ═══════════════════════════════════
#  FLOW ID HELPER (None-safe)
# ═══════════════════════════════════

def _get_active_flow(user_id):
    """Get active flow ID from SQLite (single source of truth)"""
    return get_flow_state(user_id)


def _clear_flow(user_id):
    """Clear stale flow state, scan messages, and scan notes to prevent hallucination"""
    save_flow_state(user_id, None)
    try:
        conn = sqlite3.connect(DB_PATH)
        # Remove assistant messages about scans/flows
        conn.execute(
            "DELETE FROM messages WHERE user_id = ? AND role = 'assistant' "
            "AND (content LIKE '%Flow #%' OR content LIKE '%Narrando progresso%' "
            "OR content LIKE '%scan completo%' OR content LIKE '%Pentest em%iniciado%' "
            "OR content LIKE '%Flow criado%' OR content LIKE '%scan em%' "
            "OR content LIKE '%pentest%iniciado%' OR content LIKE '%varredura%')",
            (user_id,)
        )
        # Remove user messages that triggered scans (orphaned requests)
        conn.execute(
            "DELETE FROM messages WHERE user_id = ? AND role = 'user' "
            "AND (content LIKE '%scan %' OR content LIKE '%pentest %' OR content LIKE '%hackear %' "
            "OR content LIKE '%hack %' OR content LIKE '%exploit %') "
            "AND content LIKE '%.%'",
            (user_id,)
        )
        # Remove notes about flows/scans
        conn.execute(
            "DELETE FROM notes WHERE user_id = ? "
            "AND (note LIKE '%Flow #%' OR note LIKE '%Pentest started%' "
            "OR note LIKE '%scan%started%')",
            (user_id,)
        )
        conn.commit()
        conn.close()
        log.info(f"Cleaned scan artifacts from history for user {user_id}")
    except Exception as e:
        log.warning(f"Failed to clean scan artifacts: {e}")


# ═══════════════════════════════════
#  LLM ROUTING
# ═══════════════════════════════════

def _call_llm(url, model, messages, max_tokens, timeout=300):
    """Call LLM endpoint, strip thinking tags, return content"""
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.8,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    r = requests.post(url, json=payload, timeout=timeout)
    r.raise_for_status()
    data = r.json()["choices"][0]["message"]
    content = data.get("content") or ""
    # Strip thinking tags
    if "<think>" in content and "</think>" in content:
        content = content[content.index("</think>") + len("</think>"):].strip()
    # Fallback if empty after stripping
    if not content:
        content = "🔮"
    return content


def _clean_chat_response(text):
    """Post-process chat output: light cleanup, trim trailing fragments"""
    import re as _re
    if not text or len(text) < 3:
        return text
    
    # Dedupe "mano" if repeated 3+ times
    parts = text.split('mano')
    if len(parts) > 3:
        text = parts[0] + 'mano' + ''.join(parts[1:]).replace('mano', '')
    
    # Clean artifacts
    text = _re.sub(r'mano,?\s*mano', 'mano', text)
    
    # Only truncate if clearly rambling (>15 sentences)
    sentences = _re.split(r'(?<=[.!?])\s+', text)
    if len(sentences) > 15:
        text = ' '.join(sentences[:12])
    
    # Clean trailing fragments (incomplete sentences from token cutoff)
    if text and text[-1] not in '.!?\n':
        last_punct = max(text.rfind('.'), text.rfind('!'), text.rfind('?'))
        if last_punct > len(text) * 0.3:
            text = text[:last_punct + 1]
        elif last_punct == -1 and len(text) > 100:
            # No punctuation at all — likely a cut-off fragment, trim at last comma or space
            last_comma = text.rfind(',')
            if last_comma > len(text) * 0.5:
                text = text[:last_comma + 1]
    
    return text.strip()



def llm_route(user_id, user_message):
    """Smart routing: small model for chat, big model for pentest.
    
    Returns (content, route_type).
    IMPORTANT: This function saves the user message to history.
    For PENTEST route, caller must save the cleaned assistant response.
    For CHAT/CHAT_FALLBACK, this function saves the assistant response.
    For ERROR, this function saves an error assistant response.
    """
    save_message(user_id, "user", user_message)

    classification, triggers = classify_message(user_message)

    # Force big model when flow is active — but verify flow exists first
    flow_id = _get_active_flow(user_id)
    if flow_id is not None:
        # Validate flow still exists in PentAGI before forcing PENTEST mode
        try:
            r = _safe_api("GET", f"/flows/{flow_id}", timeout=10)
            if r.get("status") == "success" and isinstance(r.get("data"), dict):
                flow_status = r["data"].get("status", "unknown")
                if flow_status in ("waiting", "running", "created"):
                    classification = "PENTEST"
                    log.info(f"ROUTER: forced PENTEST (active flow #{flow_id}, status={flow_status})")
                else:
                    # Flow finished/stopped/failed — clear it
                    log.info(f"ROUTER: flow #{flow_id} status={flow_status}, clearing")
                    _clear_flow(user_id)
                    flow_id = None
            else:
                # Flow doesn't exist (404) — clear stale reference
                log.info(f"ROUTER: flow #{flow_id} not found (404), clearing stale reference")
                _clear_flow(user_id)
                flow_id = None
        except Exception as e:
            log.warning(f"ROUTER: failed to verify flow #{flow_id}: {e}, clearing")
            _clear_flow(user_id)
            flow_id = None

    # Build context
    history = get_history(user_id)
    notes = get_notes(user_id)
    extra = ""
    if flow_id is not None:
        extra += f"\n\nACTIVE FLOW: #{flow_id} is currently running."
    else:
        extra += "\n\nNENHUM SCAN ATIVO. Se o histórico menciona scans anteriores, eles já terminaram. NÃO fale sobre resultados de scans passados como se estivessem acontecendo agora. Responda só sobre o que o usuário perguntou."
    if notes:
        extra += "\n\nSAVED NOTES:\n" + "\n".join(f"- {n[0]}" for n in notes[:10])

    if classification == "PENTEST":
        log.info(f"ROUTER: PENTEST triggers={triggers}")
        messages = [{"role": "system", "content": SYSTEM_PROMPT_PENTEST + extra}, *history]
        try:
            content = _call_llm(f"{LLM_URL}/v1/chat/completions", "qwen3-coder-30b", messages, 2048)
            # DON'T save assistant here — caller saves the cleaned response
            return content, "PENTEST"
        except Exception as e:
            log.error(f"Big model error: {e}")
            error_resp = f"Erro no modelo: {e}"
            # DON'T save here either — caller handles it
            return json.dumps({"action": "chat", "response": error_resp}), "PENTEST"

    else:
        log.info("ROUTER: CHAT (big model)")
        messages = [{"role": "system", "content": SYSTEM_PROMPT_CHAT + extra}, *history]

        # Primary: 30B abliterated for quality
        try:
            content = _call_llm(f"{LLM_URL}/v1/chat/completions", "qwen3-coder-30b", messages, 512, timeout=120)
            content = _clean_chat_response(content)
            save_message(user_id, "assistant", content)
            return content, "CHAT"
        except Exception as e:
            log.warning(f"Big model failed for chat: {e}, falling back to 1.7B")

        # Fallback: 1.7B if 30B is down/busy
        if check_router_health():
            try:
                content = _call_llm(f"{ROUTER_URL}/v1/chat/completions", "qwen3-1.7b", messages, 150, timeout=30)
                content = _clean_chat_response(content)
                save_message(user_id, "assistant", content)
                return content, "CHAT_FALLBACK"
            except Exception as e:
                log.warning(f"Fallback 1.7B also failed: {e}")

        # All failed — don't retry again, respond immediately
        error_msg = "Tá osso aqui, parceiro. Os modelos tão fora. Tenta de novo em uns minutos."
        log.error("All models failed for CHAT")
        save_message(user_id, "assistant", error_msg)
        return error_msg, "ERROR"


# ═══════════════════════════════════
#  API CALLS
# ═══════════════════════════════════

def pentagi_api(method, path, data=None, params=None, timeout=300):
    url = f"{PENTAGI_URL}/api/v1{path}"
    try:
        r = getattr(requests, method.lower())(url, headers=HEADERS, json=data, params=params, verify=False, timeout=timeout)
        log.info(f"PentAGI {method} {path} -> {r.status_code}")
        return r.json() if r.text else {}
    except Exception as e:
        log.error(f"PentAGI API error: {e}")
        return {"status": "error", "msg": str(e)}


def parse_action(llm_response):
    text = llm_response.strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
        # LLM returned array or other type — treat as plain text
    except Exception:
        pass
    if "{" in text:
        try:
            start = text.index("{")
            depth = 0
            for i in range(start, len(text)):
                if text[i] == "{":
                    depth += 1
                elif text[i] == "}":
                    depth -= 1
                if depth == 0:
                    parsed = json.loads(text[start:i+1])
                    if isinstance(parsed, dict):
                        return parsed
                    break
        except Exception:
            pass
    return {"action": "chat", "response": text}


def _safe_api(method, path, data=None, params=None, timeout=300):
    """Wrapper around pentagi_api that always returns a dict"""
    result = pentagi_api(method, path, data=data, params=params, timeout=timeout)
    if not isinstance(result, dict):
        return {"status": "error", "msg": f"Unexpected API response: {type(result).__name__}"}
    return result


def execute_action(user_id, action_data):
    action = action_data.get("action", "chat")
    response_text = action_data.get("response", "")

    if action == "scan":
        target = action_data.get("target", "")
        instructions = action_data.get("instructions", f"Comprehensive pentest on {target}")
        try:
            r = _safe_api("POST", "/flows/", {"input": instructions, "provider": "deepseek", "title": f"Pentest {target}"})
            if r.get("status") == "success" and isinstance(r.get("data"), dict) and "id" in r["data"]:
                fid = r["data"]["id"]
                save_flow_state(user_id, fid)
                save_note(user_id, f"Pentest started on {target} — Flow #{fid}")
                # Mark for narration — returned via tuple
                execute_action._narrate_fid = fid
                scan_msg = f"🚀 Flow #{fid} criado! Pentest em {target} iniciado.\n\n📡 Narrando progresso em tempo real..."
                response_text = f"{response_text}\n\n{scan_msg}".strip() if response_text else scan_msg
            else:
                err_msg = f"❌ Erro PentAGI: {r.get('msg', r.get('status', 'unknown'))}"
                response_text = f"{response_text}\n\n{err_msg}".strip() if response_text else err_msg
        except Exception as e:
            log.error(f"Scan action error: {e}")
            err_msg = f"❌ Erro ao criar scan: {e}"
            response_text = f"{response_text}\n\n{err_msg}".strip() if response_text else err_msg

    elif action == "status":
        fid = _get_active_flow(user_id)
        if fid is None:
            if not response_text:
                response_text = "Nenhum flow ativo no momento."
        else:
            try:
                r = _safe_api("GET", f"/flows/{fid}")
                flow_data = r.get("data")
                if r.get("status") == "success" and isinstance(flow_data, dict):
                    status_info = f"📊 *Flow #{fid}*\nStatus: `{flow_data.get('status','?')}`"
                    tasks = _safe_api("GET", f"/flows/{fid}/tasks/", params={"page": 1, "pageSize": 10, "type": "init"})
                    tasks_data = tasks.get("data")
                    if tasks.get("status") == "success" and isinstance(tasks_data, (dict, list)):
                        task_list = tasks_data.get("tasks", tasks_data) if isinstance(tasks_data, dict) else tasks_data
                        if isinstance(task_list, list):
                            for t in task_list[-5:]:
                                if isinstance(t, dict):
                                    icon = "✅" if t.get("status") in ("completed", "finished") else "⏳"
                                    title = t.get("title", t.get("input", ""))[:80]
                                    status_info += f"\n  {icon} {title}"
                    response_text = f"{response_text}\n\n{status_info}".strip() if response_text else status_info
                else:
                    _clear_flow(user_id)
                    err = f"❌ Flow #{fid} não encontrado. Estado limpo."
                    response_text = f"{response_text}\n\n{err}".strip() if response_text else err
            except Exception as e:
                log.error(f"Status action error: {e}")
                err = f"❌ Erro ao checar status: {e}"
                response_text = f"{response_text}\n\n{err}".strip() if response_text else err

    elif action == "input":
        fid = _get_active_flow(user_id)
        if fid is not None:
            try:
                msg = action_data.get("message", "")
                r = _safe_api("PUT", f"/flows/{fid}", {"action": "input", "input": msg})
                if r.get("status") == "success":
                    if not response_text:
                        response_text = f"📨 Instrução enviada ao flow #{fid}"
                else:
                    err = f"❌ {r.get('msg','erro')}"
                    response_text = f"{response_text}\n\n{err}".strip() if response_text else err
            except Exception as e:
                log.error(f"Input action error: {e}")
                err = f"❌ Erro ao enviar instrução: {e}"
                response_text = f"{response_text}\n\n{err}".strip() if response_text else err
        else:
            if not response_text:
                response_text = "Sem flow ativo pra receber instruções."

    elif action == "stop":
        try:
            fid = _get_active_flow(user_id)
            if fid is not None:
                _safe_api("PUT", f"/flows/{fid}", {"action": "stop"})
                _clear_flow(user_id)
                if not response_text:
                    response_text = f"🛑 Flow #{fid} parado."
            else:
                if not response_text:
                    response_text = "Nenhum flow ativo."
        except Exception as e:
            log.error(f"Stop action error: {e}")
            err = f"❌ Erro ao parar flow: {e}"
            response_text = f"{response_text}\n\n{err}".strip() if response_text else err

    elif action == "flows":
        try:
            r = _safe_api("GET", "/flows/", params={"page": 1, "pageSize": 10, "type": "init"})
            if r.get("status") == "success" and r.get("data"):
                flow_data = r["data"].get("flows", []) if isinstance(r["data"], dict) else r["data"]
                if isinstance(flow_data, list) and flow_data:
                    lines = []
                    for f in flow_data[-10:]:
                        if isinstance(f, dict):
                            lines.append(f"`#{f.get('id','?')}` [{f.get('status','?')}] {f.get('input','')[:50]}")
                    if lines:
                        flow_list = "\n".join(lines)
                        response_text = f"{response_text}\n\n📋 Flows:\n{flow_list}".strip() if response_text else f"📋 Flows:\n{flow_list}"
                    else:
                        if not response_text:
                            response_text = "Nenhum flow encontrado."
                else:
                    if not response_text:
                        response_text = "Nenhum flow encontrado."
            else:
                if not response_text:
                    response_text = "Nenhum flow encontrado."
        except Exception as e:
            log.error(f"Flows action error: {e}")
            err = f"❌ Erro ao listar flows: {e}"
            response_text = f"{response_text}\n\n{err}".strip() if response_text else err

    elif action == "note":
        note = action_data.get("note", "")
        if note:
            save_note(user_id, note)
            log.info(f"Note saved: {note[:50]}")

    return response_text or "🔮"


# Live Narration
async def narrate_flow(chat, flow_id, resume=False):
    """Poll PentAGI postgres and narrate pentest progress live to Telegram."""
    import subprocess, re as _re
    last_cmd_id = 0
    last_subtask = ""
    last_tc_id = 0
    idle = 0
    msgs_this_cycle = 0  # Rate limit: max 3 msgs per poll cycle
    MAX_MSGS_PER_CYCLE = 3
    cycles_elapsed = 0  # Each cycle = ~10s
    stall_warned = False  # Only warn once about stall
    STALL_CHECK_INTERVAL = 120  # Check every 120 cycles (~20 min)
    STALL_CMD_THRESHOLD = 50   # Suspicious: >50 cmds with 0 completed subtasks
    STALL_TIME_THRESHOLD = 180  # Alert after 180 cycles (~30 min) of zero progress

    # On resume after restart, skip to current max IDs to avoid re-sending old data
    if resume:
        def _pg_init(sql):
            try:
                r = subprocess.run(
                    ["docker", "exec", "pgvector", "psql", "-U", "postgres", "-d", "pentagidb", "-t", "-A", "-c", sql],
                    capture_output=True, text=True, timeout=5)
                return r.stdout.strip()
            except Exception:
                return "0"
        max_cmd = _pg_init(f"SELECT COALESCE(MAX(id),0) FROM termlogs WHERE flow_id={flow_id} AND type='stdin';")
        max_tc = _pg_init(f"SELECT COALESCE(MAX(id),0) FROM toolcalls WHERE flow_id={flow_id};")
        last_sub = _pg_init(f"SELECT title FROM subtasks s JOIN tasks t ON s.task_id=t.id WHERE t.flow_id={flow_id} ORDER BY s.id DESC LIMIT 1;")
        try:
            last_cmd_id = int(max_cmd)
        except ValueError:
            last_cmd_id = 0
        try:
            last_tc_id = int(max_tc)
        except ValueError:
            last_tc_id = 0
        last_subtask = last_sub or ""
        log.info(f"Narration resumed: flow #{flow_id}, skip to cmd_id={last_cmd_id}, tc_id={last_tc_id}")

    def _pg(sql):
        try:
            r = subprocess.run(
                ["docker", "exec", "pgvector", "psql", "-U", "postgres", "-d", "pentagidb", "-t", "-A", "-c", sql],
                capture_output=True, text=True, timeout=5)
            return r.stdout.strip()
        except Exception:
            return ""

    async def _send(text):
        nonlocal msgs_this_cycle
        if msgs_this_cycle >= MAX_MSGS_PER_CYCLE:
            return  # Rate limit — skip this message
        msgs_this_cycle += 1
        try:
            await chat.send_message(text, parse_mode="Markdown")
        except Exception:
            try:
                await chat.send_message(text)
            except Exception:
                pass
        await asyncio.sleep(0.5)  # Small delay between msgs to avoid Telegram 429

    # ANSI escape pattern: matches literal \x1B[...m sequences from psql output
    ansi_re = _re.compile(r'\\x1B\[[0-9;]*[mK]|\\r')

    def _build_findings_summary(fid, pg_func):
        """Build a brief findings summary from completed subtasks and tool calls"""
        stats = []
        # Count stats
        total_cmds = pg_func(f"SELECT COUNT(*) FROM termlogs WHERE flow_id={fid} AND type='stdin';")
        total_subs = pg_func(f"SELECT COUNT(*) FROM subtasks s JOIN tasks t ON s.task_id=t.id WHERE t.flow_id={fid};")
        completed = pg_func(f"SELECT COUNT(*) FROM subtasks s JOIN tasks t ON s.task_id=t.id WHERE t.flow_id={fid} AND s.status='completed';")
        tools_used = pg_func(f"SELECT DISTINCT name FROM toolcalls WHERE flow_id={fid} AND name!='terminal';")

        if total_cmds and total_cmds != "0":
            stats.append(f"  • {total_cmds} comandos executados")
        if total_subs and total_subs != "0":
            stats.append(f"  • {total_subs} subtasks ({completed or 0} completadas)")
        if tools_used:
            tool_names = [t.strip() for t in tools_used.split("\n") if t.strip()]
            if tool_names:
                stats.append(f"  • Agents: {', '.join(tool_names)}")

        # Get last 5 completed subtask titles as findings
        findings = []
        subs = pg_func(f"SELECT s.title FROM subtasks s JOIN tasks t ON s.task_id=t.id WHERE t.flow_id={fid} AND s.status='completed' ORDER BY s.id DESC LIMIT 5;")
        if subs:
            for sub in subs.split("\n"):
                sub = sub.strip()
                if sub:
                    findings.append(f"  ✅ {sub[:80]}")

        if not stats and not findings:
            return "Scan concluído."

        lines = []
        if stats:
            lines.append("📊 *Resumo:*")
            lines.extend(stats)
        if findings:
            lines.append("\n🔍 *Etapas concluídas:*")
            lines.extend(findings)

        return "\n".join(lines)

    async def _auto_report(chat_obj, fid):
        """Auto-generate and send PDF report after flow completion"""
        try:
            await chat_obj.send_message("📄 Gerando relatório automaticamente...")
            from report import generate_report
            filepath, error = await asyncio.to_thread(generate_report, fid)
            if error:
                await chat_obj.send_message(f"⚠️ Relatório falhou: {error}\nUse `/report {fid}` pra tentar de novo.", parse_mode="Markdown")
                return
            with open(filepath, 'rb') as f:
                await chat_obj.send_document(
                    document=f,
                    filename=os.path.basename(filepath),
                    caption=f"📋 Penetration Test Report — Flow #{fid}"
                )
        except Exception as e:
            log.error(f"Auto-report error: {e}")
            await chat_obj.send_message(f"⚠️ Erro no relatório: {e}\nUse `/report {fid}` manualmente.", parse_mode="Markdown")

    while True:
        await asyncio.sleep(10)
        msgs_this_cycle = 0  # Reset rate limit each cycle

        # Flow status check
        try:
            fr = pentagi_api("GET", f"/flows/{flow_id}")
            st = fr.get("data", {}).get("status", "?")
        except Exception:
            st = "?"

        if st in ("completed", "finished"):
            # Build findings summary from subtasks
            summary = _build_findings_summary(flow_id, _pg)
            await _send(f"✅ *Pentest finalizado!* Flow #{flow_id}\n\n{summary}")
            # Auto-generate and send PDF report
            await _auto_report(chat, flow_id)
            _clear_flow(chat.id)
            break
        if st in ("failed", "stopped"):
            await _send(f"❌ Flow #{flow_id} parou ({st}).")
            _clear_flow(chat.id)
            break
        if st == "waiting" and idle > 12:  # ~2min idle in waiting = likely stuck
            await _send(f"⚠️ Flow #{flow_id} em `waiting` sem atividade. Pode estar travado.\nUsa /status pra checar ou manda instrução.")
            _clear_flow(chat.id)
            break

        # New subtask?
        sub = _pg(f"SELECT title FROM subtasks s JOIN tasks t ON s.task_id=t.id WHERE t.flow_id={flow_id} AND s.status='running' ORDER BY s.id DESC LIMIT 1;")
        if sub and sub != last_subtask:
            last_subtask = sub
            await _send(f"➡️ *{sub}*")
            idle = 0

        # New terminal commands?
        rows = _pg(f"SELECT id, text FROM termlogs WHERE flow_id={flow_id} AND type='stdin' AND id>{last_cmd_id} ORDER BY id;")
        if rows:
            cmds_batch = []
            for line in rows.split("\n"):
                if "|" in line:
                    parts = line.split("|", 1)
                    try:
                        cid = int(parts[0])
                    except (ValueError, IndexError):
                        continue
                    raw = parts[1].strip()
                    # Clean ANSI escapes and shell prompt
                    clean = ansi_re.sub('', raw)
                    clean = clean.replace('/ $ ', '').strip()
                    if clean and len(clean) > 2:
                        cmds_batch.append(clean[:200])
                    last_cmd_id = cid
            # Send commands (batch if many)
            if len(cmds_batch) <= 3:
                for cmd in cmds_batch:
                    await _send(f"⚡ `{cmd}`")
            elif cmds_batch:
                # Batch: show first, count, and last
                await _send(f"⚡ `{cmds_batch[0]}`\n  _...+{len(cmds_batch)-2} comandos..._\n⚡ `{cmds_batch[-1]}`")
            idle = 0

        # New tool calls (non-terminal)?
        tcs = _pg(f"SELECT id, name FROM toolcalls WHERE flow_id={flow_id} AND id>{last_tc_id} AND name!='terminal' ORDER BY id;")
        if tcs:
            for line in tcs.split("\n"):
                if "|" in line:
                    parts = line.split("|", 1)
                    try:
                        tid = int(parts[0])
                    except (ValueError, IndexError):
                        continue
                    nm = parts[1].strip()
                    emojis = {"pentester": "🎯", "searcher": "🔎", "advice": "💡",
                              "subtask_list": "📋", "enricher": "🧠", "reflector": "🪞"}
                    e = emojis.get(nm, "🔧")
                    await _send(f"{e} *{nm}*")
                    last_tc_id = tid
            idle = 0
        else:
            idle += 1

        # ── STALL DETECTOR (Nyx) ──
        # Detects flows that run many commands but never complete subtasks
        cycles_elapsed += 1
        if not stall_warned and cycles_elapsed % STALL_CHECK_INTERVAL == 0:
            try:
                total_cmds_str = _pg(f"SELECT COUNT(*) FROM termlogs WHERE flow_id={flow_id} AND type='stdin';")
                completed_subs_str = _pg(f"SELECT COUNT(*) FROM subtasks s JOIN tasks t ON s.task_id=t.id WHERE t.flow_id={flow_id} AND s.status='completed';")
                total_cmds_n = int(total_cmds_str) if total_cmds_str else 0
                completed_subs_n = int(completed_subs_str) if completed_subs_str else 0

                if total_cmds_n > STALL_CMD_THRESHOLD and completed_subs_n == 0 and cycles_elapsed >= STALL_TIME_THRESHOLD:
                    stall_warned = True
                    await _send(
                        f"⚠️ *STALL DETECTADO* — Flow #{flow_id}\n"
                        f"📊 {total_cmds_n} comandos executados, 0 subtasks completadas\n"
                        f"⏱️ Rodando há ~{cycles_elapsed * 10 // 60} min sem progresso real\n"
                        f"💡 O modelo pode estar em loop. Use /stop pra parar."
                    )
            except Exception:
                pass  # Non-critical — don't break narration
        # ── END STALL DETECTOR ──

        if idle > 30:  # ~5min of no activity
            await _send(f"⏳ Flow #{flow_id} ainda rodando... Checar com /status")
            break



# ═══════════════════════════════════
#  HANDLERS
# ═══════════════════════════════════

async def handle_message(update: Update, ctx):
    """Handle text input — check for pending scan or redirect to menu"""
    if update.effective_user.id not in ALLOWED:
        return
    uid = update.effective_user.id
    text = update.message.text.strip()
    
    # Check if user has a pending scan type (waiting for domain)
    if uid in _user_pending_scan:
        scan_type = _user_pending_scan.pop(uid)
        # Extract domain/IP from input
        clean = re.sub(r'^https?://', '', text).split('/')[0].strip()
        if clean and ('.' in clean or ':' in clean):
            # Valid target — launch scan
            await _launch_scan(update, ctx, scan_type, clean)
            return
        else:
            scan = SCAN_PROMPTS.get(scan_type, {})
            _user_pending_scan[uid] = scan_type  # keep state
            await update.message.reply_text(
                f"\u26a0\ufe0f `{text}` n\u00e3o parece um dom\u00ednio ou IP v\u00e1lido.\n\n"
                f"Digite um dom\u00ednio (ex: `redat.ai`) ou IP (ex: `192.168.1.1`)\n"
                f"ou /start para voltar ao menu.",
                parse_mode="Markdown")
            return
    
    # No pending scan — check if text contains a domain
    target_match = re.search(r'(?:https?://)?([a-zA-Z0-9][-a-zA-Z0-9]*\.[a-zA-Z]{2,}(?:\.[a-zA-Z]{2,})?)', text)
    if target_match:
        target = target_match.group(1)
        kb = [
            [InlineKeyboardButton(f"\U0001f50d Recon", callback_data=f"scan_recon_{target}"),
             InlineKeyboardButton(f"\U0001f50c Ports", callback_data=f"scan_portscan_{target}"),
             InlineKeyboardButton(f"\u26a1 Vulns", callback_data=f"scan_vulnscan_{target}")],
            [InlineKeyboardButton(f"\U0001f310 Web", callback_data=f"scan_webscan_{target}"),
             InlineKeyboardButton(f"\U0001f512 SSL", callback_data=f"scan_sslscan_{target}"),
             InlineKeyboardButton(f"\U0001f480 Full", callback_data=f"scan_full_{target}")],
        ]
        await update.message.reply_text(
            f"\U0001f3af Alvo: `{target}`\n\nQual scan deseja executar?",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    else:
        await update.message.reply_text(
            "\u2694\ufe0f Toque em /start para abrir o menu.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f4cb Abrir Menu", callback_data="show_menu")]]))

async def _send_response(update, response):
    """Send response with chunking and Markdown fallback"""
    if len(response) > 4000:
        chunks = _smart_chunk(response, 4000)
        for chunk in chunks:
            try:
                await update.message.reply_text(chunk, parse_mode="Markdown")
            except Exception:
                await update.message.reply_text(chunk)
    else:
        try:
            await update.message.reply_text(response, parse_mode="Markdown")
        except Exception:
            await update.message.reply_text(response)


def _smart_chunk(text, max_len):
    """Split text into chunks, preferring newline boundaries"""
    chunks = []
    while text:
        if len(text) <= max_len:
            chunks.append(text)
            break
        # Try to split at last newline before limit
        split_at = text.rfind("\n", 0, max_len)
        if split_at == -1 or split_at < max_len // 2:
            # No good newline — split at space
            split_at = text.rfind(" ", 0, max_len)
        if split_at == -1 or split_at < max_len // 2:
            # No good boundary — hard split
            split_at = max_len
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    return chunks



async def _launch_scan(update, ctx, scan_type, target):
    """Launch a specific scan type against a target"""
    uid = getattr(getattr(update, 'effective_user', None), 'id', None) or getattr(getattr(update, 'from_user', None), 'id', 0)
    msg_obj = getattr(update, 'message', None)
    if uid not in ALLOWED:
        return
    scan = SCAN_PROMPTS.get(scan_type)
    if not scan:
        if msg_obj: await msg_obj.reply_text("\u274c Tipo de scan inv\u00e1lido.")
        return
    if not target:
        cmd = scan_type if scan_type != "portscan" else "scan"
        if msg_obj: await msg_obj.reply_text(f"\u26a0\ufe0f Uso: `/{cmd} <alvo>`\nExemplo: `/{cmd} redat.ai`", parse_mode="Markdown")
        return
    existing = _get_active_flow(uid)
    if existing:
        if msg_obj: await msg_obj.reply_text(f"\u26a0\ufe0f Flow #{existing} j\u00e1 ativo. Use /stop ou /nuke primeiro.", parse_mode="Markdown")
        return
    prompt = scan["prompt"].format(target=target)
    title = f"{scan['title']} \u2014 {target}"
    if msg_obj: await msg_obj.reply_text(f"\U0001f680 Iniciando {scan['title']} em `{target}`...", parse_mode="Markdown")
    try:
        r = _safe_api("POST", "/flows/", {"input": prompt, "provider": "deepseek", "title": title})
        if r.get("status") == "success" and isinstance(r.get("data"), dict) and "id" in r["data"]:
            fid = r["data"]["id"]
            save_flow_state(uid, fid)
            status_msg = f"\u2705 *Flow #{fid} criado!*\n\U0001f3af Alvo: `{target}`\n\U0001f4e1 Tipo: {scan['title']}\n\U0001f4dd {scan['desc']}\n\nNarrando progresso em tempo real..."
            if msg_obj:
                await msg_obj.reply_text(status_msg, parse_mode="Markdown")
                asyncio.create_task(narrate_flow(msg_obj.chat, fid))
        else:
            if msg_obj: await msg_obj.reply_text(f"\u274c Erro: {r.get('msg', 'unknown')}")
    except Exception as e:
        log.error(f"Scan launch error: {e}")
        if msg_obj: await msg_obj.reply_text(f"\u274c Erro: {e}")


async def cmd_recon(update: Update, ctx):
    target = " ".join(ctx.args) if ctx.args else ""
    await _launch_scan(update, ctx, "recon", target)

async def cmd_scan_target(update: Update, ctx):
    target = " ".join(ctx.args) if ctx.args else ""
    await _launch_scan(update, ctx, "portscan", target)

async def cmd_vuln(update: Update, ctx):
    target = " ".join(ctx.args) if ctx.args else ""
    await _launch_scan(update, ctx, "vulnscan", target)

async def cmd_web(update: Update, ctx):
    target = " ".join(ctx.args) if ctx.args else ""
    await _launch_scan(update, ctx, "webscan", target)

async def cmd_ssl(update: Update, ctx):
    target = " ".join(ctx.args) if ctx.args else ""
    await _launch_scan(update, ctx, "sslscan", target)

async def cmd_full(update: Update, ctx):
    target = " ".join(ctx.args) if ctx.args else ""
    await _launch_scan(update, ctx, "full", target)


async def callback_handler(update: Update, ctx):
    """Handle inline button presses"""
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    if uid not in ALLOWED:
        return
    data = query.data
    if data == "action_status":
        fid = _get_active_flow(uid)
        if not fid:
            await query.message.reply_text("\U0001f4ca Nenhum scan ativo.")
            return
        try:
            r = _safe_api("GET", f"/flows/{fid}")
            if r.get("status") == "success":
                fd = r["data"]
                await query.message.reply_text(f"\U0001f4ca *Flow #{fid}*\nStatus: `{fd.get('status','?')}`\nModel: `{fd.get('model','?')}`", parse_mode="Markdown")
        except Exception as e:
            await query.message.reply_text(f"\u274c Erro: {e}")
    elif data == "action_report":
        fid = _get_active_flow(uid)
        if fid:
            fake = type("obj", (object,), {"effective_user": query.from_user, "message": query.message})()
            await cmd_report(fake, ctx)
        else:
            await query.message.reply_text("\U0001f4cb Nenhum scan para reportar.")
    elif data == "action_nuke":
        kb = [[InlineKeyboardButton("\u2705 Confirmar NUKE", callback_data="nuke_confirm"),
               InlineKeyboardButton("\u274c Cancelar", callback_data="nuke_cancel")]]
        await query.message.reply_text("\u2622\ufe0f *NUKE \u2014 Tem certeza?*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    elif data == "nuke_confirm":
        fake = type("obj", (object,), {"effective_user": query.from_user, "message": query.message})()
        await cmd_nuke(fake, ctx)
    elif data == "nuke_cancel":
        await query.message.reply_text("\u2705 Cancelado.")
    elif data.startswith("info_"):
        scan_type = data.replace("info_", "")
        scan = SCAN_PROMPTS.get(scan_type, {})
        explain = scan.get("explain", scan.get("desc", ""))
        kb = [
            [InlineKeyboardButton("\u2705 Selecionar este scan", callback_data=f"select_{scan_type}")],
            [InlineKeyboardButton("\u25c0 Voltar ao menu", callback_data="show_menu")],
        ]
        await query.message.reply_text(
            f"{scan.get('title', '')}\n"
            f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n\n"
            f"*O que faz:*\n{explain}\n\n"
            f"*Ferramentas:* {scan.get('desc', '')}\n\n"
            f"Clique em _Selecionar_ para escolher este scan.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(kb))
    elif data.startswith("select_"):
        scan_type = data.replace("select_", "")
        scan = SCAN_PROMPTS.get(scan_type, {})
        uid = query.from_user.id
        _user_pending_scan[uid] = scan_type
        await query.message.reply_text(
            f"\U0001f3af *{scan.get('title', '')}* selecionado!\n\n"
            f"Agora digite o *dom\u00ednio ou IP* do alvo:\n\n"
            f"Exemplo: `redat.ai` ou `192.168.1.1`",
            parse_mode="Markdown")
    elif data == "noop":
        pass
    elif data == "action_stop":
        uid = query.from_user.id
        fid = _get_active_flow(uid)
        if fid:
            _safe_api("PUT", f"/flows/{fid}", {"action": "stop"})
            _clear_flow(uid)
            await query.message.reply_text(f"\U0001f6d1 Flow #{fid} parado.")
        else:
            await query.message.reply_text("Nenhum scan ativo.")
    elif data.startswith("scan_"):
        parts = data.split("_", 2)
        if len(parts) == 3:
            scan_type, target = parts[1], parts[2]
            fake = type("obj", (object,), {"message": query.message, "effective_user": query.from_user, "from_user": query.from_user})()
            await _launch_scan(fake, ctx, scan_type, target)
    elif data == "show_menu":
        fake = type("obj", (object,), {"message": query.message, "effective_user": query.from_user})()
        await cmd_start(fake, ctx)


async def cmd_start(update: Update, ctx):
    if update.effective_user.id not in ALLOWED:
        return
    uid = update.effective_user.id
    _user_pending_scan.pop(uid, None)
    
    # Check active flow
    flow_id = _get_active_flow(uid)
    flow_info = ""
    if flow_id:
        flow_info = f"\n\n\u26a1 Flow #{flow_id} ativo — use Status para checar."
    
    kb = [
        [InlineKeyboardButton("\U0001f50d Reconnaissance", callback_data="info_recon")],
        [InlineKeyboardButton("\U0001f50c Port Scan", callback_data="info_portscan")],
        [InlineKeyboardButton("\u26a1 Vulnerability Scan", callback_data="info_vulnscan")],
        [InlineKeyboardButton("\U0001f310 Web App Scan", callback_data="info_webscan")],
        [InlineKeyboardButton("\U0001f512 SSL/TLS Scan", callback_data="info_sslscan")],
        [InlineKeyboardButton("\U0001f480 Full Pentest", callback_data="info_full")],
        [InlineKeyboardButton("\u2501" * 15, callback_data="noop")],
        [InlineKeyboardButton("\U0001f4ca Status", callback_data="action_status"),
         InlineKeyboardButton("\U0001f4cb Report", callback_data="action_report"),
         InlineKeyboardButton("\U0001f6d1 Stop", callback_data="action_stop")],
        [InlineKeyboardButton("\u2622\ufe0f NUKE (reset total)", callback_data="action_nuke")],
    ]
    msg = (
        "\u2694\ufe0f *DIMITRI \u2014 Pentest Command Center*\n"
        "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n\n"
        "Selecione um tipo de scan abaixo para ver\n"
        "a descri\u00e7\u00e3o detalhada e iniciar.\n\n"
        "Cada bot\u00e3o explica o que o scan faz.\n"
        "Depois \u00e9 s\u00f3 digitar o dom\u00ednio ou IP.\n\n"
        "\U0001f6e1 _Powered by DeepSeek + Qwen Hybrid AI_"
        + flow_info
    )
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

async def cmd_reset(update: Update, ctx):
    if update.effective_user.id not in ALLOWED:
        return
    uid = update.effective_user.id
    try:
        clear_history(uid)
        await update.message.reply_text("🧹 Histórico limpo. Memória de notas preservada.")
    except Exception as e:
        log.error(f"cmd_reset error: {e}")
        await update.message.reply_text(f"⚠️ Erro ao limpar histórico: {e}")


async def cmd_stop(update: Update, ctx):
    """Stop the active pentest flow or guided scan"""
    if update.effective_user.id not in ALLOWED:
        return
    uid = update.effective_user.id
    
    # Check if guided scan is active
    try:
        if scan_engine.is_guided_scan_active(uid):
            scan_engine.abort(uid)
            if uid in scan_engine.active_sessions:
                del scan_engine.active_sessions[uid]
            await update.message.reply_text("🛑 Guided scan abortado.")
            return
    except Exception:
        pass
    
    fid = _get_active_flow(uid)
    if fid is None:
        await update.message.reply_text("Nenhum flow ativo pra parar.")
        return
    try:
        _safe_api("PUT", f"/flows/{fid}", {"action": "stop"})
        _clear_flow(uid)
        await update.message.reply_text(f"🛑 Flow #{fid} parado.")
    except Exception as e:
        log.error(f"cmd_stop error: {e}")
        await update.message.reply_text(f"⚠️ Erro ao parar flow: {e}")


async def cmd_status(update: Update, ctx):
    """Show detailed status of active pentest flow"""
    if update.effective_user.id not in ALLOWED:
        return
    uid = update.effective_user.id
    fid = _get_active_flow(uid)
    if fid is None:
        await update.message.reply_text("Nenhum flow ativo no momento.\nUse `/report <id>` pra gerar relatório de um flow anterior.", parse_mode="Markdown")
        return
    try:
        r = _safe_api("GET", f"/flows/{fid}", timeout=10)
        if r.get("status") == "success" and isinstance(r.get("data"), dict):
            data = r["data"]
            status = data.get("status", "?")
            title = data.get("title", "?")

            # Status emoji and description
            status_map = {
                "running": ("🟢", "Em execução"),
                "waiting": ("🟡", "Aguardando (pode estar travado)"),
                "completed": ("✅", "Finalizado"),
                "failed": ("❌", "Falhou"),
                "stopped": ("🛑", "Parado pelo usuário"),
                "created": ("🔵", "Criado, aguardando início"),
            }
            emoji, desc = status_map.get(status, ("❓", status))

            text = f"{emoji} *Flow #{fid}*\n"
            text += f"*Status:* {desc}\n"
            text += f"*Alvo:* {title}\n"

            # Timestamps
            created = data.get("created_at", "")[:19].replace("T", " ")
            updated = data.get("updated_at", "")[:19].replace("T", " ")
            if created:
                text += f"*Início:* `{created}` UTC\n"
            if updated:
                text += f"*Última atividade:* `{updated}` UTC\n"

            # Get subtasks + stats directly from postgres (API subtasks endpoint is unreliable)
            import subprocess
            def _pg_status(sql):
                try:
                    r = subprocess.run(
                        ["docker", "exec", "pgvector", "psql", "-U", "postgres", "-d", "pentagidb", "-t", "-A", "-c", sql],
                        capture_output=True, text=True, timeout=5)
                    return r.stdout.strip()
                except Exception:
                    return ""

            cmd_count = _pg_status(f"SELECT COUNT(*) FROM termlogs WHERE flow_id={fid} AND type='stdin';") or "?"
            total_subs = int(_pg_status(f"SELECT COUNT(*) FROM subtasks s JOIN tasks t ON s.task_id=t.id WHERE t.flow_id={fid};") or "0")
            completed_subs = int(_pg_status(f"SELECT COUNT(*) FROM subtasks s JOIN tasks t ON s.task_id=t.id WHERE t.flow_id={fid} AND s.status='completed';") or "0")
            running_sub = _pg_status(f"SELECT title FROM subtasks s JOIN tasks t ON s.task_id=t.id WHERE t.flow_id={fid} AND s.status='running' ORDER BY s.id DESC LIMIT 1;")
            
            # All subtasks with status
            subs_raw = _pg_status(f"SELECT s.status, s.title FROM subtasks s JOIN tasks t ON s.task_id=t.id WHERE t.flow_id={fid} ORDER BY s.id;")
            sub_list = []
            if subs_raw:
                for line in subs_raw.split("\n"):
                    if "|" in line:
                        parts = line.split("|", 1)
                        st = parts[0].strip()
                        stitle = parts[1].strip()[:60]
                        if st in ("completed", "finished"):
                            sub_list.append(f"  ✅ {stitle}")
                        elif st == "running":
                            sub_list.append(f"  🔄 {stitle}")
                        else:
                            sub_list.append(f"  ⏳ {stitle}")

            # Progress bar
            if total_subs > 0:
                pct = int(completed_subs / total_subs * 100)
                filled = int(pct / 10)
                bar = "▓" * filled + "░" * (10 - filled)
                text += f"\n*Progresso:* [{bar}] {pct}% ({completed_subs}/{total_subs} subtasks)\n"
            
            text += f"*Comandos executados:* {cmd_count}\n"

            if running_sub:
                text += f"\n🔄 *Executando agora:* {running_sub}\n"

            if sub_list:
                text += f"\n*Subtasks:*\n"
                shown = [s for s in sub_list if "🔄" in s or "✅" in s][:5]
                pending = [s for s in sub_list if "⏳" in s]
                if pending:
                    shown.append(f"  ⏳ _...+{len(pending)} pendentes_")
                text += "\n".join(shown)

            if status in ("completed", "finished"):
                text += "\n\n📄 Use `/report` pra gerar o relatório PDF."
            elif status == "running":
                text += "\n\n_Scan em andamento. Use_ `/stop` _pra parar._"
            elif status in ("waiting",):
                text += "\n\n⚠️ _Flow parado sem atividade. Pode estar travado._"
                text += "\n_Use_ `/stop` _pra parar e_ `/report` _pra gerar relatório parcial._"

            try:
                await update.message.reply_text(text, parse_mode="Markdown")
            except Exception:
                await update.message.reply_text(text)
        else:
            _clear_flow(uid)
            await update.message.reply_text(f"Flow #{fid} não encontrado. Estado limpo.")
    except Exception as e:
        log.error(f"cmd_status error: {e}")
        await update.message.reply_text(f"⚠️ Erro: {e}")


async def cmd_memory(update: Update, ctx):
    if update.effective_user.id not in ALLOWED:
        return
    uid = update.effective_user.id
    try:
        total_msgs, total_notes, first_ts = get_stats(uid)
        notes = get_notes(uid, 10)

        text = f"🧠 *Memória*\n\nMensagens: {total_msgs}\nNotas: {total_notes}\n"
        if first_ts:
            from datetime import datetime
            text += f"Primeira msg: {datetime.fromtimestamp(first_ts).strftime('%d/%m/%Y %H:%M')}\n"
        if notes:
            text += "\n📝 *Últimas notas:*\n"
            for n in notes:
                text += f"• {n[0][:100]}\n"
        try:
            await update.message.reply_text(text, parse_mode="Markdown")
        except Exception:
            await update.message.reply_text(text)
    except Exception as e:
        log.error(f"cmd_memory error: {e}")
        await update.message.reply_text(f"⚠️ Erro ao carregar memória: {e}")


async def cmd_report(update: Update, ctx):
    """Generate PDF report for a flow"""
    if update.effective_user.id not in ALLOWED:
        return
    uid = update.effective_user.id

    if ctx.args:
        try:
            fid = int(ctx.args[0])
        except Exception:
            await update.message.reply_text("Uso: `/report <flow_id>` ou `/report` (usa flow ativo)", parse_mode="Markdown")
            return
    else:
        fid = _get_active_flow(uid)

    if fid is None:
        await update.message.reply_text("Sem flow pra gerar relatório. Use `/report <flow_id>`", parse_mode="Markdown")
        return

    msg = await update.message.reply_text(f"📄 Gerando relatório profissional do flow #{fid}...\nIsso pode levar 1-2 minutos.")

    try:
        from report import generate_report
        filepath, error = await asyncio.to_thread(generate_report, fid)
        if error:
            await msg.edit_text(f"❌ Erro: {error}")
            return

        await msg.edit_text("📄 Relatório gerado! Enviando PDF...")
        with open(filepath, 'rb') as f:
            await update.message.reply_document(
                document=f,
                filename=os.path.basename(filepath),
                caption=f"📋 Penetration Test Report — Flow #{fid}"
            )
    except Exception as e:
        await msg.edit_text(f"❌ Erro gerando relatório: {e}")


async def cmd_dashboard(update: Update, ctx):
    if update.effective_user.id not in ALLOWED:
        return
    await update.message.reply_text(
        "🖥 *Dashboard PentAGI*\nAcesse: `https://localhost:8443`\nUser: `admin@pentagi.com`\nSenha: `admin`",
        parse_mode="Markdown"
    )



async def cmd_nuke(update: Update, ctx):
    """Nuclear reset - kill ALL flows, containers, sessions. Clean slate."""
    if update.effective_user.id not in ALLOWED:
        return
    uid = update.effective_user.id
    await update.message.reply_text("☢️ *NUKE iniciado...* Matando tudo.", parse_mode="Markdown")

    import subprocess, time
    report = []
    errors = []

    # 1. Stop all flows via PentAGI API
    try:
        r = _safe_api("GET", "/flows/?page=1&pageSize=100&type=init")
        flows = r.get("data", {}).get("list", []) if r.get("status") == "success" else []
        active = [f for f in flows if f.get("status") in ("running", "waiting", "created")]
        stopped_api = 0
        for f in active:
            try:
                _safe_api("PUT", f"/flows/{f['id']}", {"action": "stop"})
                stopped_api += 1
            except Exception:
                pass
        report.append(f"🔴 Flows parados via API: {stopped_api}/{len(active)}")
    except Exception as e:
        errors.append(f"API flows: {e}")
        report.append("🔴 Flows via API: ⚠️ erro")

    # 2. Force-stop ALL flows in DB (catches zombies)
    try:
        r = subprocess.run(
            ["docker", "exec", "pgvector", "psql", "-U", "postgres", "-d", "pentagidb",
             "-t", "-A", "-c",
             "UPDATE flows SET status = 'failed' WHERE status IN ('running', 'waiting', 'created') RETURNING id;"],
            capture_output=True, text=True, timeout=10)
        db_killed = [x.strip() for x in r.stdout.strip().split('\n') if x.strip()]
        report.append(f"💀 Flows forçados no DB: {len(db_killed)}" + (f" (IDs: {', '.join(db_killed)})" if db_killed else ""))
    except Exception as e:
        errors.append(f"DB flows: {e}")

    # 3. Delete broken flows (empty trace_id)
    try:
        r = subprocess.run(
            ["docker", "exec", "pgvector", "psql", "-U", "postgres", "-d", "pentagidb",
             "-t", "-A", "-c",
             "DELETE FROM flows WHERE trace_id IS NULL OR trace_id = '' RETURNING id;"],
            capture_output=True, text=True, timeout=10)
        broken = [x.strip() for x in r.stdout.strip().split('\n') if x.strip()]
        if broken:
            report.append(f"🗑 Flows quebrados deletados: {len(broken)}")
    except Exception:
        pass

    # 4. Kill ALL pentagi-terminal containers
    try:
        r = subprocess.run(["docker", "ps", "-a", "--format", "{{.Names}}", "--filter", "name=pentagi-terminal"],
            capture_output=True, text=True, timeout=10)
        containers = [c.strip() for c in r.stdout.strip().split('\n') if c.strip()]
        for c in containers:
            subprocess.run(["docker", "stop", c], capture_output=True, timeout=15)
            subprocess.run(["docker", "rm", c], capture_output=True, timeout=10)
        report.append(f"🐳 Containers Kali destruídos: {len(containers)}")
    except Exception as e:
        errors.append(f"Containers: {e}")

    # 5. Restart PentAGI (kills goroutine zombies)
    try:
        r = subprocess.run(["docker", "compose", "-f", "/opt/pentagi/docker-compose.yml", "restart", "pentagi"],
            capture_output=True, text=True, timeout=30, cwd="/opt/pentagi")
        report.append("🔄 PentAGI reiniciado" if r.returncode == 0 else f"🔄 PentAGI: ⚠️ {r.stderr[:80]}")
    except Exception as e:
        errors.append(f"PentAGI restart: {e}")

    time.sleep(5)

    # 6. Clear bot state
    try:
        clear_history(uid)
        _clear_flow(uid)
        report.append("🧹 Histórico + sessão limpos")
    except Exception as e:
        errors.append(f"Bot state: {e}")

    # 7. Abort guided scan
    try:
        if scan_engine.is_guided_scan_active(uid):
            scan_engine.abort(uid)
            if uid in scan_engine.active_sessions:
                del scan_engine.active_sessions[uid]
            report.append("🎯 Guided scan abortado")
    except Exception:
        pass

    # 8. Verify
    try:
        r = subprocess.run(["docker", "exec", "pgvector", "psql", "-U", "postgres", "-d", "pentagidb",
             "-t", "-A", "-c", "SELECT count(*) FROM flows WHERE status IN ('running','waiting','created');"],
            capture_output=True, text=True, timeout=10)
        active_count = int(r.stdout.strip() or "0")

        r2 = subprocess.run(["docker", "ps", "--format", "{{.Names}}", "--filter", "name=pentagi-terminal"],
            capture_output=True, text=True, timeout=5)
        live = len([x for x in r2.stdout.strip().split('\n') if x.strip()])

        r3 = subprocess.run(["docker", "ps", "--format", "{{.Status}}", "--filter", "name=^pentagi$"],
            capture_output=True, text=True, timeout=5)
        pentagi_up = "Up" in r3.stdout

        r4 = subprocess.run(["curl", "-sf", "http://localhost:8090/health"],
            capture_output=True, text=True, timeout=5)
        router_ok = "ok" in r4.stdout

        report.append("─── Verificação ───")
        report.append(f"Flows ativos: {active_count}" + (" ✅" if active_count == 0 else " ❌"))
        report.append(f"Containers Kali: {live}" + (" ✅" if live == 0 else " ❌"))
        report.append(f"PentAGI: {'UP ✅' if pentagi_up else 'DOWN ❌'}")
        report.append(f"Router: {'OK ✅' if router_ok else 'FAIL ❌'}")
    except Exception as e:
        errors.append(f"Verify: {e}")

    msg = "☢️ *NUKE COMPLETE*\n\n"
    msg += "\n".join(report)
    if errors:
        msg += "\n\n⚠️ *Erros:*\n" + "\n".join(f"• {e}" for e in errors)
    msg += "\n\n✅ *Sistema limpo. Pode mandar novo pentest.*"
    await update.message.reply_text(msg, parse_mode="Markdown")



async def cmd_gscan(update: Update, ctx):
    """Start a guided scan with structured phases"""
    if update.effective_user.id not in ALLOWED:
        return
    uid = update.effective_user.id
    
    # Check if already running
    if scan_engine.is_guided_scan_active(uid):
        await update.message.reply_text(
            "⚠️ Já tem um guided scan rodando. Use /stop pra parar primeiro."
        )
        return
    
    # Check if regular flow is active
    fid = _get_active_flow(uid)
    if fid is not None:
        await update.message.reply_text(
            f"⚠️ Flow #{fid} ativo. Use /stop primeiro."
        )
        return
    
    # Parse target from args
    if not ctx.args:
        await update.message.reply_text(
            "Uso: `/gscan <alvo>`\nExemplo: `/gscan redat.ai`",
            parse_mode="Markdown"
        )
        return
    
    target = ctx.args[0].strip()
    
    # Validate target looks real
    import re
    ip_ok = re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', target)
    domain_ok = re.match(r'^[a-zA-Z0-9][a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', target)
    if not ip_ok and not domain_ok:
        await update.message.reply_text(
            f"⚠️ Alvo inválido: `{target}`\nUse IP ou domínio.",
            parse_mode="Markdown"
        )
        return
    
    chat = update.message.chat
    
    async def send_msg(text):
        """Send message to Telegram with Markdown fallback"""
        try:
            await chat.send_message(text, parse_mode="Markdown")
        except Exception:
            try:
                await chat.send_message(text)
            except Exception as e:
                log.error(f"Failed to send gscan message: {e}")
    
    # Run guided scan in background
    async def run_guided():
        try:
            report_path, report_md = await scan_engine.run_scan(
                target=target,
                user_id=uid,
                chat_id=chat.id,
                send_func=send_msg,
            )
            
            if report_path and os.path.exists(report_path):
                # Convert to PDF and send
                try:
                    from report_md2pdf import md_to_pdf
                    pdf_path = report_path.replace('.md', '.pdf')
                    md_to_pdf(report_path, pdf_path)
                    with open(pdf_path, 'rb') as f:
                        await chat.send_document(
                            document=f,
                            filename=os.path.basename(pdf_path),
                            caption=f"📋 Guided Scan Report — {target}"
                        )
                except Exception as e:
                    log.warning(f"PDF conversion failed: {e}, sending markdown")
                    with open(report_path, 'rb') as f:
                        await chat.send_document(
                            document=f,
                            filename=os.path.basename(report_path),
                            caption=f"📋 Guided Scan Report — {target}"
                        )
            
            elif report_md:
                # Send as text if file failed
                if len(report_md) > 4000:
                    # Save and send as file
                    fallback_path = f"/tmp/report_{target}_{int(time.time())}.md"
                    with open(fallback_path, 'w') as f:
                        f.write(report_md)
                    with open(fallback_path, 'rb') as f:
                        await chat.send_document(
                            document=f,
                            filename=os.path.basename(fallback_path),
                            caption=f"📋 Guided Scan Report — {target}"
                        )
                else:
                    await send_msg(report_md)
            
        except Exception as e:
            log.error(f"Guided scan error: {e}", exc_info=True)
            await send_msg(f"❌ Guided scan falhou: {e}")
        finally:
            # Cleanup
            if uid in scan_engine.active_sessions:
                del scan_engine.active_sessions[uid]
            _clear_flow(uid)
    
    asyncio.create_task(run_guided())


async def error_handler(update, context):
    """Global error handler for unhandled exceptions"""
    log.error(f"Unhandled exception: {context.error}", exc_info=context.error)
    if update and update.effective_message:
        try:
            await update.effective_message.reply_text(
                f"⚠️ Erro inesperado. Tente novamente."
            )
        except Exception:
            pass


async def main():
    # Validate required config
    if not TELEGRAM_TOKEN:
        log.error("TELEGRAM_TOKEN not set! Bot cannot start.")
        sys.exit(1)
    if not PENTAGI_TOKEN:
        log.warning("PENTAGI_TOKEN not set — PentAGI API calls will fail")

    init_db()
    
    # Initialize Guided Scan Engine
    global scan_engine
    scan_engine = GuidedScanEngine(
        api_func=lambda method, path, data=None: _safe_api(method, path, data=data),
        flow_state_func=save_flow_state,
        clear_flow_func=_clear_flow,
    )
    log.info("Guided Scan Engine initialized")
    
    log.info("Building dual-model agent bot v3...")
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(CommandHandler("stop", cmd_stop))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("memory", cmd_memory))
    app.add_handler(CommandHandler("report", cmd_report))
    app.add_handler(CommandHandler("dashboard", cmd_dashboard))
    app.add_handler(CommandHandler("gscan", cmd_gscan))
    app.add_handler(CommandHandler("nuke", cmd_nuke))
    app.add_handler(CommandHandler("recon", cmd_recon))
    app.add_handler(CommandHandler("scan", cmd_scan_target))
    app.add_handler(CommandHandler("vuln", cmd_vuln))
    app.add_handler(CommandHandler("web", cmd_web))
    app.add_handler(CommandHandler("ssl", cmd_ssl))
    app.add_handler(CommandHandler("full", cmd_full))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)
    log.info("Starting agent bot...")
    async with app:
        await app.start()
        await app.updater.start_polling()
        log.info("🔮 PentAGI Dual-Model Bot v3 is LIVE!")
        log.info(f"  Big model:  {LLM_URL}")
        log.info(f"  Fast model: {ROUTER_URL}")

        # Resume narration for any active flows after restart
        for uid in ALLOWED:
            fid = _get_active_flow(uid)
            if fid is not None:
                try:
                    r = _safe_api("GET", f"/flows/{fid}", timeout=10)
                    if (r.get("status") == "success" and isinstance(r.get("data"), dict)
                            and r["data"].get("status") in ("waiting", "running", "created")):
                        chat = await app.bot.get_chat(uid)
                        asyncio.create_task(narrate_flow(chat, fid, resume=True))
                        log.info(f"Resumed narration for flow #{fid} (user {uid})")
                    else:
                        _clear_flow(uid)
                        log.info(f"Cleared stale flow #{fid} for user {uid}")
                except Exception as e:
                    log.warning(f"Failed to resume narration for flow #{fid}: {e}")
        stop_event = asyncio.Event()
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, stop_event.set)
        await stop_event.wait()
        await app.updater.stop()
        await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
