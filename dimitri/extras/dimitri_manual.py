#!/usr/bin/env python3
"""GLOUSOFT — Dimitri Platform Technical Manual Generator"""
import math
from datetime import datetime, timezone, timedelta
import html as html_mod

try:
    import weasyprint
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "weasyprint", "-q"])
    import weasyprint

BRT = timezone(timedelta(hours=-3))
now = datetime.now(BRT)
date_str = now.strftime("%d/%m/%Y")

def esc(t):
    return html_mod.escape(str(t)) if t else ""

CSS = '''
@page {
    size: A4;
    margin: 0;
}
@page :first {
    margin: 0;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    font-family: 'Segoe UI', 'Inter', -apple-system, sans-serif;
    color: #c8d6e5;
    background: #080c14;
    font-size: 9.5pt;
    line-height: 1.6;
}

/* ═══ COVER ═══ */
.cover {
    height: 297mm;
    background: linear-gradient(160deg, #080c14 0%, #0d1b2a 35%, #1b2838 70%, #0f172a 100%);
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    text-align: center;
    position: relative;
    overflow: hidden;
    page-break-after: always;
}
.cover::before {
    content: '';
    position: absolute;
    width: 600px; height: 600px;
    top: -200px; right: -200px;
    background: radial-gradient(circle, rgba(0,230,118,0.04) 0%, transparent 70%);
    border-radius: 50%;
}
.cover::after {
    content: '';
    position: absolute;
    width: 400px; height: 400px;
    bottom: -100px; left: -100px;
    background: radial-gradient(circle, rgba(68,138,255,0.04) 0%, transparent 70%);
    border-radius: 50%;
}
.cover-brand {
    font-size: 58pt;
    font-weight: 900;
    letter-spacing: -3px;
    background: linear-gradient(135deg, #00e676 0%, #00bcd4 40%, #448aff 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    position: relative;
    margin-bottom: 4px;
}
.cover-division {
    font-size: 10pt;
    color: #37474f;
    letter-spacing: 8px;
    text-transform: uppercase;
    margin-bottom: 50px;
}
.cover-line {
    width: 200px;
    height: 1px;
    background: linear-gradient(90deg, transparent, #00e676 50%, transparent);
    margin: 0 auto 40px;
}
.cover-doc-type {
    font-size: 9pt;
    color: #00e676;
    letter-spacing: 6px;
    text-transform: uppercase;
    margin-bottom: 16px;
}
.cover-title {
    font-size: 34pt;
    font-weight: 800;
    color: #ffffff;
    margin-bottom: 6px;
    position: relative;
}
.cover-subtitle {
    font-size: 13pt;
    color: #546e7a;
    margin-bottom: 50px;
}
.cover-info {
    font-size: 8.5pt;
    color: #37474f;
    line-height: 2.2;
}
.cover-info strong { color: #546e7a; }
.cover-footer {
    position: absolute;
    bottom: 24px;
    left: 0; right: 0;
    text-align: center;
    font-size: 7pt;
    color: #263238;
    letter-spacing: 3px;
    text-transform: uppercase;
}

/* ═══ PAGES ═══ */
.page {
    padding: 22mm 18mm 22mm 18mm;
    background: #080c14;
    page-break-before: always;
    position: relative;
    min-height: 297mm;
}
.page::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, #00e676, #00bcd4, #448aff, #7c4dff);
}
.pg-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-bottom: 8px;
    border-bottom: 1px solid #111d2c;
    margin-bottom: 18px;
}
.pg-logo {
    font-size: 10pt;
    font-weight: 800;
    background: linear-gradient(135deg, #00e676, #448aff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.pg-info {
    font-size: 6.5pt;
    color: #37474f;
    text-align: right;
}
.pg-foot {
    position: absolute;
    bottom: 14mm;
    left: 18mm; right: 18mm;
    display: flex;
    justify-content: space-between;
    font-size: 6.5pt;
    color: #263238;
    border-top: 1px solid #111d2c;
    padding-top: 4px;
}

h1 {
    font-size: 22pt;
    font-weight: 800;
    color: #ffffff;
    margin-bottom: 14px;
    padding-left: 14px;
    border-left: 3px solid #00e676;
    line-height: 1.2;
}
h2 {
    font-size: 14pt;
    font-weight: 700;
    color: #e0e0e0;
    margin: 22px 0 10px 0;
    padding-bottom: 5px;
    border-bottom: 1px solid #111d2c;
}
h3 {
    font-size: 11pt;
    font-weight: 600;
    color: #90a4ae;
    margin: 14px 0 6px 0;
}
p, li { color: #90a4ae; margin-bottom: 6px; }
ul { padding-left: 18px; }
strong { color: #c8d6e5; }
em { color: #78909c; }
code {
    font-family: 'JetBrains Mono', 'Consolas', monospace;
    font-size: 8pt;
    background: #0d1117;
    color: #00e676;
    padding: 1px 5px;
    border-radius: 3px;
}
pre {
    font-family: 'JetBrains Mono', 'Consolas', monospace;
    font-size: 7.5pt;
    background: #0d1117;
    color: #78909c;
    padding: 10px 14px;
    border-radius: 6px;
    border-left: 2px solid #00e676;
    margin: 8px 0;
    white-space: pre-wrap;
    word-break: break-word;
    line-height: 1.7;
}
pre .cmd { color: #00e676; }
pre .comment { color: #37474f; }
pre .output { color: #546e7a; }

/* ═══ CARDS ═══ */
.card {
    background: linear-gradient(145deg, #0d1520 0%, #0a0f18 100%);
    border: 1px solid #111d2c;
    border-radius: 8px;
    padding: 14px 16px;
    margin: 10px 0;
}
.card-accent { border-left: 3px solid #00e676; }
.card-blue { border-left: 3px solid #448aff; }
.card-orange { border-left: 3px solid #ff6d00; }
.card-purple { border-left: 3px solid #7c4dff; }

/* ═══ GRID ═══ */
.grid2 { display: flex; gap: 10px; margin: 10px 0; }
.grid2 > div { flex: 1; }
.grid3 { display: flex; gap: 10px; margin: 10px 0; }
.grid3 > div { flex: 1; }

/* ═══ SPEC TABLE ═══ */
table {
    width: 100%;
    border-collapse: collapse;
    margin: 10px 0;
    font-size: 8.5pt;
}
th {
    background: #0d1520;
    color: #546e7a;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-size: 7pt;
    padding: 7px 10px;
    text-align: left;
    border-bottom: 2px solid #00e676;
}
td {
    padding: 6px 10px;
    border-bottom: 1px solid #111d2c;
    color: #90a4ae;
}
td code { background: none; padding: 0; }

/* ═══ ARCH DIAGRAM ═══ */
.arch-box {
    background: #0d1117;
    border: 1px solid #1a2332;
    border-radius: 6px;
    padding: 8px 12px;
    text-align: center;
    margin: 4px;
    font-size: 8pt;
}
.arch-box strong { display: block; color: #e0e0e0; font-size: 9pt; }
.arch-box .port { color: #00e676; font-family: monospace; font-size: 7pt; }
.arch-box .desc { color: #546e7a; font-size: 7pt; }
.arch-arrow {
    text-align: center;
    color: #00e676;
    font-size: 16pt;
    margin: 4px 0;
}
.arch-arrow-h {
    color: #00e676;
    font-size: 12pt;
    display: flex;
    align-items: center;
    justify-content: center;
}

/* ═══ BADGE ═══ */
.badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 7pt;
    font-weight: 700;
    letter-spacing: 0.5px;
}
.badge-green { background: rgba(0,230,118,0.15); color: #00e676; }
.badge-blue { background: rgba(68,138,255,0.15); color: #448aff; }
.badge-orange { background: rgba(255,109,0,0.15); color: #ff6d00; }
.badge-purple { background: rgba(124,77,255,0.15); color: #7c4dff; }

/* ═══ TOC ═══ */
.toc { margin: 16px 0; }
.toc-item {
    display: flex;
    justify-content: space-between;
    padding: 6px 0;
    border-bottom: 1px dotted #111d2c;
    font-size: 9.5pt;
}
.toc-item span:first-child { color: #c8d6e5; }
.toc-item span:last-child { color: #37474f; font-family: monospace; }
.toc-section { color: #00e676 !important; font-weight: 700; font-size: 10pt; margin-top: 8px; }

.highlight {
    background: rgba(0,230,118,0.06);
    border: 1px solid rgba(0,230,118,0.15);
    border-radius: 6px;
    padding: 10px 14px;
    margin: 10px 0;
}
.warning {
    background: rgba(255,109,0,0.06);
    border: 1px solid rgba(255,109,0,0.15);
    border-radius: 6px;
    padding: 10px 14px;
    margin: 10px 0;
}
'''

# ─────────────────────────────────────────────────────────────────
# CONTENT
# ─────────────────────────────────────────────────────────────────

def pg(num, content):
    return f'''
<div class="page">
    <div class="pg-head">
        <div class="pg-logo">GLOUSOFT</div>
        <div class="pg-info">Manual Técnico — Dimitri Platform v1.0<br>Ref: GLOU-MAN-{now.strftime("%Y%m%d")}-001 | {date_str}</div>
    </div>
    {content}
    <div class="pg-foot">
        <span>GLOUSOFT — Documento Confidencial</span>
        <span>Página {num}</span>
    </div>
</div>'''

cover = f'''
<div class="cover">
    <div class="cover-brand">GLOUSOFT</div>
    <div class="cover-division">Cybersecurity Division</div>
    <div class="cover-line"></div>
    <div class="cover-doc-type">Manual Técnico</div>
    <div class="cover-title">Dimitri Platform</div>
    <div class="cover-subtitle">Plataforma de Pentest Autônomo com Inteligência Artificial</div>
    <div class="cover-line" style="margin-top:40px;"></div>
    <div class="cover-info">
        <strong>Versão:</strong> 1.0<br>
        <strong>Data:</strong> {date_str}<br>
        <strong>Classificação:</strong> Confidencial — Uso Interno<br>
        <strong>Referência:</strong> GLOU-MAN-{now.strftime("%Y%m%d")}-001
    </div>
    <div class="cover-footer">⬥ Propriedade Intelectual GLOUSOFT — Todos os direitos reservados ⬥</div>
</div>'''

# PAGE 2 — TOC
p2 = pg(2, '''
<h1>Índice</h1>
<div class="toc">
    <div class="toc-item toc-section"><span>1. Visão Geral da Plataforma</span><span>3</span></div>
    <div class="toc-item"><span>&nbsp;&nbsp;&nbsp;1.1 O que é o Dimitri</span><span>3</span></div>
    <div class="toc-item"><span>&nbsp;&nbsp;&nbsp;1.2 Diferencial Técnico</span><span>3</span></div>
    <div class="toc-item"><span>&nbsp;&nbsp;&nbsp;1.3 Stack Tecnológico</span><span>3</span></div>
    
    <div class="toc-item toc-section"><span>2. Arquitetura do Sistema</span><span>4</span></div>
    <div class="toc-item"><span>&nbsp;&nbsp;&nbsp;2.1 Diagrama de Componentes</span><span>4</span></div>
    <div class="toc-item"><span>&nbsp;&nbsp;&nbsp;2.2 Fluxo de Dados</span><span>4</span></div>
    <div class="toc-item"><span>&nbsp;&nbsp;&nbsp;2.3 Modelo Híbrido de IA</span><span>4</span></div>
    
    <div class="toc-item toc-section"><span>3. Componentes Detalhados</span><span>5</span></div>
    <div class="toc-item"><span>&nbsp;&nbsp;&nbsp;3.1 PentAGI — Motor Multi-Agent</span><span>5</span></div>
    <div class="toc-item"><span>&nbsp;&nbsp;&nbsp;3.2 DeepSeek AI — Orquestrador</span><span>5</span></div>
    <div class="toc-item"><span>&nbsp;&nbsp;&nbsp;3.3 Qwen3-Coder-30B — Executor/Analista</span><span>5</span></div>
    <div class="toc-item"><span>&nbsp;&nbsp;&nbsp;3.4 LLM Router — Proxy Inteligente</span><span>5</span></div>
    <div class="toc-item"><span>&nbsp;&nbsp;&nbsp;3.5 Bot Telegram — Interface de Comando</span><span>6</span></div>
    
    <div class="toc-item toc-section"><span>4. Arsenal de Ferramentas</span><span>7</span></div>
    <div class="toc-item toc-section"><span>5. Guia de Operação</span><span>8</span></div>
    <div class="toc-item"><span>&nbsp;&nbsp;&nbsp;5.1 Comandos do Bot</span><span>8</span></div>
    <div class="toc-item"><span>&nbsp;&nbsp;&nbsp;5.2 Fluxo de um Scan</span><span>8</span></div>
    <div class="toc-item"><span>&nbsp;&nbsp;&nbsp;5.3 Relatório Enterprise</span><span>8</span></div>
    
    <div class="toc-item toc-section"><span>6. Infraestrutura & Serviços</span><span>9</span></div>
    <div class="toc-item toc-section"><span>7. Segurança & Compliance</span><span>10</span></div>
    <div class="toc-item toc-section"><span>8. Manutenção & Operações</span><span>11</span></div>
    <div class="toc-item toc-section"><span>9. Especificações Técnicas</span><span>12</span></div>
</div>
''')

# PAGE 3 — Overview
p3 = pg(3, '''
<h1>1. Visão Geral da Plataforma</h1>

<h2>1.1 O que é o Dimitri</h2>
<p>Dimitri é uma <strong>plataforma de pentest autônomo</strong> que combina múltiplos agentes de inteligência artificial com um arsenal completo de ferramentas de segurança ofensiva. A plataforma opera de forma autônoma: o operador seleciona o tipo de avaliação e o alvo, e o sistema executa todas as fases do pentest — reconhecimento, enumeração, scanning de vulnerabilidades, exploração e geração de relatório — sem intervenção humana.</p>

<p>O sistema utiliza uma arquitetura <strong>multi-agent com modelo híbrido de IA</strong>: um modelo de linguagem de grande capacidade (DeepSeek) para orquestração estratégica e tomada de decisão, e um modelo local de alta performance (Qwen3-Coder-30B) para execução de comandos, análise de resultados e geração de relatórios — tudo processado localmente, sem envio de dados sensíveis para nuvem.</p>

<h2>1.2 Diferencial Técnico</h2>
<div class="grid2">
    <div class="card card-accent">
        <h3>IA Híbrida Multi-Model</h3>
        <p>Dois modelos especializados trabalhando em conjunto: DeepSeek para raciocínio estratégico e planejamento de ataque, Qwen3-30B para execução técnica e análise local. Router inteligente com fallback automático.</p>
    </div>
    <div class="card card-blue">
        <h3>Processamento Local</h3>
        <p>Modelo Qwen3-Coder-30B roda inteiramente na GPU local. Dados de scan, credenciais descobertas e relatórios nunca saem da máquina. Zero vazamento de informação do cliente.</p>
    </div>
</div>
<div class="grid2">
    <div class="card card-purple">
        <h3>Multi-Agent Autônomo</h3>
        <p>11 agentes especializados (adviser, pentester, coder, installer, searcher, etc.) que colaboram em tempo real. Cada agente tem um papel específico na cadeia de ataque.</p>
    </div>
    <div class="card card-orange">
        <h3>Sem Restrições de Censura</h3>
        <p>Modelo local utiliza versão abliterated (desbloqueada), sem filtros de conteúdo que impeçam a execução de técnicas ofensivas legítimas de pentest. Essencial para avaliações realistas.</p>
    </div>
</div>

<h2>1.3 Stack Tecnológico</h2>
<table>
    <thead><tr><th>Camada</th><th>Tecnologia</th><th>Função</th></tr></thead>
    <tbody>
        <tr><td>Orquestração IA</td><td>DeepSeek-Chat / DeepSeek-Reasoner</td><td>Planejamento estratégico, decomposição de tasks, reflexão</td></tr>
        <tr><td>Execução IA</td><td>Qwen3-Coder-30B-A3B (abliterated)</td><td>Execução de comandos, análise de output, geração de relatório</td></tr>
        <tr><td>Embeddings</td><td>Qwen3-1.7B</td><td>Memória vetorial, busca semântica de contexto</td></tr>
        <tr><td>Backend</td><td>PentAGI v1.2.0 (Go)</td><td>Motor multi-agent, gerenciamento de flows e tasks</td></tr>
        <tr><td>Roteamento</td><td>LLM Router v2 (Python/aiohttp)</td><td>Proxy inteligente com fallback DeepSeek → Qwen</td></tr>
        <tr><td>Interface</td><td>Bot Telegram (Python)</td><td>Interface de comando com menu interativo</td></tr>
        <tr><td>Banco de Dados</td><td>PostgreSQL + pgvector</td><td>Persistência de flows, logs, memória vetorial</td></tr>
        <tr><td>Containers</td><td>Docker + Kali Linux</td><td>Ambiente isolado de execução por scan</td></tr>
        <tr><td>Inferência</td><td>llama.cpp (llama-server)</td><td>Servidor de inferência com GPU offload</td></tr>
        <tr><td>GPU</td><td>NVIDIA RTX 3070 Ti (8GB VRAM)</td><td>Aceleração de inferência e embeddings</td></tr>
    </tbody>
</table>
''')

# PAGE 4 — Architecture
p4 = pg(4, '''
<h1>2. Arquitetura do Sistema</h1>

<h2>2.1 Diagrama de Componentes</h2>

<div style="text-align:center; margin:12px 0;">
    <div class="arch-box" style="display:inline-block;width:200px;border-color:#00e676;">
        <strong>Operador</strong>
        <span class="desc">Telegram App</span>
    </div>
    <div class="arch-arrow">↓</div>
    <div class="arch-box" style="display:inline-block;width:280px;border-color:#448aff;">
        <strong>Bot Telegram</strong>
        <span class="port">pentagi-telegram.service</span>
        <span class="desc">Menu interativo • Narração em tempo real • Geração de relatório</span>
    </div>
    <div class="arch-arrow">↓</div>
    <div class="arch-box" style="display:inline-block;width:320px;border-color:#7c4dff;">
        <strong>PentAGI Engine</strong>
        <span class="port">:8443 (HTTPS API)</span>
        <span class="desc">11 agentes • Task decomposition • Flow management • Container orchestration</span>
    </div>
    <div class="arch-arrow">↓</div>
    <div style="display:flex;justify-content:center;gap:8px;margin:6px 0;">
        <div class="arch-box" style="width:180px;border-color:#ff6d00;">
            <strong>LLM Router</strong>
            <span class="port">:8090</span>
            <span class="desc">Routing • Fallback • Model rewrite</span>
        </div>
        <div class="arch-box" style="width:180px;border-color:#00e676;">
            <strong>Kali Container</strong>
            <span class="port">Isolado por flow</span>
            <span class="desc">18+ tools ofensivas</span>
        </div>
    </div>
    <div class="arch-arrow">↓</div>
    <div style="display:flex;justify-content:center;gap:8px;">
        <div class="arch-box" style="width:150px;border-color:#ff1744;">
            <strong>DeepSeek API</strong>
            <span class="desc">Orquestração</span>
        </div>
        <div class="arch-box" style="width:150px;border-color:#00e676;">
            <strong>Qwen3-30B</strong>
            <span class="port">:8080 (GPU)</span>
            <span class="desc">Execução local</span>
        </div>
        <div class="arch-box" style="width:150px;border-color:#448aff;">
            <strong>Qwen3-1.7B</strong>
            <span class="port">:8081 (GPU)</span>
            <span class="desc">Embeddings</span>
        </div>
    </div>
</div>

<h2>2.2 Fluxo de Dados</h2>
<div class="card card-accent">
    <p><strong>1.</strong> Operador seleciona tipo de scan e alvo via Telegram → <strong>2.</strong> Bot envia prompt otimizado para PentAGI API → <strong>3.</strong> PentAGI decompõe em tasks e subtasks usando DeepSeek (via Router) → <strong>4.</strong> Agentes executam comandos no container Kali isolado → <strong>5.</strong> Output é analisado, próxima ação é decidida → <strong>6.</strong> Bot narra progresso em tempo real → <strong>7.</strong> Qwen 30B analisa resultados localmente → <strong>8.</strong> Relatório enterprise é gerado em PDF</p>
</div>

<h2>2.3 Modelo Híbrido de IA</h2>
<p>A plataforma implementa um padrão <strong>"Think Globally, Act Locally"</strong>:</p>

<div class="grid2">
    <div class="card card-orange">
        <h3>🧠 DeepSeek — O Estrategista</h3>
        <p>Modelo cloud com capacidade de raciocínio avançado (chain-of-thought). Responsável por:</p>
        <ul>
            <li>Decomposição do objetivo em tasks executáveis</li>
            <li>Decisão de próximos passos baseada em resultados</li>
            <li>Reflexão sobre falhas e replanejamento</li>
            <li>Geração de prompts para agentes especializados</li>
        </ul>
        <p><em>Roles: primary_agent, adviser, reflector, generator, refiner</em></p>
    </div>
    <div class="card card-accent">
        <h3>⚡ Qwen3-30B — O Executor</h3>
        <p>Modelo local com 30 bilhões de parâmetros, processamento GPU. Responsável por:</p>
        <ul>
            <li>Execução de comandos no terminal Kali</li>
            <li>Parsing e análise de output de ferramentas</li>
            <li>Geração de scripts e payloads</li>
            <li>Análise final e geração de relatórios</li>
        </ul>
        <p><em>Roles: pentester, coder, installer, searcher, enricher</em></p>
    </div>
</div>

<div class="highlight">
    <strong>Fallback Automático:</strong> Se o DeepSeek estiver indisponível (timeout, quota excedida), o LLM Router redireciona automaticamente para o Qwen local. O sistema nunca para — degrada graciosamente.
</div>
''')

# PAGE 5 — Components Detail
p5 = pg(5, '''
<h1>3. Componentes Detalhados</h1>

<h2>3.1 PentAGI — Motor Multi-Agent</h2>
<p>PentAGI é o backend compilado em Go que implementa a arquitetura multi-agent. Gerencia o ciclo de vida completo de um pentest:</p>
<div class="card">
    <table>
        <thead><tr><th>Agente</th><th>Modelo</th><th>Função</th></tr></thead>
        <tbody>
            <tr><td><code>primary_agent</code></td><td>DeepSeek-Chat</td><td>Controlador principal — recebe o objetivo e decompõe em tasks</td></tr>
            <tr><td><code>adviser</code></td><td>DeepSeek-Chat</td><td>Aconselha o agente principal sobre estratégia</td></tr>
            <tr><td><code>reflector</code></td><td>DeepSeek-Chat</td><td>Analisa resultados e identifica falhas na abordagem</td></tr>
            <tr><td><code>generator</code></td><td>DeepSeek-Chat</td><td>Gera conteúdo (scripts, payloads, queries)</td></tr>
            <tr><td><code>refiner</code></td><td>DeepSeek-Chat</td><td>Refina e otimiza outputs dos outros agentes</td></tr>
            <tr><td><code>pentester</code></td><td>Qwen3-30B</td><td>Executa comandos de pentest no terminal</td></tr>
            <tr><td><code>coder</code></td><td>Qwen3-30B</td><td>Escreve e modifica scripts/exploits</td></tr>
            <tr><td><code>installer</code></td><td>Qwen3-30B</td><td>Instala e configura ferramentas no container</td></tr>
            <tr><td><code>searcher</code></td><td>Qwen3-30B</td><td>Pesquisa informações sobre o alvo e vulnerabilidades</td></tr>
            <tr><td><code>enricher</code></td><td>Qwen3-30B</td><td>Enriquece dados com contexto adicional</td></tr>
            <tr><td><code>simple/simple_json</code></td><td>Qwen3-30B</td><td>Classificação e decisões rápidas (escolha de imagem, idioma)</td></tr>
        </tbody>
    </table>
</div>

<h2>3.2 DeepSeek AI — Orquestrador</h2>
<div class="card card-orange">
    <p>Dois modelos disponíveis via API:</p>
    <ul>
        <li><strong>DeepSeek-Chat:</strong> Modelo de conversação com capacidade de function calling. Usado para planejamento, decomposição e reflexão.</li>
        <li><strong>DeepSeek-Reasoner:</strong> Modelo com chain-of-thought estendido para problemas complexos. Ativado automaticamente pelo PentAGI para decisões críticas.</li>
    </ul>
    <p><em>Comunicação via LLM Router — a chave de API nunca é exposta ao container de execução.</em></p>
</div>

<h2>3.3 Qwen3-Coder-30B — Executor & Analista</h2>
<div class="card card-accent">
    <p><strong>Especificações do modelo:</strong></p>
    <ul>
        <li><strong>Arquitetura:</strong> Mixture-of-Experts (MoE) com 30B parâmetros totais, 3B ativos por inference</li>
        <li><strong>Quantização:</strong> Q4_K_S (17.4 GB em disco)</li>
        <li><strong>GPU Offload:</strong> 25 camadas na GPU, restante em RAM</li>
        <li><strong>Context Window:</strong> 65,536 tokens (2 slots × 32K)</li>
        <li><strong>Versão:</strong> Abliterated (sem filtros de censura para operações ofensivas)</li>
        <li><strong>Servidor:</strong> llama.cpp (llama-server) com GPU CUDA</li>
    </ul>
    <p><strong>Dupla função:</strong></p>
    <ul>
        <li><strong>Execução:</strong> Recebe instruções dos agentes orquestradores e executa comandos reais no terminal</li>
        <li><strong>Análise:</strong> Pós-scan, recebe os dados brutos e gera análise estruturada com CVSS scoring, classificação CWE/OWASP e recomendações — tudo processado localmente</li>
    </ul>
</div>

<h2>3.4 LLM Router — Proxy Inteligente</h2>
<div class="card card-blue">
    <p>Componente custom desenvolvido em Python (aiohttp) que age como proxy reverso para todas as chamadas LLM:</p>
    <ul>
        <li><strong>Roteamento por modelo:</strong> Requests com model <code>deepseek-*</code> → DeepSeek API; model <code>qwen*</code> → servidor local</li>
        <li><strong>Reescrita de nomes:</strong> PentAGI adiciona prefixo <code>openai/</code> — o router faz strip automático</li>
        <li><strong>Fallback automático:</strong> Se DeepSeek retorna erro (timeout, 429, 500), a request é redirecionada para Qwen local</li>
        <li><strong>Backoff exponencial:</strong> Tentativas progressivas antes de ativar fallback</li>
        <li><strong>Health endpoint:</strong> <code>/health</code> para monitoramento</li>
    </ul>
</div>
''')

# PAGE 6 — Bot
p6 = pg(6, '''
<h2>3.5 Bot Telegram — Interface de Comando</h2>

<p>O bot Telegram é a interface primária de operação. Implementado em Python com a biblioteca <code>python-telegram-bot</code>, oferece uma interface menu-driven com botões inline — projetada para que qualquer operador consiga executar pentests sem conhecimento técnico de linha de comando.</p>

<h3>Características Técnicas</h3>
<div class="grid2">
    <div class="card">
        <h3>Interface</h3>
        <ul>
            <li>Menu interativo com InlineKeyboard</li>
            <li>Descrição detalhada de cada tipo de scan</li>
            <li>Fluxo guiado: selecionar → confirmar → digitar alvo</li>
            <li>Detecção automática de domínios em texto livre</li>
        </ul>
    </div>
    <div class="card">
        <h3>Narração em Tempo Real</h3>
        <ul>
            <li>Poll do PostgreSQL a cada 10 segundos</li>
            <li>Exibe subtasks, comandos executados, tool calls</li>
            <li>Rate limiting (3 msgs/ciclo) para evitar flood</li>
            <li>Detecção automática de conclusão/falha</li>
        </ul>
    </div>
</div>

<div class="card card-accent">
    <h3>Prompts Action-Oriented</h3>
    <p>Cada tipo de scan possui um prompt otimizado que força o PentAGI a executar comandos diretos no terminal. Os prompts incluem a instrução explícita: <em>"Go directly to terminal commands. Do NOT research or search the web first."</em></p>
    <p>Isso elimina o comportamento de loop de pesquisa e direciona a IA para ação imediata.</p>
</div>

<h3>Módulos Adicionais</h3>
<table>
    <thead><tr><th>Módulo</th><th>Arquivo</th><th>Linhas</th><th>Função</th></tr></thead>
    <tbody>
        <tr><td>Bot Principal</td><td><code>bot.py</code></td><td>1,900</td><td>Comandos, menu, narração, gerenciamento de flows</td></tr>
        <tr><td>Guided Scan</td><td><code>guided_scan.py</code></td><td>626</td><td>Scan em 5 fases independentes com stall detection</td></tr>
        <tr><td>Report Generator</td><td><code>glousoft_report.py</code></td><td>1,237</td><td>Relatório enterprise com análise Qwen + PDF dark theme</td></tr>
    </tbody>
</table>

<h3>Autenticação</h3>
<div class="warning">
    <p><strong>Acesso restrito.</strong> O bot responde exclusivamente a IDs de Telegram autorizados. Qualquer mensagem de um usuário não autorizado é silenciosamente ignorada. A lista de IDs é configurada na variável de ambiente <code>ALLOWED_USERS</code>.</p>
</div>

<h3>Guided Scan Engine</h3>
<p>Modo avançado que divide o pentest em 5 fases independentes, cada uma sendo um flow PentAGI separado:</p>

<div class="card">
    <table>
        <thead><tr><th>Fase</th><th>Objetivo</th><th>Timeout</th><th>Ferramentas</th></tr></thead>
        <tbody>
            <tr><td>1. Recon</td><td>Reconhecimento completo</td><td>10 min</td><td>nmap, DNS, WHOIS</td></tr>
            <tr><td>2. Fingerprint</td><td>Identificação de tecnologias</td><td>5 min</td><td>curl, whatweb</td></tr>
            <tr><td>3. Vuln Scan</td><td>Detecção de vulnerabilidades</td><td>15 min</td><td>Nuclei, Nikto</td></tr>
            <tr><td>4. Deep Probing</td><td>Exploração (condicional)</td><td>10 min</td><td>sqlmap, ffuf</td></tr>
            <tr><td>5. Report</td><td>Compilação de resultados</td><td>—</td><td>Qwen 30B + WeasyPrint</td></tr>
        </tbody>
    </table>
    <p><em>A Fase 4 só executa se a Fase 3 encontrar vulnerabilidades. Cada fase tem stall detection independente.</em></p>
</div>
''')

# PAGE 7 — Tools
p7 = pg(7, '''
<h1>4. Arsenal de Ferramentas</h1>

<p>Cada scan é executado dentro de um container Kali Linux isolado, pré-equipado com as ferramentas abaixo. Ferramentas adicionais são instaladas automaticamente pelo agente <code>installer</code> conforme necessidade.</p>

<h2>Ferramentas Pré-instaladas</h2>

<div class="grid2">
    <div class="card card-accent">
        <h3>Scanning & Enumeration</h3>
        <table>
            <tbody>
                <tr><td><code>nmap 7.98</code></td><td>Port scanner com detecção de serviços e OS</td></tr>
                <tr><td><code>nuclei 3.6.1</code></td><td>Scanner de vuln com 12,428 templates</td></tr>
                <tr><td><code>nikto 2.5.0</code></td><td>Web server scanner</td></tr>
                <tr><td><code>naabu</code></td><td>Port scanner rápido (SYN scan)</td></tr>
                <tr><td><code>httpx</code></td><td>HTTP probe com fingerprinting</td></tr>
            </tbody>
        </table>
    </div>
    <div class="card card-blue">
        <h3>Reconhecimento</h3>
        <table>
            <tbody>
                <tr><td><code>subfinder</code></td><td>Subdomain discovery passiva</td></tr>
                <tr><td><code>dnsx</code></td><td>DNS resolver rápido multi-query</td></tr>
                <tr><td><code>whatweb</code></td><td>Technology fingerprinting</td></tr>
                <tr><td><code>waybackurls</code></td><td>URLs históricas (Wayback Machine)</td></tr>
                <tr><td><code>gau</code></td><td>URLs de múltiplas fontes OSINT</td></tr>
            </tbody>
        </table>
    </div>
</div>

<div class="grid2">
    <div class="card card-purple">
        <h3>Exploração Web</h3>
        <table>
            <tbody>
                <tr><td><code>sqlmap</code></td><td>Detecção e exploração de SQL injection</td></tr>
                <tr><td><code>ffuf</code></td><td>Directory/parameter fuzzing</td></tr>
                <tr><td><code>katana</code></td><td>Web crawler next-gen</td></tr>
                <tr><td><code>hakrawler</code></td><td>Web crawler com discovery de endpoints</td></tr>
                <tr><td><code>sslscan</code></td><td>Análise de configuração SSL/TLS</td></tr>
            </tbody>
        </table>
    </div>
    <div class="card card-orange">
        <h3>Utilitários</h3>
        <table>
            <tbody>
                <tr><td><code>chaos</code></td><td>Subdomain dataset (ProjectDiscovery)</td></tr>
                <tr><td><code>shuffledns</code></td><td>DNS bruteforce com resolvers custom</td></tr>
                <tr><td><code>curl</code></td><td>HTTP client para testes manuais</td></tr>
                <tr><td><code>whois</code></td><td>Domain registration lookup</td></tr>
                <tr><td><code>dig / nslookup</code></td><td>DNS query tools</td></tr>
            </tbody>
        </table>
    </div>
</div>

<div class="highlight">
    <strong>Instalação Dinâmica:</strong> O agente <code>installer</code> pode instalar qualquer ferramenta adicional durante o scan via <code>apt install</code> ou <code>go install</code>. O container Kali Linux tem acesso total a repositórios de pacotes.
</div>

<h2>Nuclei Templates</h2>
<div class="card">
    <p>O Nuclei opera com <strong>12,428 templates</strong> mantidos pela comunidade ProjectDiscovery, cobrindo:</p>
    <div class="grid3">
        <div>
            <ul>
                <li>CVEs conhecidos</li>
                <li>Misconfigurations</li>
                <li>Default credentials</li>
                <li>Exposed panels</li>
            </ul>
        </div>
        <div>
            <ul>
                <li>Subdomain takeover</li>
                <li>CRLF injection</li>
                <li>Open redirects</li>
                <li>SSRF</li>
            </ul>
        </div>
        <div>
            <ul>
                <li>XSS</li>
                <li>SQL injection</li>
                <li>File inclusion</li>
                <li>Technology detection</li>
            </ul>
        </div>
    </div>
</div>
''')

# PAGE 8 — Operations Guide
p8 = pg(8, '''
<h1>5. Guia de Operação</h1>

<h2>5.1 Comandos do Bot</h2>

<table>
    <thead><tr><th>Comando</th><th>Descrição</th><th>Exemplo</th></tr></thead>
    <tbody>
        <tr><td><code>/start</code></td><td>Abre o menu principal com botões interativos</td><td><code>/start</code></td></tr>
        <tr><td><code>/recon &lt;alvo&gt;</code></td><td>Reconhecimento: DNS, subdomínios, WHOIS, tecnologias</td><td><code>/recon empresa.com.br</code></td></tr>
        <tr><td><code>/scan &lt;alvo&gt;</code></td><td>Port scan: portas abertas, serviços, versões</td><td><code>/scan 192.168.1.0/24</code></td></tr>
        <tr><td><code>/vuln &lt;alvo&gt;</code></td><td>Vulnerability scan: Nuclei + Nikto (CVEs, misconfigs)</td><td><code>/vuln app.empresa.com</code></td></tr>
        <tr><td><code>/web &lt;alvo&gt;</code></td><td>Web app: SQLi, XSS, directory fuzzing, headers</td><td><code>/web loja.empresa.com</code></td></tr>
        <tr><td><code>/ssl &lt;alvo&gt;</code></td><td>SSL/TLS: certificados, cifras, protocolos</td><td><code>/ssl empresa.com.br</code></td></tr>
        <tr><td><code>/full &lt;alvo&gt;</code></td><td>Pentest completo: todas as fases em sequência</td><td><code>/full empresa.com.br</code></td></tr>
        <tr><td><code>/gscan &lt;alvo&gt;</code></td><td>Scan guiado: 5 fases independentes com stall detection</td><td><code>/gscan empresa.com.br</code></td></tr>
        <tr><td><code>/status</code></td><td>Status do scan em andamento</td><td><code>/status</code></td></tr>
        <tr><td><code>/stop</code></td><td>Para o scan ativo</td><td><code>/stop</code></td></tr>
        <tr><td><code>/report</code></td><td>Gera relatório PDF enterprise</td><td><code>/report</code></td></tr>
        <tr><td><code>/nuke</code></td><td>Reset total: para tudo, limpa DB, reinicia serviços</td><td><code>/nuke</code></td></tr>
    </tbody>
</table>

<h2>5.2 Fluxo de um Scan</h2>

<div class="card card-accent">
<pre>
<span class="comment">1. Operador abre o bot e digita /start</span>
<span class="cmd">   → Menu com 6 tipos de scan aparece com botões</span>

<span class="comment">2. Clica em "⚡ Vulnerability Scan"</span>
<span class="cmd">   → Bot mostra descrição detalhada do que o scan faz</span>

<span class="comment">3. Clica "✅ Selecionar este scan"</span>
<span class="cmd">   → Bot pede: "Agora digite o domínio ou IP do alvo"</span>

<span class="comment">4. Operador digita: empresa.com.br</span>
<span class="cmd">   → Bot cria flow no PentAGI com prompt otimizado</span>
<span class="cmd">   → Container Kali é criado automaticamente</span>
<span class="cmd">   → Ferramentas são verificadas/instaladas</span>

<span class="comment">5. Scan executa autonomamente</span>
<span class="cmd">   → Bot narra progresso: subtasks, comandos, findings</span>
<span class="cmd">   → DeepSeek decide próximos passos</span>
<span class="cmd">   → Qwen executa comandos no terminal</span>

<span class="comment">6. Scan completa</span>
<span class="cmd">   → Operador digita /report</span>
<span class="cmd">   → Qwen 30B analisa resultados localmente</span>
<span class="cmd">   → PDF enterprise é gerado e enviado no chat</span>
</pre>
</div>

<h2>5.3 Relatório Enterprise</h2>
<p>O sistema de relatório utiliza o Qwen3-30B para análise local dos resultados, gerando um PDF com:</p>
<div class="grid2">
    <div class="card">
        <ul>
            <li>Capa com branding e classificação</li>
            <li>Dashboard executivo com gauge de risco</li>
            <li>Gráfico de severidade por categoria</li>
            <li>Resumo executivo em português</li>
        </ul>
    </div>
    <div class="card">
        <ul>
            <li>Findings com CVSS 3.1, CWE, OWASP mapping</li>
            <li>Evidências técnicas por finding</li>
            <li>Remediações priorizadas</li>
            <li>Metodologia e ferramentas utilizadas</li>
        </ul>
    </div>
</div>
''')

# PAGE 9 — Infrastructure
p9 = pg(9, '''
<h1>6. Infraestrutura & Serviços</h1>

<h2>Serviços Systemd</h2>
<p>Todos os serviços são gerenciados via systemd com política de restart automático em caso de falha:</p>

<table>
    <thead><tr><th>Serviço</th><th>Unit</th><th>Porta</th><th>Restart Policy</th><th>Descrição</th></tr></thead>
    <tbody>
        <tr><td>Qwen3-30B</td><td><code>llama-server</code></td><td>8080</td><td>on-failure (30s)</td><td>Inferência GPU — 25 layers offload, ctx 65K</td></tr>
        <tr><td>Qwen3-1.7B</td><td><code>llama-router</code></td><td>8081</td><td>on-failure (30s)</td><td>Embeddings + fallback — 99 layers GPU, batch 2048</td></tr>
        <tr><td>LLM Router</td><td><code>llm-router</code></td><td>8090</td><td>on-failure (10s)</td><td>Proxy com routing e fallback automático</td></tr>
        <tr><td>Bot Telegram</td><td><code>pentagi-telegram</code></td><td>—</td><td>on-failure (5s)</td><td>Interface de operação</td></tr>
    </tbody>
</table>

<h2>Containers Docker</h2>
<table>
    <thead><tr><th>Container</th><th>Imagem</th><th>Porta</th><th>Função</th></tr></thead>
    <tbody>
        <tr><td><code>pentagi</code></td><td>vxcontrol/pentagi:latest</td><td>8443</td><td>Backend multi-agent</td></tr>
        <tr><td><code>pgvector</code></td><td>vxcontrol/pgvector:latest</td><td>5432</td><td>PostgreSQL + pgvector</td></tr>
        <tr><td><code>scraper</code></td><td>vxcontrol/scraper:latest</td><td>9443</td><td>Web scraper auxiliar</td></tr>
        <tr><td><code>pentagi-terminal-*</code></td><td>vxcontrol/kali-linux:latest</td><td>—</td><td>Container de execução (1 por flow)</td></tr>
    </tbody>
</table>

<div class="highlight">
    <strong>Isolamento por Flow:</strong> Cada scan cria um container Kali Linux dedicado (<code>pentagi-terminal-{flow_id}</code>). Isso garante que scans simultâneos não interferam entre si e que o ambiente é limpo a cada execução.
</div>

<h2>Banco de Dados</h2>
<div class="card card-blue">
    <p><strong>PostgreSQL</strong> com extensão <strong>pgvector</strong> para busca semântica.</p>
    <table>
        <thead><tr><th>Tabela</th><th>Função</th></tr></thead>
        <tbody>
            <tr><td><code>flows</code></td><td>Sessões de pentest (status, modelo, timestamps)</td></tr>
            <tr><td><code>tasks</code></td><td>Objetivos decompostos pelo agente principal</td></tr>
            <tr><td><code>subtasks</code></td><td>Ações específicas dentro de cada task</td></tr>
            <tr><td><code>termlogs</code></td><td>Comandos executados e output do terminal</td></tr>
            <tr><td><code>toolcalls</code></td><td>Chamadas de ferramentas pelos agentes</td></tr>
            <tr><td><code>searchlogs</code></td><td>Pesquisas realizadas pelo agente searcher</td></tr>
            <tr><td><code>agentlogs</code></td><td>Log de atividade de cada agente</td></tr>
            <tr><td><code>langchain_pg_embedding</code></td><td>Vetores de embedding para memória semântica</td></tr>
        </tbody>
    </table>
</div>

<h2>Rede</h2>
<div class="card">
    <table>
        <tbody>
            <tr><td><strong>Docker Bridge</strong></td><td><code>172.17.0.1</code></td><td>Host visto pelos containers</td></tr>
            <tr><td><strong>PentAGI Network</strong></td><td><code>172.18.0.0/16</code></td><td>Rede isolada dos containers PentAGI</td></tr>
            <tr><td><strong>Comunicação LLM</strong></td><td><code>http://172.17.0.1:8090</code></td><td>Container → Router → DeepSeek/Qwen</td></tr>
            <tr><td><strong>Comunicação Embeddings</strong></td><td><code>http://172.17.0.1:8081</code></td><td>Container → Qwen 1.7B (pgvector)</td></tr>
        </tbody>
    </table>
</div>
''')

# PAGE 10 — Security
p10 = pg(10, '''
<h1>7. Segurança & Compliance</h1>

<h2>Proteção de Dados</h2>
<div class="grid2">
    <div class="card card-accent">
        <h3>Processamento Local</h3>
        <p>O Qwen3-30B processa todos os dados de scan e gera relatórios <strong>inteiramente na máquina local</strong>. Dados sensíveis — credenciais descobertas, vulnerabilidades identificadas, output de ferramentas — nunca são enviados para APIs externas durante a fase de análise.</p>
    </div>
    <div class="card card-orange">
        <h3>Isolamento de Execução</h3>
        <p>Cada scan roda em um <strong>container Kali Linux isolado</strong> que é destruído após o uso. Não há persistência de dados de scan entre execuções. O container não tem acesso à rede interna da máquina host.</p>
    </div>
</div>

<h2>Controle de Acesso</h2>
<div class="card">
    <table>
        <thead><tr><th>Camada</th><th>Mecanismo</th><th>Descrição</th></tr></thead>
        <tbody>
            <tr><td>Bot Telegram</td><td>Allowlist por ID</td><td>Apenas IDs autorizados podem interagir</td></tr>
            <tr><td>PentAGI API</td><td>JWT Token</td><td>Autenticação por token com expiração</td></tr>
            <tr><td>Containers</td><td>Docker isolation</td><td>Network namespace isolado por flow</td></tr>
            <tr><td>LLM Router</td><td>Bind local</td><td>Aceita conexões apenas de Docker bridge</td></tr>
            <tr><td>Modelos locais</td><td>Bind localhost</td><td>Qwen não é acessível externamente</td></tr>
        </tbody>
    </table>
</div>

<h2>Comunicação com APIs Externas</h2>
<div class="warning">
    <p>A única comunicação externa é com a <strong>API do DeepSeek</strong> para orquestração. Os dados enviados são exclusivamente <strong>prompts de planejamento e decomposição de tasks</strong> — nunca output bruto de ferramentas, credenciais ou dados do alvo. A análise de resultados sensíveis é feita pelo Qwen local.</p>
</div>

<h2>Resiliência</h2>
<div class="card card-blue">
    <ul>
        <li><strong>Auto-restart:</strong> Todos os serviços reiniciam automaticamente em caso de falha</li>
        <li><strong>Fallback LLM:</strong> Se DeepSeek falhar, Qwen local assume — o sistema nunca para</li>
        <li><strong>Stall Detection:</strong> Bot detecta scans travados e notifica o operador</li>
        <li><strong>Nuclear Reset:</strong> Comando <code>/nuke</code> restaura todo o sistema ao estado limpo</li>
        <li><strong>Persistência:</strong> Resultados salvos em PostgreSQL — sobrevivem a reinícios</li>
    </ul>
</div>

<h2>Compliance</h2>
<table>
    <thead><tr><th>Padrão</th><th>Aplicação</th></tr></thead>
    <tbody>
        <tr><td>OWASP Testing Guide v4.2</td><td>Metodologia de testes web</td></tr>
        <tr><td>PTES</td><td>Penetration Testing Execution Standard — framework geral</td></tr>
        <tr><td>NIST SP 800-115</td><td>Guia técnico de testes de segurança</td></tr>
        <tr><td>CVSS 3.1</td><td>Scoring de vulnerabilidades nos relatórios</td></tr>
        <tr><td>CWE / OWASP Top 10</td><td>Classificação de vulnerabilidades</td></tr>
    </tbody>
</table>
''')

# PAGE 11 — Maintenance
p11 = pg(11, '''
<h1>8. Manutenção & Operações</h1>

<h2>Verificação de Saúde</h2>
<pre>
<span class="comment"># Checar todos os serviços</span>
<span class="cmd">$ systemctl is-active llama-server llama-router llm-router pentagi-telegram</span>
<span class="output">active active active active</span>

<span class="comment"># Checar containers</span>
<span class="cmd">$ docker ps --format '{{.Names}} {{.Status}}'</span>
<span class="output">pentagi     Up 2 hours</span>
<span class="output">pgvector    Up 2 hours</span>
<span class="output">scraper     Up 2 hours</span>

<span class="comment"># Health dos modelos</span>
<span class="cmd">$ curl -s localhost:8080/health | jq .status</span>
<span class="output">"ok"</span>
<span class="cmd">$ curl -s localhost:8081/health | jq .status</span>
<span class="output">"ok"</span>
<span class="cmd">$ curl -s localhost:8090/health | jq .status</span>
<span class="output">"ok"</span>

<span class="comment"># GPU usage</span>
<span class="cmd">$ nvidia-smi --query-gpu=memory.used,memory.total --format=csv</span>
<span class="output">7890 MiB, 8192 MiB</span>
</pre>

<h2>Restart de Serviços</h2>
<pre>
<span class="comment"># Restart individual</span>
<span class="cmd">$ sudo systemctl restart llama-server</span>

<span class="comment"># Restart completo (todos os componentes)</span>
<span class="cmd">$ sudo systemctl restart llama-server llama-router llm-router pentagi-telegram</span>
<span class="cmd">$ cd /opt/pentagi && docker compose up -d</span>
</pre>

<div class="warning">
    <p><strong>Atenção:</strong> Para aplicar mudanças no <code>.env</code> do PentAGI, use <code>docker compose up -d</code> (não <code>docker restart</code>). O <code>docker restart</code> não relê variáveis de ambiente.</p>
</div>

<h2>Limpeza de Flows</h2>
<pre>
<span class="comment"># Listar flows ativos</span>
<span class="cmd">$ docker exec pgvector psql -U postgres pentagidb -c \\</span>
<span class="cmd">  "SELECT id, status, title FROM flows WHERE status IN ('running','waiting');"</span>

<span class="comment"># Limpar flows zombies</span>
<span class="cmd">$ docker exec pgvector psql -U postgres pentagidb -c \\</span>
<span class="cmd">  "UPDATE flows SET status='failed' WHERE status IN ('running','waiting');"</span>

<span class="comment"># Remover containers órfãos</span>
<span class="cmd">$ docker ps -aq --filter "name=pentagi-terminal-" | xargs -r docker rm -f</span>

<span class="comment"># Reset nuclear (via bot)</span>
<span class="cmd">/nuke</span>
</pre>

<h2>Logs</h2>
<pre>
<span class="cmd">$ journalctl -u pentagi-telegram -f</span>          <span class="comment"># Bot</span>
<span class="cmd">$ journalctl -u llm-router -f</span>                <span class="comment"># Router</span>
<span class="cmd">$ journalctl -u llama-server -f</span>              <span class="comment"># Qwen 30B</span>
<span class="cmd">$ docker logs pentagi -f --since 5m</span>          <span class="comment"># PentAGI</span>
</pre>

<h2>Atualização de Templates Nuclei</h2>
<pre>
<span class="comment"># Dentro do container Kali (durante um scan ativo)</span>
<span class="cmd">$ docker exec pentagi-terminal-XX nuclei -update-templates</span>
</pre>
''')

# PAGE 12 — Specs
p12 = pg(12, '''
<h1>9. Especificações Técnicas</h1>

<h2>Hardware</h2>
<table>
    <thead><tr><th>Componente</th><th>Especificação</th></tr></thead>
    <tbody>
        <tr><td>GPU</td><td>NVIDIA GeForce RTX 3070 Ti — 8,192 MiB VRAM</td></tr>
        <tr><td>RAM</td><td>64 GB DDR4</td></tr>
        <tr><td>Armazenamento</td><td>889 GB NVMe SSD (693 GB livres)</td></tr>
        <tr><td>Driver NVIDIA</td><td>v550.163.01</td></tr>
    </tbody>
</table>

<h2>Software</h2>
<table>
    <thead><tr><th>Componente</th><th>Versão</th></tr></thead>
    <tbody>
        <tr><td>Sistema Operacional</td><td>Kali GNU/Linux Rolling</td></tr>
        <tr><td>Kernel</td><td>6.18.12+kali-amd64</td></tr>
        <tr><td>Docker</td><td>27.5.1</td></tr>
        <tr><td>PentAGI</td><td>1.2.0-6050e7f</td></tr>
        <tr><td>llama.cpp</td><td>Latest (CUDA build)</td></tr>
        <tr><td>Python</td><td>3.13</td></tr>
        <tr><td>WeasyPrint</td><td>68.1</td></tr>
    </tbody>
</table>

<h2>Modelos de IA</h2>
<table>
    <thead><tr><th>Modelo</th><th>Parâmetros</th><th>Quantização</th><th>Tamanho</th><th>VRAM</th></tr></thead>
    <tbody>
        <tr><td>Qwen3-Coder-30B-A3B (abliterated)</td><td>30B (3B ativos/MoE)</td><td>Q4_K_S</td><td>17.4 GB</td><td>~5 GB</td></tr>
        <tr><td>Qwen3-1.7B</td><td>1.7B</td><td>Q8_0</td><td>1.8 GB</td><td>~2 GB</td></tr>
        <tr><td>DeepSeek-Chat</td><td>Cloud</td><td>—</td><td>—</td><td>—</td></tr>
        <tr><td>DeepSeek-Reasoner</td><td>Cloud</td><td>—</td><td>—</td><td>—</td></tr>
    </tbody>
</table>

<h2>Configuração de Inferência</h2>
<table>
    <thead><tr><th>Parâmetro</th><th>Qwen 30B</th><th>Qwen 1.7B</th></tr></thead>
    <tbody>
        <tr><td>Context Window</td><td>65,536 tokens</td><td>4,096 tokens</td></tr>
        <tr><td>Slots Paralelos</td><td>2</td><td>1</td></tr>
        <tr><td>GPU Layers</td><td>25</td><td>99 (full)</td></tr>
        <tr><td>Batch Size</td><td>Default</td><td>2,048</td></tr>
        <tr><td>Reasoning Mode</td><td>Desativado</td><td>Desativado</td></tr>
    </tbody>
</table>

<h2>Código-fonte</h2>
<table>
    <thead><tr><th>Arquivo</th><th>Linhas</th><th>Linguagem</th></tr></thead>
    <tbody>
        <tr><td>bot.py</td><td>1,900</td><td>Python</td></tr>
        <tr><td>guided_scan.py</td><td>626</td><td>Python</td></tr>
        <tr><td>glousoft_report.py</td><td>1,237</td><td>Python</td></tr>
        <tr><td>llm-router.py</td><td>~200</td><td>Python</td></tr>
        <tr><td><strong>Total custom</strong></td><td><strong>~3,963</strong></td><td></td></tr>
    </tbody>
</table>

<div style="text-align:center; margin-top:40px;">
    <div class="cover-line"></div>
    <p style="color:#37474f; font-size:8pt; margin-top:16px;">
        Este documento é propriedade intelectual da <strong style="color:#546e7a;">GLOUSOFT</strong>.<br>
        Distribuição não autorizada é proibida.<br><br>
        <em>Dimitri Platform v1.0 — Desenvolvido por GLOUSOFT Cybersecurity Division</em><br>
        <em>© ''' + str(now.year) + ''' GLOUSOFT — Todos os direitos reservados</em>
    </p>
</div>
''')

# ─── ASSEMBLE ───
html = f'''<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="utf-8"><style>{CSS}</style></head>
<body>
{cover}
{p2}
{p3}
{p4}
{p5}
{p6}
{p7}
{p8}
{p9}
{p10}
{p11}
{p12}
</body>
</html>'''

output = "/tmp/dimitri-manual-glousoft.pdf"
pdf_bytes = weasyprint.HTML(string=html).write_pdf()
with open(output, 'wb') as f:
    f.write(pdf_bytes)
print(f"[✓] Manual generated: {output} ({len(pdf_bytes):,} bytes)")
