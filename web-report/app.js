const data = window.REPORT_DATA || { days: [], weeklies: [], generatedAt: "" };

const state = {
  view: "daily",
  tab: "summary",
  selected: null,
  query: "",
  start: "",
  end: "",
  onlyReviewed: false,
};

const els = {
  generatedAt: document.getElementById("generatedAt"),
  searchInput: document.getElementById("searchInput"),
  startDate: document.getElementById("startDate"),
  endDate: document.getElementById("endDate"),
  onlyReviewed: document.getElementById("onlyReviewed"),
  resetFilters: document.getElementById("resetFilters"),
  dateList: document.getElementById("dateList"),
  resultCount: document.getElementById("resultCount"),
  activeType: document.getElementById("activeType"),
  activeTitle: document.getElementById("activeTitle"),
  copySummary: document.getElementById("copySummary"),
  metrics: document.getElementById("metrics"),
  summaryPanel: document.getElementById("summaryPanel"),
  markdownPanel: document.getElementById("markdownPanel"),
  dataPanel: document.getElementById("dataPanel"),
};

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function fmt(value, fallback = "-") {
  if (value === null || value === undefined || value === "") return fallback;
  if (typeof value === "number") return Number.isInteger(value) ? String(value) : value.toFixed(2);
  return String(value);
}

function hitBadge(hit) {
  if (hit === true) return '<span class="badge good">命中</span>';
  if (hit === false) return '<span class="badge bad">未命中</span>';
  return '<span class="badge">未复盘</span>';
}

function renderMarkdown(markdown) {
  if (!markdown) return '<div class="empty">没有原文内容</div>';

  const lines = markdown.split(/\r?\n/);
  let html = "";
  let inCode = false;
  let listOpen = false;

  function closeList() {
    if (listOpen) {
      html += "</ul>";
      listOpen = false;
    }
  }

  for (let i = 0; i < lines.length; i += 1) {
    const raw = lines[i];
    const line = raw.trimEnd();

    if (line.startsWith("```")) {
      closeList();
      if (inCode) {
        html += "</code></pre>";
        inCode = false;
      } else {
        html += "<pre><code>";
        inCode = true;
      }
      continue;
    }

    if (inCode) {
      html += `${escapeHtml(raw)}\n`;
      continue;
    }

    if (!line.trim()) {
      closeList();
      continue;
    }

    if (/^\|.+\|$/.test(line) && i + 1 < lines.length && /^\|\s*-+/.test(lines[i + 1])) {
      closeList();
      const headers = line.split("|").slice(1, -1).map((cell) => cell.trim());
      i += 2;
      const rows = [];
      while (i < lines.length && /^\|.+\|$/.test(lines[i])) {
        rows.push(lines[i].split("|").slice(1, -1).map((cell) => cell.trim()));
        i += 1;
      }
      i -= 1;
      html += '<div class="table-wrap"><table><thead><tr>';
      html += headers.map((head) => `<th>${inlineMarkdown(head)}</th>`).join("");
      html += "</tr></thead><tbody>";
      html += rows
        .map((row) => `<tr>${row.map((cell) => `<td>${inlineMarkdown(cell)}</td>`).join("")}</tr>`)
        .join("");
      html += "</tbody></table></div>";
      continue;
    }

    const heading = line.match(/^(#{1,3})\s+(.+)$/);
    if (heading) {
      closeList();
      const level = heading[1].length;
      html += `<h${level}>${inlineMarkdown(heading[2])}</h${level}>`;
      continue;
    }

    if (line.startsWith(">")) {
      closeList();
      html += `<blockquote>${inlineMarkdown(line.replace(/^>\s?/, ""))}</blockquote>`;
      continue;
    }

    const bullet = line.match(/^[-*]\s+(.+)$/);
    if (bullet) {
      if (!listOpen) {
        html += "<ul>";
        listOpen = true;
      }
      html += `<li>${inlineMarkdown(bullet[1])}</li>`;
      continue;
    }

    closeList();
    html += `<p>${inlineMarkdown(line)}</p>`;
  }

  closeList();
  if (inCode) html += "</code></pre>";
  return html;
}

function inlineMarkdown(text) {
  let html = escapeHtml(text);
  html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
  html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  return html;
}

function getItems() {
  if (state.view === "weekly") {
    return data.weeklies
      .filter((item) => {
        const text = `${item.title} ${item.markdown}`.toLowerCase();
        return !state.query || text.includes(state.query.toLowerCase());
      })
      .map((item) => ({ type: "weekly", key: item.id, label: item.title, raw: item }));
  }

  return data.days
    .filter((day) => {
      if (state.start && day.date < state.start) return false;
      if (state.end && day.date > state.end) return false;
      if (state.onlyReviewed && !day.hasCloseReview) return false;
      if (state.view === "close" && !day.hasCloseReview) return false;
      if (state.query) {
        const haystack = [
          day.date,
          day.fundFlow?.direction,
          ...(day.mainlines || []).map((x) => x.title),
          ...(day.leaders || []).map((x) => `${x.ticker} ${x.name} ${x.sector}`),
          ...(day.beneficiaries || []).map((x) => `${x.ticker} ${x.name} ${x.sector}`),
          day.dailyMarkdown,
          day.closeMarkdown,
        ]
          .join(" ")
          .toLowerCase();
        if (!haystack.includes(state.query.toLowerCase())) return false;
      }
      return true;
    })
    .map((day) => ({ type: state.view, key: day.date, label: day.date, raw: day }))
    .sort((a, b) => b.key.localeCompare(a.key));
}

function ensureSelection(items) {
  if (items.some((item) => item.key === state.selected)) return;
  state.selected = items[0]?.key || null;
}

function renderList(items) {
  els.resultCount.textContent = `${items.length} 条`;
  if (!items.length) {
    els.dateList.innerHTML = '<div class="empty">没有匹配记录</div>';
    return;
  }

  els.dateList.innerHTML = items
    .map((item) => {
      const day = item.raw;
      const isWeekly = item.type === "weekly";
      const badges = isWeekly
        ? '<span class="badge">周报</span>'
        : [
            day.hasDaily ? '<span class="badge good">日报</span>' : '<span class="badge">日报缺失</span>',
            day.hasCloseReview ? '<span class="badge good">复盘</span>' : '<span class="badge">未复盘</span>',
            day.closeReview?.directionHit === false ? '<span class="badge bad">方向偏差</span>' : "",
          ].join("");
      const subtitle = isWeekly
        ? "周度表现与校准建议"
        : `${day.fundFlow?.direction || "资金方向未记录"} · 主线 ${day.mainlines?.length || 0}`;
      return `
        <button class="date-item ${item.key === state.selected ? "active" : ""}" data-key="${escapeHtml(item.key)}" type="button">
          <span class="date-line"><span>${escapeHtml(item.label)}</span>${!isWeekly ? hitBadge(day.closeReview?.directionHit) : ""}</span>
          <span class="badges">${badges}</span>
          <span class="badge">${escapeHtml(subtitle)}</span>
        </button>
      `;
    })
    .join("");

  els.dateList.querySelectorAll(".date-item").forEach((button) => {
    button.addEventListener("click", () => {
      state.selected = button.dataset.key;
      render();
    });
  });
}

function metric(label, value, detail = "") {
  return `<div class="metric"><span>${escapeHtml(label)}</span><strong>${escapeHtml(fmt(value))}</strong>${detail ? `<p>${escapeHtml(detail)}</p>` : ""}</div>`;
}

function renderMetrics(item) {
  if (!item) {
    els.metrics.innerHTML = "";
    return;
  }
  if (item.type === "weekly") {
    const summary = item.raw.summary?.summaries?.[0] || {};
    els.metrics.innerHTML = [
      metric("周期", item.raw.title),
      metric("复盘天数", summary.review_days),
      metric("方向命中率", summary.direction_hit_rate !== undefined ? `${(summary.direction_hit_rate * 100).toFixed(1)}%` : "-"),
      metric("股票命中率", summary.stock_hit_rate !== undefined ? `${(summary.stock_hit_rate * 100).toFixed(1)}%` : "-"),
    ].join("");
    return;
  }

  const day = item.raw;
  els.metrics.innerHTML = [
    metric("资金方向", day.fundFlow?.direction || "-", day.fundFlow?.quality ? `数据质量：${day.fundFlow.quality}` : ""),
    metric("主线板块", day.mainlines?.length || 0, (day.mainlines || []).slice(0, 3).map((x) => x.title).join(" / ")),
    metric("受益候选", day.beneficiaries?.length || 0, "通过生产机会列门槛"),
    metric(
      "收盘复盘",
      day.hasCloseReview ? (day.closeReview.directionHit ? "方向命中" : "方向偏差") : "未复盘",
      day.closeReview?.averageStockError !== undefined ? `平均偏差：${fmt(day.closeReview.averageStockError)}` : ""
    ),
  ].join("");
}

function renderSummary(item) {
  if (!item) {
    els.summaryPanel.innerHTML = '<div class="empty">请选择一条记录</div>';
    return;
  }
  if (item.type === "weekly") {
    const summary = item.raw.summary?.summaries?.[0];
    const lessons = summary?.lessons || [];
    els.summaryPanel.innerHTML = `
      <div class="section">
        <h3>周度摘要</h3>
        <div class="section-body">
          ${lessons.length ? `<ul>${lessons.map((lesson) => `<li>${escapeHtml(lesson)}</li>`).join("")}</ul>` : '<div class="empty">没有结构化摘要</div>'}
        </div>
      </div>
    `;
    return;
  }

  const day = item.raw;
  els.summaryPanel.innerHTML = `
    <div class="section-grid">
      <div class="section">
        <h3>每日主线</h3>
        <div class="table-wrap">
          <table>
            <thead><tr><th>板块</th><th>分数</th><th>方向</th></tr></thead>
            <tbody>
              ${(day.mainlines || [])
                .map((x) => `<tr><td>${escapeHtml(x.title)}</td><td>${fmt(x.score)}</td><td>${escapeHtml(x.direction || "-")}</td></tr>`)
                .join("") || '<tr><td colspan="3" class="empty">无主线数据</td></tr>'}
            </tbody>
          </table>
        </div>
      </div>
      <div class="section">
        <h3>资金方向</h3>
        <div class="section-body">
          <p><strong>${escapeHtml(day.fundFlow?.direction || "未记录")}</strong></p>
          <p>${escapeHtml(day.fundFlow?.mainFlow || day.fundFlow?.sectorFlow || "无资金摘要")}</p>
          <p>${escapeHtml(day.fundFlow?.pbc || "")}</p>
        </div>
      </div>
      <div class="section">
        <h3>受益候选</h3>
        ${stockTable(day.beneficiaries || [])}
      </div>
      <div class="section">
        <h3>收盘命中</h3>
        ${hitTable(day.closeReview?.stockHits || [])}
      </div>
    </div>
    ${day.closeReview?.lesson ? `<div class="section" style="margin-top:16px"><h3>复盘结论</h3><div class="section-body"><p>${escapeHtml(day.closeReview.lesson)}</p></div></div>` : ""}
  `;
}

function stockTable(rows) {
  if (!rows.length) return '<div class="empty">无入选股票</div>';
  return `
    <div class="table-wrap"><table>
      <thead><tr><th>代码</th><th>名称</th><th>板块</th><th>质量</th><th>风险</th><th>评级</th></tr></thead>
      <tbody>
        ${rows
          .map(
            (x) => `<tr>
              <td>${escapeHtml(x.ticker)}</td>
              <td>${escapeHtml(x.name)}</td>
              <td>${escapeHtml(x.sector)}</td>
              <td>${fmt(x.quality)}</td>
              <td>${fmt(x.risk)}</td>
              <td>${escapeHtml(x.rating || "-")}</td>
            </tr>`
          )
          .join("")}
      </tbody>
    </table></div>
  `;
}

function hitTable(rows) {
  if (!rows.length) return '<div class="empty">无收盘命中数据</div>';
  return `
    <div class="table-wrap"><table>
      <thead><tr><th>标的</th><th>板块</th><th>状态</th><th>收益/级别</th><th>说明</th></tr></thead>
      <tbody>
        ${rows
          .map(
            (x) => `<tr>
              <td>${escapeHtml([x.ticker, x.name].filter(Boolean).join(" ") || x.name)}</td>
              <td>${escapeHtml(x.sector || "-")}</td>
              <td>${hitBadge(x.hit)}</td>
              <td>${escapeHtml(x.level || fmt(x.returnPct))}</td>
              <td>${escapeHtml(x.reason || x.move || "-")}</td>
            </tr>`
          )
          .join("")}
      </tbody>
    </table></div>
  `;
}

function activeItem(items) {
  return items.find((item) => item.key === state.selected) || null;
}

function renderDetail(item) {
  renderMetrics(item);
  renderSummary(item);
  if (!item) {
    els.markdownPanel.innerHTML = '<div class="empty">请选择一条记录</div>';
    els.dataPanel.innerHTML = '<div class="empty">请选择一条记录</div>';
    return;
  }

  if (item.type === "weekly") {
    els.activeType.textContent = "周报";
    els.activeTitle.textContent = item.raw.title;
    els.markdownPanel.innerHTML = renderMarkdown(item.raw.markdown);
    els.dataPanel.innerHTML = `<pre class="json-view"><code>${escapeHtml(JSON.stringify(item.raw.summary || {}, null, 2))}</code></pre>`;
    return;
  }

  const day = item.raw;
  els.activeType.textContent = item.type === "close" ? "收盘复盘" : "日报";
  els.activeTitle.textContent = day.date;
  const markdown = item.type === "close" ? day.closeMarkdown || closeReviewFallbackMarkdown(day) : day.dailyMarkdown;
  els.markdownPanel.innerHTML = renderMarkdown(markdown);
  els.dataPanel.innerHTML = `<pre class="json-view"><code>${escapeHtml(
    JSON.stringify(
      {
        date: day.date,
        fundFlow: day.fundFlow,
        mainlines: day.mainlines,
        beneficiaries: day.beneficiaries,
        closeReview: day.closeReview,
      },
      null,
      2
    )
  )}</code></pre>`;
}

function closeReviewFallbackMarkdown(day) {
  if (!day.hasCloseReview) return "";
  const lines = [`# ${day.date} 收盘复盘`, "", `方向命中：${day.closeReview.directionHit ? "是" : "否"}`];
  if (day.closeReview.lesson) lines.push("", day.closeReview.lesson);
  return lines.join("\n");
}

function render() {
  const items = getItems();
  ensureSelection(items);
  renderList(items);
  renderDetail(activeItem(items));
  document.querySelectorAll(".segmented-btn").forEach((button) => {
    button.classList.toggle("active", button.dataset.view === state.view);
  });
  document.querySelectorAll(".tab").forEach((button) => {
    button.classList.toggle("active", button.dataset.tab === state.tab);
  });
  document.querySelectorAll(".panel").forEach((panel) => {
    panel.classList.toggle("active", panel.id === `${state.tab}Panel`);
  });
}

function resetFilters() {
  state.query = "";
  state.start = "";
  state.end = "";
  state.onlyReviewed = false;
  els.searchInput.value = "";
  els.startDate.value = "";
  els.endDate.value = "";
  els.onlyReviewed.checked = false;
  render();
}

function copySummary() {
  const items = getItems();
  const item = activeItem(items);
  if (!item) return;
  const text = item.type === "weekly"
    ? `${item.raw.title}\n${(item.raw.summary?.summaries?.[0]?.lessons || []).join("\n")}`
    : `${item.raw.date}\n资金方向：${item.raw.fundFlow?.direction || "-"}\n主线：${(item.raw.mainlines || []).map((x) => x.title).join("、")}\n复盘：${item.raw.closeReview?.lesson || "-"}`;
  navigator.clipboard?.writeText(text);
}

function bindEvents() {
  els.searchInput.addEventListener("input", (event) => {
    state.query = event.target.value;
    render();
  });
  els.startDate.addEventListener("input", (event) => {
    state.start = event.target.value;
    render();
  });
  els.endDate.addEventListener("input", (event) => {
    state.end = event.target.value;
    render();
  });
  els.onlyReviewed.addEventListener("change", (event) => {
    state.onlyReviewed = event.target.checked;
    render();
  });
  els.resetFilters.addEventListener("click", resetFilters);
  els.copySummary.addEventListener("click", copySummary);
  document.querySelectorAll(".segmented-btn").forEach((button) => {
    button.addEventListener("click", () => {
      state.view = button.dataset.view;
      state.selected = null;
      render();
    });
  });
  document.querySelectorAll(".tab").forEach((button) => {
    button.addEventListener("click", () => {
      state.tab = button.dataset.tab;
      render();
    });
  });
}

function initDates() {
  if (!data.days.length) return;
  const dates = data.days.map((day) => day.date).sort();
  els.startDate.min = dates[0];
  els.startDate.max = dates[dates.length - 1];
  els.endDate.min = dates[0];
  els.endDate.max = dates[dates.length - 1];
}

els.generatedAt.textContent = data.generatedAt ? `生成于 ${data.generatedAt}` : "未生成数据";
initDates();
bindEvents();
render();
