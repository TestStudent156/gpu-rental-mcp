"""Generate the War Room submission slide deck as a 16:9 PDF (reportlab, no browser)."""
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor

W, H = 1280, 720
NAVY  = HexColor("#0B1220")
PANEL = HexColor("#15213B")
WHITE = HexColor("#F8FAFC")
GRAY  = HexColor("#9FB3C8")
AMBER = HexColor("#FBBF24")
RED   = HexColor("#F43F5E")
GREEN = HexColor("#34D399")
BLUE  = HexColor("#60A5FA")

c = canvas.Canvas(str(__import__("pathlib").Path(__file__).with_name("WarRoom_Slides.pdf")),
                  pagesize=(W, H))


def bg():
    c.setFillColor(NAVY); c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setFillColor(AMBER); c.rect(0, 0, 10, H, fill=1, stroke=0)  # left accent rail


def footer(n):
    c.setFont("Helvetica", 12); c.setFillColor(GRAY)
    c.drawString(64, 34, "War Room  ·  Band of Agents")
    c.drawRightString(W - 60, 34, f"{n}/10")


def kicker(text):
    c.setFont("Helvetica-Bold", 15); c.setFillColor(AMBER)
    c.drawString(64, H - 96, text.upper())


def title(text, size=42, y=H - 156):
    c.setFont("Helvetica-Bold", size); c.setFillColor(WHITE)
    c.drawString(64, y, text)
    c.setFillColor(AMBER); c.rect(66, y - 18, 90, 5, fill=1, stroke=0)


def bullets(items, y0=H - 230, gap=58, size=21):
    y = y0
    for it in items:
        c.setFillColor(AMBER); c.circle(78, y + 6, 4.5, fill=1, stroke=0)
        c.setFont("Helvetica", size); c.setFillColor(WHITE if it[0] == "*" else GRAY)
        c.drawString(98, y, it[1:] if it[0] == "*" else it)
        y -= gap


def mono_panel(lines, x=64, y=120, w=W - 128, h=380, pad=26, lh=34, size=16):
    c.setFillColor(PANEL); c.roundRect(x, y, w, h, 14, fill=1, stroke=0)
    ty = y + h - pad - lh * 0.2
    for text, col in lines:
        c.setFont("Courier-Bold" if col in (RED, GREEN, AMBER) else "Courier", size)
        c.setFillColor(col); c.drawString(x + pad, ty, text); ty -= lh


def newpage(n):
    footer(n); c.showPage()


# ---- 1. Title ----------------------------------------------------------------
bg()
c.setFillColor(RED); c.setFont("Helvetica-Bold", 22); c.drawString(64, H - 150, "🚨".encode("ascii", "ignore").decode() or "")
c.setFillColor(WHITE); c.setFont("Helvetica-Bold", 92); c.drawString(60, H - 300, "WAR ROOM")
c.setFillColor(AMBER); c.rect(66, H - 330, 160, 7, fill=1, stroke=0)
c.setFillColor(WHITE); c.setFont("Helvetica-Bold", 30)
c.drawString(64, H - 392, "A band of AI agents that runs your incident response")
c.setFillColor(GRAY); c.setFont("Helvetica", 22)
c.drawString(64, H - 432, "Coordinated entirely through Band — with a human holding the only key.")
c.setFillColor(BLUE); c.setFont("Helvetica-Bold", 18)
c.drawString(64, 150, "lablab.ai  ·  Band of Agents Hackathon")
c.setFillColor(GRAY); c.setFont("Helvetica", 16)
c.drawString(64, 120, "github.com/TestStudent156/gpu-rental-mcp")
newpage(1)

# ---- 2. Problem --------------------------------------------------------------
bg(); kicker("The problem"); title("Incident response is a coordination problem")
bullets([
    "*The hard part isn't any single decision — it's the handoffs.",
    "Who investigates?  Who's allowed to act?  Who tells stakeholders?",
    "Who makes sure a bot doesn't roll back the wrong thing?",
    "*Most AI-agent demos hard-wire the handoffs into a central orchestrator.",
    "That orchestrator IS the product — the agents are just function calls.",
])
newpage(2)

# ---- 3. Solution / agents ----------------------------------------------------
bg(); kicker("The solution"); title("Six participants.  One Band room.")
rows = [
    ("Detector",      "watches metrics, raises the alert",            "non-LLM", BLUE),
    ("Commander",     "opens the incident, delegates, declares done", "LLM",     AMBER),
    ("Diagnostician", "pulls metrics / logs / deploys, finds cause",  "LLM",     AMBER),
    ("Remediator",    "proposes the fix; runs it only after approval","LLM",     AMBER),
    ("Comms",         "posts plain-English status updates",           "LLM",     AMBER),
    ("Bridge",        "mirrors room to dashboard, relays approval",   "non-LLM", BLUE),
]
y = H - 250
for name, role, kind, col in rows:
    c.setFillColor(col); c.setFont("Helvetica-Bold", 22); c.drawString(80, y, name)
    c.setFillColor(GRAY); c.setFont("Helvetica", 19); c.drawString(360, y, role)
    c.setFillColor(col); c.setFont("Helvetica-Oblique", 16); c.drawRightString(W - 80, y, kind)
    y -= 62
newpage(3)

# ---- 4. The cascade ----------------------------------------------------------
bg(); kicker("One incident, start to finish"); title("Detect · Diagnose · Block · Approve · Heal")
mono_panel([
    ("Detector      ->  @commander    ALERT checkout error_rate 42%",      WHITE),
    ("Commander     ->  @diagnostician investigate  +  @comms update",     WHITE),
    ("Diagnostician ->  root cause: deploy dpl-104, NullPointer",          WHITE),
    ("Remediator    ->  rollback dpl-104        [ BLOCKED - need human ]",  RED),
    ("Commander     ->  APPROVAL REQUESTED: rollback dpl-104 on checkout",  AMBER),
    ("                  -- human clicks  APPROVE --",                      AMBER),
    ("Server        ->  rollback dpl-104        [ OK ] checkout healthy",   GREEN),
    ("Commander     ->  INCIDENT RESOLVED",                                GREEN),
], y=170, h=360)
c.setFillColor(GRAY); c.setFont("Helvetica-Oblique", 17)
c.drawString(64, 120, "End-to-end in under a minute — every line is a real Band message.")
newpage(4)

# ---- 5. Band is the coordination layer --------------------------------------
bg(); kicker("Our core bet"); title("Band is the only channel")
bullets([
    "*No orchestrator. No message bus. No shared memory.",
    "Every handoff is a Band message with @mentions — agents act only when mentioned.",
    "The workflow emerges from who addresses whom, like a real on-call channel.",
    "*Humans and bots are first-class peers — 2 of the 6 agents are plain Python.",
    "Even governance flows through the room: the human's decision is a Band message.",
])
newpage(5)

# ---- 6. Human gate -----------------------------------------------------------
bg(); kicker("Governance that's real"); title("The human gate is unskippable")
bullets([
    "*Rollback / restart / scale are refused at the action layer until a human approves.",
    "No prompt can bypass it — it's enforced in code, not in instructions.",
    "Blocked attempts show on the timeline as visible proof of the gate.",
], y0=H - 230, gap=56)
mono_panel([
    ("[ BLOCKED ]  rollback dpl-104   -- awaiting human approval", RED),
    ("[ HUMAN   ]  operator clicks APPROVE on the dashboard",      AMBER),
    ("[ OK      ]  rollback dpl-104   -> checkout healthy",        GREEN),
], y=120, h=180, lh=42, size=17)
newpage(6)

# ---- 7. Dashboard ------------------------------------------------------------
bg(); kicker("Clarity of presentation"); title("A live ops dashboard")
bullets([
    "*Service status board — health flips red to green as the incident resolves.",
    "Live timeline — the Band conversation and blocked actions, streaming in.",
    "APPROVE / REJECT — the single human action, front and center.",
    "MTTR — time from alert to resolved, ticking live.",
])
newpage(7)

# ---- 8. Architecture ---------------------------------------------------------
bg(); kicker("Architecture"); title("How it fits together")
def box(x, y, w, h, head, sub, col):
    c.setFillColor(PANEL); c.roundRect(x, y, w, h, 12, fill=1, stroke=0)
    c.setStrokeColor(col); c.setLineWidth(2); c.roundRect(x, y, w, h, 12, fill=0, stroke=1)
    c.setFillColor(col); c.setFont("Helvetica-Bold", 20); c.drawString(x + 24, y + h - 38, head)
    c.setFillColor(GRAY); c.setFont("Helvetica", 15); c.drawString(x + 24, y + 20, sub)
def arrow(x, y0, y1):
    c.setStrokeColor(GRAY); c.setLineWidth(2); c.line(x, y0, x, y1)
    c.setFillColor(GRAY)
    c.line(x, y1, x - 6, y1 + 12); c.line(x, y1, x + 6, y1 + 12)
box(120, 430, 760, 110, "BAND ROOM",
    "commander  ·  diagnostician  ·  remediator  ·  comms   (talk only via @mentions)", AMBER)
box(940, 430, 220, 110, "Detector", "raises the alert", BLUE)
arrow(500, 430, 372)
box(120, 250, 760, 110, "Bridge   (non-LLM)",
    "mirrors the room to the dashboard  ·  relays the human's approval back in", BLUE)
arrow(500, 250, 192)
box(120, 70, 760, 110, "FastAPI server",
    "MockOps sim  ·  action-layer approval gate  ·  dashboard (status, timeline, APPROVE, MTTR)", GREEN)
newpage(8)

# ---- 9. Tech stack -----------------------------------------------------------
bg(); kicker("Built with"); title("Tech stack")
chips = ["Band SDK", "Python", "Featherless AI", "Qwen2.5-14B", "FastAPI", "SSE / polling", "HTML / JS"]
x, y = 80, H - 280
for ch in chips:
    w = 36 + len(ch) * 12
    c.setFillColor(PANEL); c.roundRect(x, y, w, 50, 10, fill=1, stroke=0)
    c.setFillColor(WHITE); c.setFont("Helvetica-Bold", 19); c.drawCentredString(x + w / 2, y + 16, ch)
    x += w + 22
    if x > W - 200:
        x = 80; y -= 74
c.setFillColor(GRAY); c.setFont("Helvetica", 20)
c.drawString(80, 230, "Each agent is a plain LLM tool-loop — no agent framework.")
c.drawString(80, 196, "1-unit model lets all four reasoning agents run in parallel.")
newpage(9)

# ---- 10. Closing -------------------------------------------------------------
bg()
c.setFillColor(WHITE); c.setFont("Helvetica-Bold", 80); c.drawString(60, H - 280, "War Room")
c.setFillColor(AMBER); c.rect(66, H - 308, 150, 6, fill=1, stroke=0)
c.setFillColor(WHITE); c.setFont("Helvetica", 28)
c.drawString(64, H - 372, "A band of agents — and a human — running a real operation together.")
c.setFillColor(AMBER); c.setFont("Helvetica-Bold", 24)
c.drawString(64, H - 420, "Coordinated entirely through Band.")
c.setFillColor(GRAY); c.setFont("Helvetica", 18)
c.drawString(64, 150, "github.com/TestStudent156/gpu-rental-mcp")
newpage(10)

c.save()
print("wrote", str(__import__("pathlib").Path(__file__).with_name("WarRoom_Slides.pdf")))
