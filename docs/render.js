(function () {
  const data = window.UPGRADEPROOF_RESULTS;
  const meta = document.getElementById("meta");
  if (!data) {
    meta.textContent = "No results.js yet. Run: upgradeproof benchmark --out docs";
    return;
  }
  meta.textContent = "Generated " + data.generated_at_asia_calcutta + " on Python " + data.python + ". Elapsed " + data.elapsed_seconds + "s. " + data.limitation;

  const metrics = document.getElementById("metrics");
  metrics.className = "metrics";
  Object.keys(data.metrics).forEach(function (name) {
    const item = data.metrics[name];
    const card = document.createElement("article");
    const rate = item.verified_success_rate == null ? "n/a" : Math.round(item.verified_success_rate * 100) + "%";
    const met = item.expectations_met == null ? "" : item.expectations_met + "/" + item.runs + " expectations met<br>";
    const per = item.cost_per_verified_repair == null ? "n/a" : item.cost_per_verified_repair;
    card.innerHTML = "<strong>" + name + "</strong>" + met + item.verified + "/" + item.runs + " verified verdicts (" + rate + ")<br>" + item.regressions + " delivered regressions<br>" + item.model_calls + " model calls<br>USD " + item.estimated_cost_usd + " / verified " + per;
    metrics.appendChild(card);
  });

  const body = document.querySelector("#cases tbody");
  data.rows.forEach(function (row) {
    const tr = document.createElement("tr");
    const met = row.expectation_met ? "met" : "MISSED";
    const klass = row.expectation_met ? "ok" : "bad";
    [row.case_id, row.cohort, row.mode, row.verdict, String(row.model_calls), String(row.wall_clock_seconds)].forEach(function (value) {
      const td = document.createElement("td");
      td.textContent = value;
      tr.appendChild(td);
    });
    const flag = document.createElement("td");
    flag.textContent = met;
    flag.className = klass;
    tr.appendChild(flag);
    body.appendChild(tr);
  });

  function fill(id, items, label) {
    const list = document.getElementById(id);
    items.forEach(function (item) {
      const li = document.createElement("li");
      li.textContent = (item.ok ? "pass " : "FAIL ") + (item.name || label) + (item.verdict ? " → " + item.verdict : "") + (item.reason ? " (" + item.reason + ")" : "");
      li.className = item.ok ? "ok" : "bad";
      list.appendChild(li);
    });
  }
  fill("probes", data.probes || [], "probe");
  fill("guards", data.guards || [], "guard");

  const promotion = data.promotion || {};
  document.getElementById("promotion").textContent =
    "First encounter " + promotion.first_source + " verified=" + promotion.first_verified + " model_calls=" + promotion.first_model_calls +
    ". Accepted=" + promotion.accepted +
    ". Later " + promotion.later_source + " verified=" + promotion.later_verified + " model_calls=" + promotion.later_model_calls +
    ". The first encounter in this milestone is a scripted proposer, not a neural model.";

  const cpu = data.cpu_model || {};
  document.getElementById("cpu").textContent = "Status: " + cpu.status + (cpu.ran ? ". Verified " + cpu.verified + "/" + cpu.runs + "." : ". Not run in this results file.");
})();
