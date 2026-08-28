// Cash projection, mirrors src/runway/projection.py. Knobs come from window.RUNWAY.
(function () {
  const MONTHS = ["2026-09","2026-10","2026-11","2026-12","2027-01","2027-02","2027-03","2027-04","2027-05","2027-06","2027-07","2027-08"];
  const NAMES = {"01":"Jan","02":"Feb","03":"Mar","04":"Apr","05":"May","06":"Jun","07":"Jul","08":"Aug","09":"Sep","10":"Oct","11":"Nov","12":"Dec"};
  const D = window.RUNWAY;
  const $ = (id) => document.getElementById(id);
  const money = (v) => (v < 0 ? "-" : "") + "$" + Math.round(Math.abs(v)).toLocaleString("en-US");
  const mlabel = (m) => NAMES[m.slice(5, 7)] + " " + m.slice(2, 4);

  function readKnobs() {
    const baseline = {};
    MONTHS.forEach((m) => { baseline[m] = parseFloat($("base-" + m).value) || 0; });
    const one_offs = [];
    ($("one_offs").value || "").split(/\n|,/).forEach((line) => {
      const mt = line.match(/(\d{4}-\d{2})\s*[:= ]\s*\$?\s*([\d.]+)/);
      if (mt) one_offs.push({ month: mt[1], amount: parseFloat(mt[2]) });
    });
    return {
      start_cash: D.start_cash,
      hire_month: $("hire_month").value,
      season_months: $("season_months").value.split(",").map((s) => parseInt(s.trim(), 10)).filter((n) => n >= 1 && n <= 12),
      new_accounts_per_month: parseFloat($("new_accounts_per_month").value) || 0,
      value_per_account: parseFloat($("value_per_account").value) || 0,
      events_multiplier: parseFloat($("events_multiplier").value) || 0,
      baseline, one_offs,
      cogs_pct: parseFloat($("cogs_pct").value) / 100 || 0,
      noncore_pct: parseFloat($("noncore_pct").value) / 100 || 0,
      sales_tax_pct: parseFloat($("sales_tax_pct").value) / 100 || 0,
      overhead_pct: parseFloat($("overhead_pct").value) / 100 || 0,
      overhead_fixed: parseFloat($("overhead_fixed").value) || 0,
      core_actual: D.core_actual,
      core_plan: parseFloat($("core_plan").value) || 0,
      tax_pct: parseFloat($("tax_pct").value) / 100 || 0,
      owner_draws: D.owner_draws,
    };
  }

  function project(k) {
    let cash = k.start_cash, accounts = 0, cumProfit = 0, reserve = 0;
    return MONTHS.map((m) => {
      const inSeason = k.season_months.includes(parseInt(m.slice(5, 7), 10));
      accounts = inSeason ? accounts + k.new_accounts_per_month : 0;
      const wholesale = inSeason ? accounts * k.value_per_account : 0;
      const events = (k.baseline[m] || 0) * k.events_multiplier;
      const one_off = k.one_offs.filter((o) => o.month === m).reduce((s, o) => s + o.amount, 0);
      const revenue = wholesale + events + one_off;
      const core = m >= k.hire_month ? k.core_plan : k.core_actual;
      const burn = revenue * (k.cogs_pct + k.noncore_pct + k.sales_tax_pct + k.overhead_pct) + k.overhead_fixed + core;
      cumProfit += revenue - burn + k.owner_draws;
      const newReserve = Math.max(0, cumProfit) * k.tax_pct;
      const tax = newReserve - reserve;
      reserve = newReserve;
      cash = cash + revenue - burn - tax;
      return { month: m, wholesale, events, one_off, revenue, burn, tax, reserve, cash, core };
    });
  }

  function renderTable(rows) {
    const body = rows.map((r) => `<tr class="${r.cash < 0 ? "neg" : ""}"><td>${mlabel(r.month)}</td><td>${money(r.wholesale)}</td><td>${money(r.events + r.one_off)}</td><td>${money(r.revenue)}</td><td>${money(r.burn)}</td><td>${money(r.tax)}</td><td class="num strong">${money(r.cash)}</td></tr>`).join("");
    $("proj-body").innerHTML = body;
  }

  function renderChart(rows) {
    const W = 760, H = 240, L = 64, R = 16, T = 16, B = 32;
    const vals = rows.map((r) => r.cash).concat([D.start_cash, 0]);
    const lo = Math.min(...vals), hi = Math.max(...vals);
    const pad = (hi - lo) * 0.08 || 1000;
    const y = (v) => T + (H - T - B) * (1 - (v - (lo - pad)) / ((hi + pad) - (lo - pad)));
    const x = (i) => L + ((W - L - R) * i) / (rows.length - 1);
    const pts = rows.map((r, i) => [x(i), y(r.cash)]);
    const path = pts.map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1)).join(" ");
    const area = path + ` L${pts[pts.length - 1][0].toFixed(1)} ${y(lo - pad).toFixed(1)} L${pts[0][0].toFixed(1)} ${y(lo - pad).toFixed(1)} Z`;
    const ticks = [];
    const step = niceStep((hi + pad) - (lo - pad));
    for (let v = Math.ceil((lo - pad) / step) * step; v <= hi + pad; v += step) ticks.push(v);
    const low = rows.reduce((a, r) => (r.cash < a.cash ? r : a), rows[0]);
    const li = rows.indexOf(low);
    let svg = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Projected cash by month">`;
    ticks.forEach((v) => { svg += `<line class="grid" x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}"/><text class="tick" x="${L - 8}" y="${y(v) + 4}" text-anchor="end">${money(v)}</text>`; });
    if (lo - pad < 0) svg += `<rect class="below" x="${L}" y="${y(0)}" width="${W - L - R}" height="${Math.max(0, y(lo - pad) - y(0))}"/>`;
    svg += `<path class="area" d="${area}"/><path class="line" d="${path}"/>`;
    svg += `<line class="zero" x1="${L}" x2="${W - R}" y1="${y(0)}" y2="${y(0)}"/><text class="zerolabel" x="${W - R - 4}" y="${y(0) - 5}" text-anchor="end">$0, out of cash below this line</text>`;
    svg += `<text class="startlabel" x="${x(0)}" y="${y(rows[0].cash) - 10}" text-anchor="start">start ${money(D.start_cash)}</text>`;
    rows.forEach((r, i) => { svg += `<text class="tick" x="${x(i)}" y="${H - 8}" text-anchor="middle">${mlabel(r.month)}</text>`; });
    svg += `<circle class="dot ${low.cash < 0 ? "bad" : ""}" cx="${x(li)}" cy="${y(low.cash)}" r="5"/>`;
    svg += `<g id="scrub" style="display:none"><line class="scrub" x1="0" x2="0" y1="${T}" y2="${H - B}"/><circle class="scrubdot" r="5"/></g>`;
    svg += "</svg>";
    $("proj-chart").innerHTML = svg + `<div class="scrubbox" id="scrubbox"></div>`;
    attachScrub(rows, x, y, W);
    const firstNeg = rows.find((r) => r.cash < 0);
    $("proj-callout").innerHTML = `<span>Lowest cash <strong>${money(low.cash)}</strong> in ${mlabel(low.month)}.</span> ` +
      (firstNeg ? `<span class="bad">Runs out in ${mlabel(firstNeg.month)}.</span>` : `<span class="good">Cash positive through ${mlabel(rows[rows.length - 1].month)}.</span>`);
  }

  function attachScrub(rows, x, y, W) {
    const host = $("proj-chart"), svg = host.querySelector("svg"), g = svg.querySelector("#scrub");
    const line = g.querySelector("line"), dot = g.querySelector("circle"), box = $("scrubbox");
    const show = (clientX) => {
      const r = svg.getBoundingClientRect();
      const vx = ((clientX - r.left) / r.width) * W;
      let i = 0, best = Infinity;
      rows.forEach((_, j) => { const d = Math.abs(x(j) - vx); if (d < best) { best = d; i = j; } });
      const row = rows[i];
      g.style.display = "";
      line.setAttribute("x1", x(i)); line.setAttribute("x2", x(i));
      dot.setAttribute("cx", x(i)); dot.setAttribute("cy", y(row.cash));
      box.innerHTML = `<strong>${mlabel(row.month)}</strong><br>Cash ${money(row.cash)}<br>Revenue ${money(row.revenue)}<br>Burn ${money(row.burn)}`;
      box.style.display = "block";
      const px = (x(i) / W) * r.width;
      box.style.left = Math.min(px + 12, r.width - 170) + "px";
    };
    svg.addEventListener("mousemove", (ev) => show(ev.clientX));
    svg.addEventListener("touchmove", (ev) => { show(ev.touches[0].clientX); ev.preventDefault(); }, { passive: false });
    svg.addEventListener("mouseleave", () => { g.style.display = "none"; box.style.display = "none"; });
  }

  function niceStep(range) {
    const raw = range / 5, mag = Math.pow(10, Math.floor(Math.log10(raw)));
    const n = raw / mag;
    return (n < 1.5 ? 1 : n < 3.5 ? 2.5 : n < 7.5 ? 5 : 10) * mag;
  }

  function renderScenario(rows, k) {
    const tot = rows.reduce((s, r) => s + r.revenue, 0);
    const winter = rows.filter((r) => ["2026-11", "2026-12", "2027-01", "2027-02", "2027-03"].includes(r.month));
    const wAvg = winter.reduce((s, r) => s + r.revenue, 0) / winter.length;
    const peak = rows.reduce((a, r) => (r.revenue > a.revenue ? r : a), rows[0]);
    const burn = rows.reduce((s, r) => s + r.burn, 0) / rows.length;
    const lift = Math.round((k.events_multiplier - 1) * 100);
    const what = k.new_accounts_per_month === 0 && lift === 0
      ? "Nothing changes: revenue repeats 2026 month for month."
      : `${k.new_accounts_per_month} new wholesale account${k.new_accounts_per_month === 1 ? "" : "s"} a month in season at ${money(k.value_per_account)} each` +
        (lift ? `, events up ${lift}% from ads and organic.` : ".");
    const hireIdx = MONTHS.findIndex((m) => m >= k.hire_month);
    const hireTxt = hireIdx < 0 ? "never in this window" : `from ${mlabel(MONTHS[hireIdx])}`;
    $("assume").innerHTML =
      `<li><strong>Revenue:</strong> ${what} That gives ${money(tot)} over the twelve months, ${money(tot / 12)} in an average month, ` +
      `${money(wAvg)} in an average winter month (Nov to Mar), peaking at ${money(peak.revenue)} in ${mlabel(peak.month)}. ` +
      `Wholesale accounts pay only ${k.season_months.length ? "May to Sep" : "never"} and start from zero each spring, per Harrison.</li>` +
      `<li><strong>Starting cash ${money(k.start_cash)}:</strong> Ramp checking minus card charges that will auto pay.</li>` +
      `<li><strong>Costs that move with revenue:</strong> product ${Math.round(k.cogs_pct * 100)}%, event staff ${Math.round(k.noncore_pct * 100)}%, event overhead (travel, rentals, meals, fuel, photographers, supplies) ${Math.round(k.overhead_pct * 100)}%, sales tax remitted ${(k.sales_tax_pct * 100).toFixed(1)}% (revenue is counted with tax in, so it goes back out here). All from May to Aug actuals, so a quiet month costs far less than a busy one.</li>` +
      `<li><strong>Fixed costs:</strong> ${money(k.overhead_fixed)} a month that does not move with events (software, insurance, accounting, ads, storage, ADP fees). Core team ${money(k.core_actual)} a month (what is paid today) until the full plan starts ${hireTxt}, then ${money(k.core_plan)} a month with the Ops Manager and Edy hired and Tim Kosmos on bookkeeping.</li>` +
      `<li><strong>Income tax:</strong> ${Math.round(k.tax_pct * 100)}% of profit set aside as it is earned, since S corp profit is taxed on the owners' returns. Reserve by ${mlabel(rows[rows.length - 1].month)}: ${money(rows[rows.length - 1].reserve)}. Cash on the chart is after this reserve. Tim Kosmos should confirm the rate.</li>` +
      `<li><strong>Result:</strong> average burn ${money(burn)} a month against average revenue ${money(tot / 12)}.</li>`;
    $("scenario").innerHTML =
      `<div><span>Revenue next 12 months</span><strong>${money(tot)}</strong></div>` +
      `<div><span>Average month</span><strong>${money(tot / 12)}</strong></div>` +
      `<div><span>Winter month, Nov to Mar</span><strong>${money(wAvg)}</strong></div>` +
      `<div><span>Peak month</span><strong>${money(peak.revenue)} ${mlabel(peak.month)}</strong></div>` +
      `<div><span>Average burn</span><strong>${money(burn)}</strong></div>` +
      `<div class="what"><span>What this scenario assumes</span><strong>${what}</strong></div>`;
  }

  function run() { const k = readKnobs(); const rows = project(k); renderTable(rows); renderChart(rows); renderScenario(rows, k); }

  function preset(name) {
    const p = D.presets[name];
    $("new_accounts_per_month").value = p.new_accounts_per_month;
    $("events_multiplier").value = p.events_multiplier;
    document.querySelectorAll("[data-preset]").forEach((b) => b.classList.toggle("on", b.dataset.preset === name));
    run();
  }

  document.querySelectorAll("#projection input, #projection textarea, #projection select").forEach((el) => el.addEventListener("input", () => {
    document.querySelectorAll("[data-preset]").forEach((b) => b.classList.remove("on"));
    run();
  }));
  document.querySelectorAll("[data-preset]").forEach((b) => b.addEventListener("click", () => preset(b.dataset.preset)));
  preset("plan");
})();
