# gpu-rental-mcp

> This is the README of the repository's **original** project — an MCP server for renting vGPUs
> via Shadeform. The repo was later repurposed to host the **War Room** hackathon entry (see the
> top-level [README](../README.md)). This file is kept for reference.

Ein MCP-Server zum Vergleichen und Mieten von vGPUs über **Shadeform** — ein einziger API-Key deckt 30+ Cloud-Provider ab (Lambda Labs, Hyperstack, TensorDock, Crusoe, Nebius, u.v.m.).

## Tools

| Tool | Beschreibung | Kosten |
|---|---|---|
| `list_cheapest_gpus` | Alle verfügbaren GPUs sortiert nach Preis | Kostenlos |
| `filter_by_gpu_type` | Suche nach GPU-Modell (A100, H100, RTX4090…) | Kostenlos |
| `rent_instance` | GPU-Instanz starten | ⚠️ Kostet Geld |
| `list_my_instances` | Alle aktiven Instanzen anzeigen | Kostenlos |
| `get_instance_info` | Details + SSH-Zugang einer Instanz | Kostenlos |
| `stop_instance` | Instanz beenden (Abrechnung stoppt) | ⚠️ Irreversibel |

Alle destruktiven/kostenpflichtigen Tools haben einen `confirm: true` Safety-Gate.

## Setup

### 1. API-Key holen
Registriere dich auf [platform.shadeform.ai](https://platform.shadeform.ai) und erstelle einen API-Key.

### 2. Build
```bash
npm install
npm run build
```

### 3. In Claude Desktop einbinden
Füge das in `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) hinzu:

```json
{
  "mcpServers": {
    "gpu-rental": {
      "command": "node",
      "args": ["/ABSOLUTER/PFAD/gpu-rental-mcp/dist/index.js"],
      "env": {
        "SHADEFORM_API_KEY": "dein-api-key-hier"
      }
    }
  }
}
```

### 4. In n8n einbinden (MCP Client Node)
n8n hat einen eingebauten **MCP Client Node**. Starte den Server als HTTP-Prozess oder nutze
den stdio-Transport über einen Wrapper:

```bash
# Server als HTTP-Wrapper starten (für n8n):
SHADEFORM_API_KEY=xxx node dist/index.js
```

Alternativ: Den MCP Server in n8n über `Execute Command` oder als subprocess einbinden.

### 5. In Cursor / Windsurf
Gleiche Config-Struktur wie Claude Desktop, nur andere Pfade:
- Cursor: `.cursor/mcp.json` im Projekt oder `~/.cursor/mcp.json` global
- Windsurf: `~/.codeium/windsurf/mcp_config.json`

## Beispiel-Prompts

```
"Zeig mir die 5 günstigsten verfügbaren H100 GPUs"

"Ich brauche eine A100 mit mindestens 80GB VRAM für max. $3/Stunde"

"Starte eine RTX4090-Instanz mit dem vLLM Docker Image"

"Zeig mir alle meine aktiven GPU-Instanzen und wie viel sie bisher gekostet haben"

"Beende Instanz abc123"
```

## Umgebungsvariablen

| Variable | Pflicht | Beschreibung |
|---|---|---|
| `SHADEFORM_API_KEY` | ✅ | Shadeform API-Key |

## Shadeform Provider-Abdeckung

Shadeform aggregiert aktuell 30+ Cloud-Provider, darunter:
Lambda Labs, Hyperstack, TensorDock, Crusoe Energy, Nebius, CoreWeave (via Shadeform),
Vast.ai, RunPod, und weitere — alles über eine einzige API.

**Free Tier:** 10 API-Anfragen/Tag, 1 GPU-Instanz max, 5 Tage max-Laufzeit
**Paid Tier:** Unbegrenzte API-Anfragen, 100 parallele Instanzen, keine Laufzeitbegrenzung

## Sicherheitshinweise

- API-Key niemals in Logs oder Ausgaben ausgeben
- `rent_instance` und `stop_instance` erfordern immer `confirm: true`
- Prüfe den Preis mit `list_cheapest_gpus` vor dem Mieten
- Instanzen laufen und kosten Geld bis du `stop_instance` aufrufst
