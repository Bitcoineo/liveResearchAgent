"""Bitcoineo DeFi Research Agent — Web UI.

Single-file stdlib HTTP server on port 8000.
All HTML/CSS/JS inline. No external Python dependencies beyond the project.
"""

import json
import sys
from datetime import date
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

from defillama import DefiLlamaClient, DefiLlamaAPIError, ProtocolNotFoundError
from markdown_report import render_markdown
from report import build_report
from web_research import (
    search_analyst_coverage,
    search_audit_reports,
    search_community_sentiment,
    search_red_flags,
)

PORT = 8000

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Bitcoineo — DeFi Due Diligence</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Playfair+Display:wght@700&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}

:root{
  --bg-gradient:linear-gradient(160deg,#fafafa 0%,#f5f3f0 30%,#f7f8fc 60%,#fafafa 100%);
  --glass:rgba(255,255,255,0.55);
  --glass-border:rgba(255,255,255,0.5);
  --accent:#6366f1;
  --accent-light:#818cf8;
  --accent-bg:rgba(99,102,241,0.08);
  --text:#1e293b;
  --text-secondary:#64748b;
  --text-dim:#94a3b8;
  --red:#ef4444;
  --radius-lg:16px;
  --radius:12px;
  --shadow:0 8px 32px rgba(0,0,0,0.06);
  --cta-dark:#1e293b;
}

body{
  background:var(--bg-gradient);
  background-size:200% 200%;
  background-attachment:fixed;
  animation:bgShift 20s ease infinite;
  color:var(--text);
  font-family:'Inter',system-ui,-apple-system,sans-serif;
  font-size:14px;
  line-height:1.6;
  min-height:100vh;
  -webkit-font-smoothing:antialiased;
  overflow-x:hidden;
}

a{color:var(--accent);text-decoration:none}
a:hover{color:var(--accent-light)}

/* ─── Animations ─── */
@keyframes fadeUp{
  from{opacity:0;transform:translateY(24px)}
  to{opacity:1;transform:translateY(0)}
}
@keyframes pulse{
  0%,100%{box-shadow:0 0 0 0 rgba(99,102,241,0.3)}
  50%{box-shadow:0 0 0 8px rgba(99,102,241,0)}
}
@keyframes bgShift{
  0%{background-position:0% 50%}
  50%{background-position:100% 50%}
  100%{background-position:0% 50%}
}
@keyframes spin{to{transform:rotate(360deg)}}

/* ─── Hero Section ─── */
#hero-section{
  position:relative;
  min-height:100vh;
  display:flex;
  align-items:center;justify-content:center;
  overflow:hidden;
}
.hero-content{
  display:flex;flex-direction:column;
  align-items:center;text-align:center;
  padding:0 24px;
  width:100%;
}

/* Hero Title */
.hero-title{
  font-family:'Playfair Display',Georgia,serif;
  font-size:64px;font-weight:700;
  color:var(--text);line-height:1.1;
  letter-spacing:-1px;
  margin-bottom:40px;
  max-width:700px;
  opacity:0;animation:fadeUp 0.8s ease forwards;
  animation-delay:0.1s;
}

/* ─── Search Bar ─── */
.search-bar-wrap{
  position:relative;display:flex;align-items:center;
  width:100%;max-width:560px;
  margin-bottom:48px;
  opacity:0;animation:fadeUp 0.8s ease forwards;
  animation-delay:0.3s;
}
.search-bar-wrap .search-icon{
  position:absolute;left:20px;
  width:20px;height:20px;color:var(--text-dim);pointer-events:none;
}
.search-bar{
  width:100%;height:56px;
  padding:16px 140px 16px 52px;
  background:rgba(255,255,255,0.85);
  border:1.5px solid rgba(0,0,0,0.08);
  border-radius:16px;
  color:var(--text);font-family:inherit;font-size:16px;
  transition:all 0.3s ease;
  box-shadow:0 4px 20px rgba(0,0,0,0.04);
}
.search-bar:focus{
  outline:none;border-color:var(--accent);
  box-shadow:0 0 0 4px rgba(99,102,241,0.12),0 8px 32px rgba(0,0,0,0.06);
  background:rgba(255,255,255,0.95);
}
.search-bar::placeholder{color:var(--text-dim)}
.generate-btn{
  position:absolute;right:6px;
  padding:10px 24px;height:44px;
  border:none;border-radius:12px;
  background:var(--cta-dark);color:white;
  font-family:inherit;font-size:14px;font-weight:600;
  cursor:pointer;transition:all 0.2s;
  animation:pulse 3s ease-in-out infinite;
  animation-delay:2s;
}
.generate-btn:hover{
  background:#334155;
  box-shadow:0 4px 16px rgba(30,41,59,0.25);
}
.generate-btn:active{transform:scale(0.97)}

/* ─── Toggle Row ─── */
.toggle-row{
  display:flex;align-items:center;gap:10px;
  margin-bottom:24px;
  opacity:0;animation:fadeUp 0.8s ease forwards;
  animation-delay:0.4s;
}
.toggle-label{
  display:flex;align-items:center;gap:8px;
  cursor:pointer;font-size:13px;font-weight:500;color:var(--text-secondary);
}
.toggle-label input[type="checkbox"]{
  width:18px;height:18px;accent-color:var(--accent);cursor:pointer;
}
.toggle-hint{font-size:12px;color:var(--text-dim)}

/* ─── Protocol Grid ─── */
.protocol-grid{
  display:flex;flex-wrap:wrap;gap:12px;
  justify-content:center;max-width:600px;
  opacity:0;animation:fadeUp 0.8s ease forwards;
  animation-delay:0.6s;
}
.protocol-card{
  display:flex;align-items:center;gap:10px;
  padding:10px 20px;border-radius:14px;
  background:rgba(255,255,255,0.6);
  border:1px solid rgba(0,0,0,0.06);
  cursor:pointer;transition:all 0.25s ease;
  backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);
}
.protocol-card:hover{
  background:rgba(255,255,255,0.85);
  transform:translateY(-2px);
  box-shadow:0 8px 24px rgba(0,0,0,0.08);
  border-color:rgba(99,102,241,0.2);
}
.protocol-card img{width:28px;height:28px;border-radius:50%;flex-shrink:0;object-fit:cover}
.protocol-card span{font-size:14px;font-weight:500;color:var(--text)}

/* ─── Social Buttons ─── */
.social-bar{
  display:flex;flex-direction:column;align-items:center;gap:10px;
  margin-top:48px;
  opacity:0;animation:fadeUp 0.8s ease forwards;
  animation-delay:0.8s;
}
.social-cta{font-size:13px;color:var(--text-dim);font-weight:500;letter-spacing:0.2px}
.social-buttons{
  display:flex;gap:10px;
}
.social-btn{
  display:flex;align-items:center;justify-content:center;
  width:44px;height:44px;border-radius:50%;
  background:rgba(255,255,255,0.8);
  border:1px solid rgba(0,0,0,0.08);
  color:var(--text-secondary);
  transition:all 0.25s ease;
  backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);
  text-decoration:none;
}
.social-btn:hover{
  background:var(--cta-dark);color:white;
  transform:translateY(-2px);
  box-shadow:0 4px 16px rgba(0,0,0,0.12);
}
.social-btn svg{width:18px;height:18px}

/* ─── Home Button ─── */
.home-btn{
  display:inline-flex;align-items:center;gap:8px;
  padding:10px 20px;border:none;border-radius:12px;
  background:rgba(255,255,255,0.7);
  border:1px solid rgba(0,0,0,0.08);
  color:var(--text-secondary);
  font-family:inherit;font-size:14px;font-weight:500;
  cursor:pointer;transition:all 0.2s;
  margin-bottom:24px;
  backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);
}
.home-btn:hover{
  background:rgba(255,255,255,0.9);color:var(--text);
  box-shadow:0 4px 12px rgba(0,0,0,0.06);
}
.home-btn svg{width:16px;height:16px}

/* ─── State Container ─── */
#state-container{
  display:none;
  max-width:760px;margin:0 auto;
  padding:80px 24px 60px;
  min-height:100vh;
}

/* Glass card */
.glass-card{
  background:var(--glass);
  backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);
  border:1px solid var(--glass-border);
  border-radius:var(--radius-lg);
  padding:32px;
  box-shadow:var(--shadow);
  transition:all 0.3s;
}

/* Buttons (report actions) */
.btn{
  padding:14px 28px;border:none;border-radius:var(--radius);
  font-family:inherit;font-size:14px;font-weight:600;
  cursor:pointer;transition:all 0.2s;white-space:nowrap;
}
.btn:active{transform:scale(0.97)}
.btn:disabled{opacity:0.5;cursor:not-allowed}
.btn-primary{background:var(--cta-dark);color:white}
.btn-primary:hover{background:#334155;box-shadow:0 4px 16px rgba(30,41,59,0.25)}
.btn-outline{background:transparent;border:1.5px solid rgba(0,0,0,0.12);color:var(--text)}
.btn-outline:hover{background:rgba(0,0,0,0.03)}

/* Loading state */
.loading-state{text-align:center;padding:48px 0}
.spinner{
  width:40px;height:40px;margin:0 auto 16px;
  border:3px solid rgba(99,102,241,0.15);
  border-top-color:var(--accent);border-radius:50%;
  animation:spin 0.8s linear infinite;
}
.loading-state p{color:var(--text-secondary);font-size:14px}

/* Error state */
.error-msg{
  padding:16px;border-radius:var(--radius);
  background:rgba(239,68,68,0.08);border:1px solid rgba(239,68,68,0.2);
  color:var(--red);font-size:14px;text-align:center;
  margin-bottom:16px;
}

/* Report card */
.report-card .report-header{
  display:flex;justify-content:space-between;align-items:center;
  margin-bottom:24px;padding-bottom:16px;
  border-bottom:1px solid rgba(0,0,0,0.06);
}
.report-card .report-header h2{font-size:16px;font-weight:600;color:var(--text)}
.report-actions{display:flex;gap:8px}

/* Markdown rendered content */
.report-content h1{font-size:22px;font-weight:700;margin:0 0 12px;color:var(--text)}
.report-content h2{font-size:18px;font-weight:600;margin:28px 0 12px;color:var(--text)}
.report-content h3{font-size:15px;font-weight:600;margin:20px 0 8px;color:var(--text)}
.report-content p{margin:0 0 12px;color:var(--text);line-height:1.7}
.report-content strong{font-weight:600}
.report-content em{color:var(--text-secondary)}
.report-content hr{border:none;border-top:1px solid rgba(0,0,0,0.08);margin:24px 0}
.report-content blockquote{
  border-left:3px solid var(--accent);padding:8px 16px;
  margin:12px 0;background:rgba(99,102,241,0.04);border-radius:0 8px 8px 0;
  color:var(--text-secondary);
}
.report-content ul,.report-content ol{margin:0 0 12px;padding-left:24px}
.report-content li{margin:4px 0}
.report-content table{width:100%;border-collapse:collapse;margin:12px 0 20px;font-size:13px}
.report-content th{
  text-align:left;padding:10px 12px;font-weight:600;font-size:12px;
  text-transform:uppercase;letter-spacing:0.3px;
  color:var(--text-secondary);background:rgba(255,255,255,0.5);
  border-bottom:1px solid rgba(0,0,0,0.08);
}
.report-content td{padding:10px 12px;border-bottom:1px solid rgba(0,0,0,0.04)}
.report-content a{color:var(--accent);font-weight:500}

/* ─── Report Badges & Indicators ─── */
.badge{
  display:inline-block;padding:2px 10px;border-radius:10px;
  font-size:11px;font-weight:700;letter-spacing:0.4px;
  vertical-align:middle;line-height:1.6;
}
.badge-green{background:rgba(16,185,129,0.12);color:#059669}
.badge-amber{background:rgba(245,158,11,0.12);color:#d97706}
.badge-red{background:rgba(239,68,68,0.12);color:#dc2626}
.badge-critical{background:rgba(127,29,29,0.15);color:#991b1b}
.badge-blue{background:rgba(59,130,246,0.12);color:#2563eb}
.badge-gray{background:rgba(100,116,139,0.1);color:#475569}

.report-content .grade-bar{
  display:flex;align-items:center;gap:12px;flex-wrap:wrap;
  padding:14px 18px;margin:12px 0 16px;
  border-radius:12px;border:1px solid rgba(0,0,0,0.06);
  background:rgba(255,255,255,0.5);
}
.grade-bar .grade-label{font-size:12px;font-weight:600;color:var(--text-secondary);text-transform:uppercase;letter-spacing:0.3px}
.grade-bar .grade-value{font-size:15px;font-weight:700}

.grade-bar.grade-low .grade-value{color:#059669}
.grade-bar.grade-medium .grade-value{color:#d97706}
.grade-bar.grade-high .grade-value{color:#dc2626}
.grade-bar.grade-critical .grade-value{color:#991b1b}
.grade-bar.grade-unknown .grade-value{color:#475569}

.grade-bar .grade-dots{display:flex;gap:4px;margin-left:auto}
.grade-bar .grade-dot{width:8px;height:8px;border-radius:50%;background:rgba(0,0,0,0.08)}
.grade-bar .grade-dot.active{background:currentColor}
.grade-bar .grade-reason{
  width:100%;font-size:12px;color:var(--text-secondary);
  margin-top:2px;line-height:1.4;
}
.grade-bar.grade-score .grade-dots{gap:3px}
.grade-bar.grade-score .grade-dot{width:7px;height:7px}
.grade-bar.grade-score .grade-max{font-size:12px;font-weight:500;color:var(--text-dim)}

/* ─── Footer ─── */
.footer{
  text-align:center;padding:40px 0 32px;
  color:var(--text-dim);font-size:13px;
}
.footer a{color:var(--text-secondary);font-weight:500}
.footer a:hover{color:var(--accent)}

/* ─── Responsive ─── */
@media(max-width:960px){
  .hero-title{font-size:52px}
}
@media(max-width:640px){
  .hero-title{font-size:38px;margin-bottom:28px}
  .search-bar-wrap{max-width:100%}
  .search-bar{font-size:14px;padding-right:110px;height:50px}
  .generate-btn{padding:8px 16px;font-size:13px;height:38px}
  .protocol-grid{gap:8px}
  .protocol-card{padding:8px 14px}
  .social-bar{margin-top:32px}
  .social-btn{width:38px;height:38px}
  .social-btn svg{width:16px;height:16px}
  #state-container{padding:40px 16px 40px}
  .glass-card{padding:20px}
}
</style>
</head>
<body>

<!-- ════════ Hero Section ════════ -->
<div id="hero-section">
  <div class="hero-content">
    <h1 class="hero-title">DeFi Due Diligence</h1>

    <div class="search-bar-wrap">
      <svg class="search-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor"><circle cx="11" cy="11" r="8"/><path stroke-linecap="round" d="M21 21l-4.35-4.35"/></svg>
      <input type="text" id="protocol-input" class="search-bar"
             placeholder="Search protocol (e.g. aave, lido, uniswap)..." autocomplete="off">
      <button class="generate-btn" onclick="generateReport()">Generate</button>
    </div>

    <div class="toggle-row">
      <label class="toggle-label">
        <input type="checkbox" id="verified-toggle" checked>
        <span>Verified data only</span>
      </label>
      <span class="toggle-hint">(uncheck to include research templates)</span>
    </div>

    <div class="protocol-grid">
      <div class="protocol-card" onclick="selectChip(this)" data-protocol="Aave">
        <img src="https://unavatar.io/x/AaveAave" alt="Aave" loading="lazy">
        <span>Aave</span>
      </div>
      <div class="protocol-card" onclick="selectChip(this)" data-protocol="Lido">
        <img src="https://unavatar.io/x/LidoFinance" alt="Lido" loading="lazy">
        <span>Lido</span>
      </div>
      <div class="protocol-card" onclick="selectChip(this)" data-protocol="Ethena">
        <img src="https://unavatar.io/x/ethena_labs" alt="Ethena" loading="lazy">
        <span>Ethena</span>
      </div>
      <div class="protocol-card" onclick="selectChip(this)" data-protocol="Uniswap">
        <img src="https://unavatar.io/x/Uniswap" alt="Uniswap" loading="lazy">
        <span>Uniswap</span>
      </div>
      <div class="protocol-card" onclick="selectChip(this)" data-protocol="Maker">
        <img src="https://unavatar.io/x/MakerDAO" alt="Maker" loading="lazy">
        <span>Maker</span>
      </div>
    </div>

    <div class="social-bar">
      <span class="social-cta">Follow me</span>
      <div class="social-buttons">
        <a href="https://x.com/Bitcoineo" target="_blank" rel="noopener" class="social-btn" title="Twitter / X">
          <svg viewBox="0 0 24 24" fill="currentColor"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
        </a>
        <a href="https://github.com/Bitcoineo" target="_blank" rel="noopener" class="social-btn" title="GitHub">
          <svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0 1 12 6.844a9.59 9.59 0 0 1 2.504.337c1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.02 10.02 0 0 0 22 12.017C22 6.484 17.522 2 12 2z"/></svg>
        </a>
        <a href="https://bitcoineo.vercel.app/" target="_blank" rel="noopener" class="social-btn" title="Website">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M2 12h20"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
        </a>
      </div>
    </div>
  </div>  <!-- .hero-content -->
</div>

<!-- ════════ State Container (loading / error / report) ════════ -->
<div id="state-container">
  <button class="home-btn" onclick="newReport()">
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5"/></svg>
    Home
  </button>
  <div id="loading-card" class="glass-card" style="display:none">
    <div class="loading-state">
      <div class="spinner"></div>
      <p>Generating report&hellip;</p>
    </div>
  </div>

  <div id="error-card" style="display:none">
    <div class="error-msg" id="error-msg"></div>
  </div>

  <div id="report-card" class="glass-card report-card" style="display:none">
    <div class="report-header">
      <h2 id="report-title">Report</h2>
      <div class="report-actions">
        <button class="btn btn-outline" onclick="newReport()">New Report</button>
        <button class="btn btn-primary" id="download-btn" onclick="downloadReport()">Download .md</button>
      </div>
    </div>
    <div class="report-content" id="report-content"></div>
  </div>
</div>

<div class="footer">
  Powered by <a href="https://defillama.com" target="_blank" rel="noopener">DeFiLlama</a> &middot; Bitcoineo Research
</div>

<script>
let _markdown = "";
let _filename = "";

const input = document.getElementById("protocol-input");
const heroSection = document.getElementById("hero-section");
const stateContainer = document.getElementById("state-container");
const loadingCard = document.getElementById("loading-card");
const errorCard = document.getElementById("error-card");
const errorMsg = document.getElementById("error-msg");
const reportCard = document.getElementById("report-card");
const reportTitle = document.getElementById("report-title");
const reportContent = document.getElementById("report-content");

function selectChip(el) {
  const protocol = el.dataset.protocol || el.textContent.trim();
  input.value = protocol;
  generateReport();
}

input.addEventListener("keydown", function(e) {
  if (e.key === "Enter") generateReport();
});

function showView(view) {
  if (view === "search") {
    heroSection.style.display = "";
    stateContainer.style.display = "none";
  } else {
    heroSection.style.display = "none";
    stateContainer.style.display = "block";
  }
  loadingCard.style.display = view === "loading" ? "" : "none";
  errorCard.style.display = view === "error" ? "" : "none";
  reportCard.style.display = view === "report" ? "" : "none";
  window.scrollTo(0, 0);
}

async function generateReport() {
  const protocol = input.value.trim();
  if (!protocol) { input.focus(); return; }

  const verifiedOnly = document.getElementById("verified-toggle").checked;
  showView("loading");

  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 120000);
    const resp = await fetch("/api/report", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({protocol: protocol, verified_only: verifiedOnly}),
      signal: controller.signal
    });
    clearTimeout(timeout);
    const data = await resp.json();

    if (!resp.ok || !data.success) {
      errorMsg.textContent = data.error || "Unknown error occurred";
      showView("error");
      setTimeout(() => showView("search"), 4000);
      return;
    }

    _markdown = data.markdown;
    _filename = data.filename;
    reportTitle.textContent = _filename;
    reportContent.innerHTML = enhanceReport(marked.parse(_markdown));
    showView("report");
  } catch (err) {
    if (err.name === "AbortError") {
      errorMsg.textContent = "Request timed out — the report took too long. Try again.";
    } else {
      errorMsg.textContent = "Network error: " + err.message;
    }
    showView("error");
    setTimeout(() => showView("search"), 4000);
  }
}

function enhanceReport(html) {
  // Severity badges: [CRITICAL], [HIGH], [MEDIUM], [LOW]
  html = html.replace(/\[CRITICAL\]/g, '<span class="badge badge-critical">CRITICAL</span>');
  html = html.replace(/\[HIGH\]/g, '<span class="badge badge-red">HIGH</span>');
  html = html.replace(/\[MEDIUM\]/g, '<span class="badge badge-amber">MEDIUM</span>');
  html = html.replace(/\[LOW\]/g, '<span class="badge badge-green">LOW</span>');

  // Risk level grade bar
  html = html.replace(
    /<strong>Overall Risk Level<\/strong>:\s*(LOW|MEDIUM|HIGH|CRITICAL|UNKNOWN)/i,
    function(_, level) {
      const lc = level.toLowerCase();
      const colors = {low:"badge-green",medium:"badge-amber",high:"badge-red",critical:"badge-critical",unknown:"badge-gray"};
      const fills = {low:1,medium:2,high:3,critical:4,unknown:0};
      const n = fills[lc] || 0;
      let dots = "";
      for (let i = 1; i <= 4; i++) dots += '<span class="grade-dot' + (i <= n ? " active" : "") + '"></span>';
      return '<div class="grade-bar grade-' + lc + '"><span class="grade-label">Risk Level</span><span class="grade-value">' + level + '</span><span class="grade-dots">' + dots + '</span></div>';
    }
  );

  // Global Score grade bar
  html = html.replace(
    /<strong>Global Score<\/strong>:\s*(\d+(?:\.\d+)?)\/10\s*\((\w+)\)/i,
    function(_, score, label) {
      var lc = label.toLowerCase();
      var gradeClass = {excellent:"grade-low",good:"grade-low",fair:"grade-medium",weak:"grade-high"};
      var cls = gradeClass[lc] || "grade-unknown";
      return '<div class="grade-bar grade-score ' + cls + '"><span class="grade-label">Global Score</span><span class="grade-value">' + score + '<span class="grade-max">/10</span></span><span class="grade-reason">' + label + '</span></div>';
    }
  );

  // Template data warning banners — amber styling
  html = html.replace(
    /<blockquote>\s*<p>\s*⚠️\s*<strong>Template Data<\/strong>/g,
    '<blockquote style="border-left-color:#d97706;background:rgba(245,158,11,0.08);"><p>⚠️ <strong>Template Data</strong>'
  );

  // Sentiment badges in tables and inline
  html = html.replace(/>\s*Positive\s*</g, '><span class="badge badge-green">Positive</span><');
  html = html.replace(/>\s*Negative\s*</g, '><span class="badge badge-red">Negative</span><');
  html = html.replace(/>\s*Neutral\s*</g, '><span class="badge badge-gray">Neutral</span><');
  html = html.replace(/>\s*Mixed\s*</g, '><span class="badge badge-amber">Mixed</span><');

  // Overall sentiment inline
  html = html.replace(
    /<strong>Overall Sentiment<\/strong>:\s*(Positive|Negative|Neutral|Mixed|Unknown)/i,
    function(_, s) {
      const map = {positive:"badge-green",negative:"badge-red",neutral:"badge-gray",mixed:"badge-amber",unknown:"badge-gray"};
      return '<strong>Overall Sentiment</strong>: <span class="badge ' + (map[s.toLowerCase()] || "badge-gray") + '">' + s + '</span>';
    }
  );

  // Bug bounty status
  html = html.replace(
    /<strong>Bug Bounty Program<\/strong>:\s*(Active|Inactive)/i,
    function(_, s) {
      const cls = s.toLowerCase() === "active" ? "badge-green" : "badge-red";
      return '<strong>Bug Bounty Program</strong>: <span class="badge ' + cls + '">' + s + '</span>';
    }
  );

  return html;
}

function downloadReport() {
  const blob = new Blob([_markdown], {type: "text/markdown"});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = _filename;
  a.click();
  URL.revokeObjectURL(url);
}

function newReport() {
  input.value = "";
  showView("search");
  input.focus();
}
</script>
</body>
</html>"""


def _run_report(protocol_name: str, verified_only: bool = True) -> tuple:
    """Run the full report pipeline. Returns (markdown, filename)."""
    client = DefiLlamaClient()
    meta = client.resolve_protocol(protocol_name)
    detail = client.get_protocol_detail(meta["slug"])

    child_names = [c["name"] for c in meta["children"]]
    hacks = client.find_hacks_for_protocol(meta["name"], child_names)

    web_research = None
    if not verified_only:
        web_research = {
            "analyst_coverage": search_analyst_coverage(meta["name"]),
            "audit_reports": search_audit_reports(meta["name"]),
            "community_sentiment": search_community_sentiment(meta["name"]),
            "red_flags": search_red_flags(meta["name"]),
        }

    report = build_report(detail, meta, hacks, tvl_history_days=180, web_research=web_research, verified_only=verified_only)
    md = render_markdown(report)

    slug = report["metadata"]["slug"]
    filename = f"{slug}-{date.today().isoformat()}.md"

    # Save to reports/ (same as CLI)
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    (reports_dir / filename).write_text(md)

    return md, filename


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode())
        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Not found"}).encode())

    def do_POST(self):
        if self.path == "/api/report":
            self._handle_report()
        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Not found"}).encode())

    def _handle_report(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length)) if length else {}
        except (json.JSONDecodeError, ValueError):
            self._json_error(400, "Invalid JSON body")
            return

        protocol = body.get("protocol", "").strip()
        verified_only = body.get("verified_only", True)
        if not protocol:
            self._json_error(400, "Missing 'protocol' field")
            return

        try:
            md, filename = _run_report(protocol, verified_only=verified_only)
            self._json_response(200, {"success": True, "markdown": md, "filename": filename})
        except ProtocolNotFoundError as e:
            self._json_error(404, str(e))
        except DefiLlamaAPIError as e:
            self._json_error(503, f"DeFiLlama API error: {e}")
        except Exception as e:
            self._json_error(500, f"Internal error: {e}")

    def _json_response(self, status, data):
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())
        except BrokenPipeError:
            pass  # Client disconnected — nothing to do

    def _json_error(self, status, message):
        self._json_response(status, {"success": False, "error": message})

    def log_message(self, format, *args):
        print(f"[web] {args[0]}", file=sys.stderr)


def main():
    server = HTTPServer(("", PORT), Handler)
    print(f"Bitcoineo DeFi Research Agent — http://localhost:{PORT}", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.", file=sys.stderr)
        server.server_close()


if __name__ == "__main__":
    main()
