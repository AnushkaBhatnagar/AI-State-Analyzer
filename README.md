# AI State Analyzer & Panel Generator

Anushka's Note: There are some test vibe-coded examples in the `tests` folder. Just copy-paste that code into `index.html` to run the experience each time. The commands below should be helpful!

Turn any interactive HTML experience into a fully instrumented, state-aware experience with visual debugging panels, jump-to-state navigation, flow diagrams, and aesthetics/strategy analysis.

## Quick Start

### 1. Install Dependencies
```bash
pip install google-generativeai python-dotenv flask flask-cors watchdog
```
Set a `GOOGLE_API_KEY` in your environment or `.env` file.

### 2. Generate the Panel
```bash
python generate_state_panel.py index.html
```
This runs AI analysis and outputs `index_with_panel.html` + `states_schema.json`.

### 3. View the Result
(Anushka's Note: Use Option B for Testing)
```bash
# Option A: Simple static server
python server.py

# Option B: Dev server with live reload + file watching
python dev_server.py
```
Both open `index_with_panel.html` in your browser with the **State Progression Panel** on the right side.

---

## Optional Features

These are opt-in flags on `generate_state_panel.py`:

### Jump Codes (`--jump-code`)
Generates `jump-states/state_jumper.js` — AI-written JavaScript that adds "Jump" buttons to each state card in the panel. Load the script in DevTools to instantly teleport the experience to any state.

### Flow Diagram (`--flow-diagram`)
Generates a Mermaid-based state flow diagram showing transitions between states:
- `state-flow-diagram/state_flow_diagram.js` — diagram data
- `state-flow-diagram/state_flow_map.html` — standalone visual flow map

### Layers Analysis (on by default)
Runs an aesthetics + strategy analysis on each state using AI. Identifies the emotional arc, narrative structure, user role, and design strategy behind each state. Generates:
- `layer/layers_schema.json` — layers analysis schema
- `layers.html` — side-by-side view of state panel + aesthetics + strategy panels

Skip with `--skip-layers`, or run standalone with `--layers-only`.

### Enable Everything
```bash
python generate_state_panel.py index.html --jump-code --flow-diagram
```

---

## System Architecture

### 1. The Orchestrator: `generate_state_panel.py`
Main entry point. Coordinates the entire pipeline:
1. Calls **The Brain** (`state_analyzer.py`) to analyze your code.
2. Takes the resulting blueprint (`states_schema.json`).
3. Calls **The Builder** (`panel_generator.py`) to generate the final HTML.
4. Optionally generates jump codes, flow diagrams, and layers analysis.

Supports two modes:
```bash
# Full analysis from scratch (default)
python generate_state_panel.py index.html

# Incremental analysis (updates existing schema — faster, cheaper)
python generate_state_panel.py index.html --mode incremental
```

### 2. The Brain: `state_analyzer.py` (AI Agent)
Uses Google Gemini to act as an expert code analyst.
- **State Detection**: Identifies distinct behavioral states (e.g., "Intro", "Game Over", "Loading").
- **Logic Extraction**: Figures out the exact JavaScript conditions that trigger each state.
- **Asset Identification**: Finds interactive elements and key variables relevant to each state.
- **Hook Discovery**: Identifies where in your code variables change, so we can instrument them.
- **Jump Code Generation**: Writes JavaScript to transition directly to any state.
- **Flow Diagram Generation**: Produces Mermaid flowcharts showing state transitions.
- **Output**: `states_schema.json` — a structured blueprint of your application's logic.

Two analysis methods:
- **Full** (`detect_states`): Analyzes code from scratch. Use for first run or major rewrites.
- **Incremental** (`update_states`): Sends existing schema + new code to AI. Preserves state IDs, only updates what changed. Faster and cheaper.

### 3. The Builder: `panel_generator.py` (Code Generator)
Takes the AI's blueprint and programmatically constructs the debugging tools.
- **Code Injection**: Inserts a Runtime Monitor (`window.__ai_state_monitor`) into your HTML, using the hooks found by the AI to inject reporting lines right after variables change.
- **Panel Construction**: Builds the HTML/CSS for the side panel, creating a section for each state.
- **Logic Embedding**: Embeds JavaScript logic to constantly evaluate trigger conditions and update the panel in real-time.
- **Re-Analysis Toolbar**: Adds buttons to trigger re-analysis directly from the panel UI.
- **Output**: `index_with_panel.html`

### 4. The Layers Analyzer: `layer/layers.py`
Uses Google Gemini to analyze the aesthetics and strategy of each state.
- **Emotion Analysis**: Identifies the intended emotional arc across states.
- **Strategy Extraction**: Maps narrative structure, user roles, directives, and choices per state.
- **Output**: `layer/layers_schema.json`

### 5. The Layers Panel Builder: `layer/layers_panel_generator.py`
Generates `layers.html` — a combined view with the state panel alongside aesthetics and strategy panels.

---

## Dev Server: `dev_server.py`

A Flask-based development server with file watching, live reload, and auto re-analysis.

```bash
python dev_server.py                # Start on port 8000
python dev_server.py --port 8080    # Custom port
python dev_server.py --no-watch     # Disable file watching
python dev_server.py --debounce 5   # 5 second debounce
python dev_server.py --no-browser   # Don't auto-open browser
```

### How it works
- **File watcher**: Monitors `index.html` for changes using `watchdog` (2s debounce by default)
- **Auto re-analysis**: When `index.html` changes, automatically runs incremental AI analysis and regenerates the panel
- **Live reload**: Uses Server-Sent Events (SSE) to auto-reload the browser when analysis completes
- **Panel toolbar**: The generated panel includes buttons for:
  - **Incremental Analysis** — context-aware update using existing schema (~15-25s)
  - **Full Analysis** — from-scratch AI analysis (~20-30s)
  - **Quick Regen** — regenerate panel from existing schema (no AI call)

### API Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/reanalyze` | Trigger re-analysis. Body: `{"mode": "incremental"}` or `{"mode": "full"}` |
| `POST` | `/api/quick-regen` | Fast panel regeneration (no AI call) |
| `GET` | `/api/status` | Check current analysis status |
| `GET` | `/api/events` | SSE stream for live reload notifications |

### Workflow with a coding agent
1. Start the dev server: `python dev_server.py`
2. Open `http://localhost:8000/index_with_panel.html`
3. Copy state info from the panel, paste it into your coding agent (e.g., Claude Code) as context
4. Agent edits `index.html` — the dev server detects the change, re-analyzes, and live-reloads the panel automatically

---

## Files

| File / Directory | Description |
|------------------|-------------|
| `index.html` | Your original source file |
| `index_with_panel.html` | Generated output — your app + state panel + monitoring logic |
| `layers.html` | Generated output — state + aesthetics + strategy panels side by side |
| `states_schema.json` | AI-generated blueprint of your app's states and logic |
| `generate_state_panel.py` | CLI orchestrator (entry point) |
| `state_analyzer.py` | AI analysis engine (calls Google Gemini) |
| `panel_generator.py` | Code generator (builds panel HTML/CSS/JS) |
| `layer/` | Layers (aesthetics + strategy) analyzer and panel generator |
| `layer/layers.py` | AI aesthetics/strategy analyzer |
| `layer/layers_panel_generator.py` | Generates `layers.html` |
| `layer/layers_schema.json` | AI-generated layers schema |
| `jump-states/` | AI-generated jump-to-state scripts |
| `jump-states/state_jumper.js` | Adds "Jump" buttons to panel for instant state navigation |
| `state-flow-diagram/` | Mermaid state flow diagrams |
| `state-flow-diagram/state_flow_diagram.js` | Mermaid diagram data |
| `state-flow-diagram/state_flow_map.html` | Standalone flow map page |
| `dev_server.py` | Dev server with file watching + live reload |
| `server.py` | Simple static HTTP server |
| `tests/` | Example HTML experiences for testing |
| `playwright_recorder/` | Session recording and replay tools |

---

## CLI Reference

See [CLI_COMMANDS.md](CLI_COMMANDS.md) for the full command reference with all arguments and API endpoints.

---

## Advanced Usage

### Re-generating ONLY the Panel (Skip AI)
If you've manually edited `states_schema.json` and want to update the HTML without an AI call:
```bash
python panel_generator.py
```

### Run Only Layers Analysis
If states are already detected and you just want layers:
```bash
python generate_state_panel.py index.html --layers-only
```

### Custom Output Filename
```bash
python generate_state_panel.py input.html my_debug_version.html
```

### Custom Schema Output Path
```bash
python generate_state_panel.py index.html --schema-output my_schema.json
python generate_state_panel.py index.html --layers-schema my_layers.json
```
