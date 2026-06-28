#!/usr/bin/env python3
"""Unified local workbench for the stock-analysis repository."""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from dataclasses import dataclass, field
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TMP = ROOT / "tmp" / "workbench"
REPORT_APP = ROOT / "web-apps" / "report"
INVESTMENT_NEWS = ROOT / ".agents" / "skills" / "investment-news"
VIBE_TRADING = ROOT / "web-apps" / "vibe-trading"
VIBE_FRONTEND = VIBE_TRADING / "frontend"
VIBE_WIKI = VIBE_TRADING / "wiki"
PORTAL_PID = TMP / "portal.pid"
PORTAL_LOG = TMP / "portal.log"

PORTAL_HTML = r"""<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>A股研究工作台</title>
    <style>
      :root {
        color-scheme: light;
        --bg: #f6f7f4;
        --panel: #ffffff;
        --panel-2: #eef4f0;
        --line: #d8ded7;
        --text: #17211b;
        --muted: #65736c;
        --accent: #0f6b4f;
        --accent-2: #315f9b;
        --bad: #a83434;
        --good: #18724f;
      }
      * { box-sizing: border-box; }
      body {
        margin: 0;
        background: var(--bg);
        color: var(--text);
        font: 14px/1.55 ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      }
      header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 16px;
        padding: 18px 24px;
        border-bottom: 1px solid var(--line);
        background: var(--panel);
        position: sticky;
        top: 0;
        z-index: 5;
      }
      h1, h2, h3 { margin: 0; line-height: 1.2; }
      h1 { font-size: 20px; }
      h2 { font-size: 16px; }
      h3 { font-size: 14px; }
      p { margin: 0; }
      a { color: var(--accent-2); text-decoration: none; }
      a:hover { text-decoration: underline; }
      button, input, select, textarea {
        font: inherit;
      }
      button, .button {
        border: 1px solid var(--line);
        background: var(--panel);
        color: var(--text);
        border-radius: 6px;
        min-height: 34px;
        padding: 0 12px;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
        text-decoration: none;
      }
      button.primary {
        border-color: var(--accent);
        background: var(--accent);
        color: #fff;
      }
      button:disabled { opacity: .55; cursor: wait; }
      input, select, textarea {
        width: 100%;
        border: 1px solid var(--line);
        border-radius: 6px;
        background: #fff;
        min-height: 34px;
        padding: 7px 9px;
        color: var(--text);
      }
      textarea { min-height: 96px; resize: vertical; }
      main {
        display: grid;
        grid-template-columns: 250px minmax(0, 1fr);
        min-height: calc(100vh - 72px);
      }
      nav {
        border-right: 1px solid var(--line);
        padding: 18px 14px;
        background: #fbfcfa;
      }
      nav button {
        width: 100%;
        justify-content: flex-start;
        border-color: transparent;
        background: transparent;
        margin-bottom: 5px;
      }
      nav button.active {
        background: var(--panel-2);
        border-color: var(--line);
        color: var(--accent);
        font-weight: 700;
      }
      .content {
        padding: 22px;
        display: grid;
        gap: 18px;
        align-content: start;
      }
      .grid {
        display: grid;
        grid-template-columns: repeat(12, 1fr);
        gap: 14px;
      }
      .card {
        grid-column: span 6;
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 16px;
        display: grid;
        gap: 12px;
      }
      .card.full { grid-column: 1 / -1; }
      .card.third { grid-column: span 4; }
      .row {
        display: grid;
        grid-template-columns: repeat(12, 1fr);
        gap: 10px;
        align-items: end;
      }
      .field { grid-column: span 4; display: grid; gap: 5px; }
      .field.small { grid-column: span 2; }
      .field.wide { grid-column: span 8; }
      .actions { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
      .muted { color: var(--muted); }
      .badge {
        display: inline-flex;
        align-items: center;
        min-height: 22px;
        padding: 0 8px;
        border: 1px solid var(--line);
        border-radius: 999px;
        color: var(--muted);
        background: #fff;
        font-size: 12px;
      }
      .badge.good { color: var(--good); border-color: #bcdccc; background: #f1fbf5; }
      .badge.bad { color: var(--bad); border-color: #e7c3c3; background: #fff4f4; }
      .toast {
        position: fixed;
        right: 18px;
        bottom: 18px;
        z-index: 20;
        max-width: min(420px, calc(100vw - 36px));
        border: 1px solid var(--line);
        border-radius: 8px;
        background: #102018;
        color: #f3fbf6;
        padding: 10px 12px;
        box-shadow: 0 12px 30px rgba(23, 33, 27, .16);
        opacity: 0;
        transform: translateY(8px);
        pointer-events: none;
        transition: opacity .16s ease, transform .16s ease;
      }
      .toast.show { opacity: 1; transform: translateY(0); }
      .list {
        display: grid;
        gap: 8px;
        max-height: 420px;
        overflow: auto;
        padding-right: 4px;
      }
      .item {
        border: 1px solid var(--line);
        border-radius: 7px;
        background: #fff;
        padding: 10px;
        display: grid;
        gap: 5px;
      }
      pre {
        margin: 0;
        white-space: pre-wrap;
        word-break: break-word;
        background: #152019;
        color: #e8f1eb;
        padding: 14px;
        border-radius: 7px;
        max-height: 560px;
        overflow: auto;
      }
      .markdown {
        border: 1px solid var(--line);
        border-radius: 7px;
        padding: 14px;
        background: #fff;
        max-height: 560px;
        overflow: auto;
      }
      .markdown h1 { font-size: 20px; margin: 0 0 12px; }
      .markdown h2 { font-size: 17px; margin: 18px 0 8px; }
      .markdown h3 { font-size: 15px; margin: 16px 0 8px; }
      .markdown p, .markdown li { margin: 5px 0; }
      .markdown ul { margin: 8px 0 12px; padding-left: 20px; }
      .markdown table { width: 100%; border-collapse: collapse; font-size: 13px; }
      .markdown th, .markdown td { border: 1px solid var(--line); padding: 6px; vertical-align: top; }
      .hidden { display: none !important; }
      @media (max-width: 900px) {
        main { grid-template-columns: 1fr; }
        nav { border-right: 0; border-bottom: 1px solid var(--line); display: flex; gap: 6px; overflow: auto; }
        nav button { width: auto; white-space: nowrap; }
        .card, .card.third { grid-column: 1 / -1; }
        .field, .field.small, .field.wide { grid-column: 1 / -1; }
      }
    </style>
  </head>
  <body>
    <header>
      <div>
        <h1>A股研究工作台</h1>
        <p class="muted">统一启动、检索、运行 skill 和查看本地报告。</p>
      </div>
      <div class="actions">
        <a class="button" href="http://127.0.0.1:8765/report/" target="_blank">报告页</a>
        <a class="button" href="http://127.0.0.1:8793/index.html" target="_blank">资讯看板</a>
        <a class="button" href="http://127.0.0.1:4173/" target="_blank">Vibe 前端</a>
      </div>
    </header>
    <main>
      <nav aria-label="工作台导航">
        <button class="active" data-view="home">总览</button>
        <button data-view="selection">综合选股</button>
        <button data-view="reports">日期报告</button>
        <button data-view="stocks">股票分析</button>
        <button data-view="industries">产业链</button>
        <button data-view="news">新闻搜索</button>
        <button data-view="skills">Skills</button>
      </nav>
      <section class="content">
        <section id="view-home" class="view grid"></section>
        <section id="view-selection" class="view grid hidden"></section>
        <section id="view-reports" class="view grid hidden"></section>
        <section id="view-stocks" class="view grid hidden"></section>
        <section id="view-industries" class="view grid hidden"></section>
        <section id="view-news" class="view grid hidden"></section>
        <section id="view-skills" class="view grid hidden"></section>
      </section>
    </main>
    <div id="toast" class="toast" role="status" aria-live="polite"></div>
    <script>
      const state = { reports: [], industries: [], skills: [], services: [] };
      const $ = (id) => document.getElementById(id);
      const esc = (v) => String(v ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");

      function md(text) {
        if (!text) return '<p class="muted">没有内容。</p>';
        const lines = String(text).replace(/\r\n/g, "\n").split("\n");
        const out = [];
        let table = [];
        let list = [];
        let code = [];
        let inCode = false;
        const flushList = () => {
          if (!list.length) return;
          out.push(`<ul>${list.map((line) => `<li>${esc(line)}</li>`).join("")}</ul>`);
          list = [];
        };
        const flushTable = () => {
          if (!table.length) return;
          const rows = table.map((line) => line.trim().replace(/^\||\|$/g, "").split("|").map((cell) => esc(cell.trim())));
          const hasHeader = rows.length > 1 && rows[1].every((cell) => /^:?-{3,}:?$/.test(cell));
          const bodyRows = hasHeader ? rows.slice(2) : rows;
          const head = hasHeader ? `<thead><tr>${rows[0].map((cell) => `<th>${cell}</th>`).join("")}</tr></thead>` : "";
          out.push(`<table>${head}<tbody>${bodyRows.map((row) => `<tr>${row.map((cell) => `<td>${cell}</td>`).join("")}</tr>`).join("")}</tbody></table>`);
          table = [];
        };
        const flushCode = () => {
          if (!code.length) return;
          out.push(`<pre>${esc(code.join("\n"))}</pre>`);
          code = [];
        };
        for (const raw of lines) {
          const line = raw.trimEnd();
          if (line.startsWith("```")) {
            flushList();
            flushTable();
            if (inCode) {
              flushCode();
              inCode = false;
            } else {
              inCode = true;
            }
            continue;
          }
          if (inCode) {
            code.push(line);
            continue;
          }
          if (/^\|.+\|$/.test(line.trim())) {
            flushList();
            table.push(line);
            continue;
          }
          flushTable();
          const bullet = line.match(/^\s*[-*]\s+(.+)$/);
          if (bullet) {
            list.push(bullet[1]);
            continue;
          }
          flushList();
          if (!line.trim()) continue;
          if (line.startsWith("### ")) out.push(`<h3>${esc(line.slice(4))}</h3>`);
          else if (line.startsWith("## ")) out.push(`<h2>${esc(line.slice(3))}</h2>`);
          else if (line.startsWith("# ")) out.push(`<h1>${esc(line.slice(2))}</h1>`);
          else out.push(`<p>${esc(line)}</p>`);
        }
        flushList();
        flushTable();
        flushCode();
        return out.join("");
      }

      function showToast(message) {
        const toast = $("toast");
        toast.textContent = message;
        toast.classList.add("show");
        clearTimeout(showToast.timer);
        showToast.timer = setTimeout(() => toast.classList.remove("show"), 2600);
      }

      async function api(path, options = {}) {
        const res = await fetch(path, {
          ...options,
          headers: { "Content-Type": "application/json", ...(options.headers || {}) },
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.error || data.message || `HTTP ${res.status}`);
        return data;
      }

      function setBusy(button, busy) {
        button.disabled = busy;
        button.dataset.originalText ||= button.textContent;
        button.textContent = busy ? "运行中..." : button.dataset.originalText;
      }

      function show(view) {
        document.querySelectorAll("nav button").forEach((btn) => btn.classList.toggle("active", btn.dataset.view === view));
        document.querySelectorAll(".view").forEach((el) => el.classList.add("hidden"));
        $(`view-${view}`).classList.remove("hidden");
      }

      async function refreshStatus() {
        const data = await api("/api/status");
        state.services = data.services || [];
        renderHome();
      }

      function renderHome() {
        $("view-home").innerHTML = `
          <div class="card full">
            <h2>服务状态</h2>
            <div class="grid">
              ${state.services.map((s) => `
                <div class="card third">
                  <div class="actions" style="justify-content:space-between">
                    <h3>${esc(s.name)}</h3>
                    <span class="badge ${s.running ? "good" : "bad"}">${s.running ? "运行中" : "不可用"}</span>
                  </div>
                  <p class="muted">${esc(s.detail || "")}</p>
                  ${s.url ? `<a href="${esc(s.url)}" target="_blank">${esc(s.url)}</a>` : ""}
                </div>
              `).join("")}
            </div>
            <div class="actions">
              <button onclick="refreshStatus()">刷新状态</button>
              <button onclick="rebuildReport(this)">重建报告数据</button>
            </div>
          </div>
          <div class="card third"><h2>日期报告</h2><p class="muted">查看日报、收盘复盘、周报和产业链报告。</p><button onclick="show('reports')">进入</button></div>
          <div class="card third"><h2>综合选股</h2><p class="muted">一键运行 iWenCai 趋势池和综合选股，展示核心池、观察池与证据缺口。</p><button onclick="show('selection')">进入</button></div>
          <div class="card third"><h2>股票分析</h2><p class="muted">实时股价估值、基础数据抓取、财务分析入口。</p><button onclick="show('stocks')">进入</button></div>
          <div class="card third"><h2>新闻搜索</h2><p class="muted">刷新本地投资资讯，看最近赛道新闻。</p><button onclick="show('news')">进入</button></div>
        `;
      }

      async function rebuildReport(btn) {
        try {
          setBusy(btn, true);
          const data = await api("/api/report/rebuild", { method: "POST", body: "{}" });
          showToast(`已重建: days=${data.days}, weeklies=${data.weeklies}, industryReports=${data.industryReports}`);
        } catch (err) {
          showToast(err.message);
        } finally {
          setBusy(btn, false);
        }
      }

      async function loadReports() {
        const data = await api("/api/reports");
        state.reports = data.days || [];
        const options = state.reports.map((r) => `<option value="${esc(r.date)}">${esc(r.date)} ${r.hasCloseReview ? "复盘" : ""}</option>`).join("");
        $("view-reports").innerHTML = `
          <div class="card">
            <h2>日期报告</h2>
            <div class="row">
              <label class="field wide"><span>日期</span><select id="reportDate">${options}</select></label>
              <label class="field small"><span>类型</span><select id="reportType"><option value="daily">日报</option><option value="close">收盘复盘</option></select></label>
              <div class="field small"><button class="primary" onclick="loadReport(this)">查看</button></div>
            </div>
            <div class="actions">
              <a class="button" href="http://127.0.0.1:8765/report/" target="_blank">打开完整报告页</a>
            </div>
          </div>
          <div class="card"><h2>周报</h2><div class="list">${(data.weeklies || []).map((w) => `<div class="item"><strong>${esc(w.title)}</strong><span class="muted">${esc(w.id)}</span></div>`).join("")}</div></div>
          <div class="card full"><h2>预览</h2><div id="reportPreview" class="markdown">请选择日期。</div></div>
        `;
      }

      async function loadReport(btn) {
        try {
          setBusy(btn, true);
          const date = $("reportDate").value;
          const type = $("reportType").value;
          const data = await api(`/api/report?date=${encodeURIComponent(date)}&type=${encodeURIComponent(type)}`);
          $("reportPreview").innerHTML = md(data.markdown || "");
        } catch (err) {
          $("reportPreview").innerHTML = `<pre>${esc(err.message)}</pre>`;
        } finally {
          setBusy(btn, false);
        }
      }

      async function renderSelection() {
        const reports = state.reports.length ? state.reports : (await api("/api/reports")).days || [];
        state.reports = reports;
        const options = reports.map((r) => `<option value="${esc(r.date)}">${esc(r.date)}</option>`).join("");
        $("view-selection").innerHTML = `
          <div class="card full">
            <h2>综合选股</h2>
            <div class="row">
              <label class="field small"><span>日期</span><select id="selectionDate">${options}</select></label>
              <label class="field"><span>主题</span><input id="selectionTheme" placeholder="可选，例如 存储芯片" /></label>
              <label class="field"><span>指定代码</span><input id="selectionCodes" placeholder="可选，例如 603986,600584" /></label>
              <label class="field small"><span>候选数</span><input id="selectionMax" type="number" min="1" max="60" value="20" /></label>
              <label class="field small"><span>行情复核</span><select id="selectionRefresh"><option value="true">开启</option><option value="false">关闭</option></select></label>
              <label class="field small"><span>复核数量</span><input id="selectionQuoteLimit" type="number" min="0" max="20" value="3" /></label>
            </div>
            <div class="actions">
              <button class="primary" onclick="runSelection(this)">一键选股</button>
              <button onclick="loadLatestSelection(this)">查看最近结果</button>
            </div>
            <p class="muted">执行顺序：先运行 iwencai-trend-stock-pool，再叠加本地日报、产业链、估值和风险证据。输出保存在 tmp/workbench，不入库。</p>
          </div>
          <div class="card full"><h2>报告</h2><div id="selectionReport" class="markdown">等待运行。</div></div>
          <div class="card full"><h2>结构化结果</h2><pre id="selectionJson">等待运行。</pre></div>
        `;
      }

      function renderSelectionResult(data) {
        $("selectionReport").innerHTML = md(data.markdown || "");
        $("selectionJson").textContent = JSON.stringify({
          output: data.output,
          markdown_output: data.markdown_output,
          summary: data.payload?.summary,
          iwencai: data.payload?.iwencai,
          generated_at: data.payload?.generated_at,
        }, null, 2);
      }

      async function runSelection(btn) {
        try {
          setBusy(btn, true);
          $("selectionReport").innerHTML = '<p class="muted">正在运行综合选股，首次拉取行情可能需要几分钟。</p>';
          const data = await api("/api/selection/run", { method: "POST", body: JSON.stringify({
            date: $("selectionDate").value,
            theme: $("selectionTheme").value,
            codes: $("selectionCodes").value,
            max_candidates: Number($("selectionMax").value || 20),
            refresh_quotes: $("selectionRefresh").value === "true",
            quote_limit: Number($("selectionQuoteLimit").value || 0),
          }) });
          renderSelectionResult(data);
          showToast(`选股完成：核心 ${data.payload?.summary?.core ?? 0}，观察 ${data.payload?.summary?.watch ?? 0}`);
        } catch (err) {
          $("selectionReport").innerHTML = `<pre>${esc(err.message)}</pre>`;
        } finally {
          setBusy(btn, false);
        }
      }

      async function loadLatestSelection(btn) {
        try {
          setBusy(btn, true);
          const data = await api("/api/selection/latest");
          renderSelectionResult(data);
        } catch (err) {
          $("selectionReport").innerHTML = `<pre>${esc(err.message)}</pre>`;
        } finally {
          setBusy(btn, false);
        }
      }

      function renderStocks() {
        $("view-stocks").innerHTML = `
          <div class="card full">
            <h2>股票分析</h2>
            <div class="row">
              <label class="field"><span>代码</span><input id="stockCode" value="600519" /></label>
              <label class="field"><span>行业口径</span><input id="stockIndustry" value="白酒龙头" /></label>
              <label class="field small"><span>预期 EPS</span><input id="stockEps" type="number" step="0.01" placeholder="可选" /></label>
              <label class="field small"><span>目标价</span><input id="stockTarget" type="number" step="0.01" placeholder="可选" /></label>
            </div>
            <div class="actions">
              <button class="primary" onclick="runPriceAnalysis(this)">股价/估值快跑</button>
              <button onclick="runBasicFetch(this)">基础信息抓取</button>
              <button onclick="runFullFetch(this)">全量基础面抓取</button>
            </div>
            <p class="muted">全量基础面会调用真实远端接口，可能需要数分钟。输出保存在 tmp/workbench。</p>
          </div>
          <div class="card full"><h2>结果</h2><div id="stockResult" class="markdown">等待运行。</div></div>
        `;
      }

      async function runPriceAnalysis(btn) {
        try {
          setBusy(btn, true);
          const data = await api("/api/stock/price", { method: "POST", body: JSON.stringify({
            code: $("stockCode").value,
            industry: $("stockIndustry").value,
            eps_expected: $("stockEps").value,
            consensus_target: $("stockTarget").value,
          }) });
          $("stockResult").innerHTML = md(data.markdown || JSON.stringify(data, null, 2));
        } catch (err) {
          $("stockResult").innerHTML = `<pre>${esc(err.message)}</pre>`;
        } finally {
          setBusy(btn, false);
        }
      }

      async function runBasicFetch(btn) {
        await runFetch(btn, "basic");
      }

      async function runFullFetch(btn) {
        await runFetch(btn, "all");
      }

      async function runFetch(btn, dataType) {
        try {
          setBusy(btn, true);
          const data = await api("/api/stock/fetch", { method: "POST", body: JSON.stringify({
            code: $("stockCode").value,
            data_type: dataType,
            years: dataType === "all" ? 1 : 3,
          }) });
          $("stockResult").innerHTML = `<pre>${esc(JSON.stringify(data, null, 2))}</pre>`;
        } catch (err) {
          $("stockResult").innerHTML = `<pre>${esc(err.message)}</pre>`;
        } finally {
          setBusy(btn, false);
        }
      }

      async function loadIndustries() {
        const data = await api("/api/industries");
        state.industries = data.items || [];
        $("view-industries").innerHTML = `
          <div class="card">
            <h2>产业链报告</h2>
            <div class="list">
              ${state.industries.map((it) => `
                <div class="item">
                  <strong>${esc(it.title)}</strong>
                  <span class="muted">${esc(it.id)} · ${esc(it.date || "")}</span>
                  <div class="actions"><button onclick="loadIndustry('${esc(it.id)}', this)">预览</button></div>
                </div>
              `).join("")}
            </div>
          </div>
          <div class="card">
            <h2>新产业分析</h2>
            <p class="muted">当前工作台提供已有产业链报告的检索和预览。新的产业链研究仍建议由 Codex 调用 skill 完成，以便联网核验和生成图表。</p>
            <textarea id="industryPrompt" placeholder="例如：分析AI服务器液冷产业链，重点找上游瓶颈和A股映射"></textarea>
            <button onclick="copyIndustryPrompt()">复制研究题目</button>
          </div>
          <div class="card full"><h2>预览</h2><div id="industryPreview" class="markdown">请选择报告。</div></div>
        `;
      }

      async function loadIndustry(id, btn) {
        try {
          setBusy(btn, true);
          const data = await api(`/api/industry?id=${encodeURIComponent(id)}`);
          $("industryPreview").innerHTML = md(data.markdown || "");
        } catch (err) {
          $("industryPreview").innerHTML = `<pre>${esc(err.message)}</pre>`;
        } finally {
          setBusy(btn, false);
        }
      }

      function copyIndustryPrompt() {
        navigator.clipboard?.writeText($("industryPrompt").value || "");
        showToast("已复制。");
      }

      async function renderNews() {
        const data = await api("/api/news/summary");
        $("view-news").innerHTML = `
          <div class="card full">
            <h2>投资资讯</h2>
            <p class="muted">当前数据：${esc(data.generated_at || "未知")} · ${esc(data.total_sources || 0)} 个源</p>
            <div class="actions">
              <a class="button" href="http://127.0.0.1:8793/index.html" target="_blank">打开资讯看板</a>
              <button class="primary" onclick="refreshNews(this)">刷新抓取+摘要</button>
            </div>
          </div>
          <div class="card full">
            <h2>赛道概览</h2>
            <div class="grid">
              ${(data.industries || []).map((it) => `
                <div class="card third">
                  <h3>${esc(it.name)}</h3>
                  <p class="muted">${esc(it.total)} 源 · ${esc(it.items)} 条</p>
                  <p>${esc((it.top || []).join(" / "))}</p>
                </div>
              `).join("")}
            </div>
          </div>
          <div class="card full"><h2>刷新结果</h2><pre id="newsResult">等待刷新。</pre></div>
        `;
      }

      async function refreshNews(btn) {
        try {
          setBusy(btn, true);
          const data = await api("/api/news/refresh", { method: "POST", body: "{}" });
          $("newsResult").textContent = JSON.stringify(data, null, 2);
        } catch (err) {
          $("newsResult").textContent = err.message;
        } finally {
          setBusy(btn, false);
        }
      }

      async function loadSkills() {
        const data = await api("/api/skills");
        state.skills = data.skills || [];
        $("view-skills").innerHTML = `
          <div class="card full">
            <h2>Skills</h2>
            <p class="muted">这里列出当前仓库能力。脚本型 skill 可直接触发；研究型 skill 保留为 Codex 工作流入口。</p>
          </div>
          ${state.skills.map((s) => `
            <div class="card third">
              <h3>${esc(s.name)}</h3>
              <p class="muted">${esc(s.description)}</p>
              <pre>${esc((s.commands || []).join("\n\n") || "无直接命令，作为研究方法/提示使用。")}</pre>
              ${(s.commands || []).map((cmd, idx) => `<button onclick="runSkillCommand('${esc(s.id)}', ${idx}, this)">运行示例 ${idx + 1}</button>`).join("")}
            </div>
          `).join("")}
          <div class="card full"><h2>运行输出</h2><pre id="skillResult">等待运行。</pre></div>
        `;
      }

      async function runSkillCommand(skillId, commandIndex, btn) {
        try {
          setBusy(btn, true);
          const data = await api("/api/skill/run", { method: "POST", body: JSON.stringify({ skill: skillId, command_index: commandIndex }) });
          $("skillResult").textContent = data.stdout || data.stderr || JSON.stringify(data, null, 2);
        } catch (err) {
          $("skillResult").textContent = err.message;
        } finally {
          setBusy(btn, false);
        }
      }

      document.querySelectorAll("nav button").forEach((btn) => {
        btn.addEventListener("click", () => show(btn.dataset.view));
      });

      async function boot() {
        renderStocks();
        await Promise.allSettled([refreshStatus(), loadReports(), renderSelection(), loadIndustries(), renderNews(), loadSkills()]);
      }
      boot();
    </script>
  </body>
</html>
"""


@dataclass
class Service:
    key: str
    name: str
    port: int
    url: str
    command: list[str] | None = None
    cwd: Path = ROOT
    env: dict[str, str] = field(default_factory=dict)
    enabled: bool = True
    detail: str = ""
    health_url: str = ""
    startup_timeout: int = 15
    process: subprocess.Popen[str] | None = field(default=None, init=False)


def is_port_open(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.25)
        return sock.connect_ex((host, port)) == 0


def is_url_healthy(url: str, timeout: float = 2) -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            status = response.getcode()
            if 200 <= status < 400:
                return True, f"HTTP {status}"
            return False, f"HTTP {status}"
    except urllib.error.HTTPError as exc:
        return False, f"HTTP {exc.code}"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def request_json(url: str, timeout: float = 10) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": "stock-workbench/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def run_command(command: list[str], *, cwd: Path = ROOT, timeout: float = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(cwd),
        text=True,
        capture_output=True,
        timeout=timeout,
        env={**os.environ, "PYTHONUTF8": "1"},
    )


def build_report_data() -> dict[str, Any]:
    result = run_command(["uv", "run", "python", "web-apps/report/build_data.py"], timeout=120)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "report data build failed").strip())
    return json.loads(result.stdout.strip().splitlines()[-1])


class Workbench:
    def __init__(self, *, include_vibe: bool = True) -> None:
        self.include_vibe = include_vibe
        self.services = self._make_services()

    def _make_services(self) -> list[Service]:
        py = sys.executable
        services = [
            Service(
                key="report",
                name="交互报告",
                port=8765,
                url="http://127.0.0.1:8765/report/",
                command=[py, "-m", "http.server", "8765", "--directory", "web-apps/report"],
                detail="日报、复盘、周报、产业链报告",
                health_url="http://127.0.0.1:8765/report/",
            ),
            Service(
                key="news",
                name="投资资讯看板",
                port=8793,
                url="http://127.0.0.1:8793/index.html",
                command=["uv", "run", "python", ".agents/skills/investment-news/server.py", "8793"],
                detail="108+ 新闻源和本地刷新接口",
                health_url="http://127.0.0.1:8793/index.html",
            ),
            Service(
                key="wiki",
                name="Vibe-Trading Wiki",
                port=8088,
                url="http://127.0.0.1:8088/home/",
                command=[py, "-m", "http.server", "8088", "--directory", "web-apps/vibe-trading/wiki"],
                detail="外部应用文档静态预览",
                health_url="http://127.0.0.1:8088/home/",
            ),
        ]
        if self.include_vibe:
            vibe_python = VIBE_TRADING / ".venv" / "bin" / "python"
            backend_command = None
            backend_detail = "Vibe-Trading FastAPI 后端；LLM 研究任务需要 agent/.env 中的 provider/key"
            if vibe_python.exists():
                backend_command = [
                    str(vibe_python),
                    "-c",
                    "import cli, sys; raise SystemExit(cli.main(sys.argv[1:]))",
                    "serve",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "8899",
                ]
            else:
                backend_detail = "未找到 .venv/bin/python；先在 web-apps/vibe-trading 用 Python 3.11 创建 venv 并 pip install -e ."
            services.append(
                Service(
                    key="vibe_backend",
                    name="Vibe-Trading 后端",
                    port=8899,
                    url="http://127.0.0.1:8899/health",
                    command=backend_command,
                    cwd=VIBE_TRADING,
                    env={"PYTHONPATH": str(VIBE_TRADING / "agent")},
                    enabled=backend_command is not None,
                    detail=backend_detail,
                    health_url="http://127.0.0.1:8899/health",
                    startup_timeout=90,
                )
            )
            command = None
            detail = "Vibe-Trading 前端预览；/sessions 等接口代理到 127.0.0.1:8899"
            if (VIBE_FRONTEND / "node_modules").exists() and (VIBE_FRONTEND / "dist").exists():
                command = ["npm", "run", "preview", "--", "--host", "127.0.0.1", "--port", "4173"]
            else:
                detail = "未找到 frontend/node_modules 或 dist；先在 web-apps/vibe-trading/frontend 运行 npm ci && npm run build"
            services.append(
                Service(
                    key="vibe_frontend",
                    name="Vibe-Trading 前端",
                    port=4173,
                    url="http://127.0.0.1:4173/",
                    command=command,
                    cwd=VIBE_FRONTEND,
                    enabled=command is not None,
                    detail=detail,
                    health_url="http://127.0.0.1:4173/",
                    startup_timeout=45,
                )
            )
        return services

    def service_running(self, service: Service) -> tuple[bool, str]:
        if service.health_url:
            healthy, detail = is_url_healthy(service.health_url)
            if healthy:
                return True, detail
            if not is_port_open(service.port):
                return False, detail
            return False, f"port open, health failed: {detail}"
        return is_port_open(service.port), "port open" if is_port_open(service.port) else "port closed"

    def start_dependencies(self) -> None:
        TMP.mkdir(parents=True, exist_ok=True)
        try:
            build_report_data()
        except Exception as exc:  # noqa: BLE001
            print(f"[warn] report data build failed: {exc}", file=sys.stderr)

        for service in self.services:
            if not service.enabled:
                print(f"[skip] {service.name}: {service.detail}")
                continue
            running, _ = self.service_running(service)
            if running:
                print(f"[reuse] {service.name}: {service.url}")
                continue
            if not service.command:
                print(f"[skip] {service.name}: no command")
                continue
            print(f"[start] {service.name}: {service.url}")
            log_path = TMP / f"{service.key}.log"
            log_file = log_path.open("ab", buffering=0)
            service.process = subprocess.Popen(
                service.command,
                cwd=str(service.cwd),
                stdout=log_file,
                stderr=subprocess.STDOUT,
                text=True,
                env={**os.environ, "PYTHONUTF8": "1", **service.env},
            )
            log_file.close()
            deadline = time.time() + service.startup_timeout
            while time.time() < deadline:
                running, _ = self.service_running(service)
                if running:
                    break
                if service.process.poll() is not None:
                    print(
                        f"[warn] {service.name} exited early with {service.process.returncode}; log: {log_path}",
                        file=sys.stderr,
                    )
                    break
                time.sleep(0.25)
            else:
                print(f"[warn] {service.name} not healthy after {service.startup_timeout}s; log: {log_path}", file=sys.stderr)

    def stop(self) -> None:
        for service in reversed(self.services):
            proc = service.process
            if proc and proc.poll() is None:
                proc.terminate()
        for service in reversed(self.services):
            proc = service.process
            if proc and proc.poll() is None:
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()

    def status(self) -> list[dict[str, Any]]:
        statuses = []
        for service in self.services:
            running, health_detail = self.service_running(service) if service.enabled else (False, "disabled")
            detail = service.detail
            if service.enabled and service.health_url and not running:
                detail = f"{detail}；健康检查失败: {health_detail}"
            statuses.append(
                {
                    "key": service.key,
                    "name": service.name,
                    "port": service.port,
                    "url": service.url,
                    "running": running,
                    "enabled": service.enabled,
                    "detail": detail,
                    "health": health_detail,
                }
            )
        return statuses

    def health(self) -> dict[str, Any]:
        services = self.status()
        enabled = [service for service in services if service["enabled"]]
        running = [service for service in enabled if service["running"]]
        return {
            "status": "healthy" if len(running) == len(enabled) else "degraded",
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "services": services,
            "summary": {
                "enabled": len(enabled),
                "running": len(running),
                "down": len(enabled) - len(running),
            },
        }


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def read_json(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def first_heading(markdown: str, fallback: str) -> str:
    for line in markdown.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def list_reports() -> dict[str, Any]:
    days = []
    local_dir = ROOT / "local"
    if local_dir.exists():
        for child in sorted(local_dir.iterdir(), reverse=True):
            if not child.is_dir() or not re.match(r"^\d{4}-\d{2}-\d{2}$", child.name):
                continue
            if not (child / "report.md").exists() and not (child / "assembled.json").exists():
                continue
            days.append(
                {
                    "date": child.name,
                    "hasDaily": (child / "report.md").exists(),
                    "hasCloseReview": (child / "close_review.json").exists() or (child / "close_review.md").exists(),
                }
            )
    weeklies = []
    weekly_dir = ROOT / "local" / "reviews" / "weekly"
    if weekly_dir.exists():
        for path in sorted(weekly_dir.glob("weekly_review_*.md"), reverse=True):
            weeklies.append({"id": path.stem, "title": path.stem.removeprefix("weekly_review_").replace("_", " 至 ")})
    return {"days": days, "weeklies": weeklies}


def list_industries() -> dict[str, Any]:
    items = []
    root = ROOT / "industry-analysis"
    if root.exists():
        for child in sorted(root.iterdir(), reverse=True):
            report = child / "report.md"
            if not child.is_dir() or not report.exists():
                continue
            markdown = read_text(report)
            quality = read_json(child / "quality_report.json") or {}
            items.append(
                {
                    "id": child.name,
                    "title": first_heading(markdown, child.name),
                    "date": child.name[-10:] if re.search(r"\d{4}-\d{2}-\d{2}$", child.name) else "",
                    "qualityPassed": quality.get("passed"),
                    "qualityScore": quality.get("score"),
                }
            )
    return {"items": items}


def parse_skill_header(text: str) -> dict[str, str]:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    header = text[3:end]
    result: dict[str, str] = {}
    lines = header.splitlines()
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip().strip('"')
            if value in {">-", ">", "|", "|-"}:
                block: list[str] = []
                idx += 1
                while idx < len(lines) and (lines[idx].startswith(" ") or not lines[idx].strip()):
                    block.append(lines[idx].strip())
                    idx += 1
                result[key] = " ".join(part for part in block if part)
                continue
            result[key] = value
        idx += 1
    return result


def normalize_skill_command(skill_dir: Path, command: str) -> str:
    parts = shlex.split(command)
    if not parts:
        return ""
    if parts[0] == "python":
        parts[0:1] = ["uv", "run", "python"]
    if parts[:3] != ["uv", "run", "python"] or len(parts) < 4:
        return ""
    if parts[3] == "-c":
        return ""
    script = parts[3]
    if script.startswith("scripts/"):
        parts[3] = str((skill_dir / script).relative_to(ROOT))
    skill_tmp = TMP / skill_dir.name
    for flag in ("--output", "--dump-json"):
        if flag not in parts:
            continue
        value_index = parts.index(flag) + 1
        if value_index >= len(parts):
            continue
        value = Path(parts[value_index])
        if not value.is_absolute() and not str(value).startswith("tmp/"):
            parts[value_index] = str((skill_tmp / value.name).relative_to(ROOT))
    if "--input" in parts:
        value_index = parts.index("--input") + 1
        if value_index < len(parts):
            value = Path(parts[value_index])
            if not value.is_absolute() and not str(value).startswith("tmp/"):
                parts[value_index] = str((skill_tmp / value.name).relative_to(ROOT))
    if "--json" in parts:
        value_index = parts.index("--json") + 1
        if value_index < len(parts):
            value = Path(parts[value_index])
            if not value.is_absolute() and not (ROOT / value).exists():
                return ""
    return shlex.join(parts)


def extract_skill_commands(skill_dir: Path, text: str) -> list[str]:
    commands: list[str] = []
    in_code = False
    pending = ""
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("```"):
            in_code = not in_code
            pending = ""
            continue
        if not in_code or not line or line.startswith("#"):
            continue
        pending = f"{pending} {line}".strip() if pending else line
        if pending.endswith("\\"):
            pending = pending[:-1].strip()
            continue
        if pending.startswith(("python ", "uv run python ")):
            command = normalize_skill_command(skill_dir, pending)
            if command and command not in commands:
                commands.append(command)
        pending = ""
    return commands


def list_skills() -> dict[str, Any]:
    skills = []
    for path in sorted((ROOT / ".agents" / "skills").glob("*/SKILL.md")):
        text = read_text(path)
        header = parse_skill_header(text)
        commands = extract_skill_commands(path.parent, text)
        skills.append(
            {
                "id": path.parent.name,
                "name": header.get("name") or path.parent.name,
                "description": header.get("description") or "",
                "commands": commands[:4],
            }
        )
    return {"skills": skills}


def investment_news_summary() -> dict[str, Any]:
    data_js = read_text(INVESTMENT_NEWS / "data.js")
    match = re.search(r"window\.DATA\s*=\s*(\{.*\});\s*$", data_js, re.S)
    if not match:
        return {"generated_at": "", "total_sources": 0, "industries": []}
    data = json.loads(match.group(1))
    industries = []
    for item in data.get("industries", []):
        headlines = [entry.get("title", "") for entry in item.get("items", [])[:3]]
        industries.append(
            {
                "key": item.get("key", ""),
                "name": item.get("name", ""),
                "total": item.get("total", 0),
                "items": len(item.get("items", [])),
                "top": headlines,
            }
        )
    return {
        "generated_at": data.get("generated_at", ""),
        "total_sources": data.get("stats", {}).get("total_sources", 0),
        "industries": industries,
    }


def render_selection_markdown(payload: dict[str, Any]) -> str:
    summary = payload.get("summary") or {}
    lines = [
        f"# 综合选股报告 {payload.get('date') or ''}",
        "",
        f"- 生成时间: {payload.get('generated_at') or ''}",
        f"- 主题: {payload.get('theme') or '全部'}",
        f"- 候选数: {summary.get('total', 0)}，核心池: {summary.get('core', 0)}，观察池: {summary.get('watch', 0)}，排除: {summary.get('reject', 0)}",
        f"- iWenCai 状态: {(payload.get('iwencai') or {}).get('status', 'unknown')}",
        "",
        "## 主线",
    ]
    mainlines = payload.get("mainlines") or []
    if mainlines:
        for item in mainlines[:8]:
            title = item.get("title") or item.get("sector") or "-"
            score = item.get("impact_score") or item.get("score") or ""
            lines.append(f"- {title}: {score}")
    else:
        lines.append("- 未匹配到主题主线，按股票和产业链证据补充筛选。")

    for bucket, title in (("core", "核心池"), ("watch", "观察池"), ("reject", "排除/待验证")):
        rows = [row for row in payload.get("candidates", []) if row.get("bucket") == bucket]
        lines.extend(
            [
                "",
                f"## {title}",
                "",
                "| 代码 | 名称 | 主题/行业 | 分数 | 估值 | 证据 | 缺口 |",
                "| --- | --- | --- | ---: | --- | --- | --- |",
            ]
        )
        if not rows:
            lines.append("| - | - | - | - | - | - | - |")
            continue
        for row in rows:
            quote = row.get("quote") or {}
            valuation = []
            if quote.get("latest") is not None:
                valuation.append(f"价 {quote.get('latest')}")
            if quote.get("pe_ttm") is not None:
                valuation.append(f"PE {quote.get('pe_ttm')}")
            if quote.get("pb") is not None:
                valuation.append(f"PB {quote.get('pb')}")
            evidence = "；".join(str(item) for item in (row.get("reasons") or [])[:3]) or "-"
            missing = "；".join(str(item) for item in (row.get("missing_evidence") or [])[:3]) or "无"
            lines.append(
                "| {code} | {name} | {sector} | {score} | {valuation} | {evidence} | {missing} |".format(
                    code=row.get("code") or "",
                    name=row.get("name") or "",
                    sector=row.get("sector") or "",
                    score=row.get("score") or "",
                    valuation="；".join(valuation) or "-",
                    evidence=evidence,
                    missing=missing,
                )
            )
    lines.extend(["", "> 仅用于研究和复盘校准，不构成买卖建议。"])
    return "\n".join(lines) + "\n"


def selection_output_paths() -> tuple[Path, Path, Path]:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = TMP / f"integrated_selection_{timestamp}.json"
    markdown_output = TMP / f"integrated_selection_{timestamp}.md"
    iwencai_output = TMP / f"iwencai_{timestamp}"
    return output, markdown_output, iwencai_output


def latest_selection_json() -> Path | None:
    candidates = sorted(TMP.glob("integrated_selection_*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def read_selection_result(path: Path) -> dict[str, Any]:
    payload = read_json(path)
    if not isinstance(payload, dict):
        raise FileNotFoundError(f"selection result not found: {path}")
    markdown_path = path.with_suffix(".md")
    markdown = read_text(markdown_path) or render_selection_markdown(payload)
    return {
        "output": str(path.relative_to(ROOT)),
        "markdown_output": str(markdown_path.relative_to(ROOT)) if markdown_path.exists() else "",
        "payload": payload,
        "markdown": markdown,
    }


def run_integrated_selection(data: dict[str, Any]) -> dict[str, Any]:
    TMP.mkdir(parents=True, exist_ok=True)
    output, markdown_output, iwencai_output = selection_output_paths()
    command = [
        "uv",
        "run",
        "python",
        ".agents/skills/integrated-stock-selection/scripts/run_integrated_selection.py",
        "--max-candidates",
        str(max(1, min(60, int(data.get("max_candidates") or 20)))),
        "--iwencai-output-dir",
        str(iwencai_output),
        "--output",
        str(output),
    ]
    date = str(data.get("date") or "").strip()
    theme = str(data.get("theme") or "").strip()
    codes = str(data.get("codes") or "").strip()
    if date:
        command.extend(["--date", date])
    if theme:
        command.extend(["--theme", theme])
    if codes:
        command.extend(["--codes", codes])
    if bool(data.get("refresh_quotes")):
        command.append("--refresh-quotes")
        command.extend(["--quote-limit", str(max(0, min(20, int(data.get("quote_limit") or 3))))])
    result = run_command(command, timeout=1200)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "integrated selection failed").strip())
    payload = read_json(output)
    markdown = render_selection_markdown(payload)
    markdown_output.write_text(markdown, encoding="utf-8")
    response = read_selection_result(output)
    response["command"] = shlex.join(command)
    response["stdout"] = result.stdout[-4000:]
    return response


def json_response(handler: BaseHTTPRequestHandler, payload: Any, status: int = 200) -> None:
    body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def is_pid_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def read_portal_pid() -> int | None:
    if not PORTAL_PID.exists():
        return None
    try:
        return int(PORTAL_PID.read_text(encoding="utf-8").strip())
    except ValueError:
        return None


def start_daemon(args: argparse.Namespace) -> int:
    TMP.mkdir(parents=True, exist_ok=True)
    pid = read_portal_pid()
    if pid and is_pid_running(pid):
        print(f"workbench already running pid={pid} url=http://{args.host}:{args.port}/")
        return 0
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--host",
        args.host,
        "--port",
        str(args.port),
    ]
    if args.no_deps:
        command.append("--no-deps")
    if args.no_vibe:
        command.append("--no-vibe")
    with PORTAL_LOG.open("ab", buffering=0) as log:
        proc = subprocess.Popen(
            command,
            cwd=str(ROOT),
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            close_fds=True,
            text=True,
            env={**os.environ, "PYTHONUTF8": "1"},
        )
    PORTAL_PID.write_text(str(proc.pid), encoding="utf-8")
    deadline = time.time() + 30
    url = f"http://{args.host}:{args.port}/"
    while time.time() < deadline:
        healthy, detail = is_url_healthy(url)
        if healthy:
            print(f"workbench started pid={proc.pid} url=http://{args.host}:{args.port}/ log={PORTAL_LOG}")
            return 0
        if proc.poll() is not None:
            print(f"workbench exited early with {proc.returncode}; log={PORTAL_LOG}", file=sys.stderr)
            return 1
        time.sleep(0.25)
    print(f"workbench not healthy after 30s ({detail}); log={PORTAL_LOG}", file=sys.stderr)
    return 1


def stop_daemon() -> int:
    pid = read_portal_pid()
    if not pid:
        print("workbench pid file not found")
        return 0
    if not is_pid_running(pid):
        PORTAL_PID.unlink(missing_ok=True)
        print(f"stale workbench pid removed: {pid}")
        return 0
    os.kill(pid, signal.SIGTERM)
    deadline = time.time() + 8
    while time.time() < deadline:
        if not is_pid_running(pid):
            PORTAL_PID.unlink(missing_ok=True)
            print(f"workbench stopped pid={pid}")
            return 0
        time.sleep(0.2)
    os.kill(pid, signal.SIGKILL)
    PORTAL_PID.unlink(missing_ok=True)
    print(f"workbench killed pid={pid}")
    return 0


def text_response(handler: BaseHTTPRequestHandler, text: str, content_type: str = "text/html; charset=utf-8") -> None:
    body = text.encode("utf-8")
    handler.send_response(200)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def read_body(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length", "0") or "0")
    if not length:
        return {}
    raw = handler.rfile.read(length).decode("utf-8")
    return json.loads(raw) if raw else {}


def safe_skill_command(skill_id: str, command_index: int) -> list[str]:
    skill_file = ROOT / ".agents" / "skills" / skill_id / "SKILL.md"
    if not skill_file.exists():
        raise FileNotFoundError(f"skill not found: {skill_id}")
    commands = extract_skill_commands(skill_file.parent, read_text(skill_file))
    if command_index < 0 or command_index >= len(commands):
        raise ValueError("command_index is out of range")
    argv = shlex.split(commands[command_index])
    if argv[:3] != ["uv", "run", "python"] or len(argv) < 4:
        raise ValueError("only uv run python commands are supported")
    script = (ROOT / argv[3]).resolve()
    if ROOT not in script.parents or not script.exists():
        raise ValueError(f"script is not inside this repository: {argv[3]}")
    TMP.mkdir(parents=True, exist_ok=True)
    (TMP / skill_id).mkdir(parents=True, exist_ok=True)
    return argv


class WorkbenchHandler(BaseHTTPRequestHandler):
    workbench: Workbench

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[portal] {self.address_string()} {fmt % args}")

    def do_GET(self) -> None:  # noqa: N802
        try:
            self.handle_get()
        except Exception as exc:  # noqa: BLE001
            json_response(self, {"error": str(exc)}, 500)

    def do_HEAD(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        status = 200 if parsed.path in {"/", "/favicon.ico"} or parsed.path.startswith("/api/") else 404
        self.send_response(status)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_POST(self) -> None:  # noqa: N802
        try:
            self.handle_post()
        except subprocess.TimeoutExpired as exc:
            json_response(self, {"error": f"command timed out after {exc.timeout}s"}, 504)
        except Exception as exc:  # noqa: BLE001
            json_response(self, {"error": str(exc)}, 500)

    def handle_get(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        path = parsed.path
        if path == "/":
            text_response(self, PORTAL_HTML)
        elif path == "/favicon.ico":
            text_response(self, "", "image/x-icon")
        elif path == "/api/status":
            json_response(self, {"services": self.workbench.status()})
        elif path == "/api/health":
            payload = self.workbench.health()
            json_response(self, payload, 200 if payload["status"] == "healthy" else 503)
        elif path == "/api/reports":
            json_response(self, list_reports())
        elif path == "/api/report":
            date = query.get("date", [""])[0]
            kind = query.get("type", ["daily"])[0]
            target = ROOT / "local" / date / ("close_review.md" if kind == "close" else "report.md")
            if kind == "close" and not target.exists():
                json_path = ROOT / "local" / date / "close_review.json"
                markdown = json.dumps(read_json(json_path) or {}, ensure_ascii=False, indent=2)
            else:
                markdown = read_text(target)
            if not markdown:
                raise FileNotFoundError(f"report not found for {date} ({kind})")
            json_response(self, {"date": date, "type": kind, "markdown": markdown})
        elif path == "/api/industries":
            json_response(self, list_industries())
        elif path == "/api/industry":
            item_id = query.get("id", [""])[0]
            report = ROOT / "industry-analysis" / item_id / "report.md"
            markdown = read_text(report)
            if not markdown:
                raise FileNotFoundError(f"industry report not found: {item_id}")
            json_response(self, {"id": item_id, "markdown": markdown, "quality": read_json(report.parent / "quality_report.json")})
        elif path == "/api/news/summary":
            json_response(self, investment_news_summary())
        elif path == "/api/selection/latest":
            latest = latest_selection_json()
            if not latest:
                raise FileNotFoundError("no integrated selection result found in tmp/workbench")
            json_response(self, read_selection_result(latest))
        elif path == "/api/skills":
            json_response(self, list_skills())
        else:
            json_response(self, {"error": "not found"}, 404)

    def handle_post(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        data = read_body(self)
        if path == "/api/report/rebuild":
            json_response(self, build_report_data())
        elif path == "/api/news/refresh":
            try:
                payload = request_json("http://127.0.0.1:8793/api/refresh", timeout=180)
            except urllib.error.URLError as exc:
                raise RuntimeError(f"investment-news server unavailable: {exc}") from exc
            json_response(self, payload)
        elif path == "/api/selection/run":
            json_response(self, run_integrated_selection(data))
        elif path == "/api/stock/price":
            code = str(data.get("code") or "").strip()
            if not code:
                raise ValueError("code is required")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dump = TMP / f"stock_price_{code}_{timestamp}.json"
            command = [
                "uv",
                "run",
                "python",
                ".agents/skills/china-stock-price-analysis/scripts/stock_analyze.py",
                code,
                "--industry",
                str(data.get("industry") or "消费电子龙头"),
                "--dump-json",
                str(dump),
            ]
            if data.get("eps_expected"):
                command.extend(["--eps-expected", str(data["eps_expected"])])
            if data.get("consensus_target"):
                command.extend(["--consensus-target", str(data["consensus_target"])])
            result = run_command(command, timeout=90)
            if result.returncode != 0:
                raise RuntimeError((result.stderr or result.stdout).strip())
            json_response(self, {"markdown": result.stdout, "snapshot": str(dump.relative_to(ROOT))})
        elif path == "/api/stock/fetch":
            code = str(data.get("code") or "").strip()
            if not code:
                raise ValueError("code is required")
            data_type = str(data.get("data_type") or "basic")
            years = str(data.get("years") or "1")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output = TMP / f"stock_{data_type}_{code}_{timestamp}.json"
            command = [
                "uv",
                "run",
                "python",
                ".agents/skills/china-stock-analysis/scripts/data_fetcher.py",
                "--code",
                code,
                "--data-type",
                data_type,
                "--years",
                years,
                "--no-cache",
                "--output",
                str(output),
            ]
            result = run_command(command, timeout=420 if data_type == "all" else 120)
            if result.returncode != 0:
                raise RuntimeError((result.stderr or result.stdout).strip())
            json_response(self, {"output": str(output.relative_to(ROOT)), "data": read_json(output), "stdout": result.stdout[-2000:]})
        elif path == "/api/skill/run":
            skill_id = str(data.get("skill") or "").strip()
            command_index = int(data.get("command_index", 0))
            argv = safe_skill_command(skill_id, command_index)
            result = run_command(argv, timeout=300)
            payload = {
                "skill": skill_id,
                "command": shlex.join(argv),
                "returncode": result.returncode,
                "stdout": result.stdout[-8000:],
                "stderr": result.stderr[-8000:],
            }
            if result.returncode != 0:
                json_response(self, payload, 500)
            else:
                json_response(self, payload)
        else:
            json_response(self, {"error": "not found"}, 404)


class LocalThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True

    def server_bind(self) -> None:
        # Avoid BaseHTTPServer's reverse DNS lookup, which can hang on some local networks.
        self.socket.bind(self.server_address)
        host, port = self.socket.getsockname()[:2]
        self.server_name = str(host)
        self.server_port = int(port)


def main() -> int:
    parser = argparse.ArgumentParser(description="Start the unified stock-analysis workbench.")
    parser.add_argument("--host", default="127.0.0.1", help="Workbench host.")
    parser.add_argument("--port", type=int, default=8788, help="Workbench port.")
    parser.add_argument("--no-deps", action="store_true", help="Do not start dependent web apps.")
    parser.add_argument("--no-vibe", action="store_true", help="Do not start Vibe-Trading frontend preview.")
    parser.add_argument("--open", action="store_true", help="Open the workbench in the default browser.")
    parser.add_argument("--daemon", action="store_true", help="Start the workbench in the background.")
    parser.add_argument("--stop", action="store_true", help="Stop a daemonized workbench.")
    args = parser.parse_args()

    if args.stop:
        return stop_daemon()
    if args.daemon:
        return start_daemon(args)

    workbench = Workbench(include_vibe=not args.no_vibe)
    if not args.no_deps:
        workbench.start_dependencies()

    WorkbenchHandler.workbench = workbench
    server = LocalThreadingHTTPServer((args.host, args.port), WorkbenchHandler)
    url = f"http://{args.host}:{args.port}/"
    print("=" * 56, flush=True)
    print("  A股研究工作台", flush=True)
    print(f"  {url}", flush=True)
    print("=" * 56, flush=True)
    if args.open:
        webbrowser.open(url)

    stop_requested = False

    def request_stop(_signum: int, _frame: Any) -> None:
        nonlocal stop_requested
        if stop_requested:
            return
        stop_requested = True
        print("\n[stop] shutting down workbench...")
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        workbench.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
