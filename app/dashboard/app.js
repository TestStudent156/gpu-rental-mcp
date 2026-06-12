// Poll-based dashboard: far more robust than one-shot SSE events — the APPROVE button
// reliably appears whenever an approval is pending, no matter when the page loaded.
const eventsEl = document.getElementById("events");
const approval = document.getElementById("approval");
const approvalText = document.getElementById("approval-text");
let incidentStart = null;

function fmtEvent(ev) {
  if (ev.type === "incident_injected") return `🚨 Incident injected: ${ev.scenario}`;
  if (ev.type === "message") return `${ev.sender}: ${ev.content}`;
  if (ev.type === "action") return `✅ action ${ev.name} → ${JSON.stringify(ev.result)}`;
  if (ev.type === "action_blocked") return `⛔ BLOCKED ${ev.name} — awaiting human approval`;
  if (ev.type === "approval_request") return `🟡 APPROVAL REQUESTED: ${ev.action} on ${ev.service}`;
  if (ev.type === "approval_decided") return `👤 Human ${ev.decision}`;
  return JSON.stringify(ev);
}

async function refreshBoard() {
  const r = await (await fetch("/status")).json();
  const board = document.getElementById("board");
  board.innerHTML = "";
  for (const s of r.services) {
    const d = document.createElement("div");
    d.className = "tile " + s.status;
    d.innerHTML = `<b>${s.name}</b><br>${s.status}<br>err ${(s.error_rate * 100).toFixed(0)}%`;
    board.appendChild(d);
  }
}

async function refreshTimeline() {
  const r = await (await fetch("/timeline")).json();
  eventsEl.innerHTML = "";
  for (const ev of r.events) {
    if (ev.type === "incident_injected" && incidentStart === null) incidentStart = Date.now();
    const li = document.createElement("li");
    li.textContent = fmtEvent(ev);
    eventsEl.prepend(li); // newest on top
  }
  if (r.events.length === 0) incidentStart = null; // timeline cleared (server restarted)
}

async function refreshApproval() {
  const p = await (await fetch("/approval/pending")).json();
  if (p.pending) {
    approval.hidden = false;
    approvalText.textContent = `Approve "${p.action}" on ${p.service}?`;
  } else {
    approval.hidden = true;
  }
}

async function tick() {
  try { await Promise.all([refreshBoard(), refreshTimeline(), refreshApproval()]); } catch (e) {}
}

document.getElementById("approve").onclick = () =>
  fetch("/approval/decide", { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ approved: true }) });
document.getElementById("reject").onclick = () =>
  fetch("/approval/decide", { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ approved: false }) });

setInterval(tick, 1000);
setInterval(() => {
  if (incidentStart) {
    const s = Math.floor((Date.now() - incidentStart) / 1000);
    document.getElementById("mttr").textContent =
      `MTTR ${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
  }
}, 1000);
tick();
