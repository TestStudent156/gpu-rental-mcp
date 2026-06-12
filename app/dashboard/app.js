const es = new EventSource("/events");
const events = document.getElementById("events");
const approval = document.getElementById("approval");
const approvalText = document.getElementById("approval-text");
let incidentStart = null;

function addEvent(text) {
  const li = document.createElement("li");
  li.textContent = `${new Date().toLocaleTimeString()} — ${text}`;
  events.prepend(li);
}

async function refreshBoard() {
  const r = await (await fetch("/status")).json();
  const board = document.getElementById("board");
  board.innerHTML = "";
  for (const s of r.services) {
    const d = document.createElement("div");
    d.className = "tile " + s.status;
    d.innerHTML = `<b>${s.name}</b><br>${s.status}<br>err ${(s.error_rate*100).toFixed(0)}%`;
    board.appendChild(d);
  }
}

es.onmessage = (e) => {
  const ev = JSON.parse(e.data);
  if (ev.type === "incident_injected") { incidentStart = Date.now(); addEvent(`Incident: ${ev.scenario}`); }
  if (ev.type === "message") addEvent(`${ev.sender}: ${ev.content}`);
  if (ev.type === "action") addEvent(`action ${ev.name} → ${JSON.stringify(ev.result)}`);
  if (ev.type === "approval_request") {
    approval.hidden = false;
    approvalText.textContent = `Approve ${ev.action} on ${ev.service}?`;
  }
  if (ev.type === "approval_decided") { approval.hidden = true; addEvent(`Human ${ev.decision}`); }
  refreshBoard();
};

document.getElementById("approve").onclick = () =>
  fetch("/approval/decide", {method:"POST", headers:{"Content-Type":"application/json"},
        body: JSON.stringify({approved:true})});
document.getElementById("reject").onclick = () =>
  fetch("/approval/decide", {method:"POST", headers:{"Content-Type":"application/json"},
        body: JSON.stringify({approved:false})});

setInterval(() => {
  if (incidentStart) {
    const s = Math.floor((Date.now()-incidentStart)/1000);
    document.getElementById("mttr").textContent =
      `MTTR ${String(Math.floor(s/60)).padStart(2,"0")}:${String(s%60).padStart(2,"0")}`;
  }
}, 1000);
refreshBoard();
