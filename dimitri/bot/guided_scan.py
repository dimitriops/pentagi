"""
Guided Scan Engine — Orchestrates PentAGI flows in structured phases.

Instead of 1 giant flow with vague prompt, runs 5 focused phases:
  Phase 1: Recon (nmap)
  Phase 2: Web Fingerprint (curl headers)
  Phase 3: Vuln Scan (nuclei)
  Phase 4: Deep Probing (ffuf, sqlmap — only if phase 3 found something)
  Phase 5: Report (assembled from real data, no hallucination)

Each phase = 1 PentAGI flow with:
  - Surgical prompt (specific commands, not vague "do pentest")
  - Hard timeout
  - Max command limit
  - Auto-stop if stalled

The bot controls the flow between phases. PentAGI just executes.
"""

import logging
import time
import subprocess
import asyncio
import json
import os
from dataclasses import dataclass, field
from typing import Optional

log = logging.getLogger(__name__)

# ═══════════════════════════════════
#  PHASE DEFINITIONS
# ═══════════════════════════════════

@dataclass
class PhaseResult:
    """Result of a single scan phase"""
    phase_num: int
    phase_name: str
    flow_id: Optional[int] = None
    status: str = "pending"  # pending, running, completed, failed, timeout, skipped
    commands_executed: int = 0
    subtasks_completed: int = 0
    raw_output: str = ""  # Terminal output collected
    findings: list = field(default_factory=list)
    duration_secs: float = 0
    error: str = ""


@dataclass
class ScanSession:
    """Tracks the full guided scan across all phases"""
    target: str
    user_id: int
    chat_id: int
    started_at: float = field(default_factory=time.time)
    current_phase: int = 0
    phases: list = field(default_factory=list)
    active_flow_id: Optional[int] = None
    aborted: bool = False
    
    def total_commands(self) -> int:
        return sum(p.commands_executed for p in self.phases)
    
    def total_findings(self) -> int:
        return sum(len(p.findings) for p in self.phases)


# Phase configs: prompt template, timeout, max commands
PHASES = [
    {
        "num": 1,
        "name": "Reconhecimento",
        "emoji": "🔍",
        "timeout_secs": 600,      # 10 min max
        "max_commands": 20,
        "prompt_template": (
            "Execute APENAS os seguintes comandos no alvo {target} e retorne os resultados completos. "
            "NÃO faça nada além destes comandos. NÃO tente explorar ou aprofundar. "
            "Apenas execute e reporte:\n\n"
            "1. nmap -sS -sV -O -sC -p- --min-rate 1000 {target} -oN /work/nmap_full.txt\n"
            "2. nmap -sU --top-ports 50 --min-rate 500 {target} -oN /work/nmap_udp.txt\n"
            "3. host {target}\n"
            "4. dig {target} ANY +noall +answer\n"
            "5. dig {target} -t TXT +short\n"
            "6. nslookup {target}\n\n"
            "Quando TODOS os comandos terminarem, reporte os resultados e PARE."
        ),
    },
    {
        "num": 2,
        "name": "Web Fingerprint",
        "emoji": "🌐",
        "timeout_secs": 300,      # 5 min max
        "max_commands": 25,
        "prompt_template": (
            "O reconhecimento do alvo {target} encontrou estas portas/serviços:\n"
            "{phase1_summary}\n\n"
            "Execute APENAS estes comandos para cada porta HTTP/HTTPS encontrada:\n\n"
            "1. curl -s -I -L https://{target} -o /work/headers_443.txt 2>&1\n"
            "2. curl -s -I -L http://{target} -o /work/headers_80.txt 2>&1\n"
            "3. Para cada porta HTTP adicional encontrada: curl -s -I http://{target_ip}:<porta>\n"
            "4. whatweb {target} -v > /work/whatweb.txt 2>&1\n"
            "5. curl -s https://{target}/robots.txt -o /work/robots.txt 2>&1\n"
            "6. curl -s https://{target}/sitemap.xml -o /work/sitemap.xml 2>&1\n"
            "7. curl -s -D- https://{target} -o /dev/null | grep -iE 'server|x-powered|x-frame|content-security|strict-transport|x-xss|x-content-type'\n\n"
            "Quando TODOS terminarem, reporte os resultados e PARE. NÃO tente explorar nada."
        ),
    },
    {
        "num": 3,
        "name": "Vuln Scanning",
        "emoji": "⚡",
        "timeout_secs": 900,      # 15 min max (nuclei can be slow)
        "max_commands": 15,
        "prompt_template": (
            "O alvo {target} tem os seguintes serviços e tecnologias:\n"
            "{phase2_summary}\n\n"
            "Execute APENAS estes scans de vulnerabilidade:\n\n"
            "1. nuclei -u https://{target} -severity critical,high,medium -o /work/nuclei_results.txt\n"
            "2. nuclei -u http://{target} -severity critical,high,medium -o /work/nuclei_http.txt\n"
            "3. nikto -h https://{target} -output /work/nikto.txt -Format txt\n\n"
            "Se houver portas adicionais HTTP: nuclei -u http://{target_ip}:<porta> -severity critical,high\n\n"
            "Quando TODOS terminarem, reporte TODAS as vulnerabilidades encontradas e PARE."
        ),
    },
    {
        "num": 4,
        "name": "Deep Probing",
        "emoji": "💉",
        "timeout_secs": 600,      # 10 min max
        "max_commands": 30,
        "conditional": True,  # Only runs if phase 3 found vulns
        "prompt_template": (
            "O scan de vulnerabilidades do alvo {target} encontrou:\n"
            "{phase3_summary}\n\n"
            "Realize testes de validação APENAS para as vulnerabilidades encontradas acima. "
            "Para cada vulnerabilidade:\n\n"
            "1. Se possível SQL injection: sqlmap -u '<url_vulneravel>' --batch --level 2 --risk 2 --output-dir=/work/sqlmap/\n"
            "2. Se possível XSS: testar com payload simples via curl\n"
            "3. Se diretórios expostos: ffuf -u https://{target}/FUZZ -w /usr/share/wordlists/dirb/common.txt -o /work/ffuf.json -of json\n"
            "4. Se headers de segurança ausentes: documentar quais faltam\n"
            "5. Se serviços desatualizados: searchsploit <serviço> <versão>\n\n"
            "NÃO faça nada destrutivo. Apenas valide e documente. PARE quando terminar."
        ),
    },
]


# ═══════════════════════════════════
#  DATABASE HELPERS (PentAGI postgres)
# ═══════════════════════════════════

def _pg(sql):
    """Query PentAGI postgres via docker exec"""
    try:
        r = subprocess.run(
            ["docker", "exec", "pgvector", "psql", "-U", "postgres", "-d", "pentagidb", "-t", "-A", "-c", sql],
            capture_output=True, text=True, timeout=10
        )
        return r.stdout.strip()
    except Exception as e:
        log.warning(f"PG query failed: {e}")
        return ""


def get_flow_commands(flow_id):
    """Get all stdin commands from a flow"""
    raw = _pg(
        f"SELECT text FROM termlogs WHERE flow_id={flow_id} AND type='stdin' ORDER BY id;"
    )
    if not raw:
        return []
    return [line.strip() for line in raw.split("\n") if line.strip()]


def get_flow_outputs(flow_id):
    """Get all stdout outputs from a flow"""
    raw = _pg(
        f"SELECT text FROM termlogs WHERE flow_id={flow_id} AND type='stdout' ORDER BY id;"
    )
    return raw or ""


def get_flow_command_count(flow_id):
    """Get total number of commands executed in a flow"""
    raw = _pg(f"SELECT COUNT(*) FROM termlogs WHERE flow_id={flow_id} AND type='stdin';")
    try:
        return int(raw)
    except (ValueError, TypeError):
        return 0


def get_flow_subtask_status(flow_id):
    """Get subtask completion status"""
    total = _pg(
        f"SELECT COUNT(*) FROM subtasks s JOIN tasks t ON s.task_id=t.id WHERE t.flow_id={flow_id};"
    )
    completed = _pg(
        f"SELECT COUNT(*) FROM subtasks s JOIN tasks t ON s.task_id=t.id "
        f"WHERE t.flow_id={flow_id} AND s.status='completed';"
    )
    try:
        return int(total or 0), int(completed or 0)
    except (ValueError, TypeError):
        return 0, 0


def get_flow_status(flow_id):
    """Get flow status from DB"""
    return _pg(f"SELECT status FROM flows WHERE id={flow_id};") or "unknown"


def collect_phase_output(flow_id):
    """Collect meaningful output from a flow for use in next phase's prompt.
    Returns a condensed summary string."""
    import re
    
    # Get all stdout
    raw = get_flow_outputs(flow_id)
    if not raw:
        return "Nenhum output coletado."
    
    # Clean ANSI codes (both raw ESC byte \x1b and literal \x1B text)
    clean = re.sub(r'\x1b\[[0-9;]*[mK]|\r', '', raw)
    clean = re.sub(r'\\x1B\[[0-9;]*[mK]|\\r', '', clean)
    
    # Truncate to reasonable size for next phase prompt (max ~4000 chars)
    if len(clean) > 4000:
        # Keep first 2000 and last 2000
        clean = clean[:2000] + "\n\n[... output truncado ...]\n\n" + clean[-2000:]
    
    return clean


# ═══════════════════════════════════
#  SCAN ENGINE
# ═══════════════════════════════════

class GuidedScanEngine:
    """Orchestrates a multi-phase guided scan."""
    
    def __init__(self, api_func, flow_state_func, clear_flow_func):
        """
        api_func: pentagi_api(method, path, data) function
        flow_state_func: save_flow_state(user_id, flow_id) function  
        clear_flow_func: _clear_flow(user_id) function
        """
        self.api = api_func
        self.save_flow = flow_state_func
        self.clear_flow = clear_flow_func
        self.active_sessions = {}  # user_id -> ScanSession
    
    def is_guided_scan_active(self, user_id):
        """Check if a guided scan is running for this user"""
        return user_id in self.active_sessions and not self.active_sessions[user_id].aborted
    
    def get_session(self, user_id) -> Optional[ScanSession]:
        return self.active_sessions.get(user_id)
    
    def abort(self, user_id):
        """Abort a guided scan"""
        session = self.active_sessions.get(user_id)
        if session:
            session.aborted = True
            if session.active_flow_id:
                try:
                    self.api("PUT", f"/flows/{session.active_flow_id}", {"action": "stop"})
                except Exception:
                    pass
            self.clear_flow(user_id)
    
    def _resolve_target_ip(self, target):
        """Resolve domain to IP for direct probing"""
        try:
            r = subprocess.run(
                ["dig", "+short", target, "A"],
                capture_output=True, text=True, timeout=5
            )
            ips = [line.strip() for line in r.stdout.strip().split("\n") if line.strip()]
            # Filter to actual IPs (not CNAMEs)
            import re
            ip_pattern = re.compile(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$')
            actual_ips = [ip for ip in ips if ip_pattern.match(ip)]
            return actual_ips[0] if actual_ips else target
        except Exception:
            return target
    
    def _create_flow(self, prompt, title):
        """Create a PentAGI flow with specific prompt. Returns flow_id or None."""
        try:
            r = self.api("POST", "/flows/", {
                "input": prompt,
                "provider": "deepseek",
                "title": title
            })
            if r.get("status") == "success" and isinstance(r.get("data"), dict):
                fid = r["data"].get("id")
                if fid:
                    return int(fid)
        except Exception as e:
            log.error(f"Failed to create flow: {e}")
        return None
    
    def _stop_flow(self, flow_id):
        """Stop a flow"""
        try:
            self.api("PUT", f"/flows/{flow_id}", {"action": "stop"})
        except Exception as e:
            log.warning(f"Failed to stop flow {flow_id}: {e}")
    
    async def _wait_for_flow(self, flow_id, timeout_secs, max_commands, send_func, session=None):
        """Wait for a flow to complete, with timeout and command limits.
        
        Returns: (status, commands_executed)
        status: 'completed', 'timeout', 'max_commands', 'failed', 'aborted'
        """
        start = time.time()
        poll_interval = 10  # seconds
        idle_cycles = 0
        last_cmd_count = 0
        
        while True:
            await asyncio.sleep(poll_interval)
            elapsed = time.time() - start
            
            # Check abort (user pressed /stop)
            if session and session.aborted:
                self._stop_flow(flow_id)
                return "aborted", get_flow_command_count(flow_id)
            
            # Check flow status
            status = get_flow_status(flow_id)
            
            if status == "finished":
                return "completed", get_flow_command_count(flow_id)
            
            if status == "failed":
                return "failed", get_flow_command_count(flow_id)
            
            # Check timeout
            if elapsed >= timeout_secs:
                self._stop_flow(flow_id)
                return "timeout", get_flow_command_count(flow_id)
            
            # Check command limit
            cmd_count = get_flow_command_count(flow_id)
            if cmd_count >= max_commands:
                self._stop_flow(flow_id)
                return "max_commands", cmd_count
            
            # Check stall (no new commands)
            if cmd_count == last_cmd_count:
                idle_cycles += 1
            else:
                idle_cycles = 0
                last_cmd_count = cmd_count
            
            # Stall detection: 2 min idle in waiting, 3 min idle in running
            if idle_cycles >= 12 and status in ("waiting",):
                self._stop_flow(flow_id)
                return "completed", cmd_count  # Treat as done — got what we could
            if idle_cycles >= 18 and status in ("running", "created"):
                # Running but no new commands for 3 minutes — likely stuck
                self._stop_flow(flow_id)
                return "completed", cmd_count
    
    async def run_scan(self, target, user_id, chat_id, send_func):
        """Run the full guided scan. send_func(text) sends messages to Telegram."""
        
        target_ip = self._resolve_target_ip(target)
        
        session = ScanSession(
            target=target,
            user_id=user_id,
            chat_id=chat_id
        )
        self.active_sessions[user_id] = session
        
        await send_func(
            f"🎯 *Guided Scan iniciado — {target}*\n"
            f"IP: `{target_ip}`\n"
            f"📋 5 fases estruturadas com limites automáticos\n"
            f"Use /stop pra abortar a qualquer momento."
        )
        
        phase_summaries = {}
        
        for phase_config in PHASES:
            if session.aborted:
                break
            
            phase_num = phase_config["num"]
            phase_name = phase_config["name"]
            emoji = phase_config["emoji"]
            timeout = phase_config["timeout_secs"]
            max_cmds = phase_config["max_commands"]
            
            # Check conditional phase
            if phase_config.get("conditional"):
                # Phase 4 only runs if phase 3 found vulnerabilities
                prev_findings = phase_summaries.get(3, "")
                skip_keywords = ["nenhum", "no vulnerabilit", "0 vulnerabilit", "nada encontrado", "0 findings", "no findings", "no issues", "clean scan"]
                has_skip_kw = any(kw in prev_findings.lower() for kw in skip_keywords)
                if has_skip_kw or not prev_findings.strip():
                    result = PhaseResult(
                        phase_num=phase_num,
                        phase_name=phase_name,
                        status="skipped",
                    )
                    session.phases.append(result)
                    await send_func(f"⏭️ *Fase {phase_num}/5 — {phase_name}* pulada (nenhuma vuln encontrada)")
                    continue
            
            session.current_phase = phase_num
            
            # Build prompt with context from previous phases
            prompt = phase_config["prompt_template"].format(
                target=target,
                target_ip=target_ip,
                phase1_summary=phase_summaries.get(1, "Não disponível"),
                phase2_summary=phase_summaries.get(2, "Não disponível"),
                phase3_summary=phase_summaries.get(3, "Não disponível"),
            )
            
            await send_func(
                f"\n{emoji} *Fase {phase_num}/5 — {phase_name}*\n"
                f"⏱️ Timeout: {timeout//60}min | Max: {max_cmds} comandos"
            )
            
            # Create flow
            flow_title = f"[Fase {phase_num}] {phase_name} — {target}"
            flow_id = self._create_flow(prompt, flow_title)
            
            if flow_id is None:
                result = PhaseResult(
                    phase_num=phase_num,
                    phase_name=phase_name,
                    status="failed",
                    error="Falha ao criar flow no PentAGI"
                )
                session.phases.append(result)
                await send_func(f"❌ Fase {phase_num} falhou — não conseguiu criar flow")
                continue
            
            session.active_flow_id = flow_id
            self.save_flow(user_id, flow_id)
            
            await send_func(f"🚀 Flow #{flow_id} criado")
            
            # Wait for completion
            phase_start = time.time()
            end_status, cmds = await self._wait_for_flow(
                flow_id, timeout, max_cmds, send_func, session=session
            )
            duration = time.time() - phase_start
            
            # Collect output
            output = collect_phase_output(flow_id)
            total_subs, completed_subs = get_flow_subtask_status(flow_id)
            
            # Store summary for next phases
            phase_summaries[phase_num] = output
            
            result = PhaseResult(
                phase_num=phase_num,
                phase_name=phase_name,
                flow_id=flow_id,
                status=end_status,
                commands_executed=cmds,
                subtasks_completed=completed_subs,
                raw_output=output,
                duration_secs=duration,
            )
            session.phases.append(result)
            session.active_flow_id = None
            
            # Cleanup terminal container for this phase
            if flow_id:
                try:
                    subprocess.run(
                        ["docker", "stop", f"pentagi-terminal-{flow_id}"],
                        capture_output=True, timeout=10
                    )
                    subprocess.run(
                        ["docker", "rm", f"pentagi-terminal-{flow_id}"],
                        capture_output=True, timeout=10
                    )
                except Exception:
                    pass  # Non-critical — container may not exist
            
            # Status emoji
            status_emoji = {
                "completed": "✅",
                "timeout": "⏰",
                "max_commands": "🔢",
                "failed": "❌",
            }.get(end_status, "❓")
            
            await send_func(
                f"{status_emoji} *Fase {phase_num} finalizada* ({end_status})\n"
                f"📊 {cmds} comandos | ⏱️ {int(duration)}s"
            )
        
        # ── PHASE 5: Report ──
        if not session.aborted:
            session.current_phase = 5
            await send_func("\n📝 *Fase 5/5 — Montando Relatório*")
            
            report = self._build_report(session, target, target_ip, phase_summaries)
            
            # Save report to file
            report_path = f"/tmp/guided_scan_{target.replace('.','_')}_{int(time.time())}.md"
            try:
                with open(report_path, 'w') as f:
                    f.write(report)
            except Exception as e:
                log.error(f"Failed to save report: {e}")
                report_path = None
            
            await send_func(
                f"✅ *Guided Scan Completo — {target}*\n"
                f"📊 {session.total_commands()} comandos totais | "
                f"{len([p for p in session.phases if p.status == 'completed'])}/{len(session.phases)} fases completadas\n"
                f"⏱️ Duração total: {int(time.time() - session.started_at)}s"
            )
            
            result = PhaseResult(
                phase_num=5,
                phase_name="Relatório",
                status="completed",
            )
            session.phases.append(result)
        
        # Cleanup
        self.clear_flow(user_id)
        
        # Return report path and markdown
        return report_path if not session.aborted else None, report if not session.aborted else ""
    
    def _build_report(self, session, target, target_ip, summaries):
        """Build the final report from real collected data. No LLM hallucination."""
        import re
        from datetime import datetime, timezone
        
        ansi_re = re.compile(r'\x1b\[[0-9;]*[mK]|\r|\\x1B\[[0-9;]*[mK]|\\r|\\n')
        
        def clean(text):
            if not text:
                return "Sem dados coletados."
            cleaned = ansi_re.sub('\n', text)
            # Remove excessive empty lines
            cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
            return cleaned.strip() or "Sem dados coletados."
        
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        total_duration = int(time.time() - session.started_at)
        
        lines = []
        lines.append(f"# Penetration Test Report — {target}")
        lines.append(f"**Gerado por:** Dimitri (Guided Scan Engine)")
        lines.append(f"**Data:** {now}")
        lines.append(f"**Alvo:** {target} ({target_ip})")
        lines.append(f"**Duração total:** {total_duration}s ({total_duration//60}min)")
        lines.append(f"**Comandos executados:** {session.total_commands()}")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # Summary table
        lines.append("## Resumo das Fases")
        lines.append("")
        lines.append("| Fase | Nome | Status | Comandos | Duração |")
        lines.append("|------|------|--------|----------|---------|")
        for p in session.phases:
            status_text = {
                "completed": "✅ Completo",
                "timeout": "⏰ Timeout",
                "max_commands": "🔢 Limite cmds",
                "failed": "❌ Falhou",
                "skipped": "⏭️ Pulada",
                "pending": "⏳ Pendente",
            }.get(p.status, p.status)
            lines.append(
                f"| {p.phase_num} | {p.phase_name} | {status_text} | "
                f"{p.commands_executed} | {int(p.duration_secs)}s |"
            )
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # Phase details
        for p in session.phases:
            if p.status == "skipped" or p.phase_num == 5:
                continue
            
            lines.append(f"## Fase {p.phase_num} — {p.phase_name}")
            lines.append(f"**Flow:** #{p.flow_id} | **Status:** {p.status} | "
                        f"**Comandos:** {p.commands_executed} | **Duração:** {int(p.duration_secs)}s")
            lines.append("")
            
            output = clean(summaries.get(p.phase_num, ""))
            if len(output) > 8000:
                output = output[:4000] + "\n\n[... output truncado ...]\n\n" + output[-4000:]
            
            lines.append("### Output")
            lines.append("```")
            lines.append(output)
            lines.append("```")
            lines.append("")
        
        # Footer
        lines.append("---")
        lines.append("")
        lines.append("## Próximos Passos")
        lines.append("")
        lines.append("Este relatório contém dados brutos coletados pelo scan automatizado.")
        lines.append("Para análise aprofundada e recomendações de correção, use o Dimitri Protocol:")
        lines.append("1. Cole este relatório no Claude Code com o prompt de análise")
        lines.append("2. Claude Code vai classificar cada achado por severidade")
        lines.append("3. Gere comandos de validação e mande de volta pro Dimitri")
        lines.append("")
        lines.append("---")
        lines.append(f"*Gerado automaticamente por Dimitri Guided Scan Engine v1.0 — {now}*")
        
        return "\n".join(lines)
