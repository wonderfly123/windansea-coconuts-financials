"use strict";

const BUCKETS = [
  "Revenue", "Operating Expense", "Payroll",
  "Owner Pay", "Owner Draw", "Excluded"
];

let trendChart = null;
let allMonths = [];

function money(v) {
  const r = Math.round(v || 0);
  const abs = Math.abs(r).toLocaleString("en-US");
  return r < 0 ? "($" + abs + ")" : "$" + abs;
}

function pct(v) {
  return Math.round((v || 0) * 100) + "%";
}

function square(key, value, cls, tip) {
  const c = cls ? " " + cls : "";
  const t = tip ? ' data-tip="' + tip.replace(/"/g, "&quot;") + '"' : "";
  const mark = tip ? ' <span style="opacity:0.45">&#9432;</span>' : "";
  return '<div class="square"' + t + '><div class="k">' + key + mark +
    '</div><div class="v' + c + '">' + value + "</div></div>";
}

const TIPS = {
  cash: "Live cash on hand right now. Your Mercury account balances plus the Ramp balance, as of the last data pull.",
  net: "Average monthly net over the selected month window. Revenue minus all cash out (operating expenses, payroll, owner pay, owner draws). Green when positive, red when negative.",
  runway: "If you are burning cash, how many months your current cash lasts at the average monthly burn. If profitable, how fast cash is growing per month.",
  revytd: "Total revenue collected year to date, January 1 through today. Square sales plus company payments. Includes the partial current month.",
  rev: "Average monthly revenue over the selected window.",
  exp: "Average monthly expenses over the selected window. Includes operating costs, payroll, and Harrison's pay and distributions, since he runs the business. Jordan's owner pay and draws are NOT included here, they are shown in the Owner Compensation panel. Note. May runs high because Harrison paid down his personal debt that month, his Chase and Amex cards and his Chase checking, about $15,500 of distributions that all landed in May.",
  margin: "Share of revenue kept after money out, computed as (average revenue minus average expenses) divided by average revenue over the selected window. Money out here is operating costs, payroll, and Harrison's pay. Jordan's owner pay and draws are not subtracted, so this runs a bit higher than a full bottom line.",
  ytd: "Net for the year so far, January 1 through today. Total revenue minus all cash out. A running total, so it includes the partial current month.",
  cotw: "Money expected to arrive soon, such as unpaid invoices. Left as TBD because it cannot be pulled reliably from the connected accounts."
};

function renderSquares(d) {
  document.getElementById("squares").innerHTML = [
    square("Current Cash", money(d.current_cash), "green", TIPS.cash),
    square("Revenue YTD", money(d.ytd.revenue), "green", TIPS.revytd),
    square("Revenue avg", money(d.revenue_avg), "", TIPS.rev),
    square("Expenses avg", money(d.expense_avg), "", TIPS.exp),
    square("Margin", pct(d.margin), d.margin >= 0 ? "green" : "red", TIPS.margin),
    square("Cash on the Way", d.cash_on_the_way, "", TIPS.cotw)
  ].join("");
}

function renderTakeaways(list) {
  document.getElementById("takeaways").innerHTML =
    list.map(function (t) { return "<li>" + t + "</li>"; }).join("");
}

function renderOwner(o) {
  document.getElementById("jCar").textContent = money(o.jordan.capital_one);
  document.getElementById("jDraw").textContent = money(o.jordan.bofa_draw);
  document.getElementById("jTotal").textContent = money(o.jordan.total);
  document.getElementById("hW2").textContent = money(o.harrison.adp_w2);
  document.getElementById("hDirect").textContent = money(o.harrison.direct);
  document.getElementById("hTotal").textContent = money(o.harrison.total);
}

function renderCategories(cats) {
  const max = cats.reduce(function (m, c) { return Math.max(m, c.amount); }, 0) || 1;
  document.getElementById("categories").innerHTML = cats.map(function (c) {
    const w = Math.max(2, Math.round((c.amount / max) * 200));
    return '<div class="cat-row"><span class="cat-name">' + c.category +
      '</span><span class="cat-bar" style="width:' + w + 'px"></span>' +
      '<span class="cat-amt">' + money(c.amount) + "</span></div>";
  }).join("");
}

function renderTrend(monthly) {
  const labels = monthly.map(function (m) {
    return m.is_partial ? m.month + " (partial)" : m.month;
  });
  const partialIdx = monthly.map(function (m, i) { return m.is_partial ? i : -1; })
    .filter(function (i) { return i >= 0; });

  function dash(ctx) {
    return partialIdx.indexOf(ctx.p1DataIndex) >= 0 ? [6, 4] : undefined;
  }
  function pointR(ctx) {
    return monthly[ctx.dataIndex] && monthly[ctx.dataIndex].is_partial ? 6 : 3;
  }

  const series = [
    { label: "Revenue", color: "#2ecc71", key: "revenue" },
    { label: "Expenses", color: "#e74c3c", key: "expense" }
  ];
  const datasets = series.map(function (s) {
    return {
      label: s.label,
      data: monthly.map(function (m) { return m[s.key]; }),
      borderColor: s.color,
      backgroundColor: s.color,
      tension: 0.25,
      pointRadius: pointR,
      segment: { borderDash: dash }
    };
  });

  if (trendChart) { trendChart.destroy(); }
  trendChart = new Chart(document.getElementById("trend"), {
    type: "line",
    data: { labels: labels, datasets: datasets },
    options: {
      responsive: true,
      plugins: { legend: { labels: { color: "#e6edf3" } } },
      scales: {
        x: { ticks: { color: "#8b97a7" }, grid: { color: "#2a333f" } },
        y: { ticks: { color: "#8b97a7" }, grid: { color: "#2a333f" } }
      }
    }
  });
}

function populateMonthSelectors(monthly, start, end) {
  allMonths = monthly.map(function (m) { return m.month; });
  const startSel = document.getElementById("startSel");
  const endSel = document.getElementById("endSel");
  const opts = allMonths.map(function (m) {
    return '<option value="' + m + '">' + m + "</option>";
  }).join("");
  startSel.innerHTML = opts;
  endSel.innerHTML = opts;
  startSel.value = allMonths.indexOf(start) >= 0 ? start : allMonths[0];
  endSel.value = allMonths.indexOf(end) >= 0 ? end : allMonths[allMonths.length - 1];
}

function loadSummary(start, end, isFirst) {
  var url = "/api/summary";
  if (start && end) { url += "?start=" + start + "&end=" + end; }
  fetch(url)
    .then(function (r) { return r.json(); })
    .then(function (d) {
      renderSquares(d);
      renderOwner(d.owner_comp);
      renderCategories(d.categories);
      renderTrend(d.monthly);
      // On first load the server picks the default window; sync the selectors to it.
      if (isFirst) { populateMonthSelectors(d.monthly, d.start, d.end); }
    });
}

function renderTxns(rows) {
  document.getElementById("txnBody").innerHTML = rows.map(function (r) {
    const cls = r.amount >= 0 ? "pos" : "neg";
    return "<tr><td>" + (r.date || "") + "</td><td>" + (r.source || "") +
      "</td><td>" + (r.counterparty || "") + "</td><td>" + (r.category || "") +
      '</td><td class="num ' + cls + '">' + money(r.amount) + "</td><td>" +
      (r.bucket || "") + "</td><td>" + (r.flag || "") + "</td><td>" +
      (r.review || "") + "</td></tr>";
  }).join("");
}

function loadTxns() {
  const q = document.getElementById("txnSearch").value;
  const bucket = document.getElementById("txnBucket").value;
  fetch("/api/transactions?q=" + encodeURIComponent(q) + "&bucket=" + encodeURIComponent(bucket))
    .then(function (r) { return r.json(); })
    .then(renderTxns);
}

function escapeHtml(s) {
  return (s || "").replace(/[&<>"']/g, function (c) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
  });
}

function renderQuestions(items) {
  document.getElementById("qList").innerHTML = items.map(function (it) {
    return "<li><span class='qmeta'>" + escapeHtml((it.created_at || "").slice(0, 16)) +
      "</span><span class='qtext'>" + escapeHtml(it.text) +
      "</span><button class='del' data-id='" + it.id + "' title='Delete'>&times;</button></li>";
  }).join("");
}

function loadQuestions() {
  fetch("/api/questions").then(function (r) { return r.json(); }).then(renderQuestions);
}

function saveQuestion() {
  var el = document.getElementById("qInput");
  var t = el.value.trim();
  if (!t) { return; }
  fetch("/api/questions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text: t })
  }).then(function () { el.value = ""; loadQuestions(); });
}

function init() {
  document.getElementById("txnBucket").innerHTML +=
    BUCKETS.map(function (b) { return '<option value="' + b + '">' + b + "</option>"; }).join("");

  loadSummary(null, null, true);
  loadTxns();

  document.getElementById("startSel").addEventListener("change", function () {
    loadSummary(this.value, document.getElementById("endSel").value, false);
  });
  document.getElementById("endSel").addEventListener("change", function () {
    loadSummary(document.getElementById("startSel").value, this.value, false);
  });
  document.getElementById("txnSearch").addEventListener("input", loadTxns);
  document.getElementById("txnBucket").addEventListener("change", loadTxns);

  // Questions / Notes
  loadQuestions();
  document.getElementById("qSave").addEventListener("click", saveQuestion);
  document.getElementById("qInput").addEventListener("keydown", function (e) {
    if (e.key === "Enter") { saveQuestion(); }
  });
  document.getElementById("qList").addEventListener("click", function (e) {
    var btn = e.target.closest("button.del");
    if (!btn) { return; }
    fetch("/api/questions/" + btn.getAttribute("data-id"), { method: "DELETE" })
      .then(loadQuestions);
  });

  // Click a square to pin its tooltip open (hover also shows it).
  document.getElementById("squares").addEventListener("click", function (e) {
    const sq = e.target.closest(".square[data-tip]");
    const wasOpen = sq && sq.classList.contains("tip-open");
    this.querySelectorAll(".tip-open").forEach(function (el) {
      el.classList.remove("tip-open");
    });
    if (sq && !wasOpen) { sq.classList.add("tip-open"); }
  });

  // Click to pin the Owner Comp line tooltip (hover also shows it).
  document.addEventListener("click", function (e) {
    var line = e.target.closest(".owner .line[data-tip]");
    document.querySelectorAll(".owner .line.tip-open").forEach(function (el) {
      if (el !== line) { el.classList.remove("tip-open"); }
    });
    if (line) { line.classList.toggle("tip-open"); }
  });
}

document.addEventListener("DOMContentLoaded", init);
