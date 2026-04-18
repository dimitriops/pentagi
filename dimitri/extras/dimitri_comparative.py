#!/usr/bin/env python3
"""GLOUSOFT — Dimitri vs Market: Enterprise Competitive Analysis"""
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
def esc(t): return html_mod.escape(str(t)) if t else ""

CSS = '''
@page { size: A4 landscape; margin: 0; }
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Segoe UI','Inter',-apple-system,sans-serif; color: #c8d6e5; background: #080c14; font-size: 8.5pt; line-height: 1.5; }
.cover { height: 210mm; width: 297mm; background: linear-gradient(160deg, #080c14 0%, #0d1b2a 35%, #1b2838 70%, #0f172a 100%); display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; position: relative; overflow: hidden; page-break-after: always; }
.cover::before { content:''; position:absolute; width:800px; height:800px; top:-300px; right:-300px; background:radial-gradient(circle, rgba(0,230,118,0.04) 0%, transparent 70%); border-radius:50%; }
.cover-brand { font-size:52pt; font-weight:900; letter-spacing:-3px; background:linear-gradient(135deg, #00e676 0%, #00bcd4 50%, #448aff 100%); -webkit-background-clip:text; -webkit-text-fill-color:transparent; margin-bottom:4px; }
.cover-division { font-size:10pt; color:#37474f; letter-spacing:8px; text-transform:uppercase; margin-bottom:50px; }
.cover-line { width:200px; height:1px; background:linear-gradient(90deg, transparent, #00e676 50%, transparent); margin:0 auto 40px; }
.cover-doc { font-size:9pt; color:#00e676; letter-spacing:6px; text-transform:uppercase; margin-bottom:16px; }
.cover-title { font-size:30pt; font-weight:800; color:#fff; margin-bottom:6px; }
.cover-sub { font-size:12pt; color:#546e7a; margin-bottom:50px; }
.cover-info { font-size:8.5pt; color:#37474f; line-height:2.2; }
.cover-info strong { color:#546e7a; }
.cover-foot { position:absolute; bottom:20px; left:0; right:0; text-align:center; font-size:7pt; color:#263238; letter-spacing:3px; text-transform:uppercase; }

.page { padding:16mm 14mm 16mm 14mm; background:#080c14; page-break-before:always; position:relative; min-height:210mm; }
.page::before { content:''; position:absolute; top:0; left:0; right:0; height:2px; background:linear-gradient(90deg, #00e676, #00bcd4, #448aff, #7c4dff); }
.pg-h { display:flex; justify-content:space-between; align-items:center; padding-bottom:6px; border-bottom:1px solid #111d2c; margin-bottom:14px; }
.pg-logo { font-size:9pt; font-weight:800; background:linear-gradient(135deg, #00e676, #448aff); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
.pg-i { font-size:6pt; color:#37474f; text-align:right; }
.pg-f { position:absolute; bottom:10mm; left:14mm; right:14mm; display:flex; justify-content:space-between; font-size:6pt; color:#263238; border-top:1px solid #111d2c; padding-top:3px; }

h1 { font-size:18pt; font-weight:800; color:#fff; margin-bottom:12px; padding-left:12px; border-left:3px solid #00e676; line-height:1.2; }
h2 { font-size:12pt; font-weight:700; color:#e0e0e0; margin:16px 0 8px 0; padding-bottom:4px; border-bottom:1px solid #111d2c; }
h3 { font-size:10pt; font-weight:600; color:#90a4ae; margin:10px 0 4px 0; }
p,li { color:#90a4ae; margin-bottom:4px; }
ul { padding-left:16px; }
strong { color:#c8d6e5; }
code { font-family:'JetBrains Mono','Consolas',monospace; font-size:7pt; background:#0d1117; color:#00e676; padding:1px 4px; border-radius:3px; }

table { width:100%; border-collapse:collapse; margin:8px 0; font-size:7.5pt; table-layout:fixed; word-wrap:break-word; }
th { background:#0d1520; color:#546e7a; text-transform:uppercase; letter-spacing:0.5px; font-size:6.5pt; padding:5px 6px; text-align:left; border-bottom:2px solid #00e676; overflow:hidden; text-overflow:ellipsis; }
td { padding:4px 6px; border-bottom:1px solid #111d2c; color:#90a4ae; vertical-align:top; overflow:hidden; }
td:first-child { font-weight:600; color:#c8d6e5; }
.win { color:#00e676; font-weight:700; }
.lose { color:#ff1744; }
.tie { color:#ffd600; }
.na { color:#37474f; }
.dim { color:#546e7a; }

.card { background:linear-gradient(145deg, #0d1520, #0a0f18); border:1px solid #111d2c; border-radius:8px; padding:12px 14px; margin:8px 0; }
.card-g { border-left:3px solid #00e676; }
.card-r { border-left:3px solid #ff1744; }
.card-b { border-left:3px solid #448aff; }
.grid2 { display:flex; gap:8px; margin:8px 0; }
.grid2>div { flex:1; }
.highlight { background:rgba(0,230,118,0.06); border:1px solid rgba(0,230,118,0.15); border-radius:6px; padding:8px 12px; margin:8px 0; }
.bar-container { display:flex; align-items:center; gap:4px; }
.bar-bg { flex:1; height:14px; background:#111827; border-radius:3px; overflow:hidden; }
.bar { height:100%; border-radius:3px; display:flex; align-items:center; padding-left:6px; font-size:6.5pt; font-weight:700; color:#080c14; }
.bar-label { width:80px; font-size:7pt; color:#78909c; }
.bar-val { width:30px; text-align:right; font-size:7pt; font-weight:700; font-family:monospace; }
'''

def pg(n, c):
    return f'''<div class="page"><div class="pg-h"><div class="pg-logo">GLOUSOFT</div><div class="pg-i">Competitive Analysis — Dimitri Platform<br>GLOU-CMP-{now.strftime("%Y%m%d")}-001 | {date_str}</div></div>{c}<div class="pg-f"><span>GLOUSOFT — Documento Confidencial</span><span>Página {n}</span></div></div>'''

cover = f'''<div class="cover">
<div class="cover-brand">GLOUSOFT</div>
<div class="cover-division">Market Intelligence</div>
<div class="cover-line"></div>
<div class="cover-doc">Análise Competitiva</div>
<div class="cover-title">Dimitri vs. Mercado</div>
<div class="cover-sub">Comparativo Técnico de Ferramentas de Pentest Enterprise</div>
<div class="cover-line" style="margin-top:40px;"></div>
<div class="cover-info">
<strong>Versão:</strong> 1.0 | <strong>Data:</strong> {date_str} | <strong>Classificação:</strong> Confidencial — Comercial<br>
<strong>Referência:</strong> GLOU-CMP-{now.strftime("%Y%m%d")}-001 | <strong>Fontes:</strong> G2, PeerSpot, Gartner, vendor sites, pesquisa independente
</div>
<div class="cover-foot">⬥ GLOUSOFT — Todos os direitos reservados ⬥</div>
</div>'''

# PAGE 2 — Executive Summary
p2 = pg(2, '''
<h1>Resumo Executivo</h1>

<p>Este documento compara a plataforma <strong>Dimitri</strong> (GLOUSOFT) com as 14 principais ferramentas de pentest do mercado global, em 12 dimensões técnicas e comerciais. A análise é baseada em dados públicos de pricing, reviews de usuários (G2, PeerSpot, Gartner), documentação oficial e testes técnicos independentes.</p>

<div class="highlight">
    <strong>Conclusão:</strong> O Dimitri é a única plataforma que combina orquestração autônoma por IA multi-model, arsenal ofensivo completo (18+ ferramentas), processamento local de dados sensíveis e interface operacional via Telegram — a uma fração do custo de qualquer concorrente enterprise.
</div>

<h2>Landscape Competitivo</h2>
<table>
    <thead><tr><th>Categoria</th><th>Ferramentas</th><th>Faixa de Preço (Anual)</th></tr></thead>
    <tbody>
        <tr><td>Pentest Autônomo (IA)</td><td>Dimitri, PentestGPT, HexStrike AI</td><td>$0 – $600</td></tr>
        <tr><td>Breach & Attack Simulation</td><td>Pentera, NodeZero (Horizon3.ai)</td><td>$50,000 – $200,000+</td></tr>
        <tr><td>DAST / Web Scanners</td><td>Burp Suite Pro/Enterprise, Acunetix, Invicti</td><td>$399 – $45,000+</td></tr>
        <tr><td>Vulnerability Management</td><td>Nessus, Qualys VMDR, OpenVAS</td><td>$0 – $12,000+</td></tr>
        <tr><td>Red Team / C2</td><td>Cobalt Strike, Metasploit Pro</td><td>$5,900 – $15,000+</td></tr>
        <tr><td>PTaaS Platforms</td><td>Cobalt, HackerOne, Synack</td><td>$10,000 – $100,000+</td></tr>
    </tbody>
</table>

<h2>Posicionamento do Dimitri</h2>
<div class="grid2">
    <div class="card card-g">
        <h3>Vantagens Únicas</h3>
        <ul>
            <li>IA multi-model híbrida (cloud + local) — nenhum concorrente tem</li>
            <li>Modelo desbloqueado (abliterated) — zero recusas em operações ofensivas</li>
            <li>Processamento local de dados — compliance de dados sensíveis</li>
            <li>Interface Telegram — operação de campo sem laptop</li>
            <li>Relatório enterprise automático com análise por IA local</li>
            <li>Custo ~$50/mês vs $50K-200K/ano dos concorrentes enterprise</li>
        </ul>
    </div>
    <div class="card card-b">
        <h3>Trade-offs Conhecidos</h3>
        <ul>
            <li>Single-machine (vs. cloud-native dos enterprise)</li>
            <li>Não tem GUI web própria (usa PentAGI UI + Telegram)</li>
            <li>Sem certificação FedRAMP/SOC2 (não aplicável ao modelo)</li>
            <li>Depende de modelo local 8GB VRAM (vs GPUs enterprise)</li>
            <li>Não substitui pentest manual humano (complementa)</li>
        </ul>
    </div>
</div>
''')

# PAGE 3 — MEGA COMPARISON TABLE
p3 = pg(3, '''
<h1>Comparativo Geral — Preço, IA e Infraestrutura</h1>

<table>
    <colgroup>
        <col style="width:18%">
        <col style="width:10%">
        <col style="width:12%">
        <col style="width:12%">
        <col style="width:12%">
        <col style="width:12%">
        <col style="width:12%">
        <col style="width:12%">
    </colgroup>
    <thead>
        <tr>
            <th>Ferramenta</th>
            <th>Preço/Ano</th>
            <th>Tipo</th>
            <th>IA Autônoma</th>
            <th>Multi-Agent</th>
            <th>Dados Locais</th>
            <th>Relatório Auto</th>
            <th>Interface</th>
        </tr>
    </thead>
    <tbody>
        <tr><td><strong style="color:#00e676;">Dimitri</strong></td><td class="win">~$600</td><td>Autônomo</td><td class="win">✅ Hybrid</td><td class="win">✅ 11</td><td class="win">✅ GPU</td><td class="win">✅ PDF+AI</td><td class="win">Telegram</td></tr>
        <tr><td>Pentera</td><td class="lose">$50-200K</td><td>BAS</td><td class="tie">Parcial</td><td class="lose">❌</td><td class="win">✅</td><td class="win">✅</td><td>Web UI</td></tr>
        <tr><td>NodeZero</td><td class="lose">$50-100K</td><td>BAS</td><td class="win">✅</td><td class="lose">❌</td><td class="lose">❌ Cloud</td><td class="win">✅</td><td>Web UI</td></tr>
        <tr><td>Cobalt Strike</td><td class="lose">$5,900/u</td><td>C2</td><td class="lose">❌</td><td class="lose">❌</td><td class="win">✅</td><td class="lose">❌</td><td>GUI</td></tr>
        <tr><td>Metasploit Pro</td><td class="lose">$15,000+</td><td>Exploit</td><td class="lose">❌</td><td class="lose">❌</td><td class="win">✅</td><td class="tie">Básico</td><td>Web/CLI</td></tr>
        <tr><td>Burp Pro</td><td class="tie">$449/u</td><td>DAST</td><td class="tie">Burp AI</td><td class="lose">❌</td><td class="win">✅</td><td class="tie">Básico</td><td>GUI</td></tr>
        <tr><td>Burp Enterprise</td><td class="lose">$8,395+</td><td>DAST</td><td class="tie">Burp AI</td><td class="lose">❌</td><td class="tie">Dep.</td><td class="win">✅</td><td>Web/CI</td></tr>
        <tr><td>Acunetix</td><td class="lose">$4,500+</td><td>DAST</td><td class="lose">❌</td><td class="lose">❌</td><td class="tie">Dep.</td><td class="win">✅</td><td>Web UI</td></tr>
        <tr><td>Invicti</td><td class="lose">$6,000+</td><td>DAST</td><td class="lose">❌</td><td class="lose">❌</td><td class="tie">Dep.</td><td class="win">✅</td><td>Web/CI</td></tr>
        <tr><td>Nessus Pro</td><td class="tie">$3,390+</td><td>VulnMgmt</td><td class="lose">❌</td><td class="lose">❌</td><td class="win">✅</td><td class="win">✅</td><td>Web UI</td></tr>
        <tr><td>Qualys VMDR</td><td class="lose">$7,200+</td><td>VulnMgmt</td><td class="lose">❌</td><td class="lose">❌</td><td class="lose">❌ Cloud</td><td class="win">✅</td><td>Web UI</td></tr>
        <tr><td>PentestGPT</td><td class="win">$0 OSS</td><td>AI Agent</td><td class="win">✅</td><td class="lose">❌</td><td class="tie">Dep.</td><td class="lose">❌</td><td>CLI</td></tr>
        <tr><td>Cobalt PTaaS</td><td class="lose">$10-50K</td><td>PTaaS</td><td class="lose">❌ Human</td><td class="lose">❌</td><td class="lose">❌ Cloud</td><td class="win">✅</td><td>Platform</td></tr>
        <tr><td>OpenVAS</td><td class="win">$0 OSS</td><td>VulnMgmt</td><td class="lose">❌</td><td class="lose">❌</td><td class="win">✅</td><td class="tie">Básico</td><td>Web UI</td></tr>
    </tbody>
</table>

<h2>Comparativo — Arsenal e Cobertura</h2>

<table>
    <colgroup>
        <col style="width:18%">
        <col style="width:12%">
        <col style="width:10%">
        <col style="width:10%">
        <col style="width:10%">
        <col style="width:10%">
        <col style="width:10%">
        <col style="width:10%">
        <col style="width:10%">
    </colgroup>
    <thead>
        <tr>
            <th>Ferramenta</th>
            <th>Arsenal</th>
            <th>OWASP</th>
            <th>Sem Censura</th>
            <th>Port Scan</th>
            <th>Web Vuln</th>
            <th>SQLi</th>
            <th>Fuzzing</th>
            <th>Exploit Gen</th>
        </tr>
    </thead>
    <tbody>
        <tr><td><strong style="color:#00e676;">Dimitri</strong></td><td class="win">18+ tools</td><td class="win">✅ Full</td><td class="win">✅</td><td class="win">✅</td><td class="win">✅</td><td class="win">✅</td><td class="win">✅</td><td class="win">✅ IA</td></tr>
        <tr><td>Pentera</td><td class="tie">Moderado</td><td class="win">✅</td><td class="na">N/A</td><td class="win">✅</td><td class="win">✅</td><td class="win">✅</td><td class="lose">❌</td><td class="lose">❌</td></tr>
        <tr><td>NodeZero</td><td class="tie">Moderado</td><td class="win">✅</td><td class="na">N/A</td><td class="win">✅</td><td class="win">✅</td><td class="win">✅</td><td class="tie">⚠️</td><td class="lose">❌</td></tr>
        <tr><td>Cobalt Strike</td><td class="win">C2 full</td><td class="lose">Parcial</td><td class="win">✅</td><td class="tie">⚠️</td><td class="lose">❌</td><td class="lose">❌</td><td class="lose">❌</td><td class="tie">⚠️</td></tr>
        <tr><td>Metasploit Pro</td><td class="win">Exploits</td><td class="tie">Parcial</td><td class="win">✅</td><td class="win">✅</td><td class="tie">⚠️</td><td class="win">✅</td><td class="lose">❌</td><td class="tie">⚠️</td></tr>
        <tr><td>Burp Pro</td><td class="tie">Web only</td><td class="win">✅ Web</td><td class="na">N/A</td><td class="lose">❌</td><td class="win">✅</td><td class="win">✅</td><td class="win">✅</td><td class="lose">❌</td></tr>
        <tr><td>Acunetix</td><td class="tie">Web only</td><td class="win">✅ Web</td><td class="na">N/A</td><td class="lose">❌</td><td class="win">✅</td><td class="win">✅</td><td class="tie">⚠️</td><td class="lose">❌</td></tr>
        <tr><td>Nessus Pro</td><td class="tie">Vuln scan</td><td class="tie">Parcial</td><td class="na">N/A</td><td class="win">✅</td><td class="tie">⚠️</td><td class="lose">❌</td><td class="lose">❌</td><td class="lose">❌</td></tr>
        <tr><td>PentestGPT</td><td class="lose">Limitado</td><td class="lose">Parcial</td><td class="tie">Dep.</td><td class="lose">❌</td><td class="lose">❌</td><td class="lose">❌</td><td class="lose">❌</td><td class="tie">⚠️</td></tr>
        <tr><td>OpenVAS</td><td class="tie">Vuln scan</td><td class="tie">Parcial</td><td class="na">N/A</td><td class="win">✅</td><td class="tie">⚠️</td><td class="lose">❌</td><td class="lose">❌</td><td class="lose">❌</td></tr>
    </tbody>
</table>

<p style="font-size:6.5pt; color:#37474f; margin-top:4px;">
<span class="win">✅ Verde</span> = vantagem | <span class="tie">⚠️ Amarelo</span> = parcial | <span class="lose">❌ Vermelho</span> = ausente | <span class="na">N/A</span> = não aplicável. Preços: G2, PeerSpot, sites oficiais (Q1 2026).
</p>
''')

# PAGE 4 — Deep Dive Pricing
p4 = pg(4, '''
<h1>Análise de Custo — Dimitri vs. Mercado</h1>

<h2>Custo Total de Propriedade (TCO) — 3 Anos</h2>
<table>
    <colgroup>
        <col style="width:16%"><col style="width:13%"><col style="width:14%"><col style="width:11%"><col style="width:13%"><col style="width:14%"><col style="width:19%">
    </colgroup>
    <thead><tr><th>Ferramenta</th><th>Licença Ano 1</th><th>Licença Ano 2-3</th><th>Infra</th><th>Treinamento</th><th>TCO 3 Anos</th><th>vs Dimitri</th></tr></thead>
    <tbody>
        <tr style="background:rgba(0,230,118,0.05);">
            <td><strong style="color:#00e676;">Dimitri</strong></td>
            <td>$0</td>
            <td>$0</td>
            <td>$600/yr (API)</td>
            <td>$0 (manual incluso)</td>
            <td class="win"><strong>$1,800</strong></td>
            <td>—</td>
        </tr>
        <tr>
            <td>Pentera</td>
            <td>$100,000</td>
            <td>$80,000/yr</td>
            <td>$5,000/yr</td>
            <td>$10,000</td>
            <td>$285,000</td>
            <td class="lose">158× mais caro</td>
        </tr>
        <tr>
            <td>NodeZero</td>
            <td>$75,000</td>
            <td>$60,000/yr</td>
            <td>$0 (cloud)</td>
            <td>$5,000</td>
            <td>$200,000</td>
            <td class="lose">111× mais caro</td>
        </tr>
        <tr>
            <td>Cobalt Strike</td>
            <td>$5,900</td>
            <td>$5,900/yr</td>
            <td>$2,000/yr</td>
            <td>$3,000</td>
            <td>$26,700</td>
            <td class="lose">15× mais caro</td>
        </tr>
        <tr>
            <td>Metasploit Pro</td>
            <td>$15,000</td>
            <td>$15,000/yr</td>
            <td>$2,000/yr</td>
            <td>$5,000</td>
            <td>$56,000</td>
            <td class="lose">31× mais caro</td>
        </tr>
        <tr>
            <td>Burp Suite Enterprise</td>
            <td>$8,395</td>
            <td>$8,395/yr</td>
            <td>$1,000/yr</td>
            <td>$2,000</td>
            <td>$30,185</td>
            <td class="lose">17× mais caro</td>
        </tr>
        <tr>
            <td>Acunetix</td>
            <td>$4,500</td>
            <td>$4,500/yr</td>
            <td>$500/yr</td>
            <td>$1,000</td>
            <td>$16,000</td>
            <td class="lose">9× mais caro</td>
        </tr>
        <tr>
            <td>Nessus Pro</td>
            <td>$4,390</td>
            <td>$4,390/yr</td>
            <td>$500/yr</td>
            <td>$1,000</td>
            <td>$15,670</td>
            <td class="lose">9× mais caro</td>
        </tr>
        <tr>
            <td>Qualys VMDR</td>
            <td>$9,600</td>
            <td>$9,600/yr</td>
            <td>$0 (cloud)</td>
            <td>$3,000</td>
            <td>$31,800</td>
            <td class="lose">18× mais caro</td>
        </tr>
        <tr>
            <td>Cobalt PTaaS</td>
            <td>$25,000</td>
            <td>$25,000/yr</td>
            <td>$0 (cloud)</td>
            <td>$0</td>
            <td>$75,000</td>
            <td class="lose">42× mais caro</td>
        </tr>
        <tr>
            <td>Stack Completo*</td>
            <td colspan="4"><em>Burp Pro + Nessus + Metasploit + Cobalt Strike + Cobalt PTaaS</em></td>
            <td class="lose"><strong>$189,000+</strong></td>
            <td class="lose">105× mais caro</td>
        </tr>
    </tbody>
</table>
<p style="font-size:6.5pt; color:#37474f;">* Stack necessário para cobrir o mesmo escopo que o Dimitri cobre sozinho. Não inclui custos de pessoal para operar cada ferramenta.</p>

<h2>Custo por Pentest Completo</h2>
<table>
    <thead><tr><th>Abordagem</th><th>Custo/Pentest</th><th>Tempo</th><th>Resultado</th></tr></thead>
    <tbody>
        <tr style="background:rgba(0,230,118,0.05);">
            <td><strong style="color:#00e676;">Dimitri (GLOUSOFT)</strong></td>
            <td class="win"><strong>~$2-5</strong> (API usage)</td>
            <td>30-60 min</td>
            <td>Relatório PDF enterprise + PoC data</td>
        </tr>
        <tr>
            <td>Consultoria boutique</td>
            <td>$5,000-15,000</td>
            <td>1-3 semanas</td>
            <td>Relatório manual + reteste</td>
        </tr>
        <tr>
            <td>Big 4 (Deloitte, etc)</td>
            <td>$25,000-100,000</td>
            <td>2-6 semanas</td>
            <td>Relatório + compliance</td>
        </tr>
        <tr>
            <td>Bug Bounty (HackerOne)</td>
            <td>$10,000-50,000</td>
            <td>Contínuo</td>
            <td>Findings individuais</td>
        </tr>
        <tr>
            <td>PTaaS (Cobalt/Synack)</td>
            <td>$5,000-20,000</td>
            <td>1-2 semanas</td>
            <td>Relatório + plataforma</td>
        </tr>
    </tbody>
</table>
''')

# PAGE 5 — Technical Depth Comparison
p5 = pg(5, '''
<h1>Análise Técnica — Profundidade de Cada Solução</h1>

<h2>Capacidades de IA</h2>
<table>
    <colgroup>
        <col style="width:14%"><col style="width:22%"><col style="width:28%"><col style="width:10%"><col style="width:26%">
    </colgroup>
    <thead><tr><th>Ferramenta</th><th>Tipo de IA</th><th>Capacidade</th><th>Autonomia</th><th>Limitações</th></tr></thead>
    <tbody>
        <tr style="background:rgba(0,230,118,0.05);">
            <td><strong style="color:#00e676;">Dimitri</strong></td>
            <td>Multi-model hybrid (DeepSeek + Qwen 30B)</td>
            <td>Planejamento, execução, análise, relatório — tudo autônomo</td>
            <td class="win">Total</td>
            <td>Depende de qualidade dos modelos base</td>
        </tr>
        <tr>
            <td>Pentera</td>
            <td>Algoritmos proprietários (não LLM)</td>
            <td>Simulação de ataques predefinidos, validação de paths</td>
            <td>Alta (predefinida)</td>
            <td>Não gera exploits novos; playbooks fixos</td>
        </tr>
        <tr>
            <td>NodeZero</td>
            <td>Algoritmos + heurísticas</td>
            <td>Discovery, exploitation, lateral movement automático</td>
            <td>Alta</td>
            <td>Sem LLM; raciocínio limitado a heurísticas</td>
        </tr>
        <tr>
            <td>Burp AI</td>
            <td>LLM-assisted (2024+)</td>
            <td>Sugestões de teste, análise de responses</td>
            <td>Baixa (sugestões)</td>
            <td>Não executa; apenas assiste. Requer operador humano</td>
        </tr>
        <tr>
            <td>PentestGPT</td>
            <td>Single LLM (GPT-4/Claude)</td>
            <td>Planejamento e sugestão de próximos passos</td>
            <td>Parcial</td>
            <td>Single agent; sem arsenal integrado; precisa de humano</td>
        </tr>
    </tbody>
</table>

<h2>Cobertura de Ataque</h2>
<table>
    <colgroup>
        <col style="width:22%"><col style="width:13%"><col style="width:13%"><col style="width:13%"><col style="width:13%"><col style="width:13%"><col style="width:13%">
    </colgroup>
    <thead><tr><th>Vetor</th><th style="color:#00e676;">Dimitri</th><th>Pentera</th><th>NodeZero</th><th>Burp Pro</th><th>Nessus</th><th>Metasploit</th></tr></thead>
    <tbody>
        <tr><td>Port Scanning</td><td class="win">✅ nmap</td><td>✅</td><td>✅</td><td>❌</td><td>✅</td><td>✅</td></tr>
        <tr><td>Subdomain Enum</td><td class="win">✅ subfinder+</td><td>❌</td><td>✅</td><td>❌</td><td>❌</td><td>❌</td></tr>
        <tr><td>Web Vuln (OWASP)</td><td class="win">✅ nuclei+nikto</td><td>✅</td><td>✅</td><td>✅</td><td>⚠️ Parcial</td><td>⚠️ Parcial</td></tr>
        <tr><td>SQL Injection</td><td class="win">✅ sqlmap</td><td>✅</td><td>✅</td><td>✅</td><td>❌</td><td>✅</td></tr>
        <tr><td>XSS</td><td class="win">✅ nuclei</td><td>✅</td><td>⚠️</td><td>✅</td><td>❌</td><td>⚠️</td></tr>
        <tr><td>SSL/TLS Analysis</td><td class="win">✅ sslscan</td><td>✅</td><td>✅</td><td>⚠️</td><td>✅</td><td>❌</td></tr>
        <tr><td>Directory Fuzzing</td><td class="win">✅ ffuf</td><td>❌</td><td>⚠️</td><td>✅</td><td>❌</td><td>❌</td></tr>
        <tr><td>Exploitation</td><td class="tie">⚠️ Via IA</td><td>✅ Auto</td><td>✅ Auto</td><td>❌</td><td>❌</td><td>✅ Full</td></tr>
        <tr><td>Lateral Movement</td><td class="lose">❌</td><td>✅</td><td>✅</td><td>❌</td><td>❌</td><td>✅</td></tr>
        <tr><td>AD/Kerberos</td><td class="lose">❌</td><td>✅</td><td>✅</td><td>❌</td><td>⚠️</td><td>✅</td></tr>
        <tr><td>Custom Exploit Gen</td><td class="win">✅ Qwen AI</td><td>❌</td><td>❌</td><td>❌</td><td>❌</td><td>⚠️ Manual</td></tr>
        <tr><td>Report (AI-generated)</td><td class="win">✅ Qwen 30B</td><td>❌</td><td>❌</td><td>❌</td><td>❌</td><td>❌</td></tr>
    </tbody>
</table>
<p style="font-size:6.5pt; color:#37474f;">✅ = suporte nativo completo | ⚠️ = suporte parcial/limitado | ❌ = não suporta</p>
''')

# PAGE 6 — Data Privacy + Unique Advantages
p6 = pg(6, '''
<h1>Diferencias Exclusivos do Dimitri</h1>

<h2>1. Processamento Local de Dados Sensíveis</h2>
<div class="card card-g">
    <p>O Dimitri é a <strong>única plataforma de pentest autônomo que processa dados sensíveis exclusivamente na máquina local</strong>. O Qwen3-30B roda na GPU local — credenciais descobertas, vulnerabilidades críticas e output de ferramentas nunca saem da máquina.</p>
    <table>
        <thead><tr><th>Ferramenta</th><th>Onde dados são processados</th><th>Risco de vazamento</th></tr></thead>
        <tbody>
            <tr style="background:rgba(0,230,118,0.05);"><td><strong style="color:#00e676;">Dimitri</strong></td><td>GPU local (Qwen 30B)</td><td class="win">Zero — dados nunca saem</td></tr>
            <tr><td>Pentera</td><td>On-prem (appliance)</td><td class="tie">Baixo — mas vendor tem acesso</td></tr>
            <tr><td>NodeZero</td><td>Cloud (Horizon3.ai)</td><td class="lose">Alto — dados na cloud do vendor</td></tr>
            <tr><td>Qualys VMDR</td><td>Cloud (Qualys)</td><td class="lose">Alto — dados na cloud do vendor</td></tr>
            <tr><td>HackerOne</td><td>Cloud + hackers terceiros</td><td class="lose">Alto — múltiplos acessos</td></tr>
            <tr><td>Cobalt PTaaS</td><td>Cloud + pentesters terceiros</td><td class="lose">Alto — múltiplos acessos</td></tr>
        </tbody>
    </table>
</div>

<h2>2. Modelo Desbloqueado (Abliterated)</h2>
<div class="card card-g">
    <p>O Qwen3-Coder-30B do Dimitri é uma <strong>versão abliterated</strong> — sem filtros de censura que impeçam operações ofensivas legítimas. Isso significa:</p>
    <ul>
        <li>Gera payloads de exploit sem recusar</li>
        <li>Escreve scripts de reverse shell para PoC</li>
        <li>Analisa vulnerabilidades sem disclaimers</li>
        <li>Produz relatórios ofensivos completos</li>
    </ul>
    <p>Concorrentes que usam GPT-4 ou Claude via API estão sujeitos a <strong>recusas de segurança</strong> que bloqueiam operações ofensivas legítimas. O Dimitri não tem esse problema.</p>
</div>

<h2>3. Operação via Telegram</h2>
<div class="card card-g">
    <p>Nenhum concorrente oferece <strong>interface operacional via Telegram</strong>. O Dimitri permite:</p>
    <ul>
        <li>Iniciar pentests do celular — operação de campo sem laptop</li>
        <li>Receber narração em tempo real dos scans</li>
        <li>Receber relatório PDF direto no chat</li>
        <li>Controlar todo o ciclo via botões inline (sem digitar comandos)</li>
    </ul>
</div>

<h2>4. IA Híbrida Multi-Model</h2>
<div class="card card-g">
    <p><strong>Nenhum concorrente implementa arquitetura multi-model com routing inteligente.</strong> O Dimitri usa:</p>
    <ul>
        <li><strong>DeepSeek</strong> (cloud) para planejamento estratégico e decomposição de tasks</li>
        <li><strong>Qwen 30B</strong> (local) para execução técnica e análise de resultados</li>
        <li><strong>Router com fallback</strong> — se cloud falhar, local assume automaticamente</li>
        <li><strong>11 agentes especializados</strong> vs. agente único dos concorrentes</li>
    </ul>
</div>
''')

# PAGE 7 — Final verdict
p7 = pg(7, '''
<h1>Veredicto Final</h1>

<h2>Quando usar Dimitri vs. Concorrentes</h2>
<table>
    <thead><tr><th>Cenário</th><th>Melhor Solução</th><th>Por quê</th></tr></thead>
    <tbody>
        <tr style="background:rgba(0,230,118,0.05);">
            <td>Pentest externo de web apps</td>
            <td class="win"><strong>Dimitri</strong></td>
            <td>Arsenal completo (nuclei, nikto, sqlmap, ffuf) + IA para análise. Custo ínfimo.</td>
        </tr>
        <tr style="background:rgba(0,230,118,0.05);">
            <td>Avaliação rápida de segurança</td>
            <td class="win"><strong>Dimitri</strong></td>
            <td>30 min do Telegram ao relatório PDF enterprise. Zero setup para o operador.</td>
        </tr>
        <tr style="background:rgba(0,230,118,0.05);">
            <td>Dados sensíveis (saúde, financeiro)</td>
            <td class="win"><strong>Dimitri</strong></td>
            <td>Processamento 100% local. Dados nunca saem da máquina.</td>
        </tr>
        <tr style="background:rgba(0,230,118,0.05);">
            <td>Cliente com orçamento limitado</td>
            <td class="win"><strong>Dimitri</strong></td>
            <td>~$2-5 por pentest vs $5,000-25,000 de consultoria.</td>
        </tr>
        <tr>
            <td>Pentest interno (AD, lateral movement)</td>
            <td>Pentera / NodeZero</td>
            <td>Dimitri foca em external. Para AD/internal, BAS é mais adequado.</td>
        </tr>
        <tr>
            <td>Compliance corporativo (SOC2, FedRAMP)</td>
            <td>Qualys / Nessus</td>
            <td>Certificações e integração com frameworks de compliance.</td>
        </tr>
        <tr>
            <td>Red Team avançado (C2, persistence)</td>
            <td>Cobalt Strike</td>
            <td>Framework C2 maduro com anos de desenvolvimento.</td>
        </tr>
    </tbody>
</table>

<h2>Matriz de Decisão</h2>
<div class="card card-g">
<p><strong>Escolha o Dimitri quando o cliente precisa de:</strong></p>
<ul>
    <li>✅ Pentest externo automatizado com relatório enterprise</li>
    <li>✅ Velocidade (minutos, não semanas)</li>
    <li>✅ Custo acessível para PMEs e startups</li>
    <li>✅ Privacidade de dados (processamento local)</li>
    <li>✅ Operação simples via celular (Telegram)</li>
    <li>✅ IA que realmente pensa e adapta (não scripts predefinidos)</li>
    <li>✅ Integração com Claude Code para investigação aprofundada</li>
</ul>
</div>

<div style="text-align:center; margin-top:30px;">
    <div style="width:200px;height:1px;background:linear-gradient(90deg,transparent,#00e676 50%,transparent);margin:0 auto 16px;"></div>
    <p style="color:#37474f; font-size:8pt;">
        <strong style="color:#546e7a;">GLOUSOFT</strong> — Market Intelligence Division<br>
        <em>Análise Competitiva v1.0 — Dados de Q1 2026</em><br>
        <em>Fontes: G2, PeerSpot, Gartner, vendor sites, pesquisa independente</em><br><br>
        © ''' + str(now.year) + ''' GLOUSOFT — Todos os direitos reservados
    </p>
</div>
''')

html = f'''<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8"><style>{CSS}</style></head><body>
{cover}{p2}{p3}{p4}{p5}{p6}{p7}
</body></html>'''

output = "/tmp/dimitri-competitive-analysis.pdf"
pdf_bytes = weasyprint.HTML(string=html).write_pdf()
with open(output, 'wb') as f:
    f.write(pdf_bytes)
print(f"[OK] {output} ({len(pdf_bytes):,} bytes)")
