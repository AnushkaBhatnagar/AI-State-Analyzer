# AI State Analyzer & Panel Generator

Anushka's Note: There are some test vibe-coded examples in the `tests` folder. Just copy-paste that code into `index.html` to run the experience each time. The commands below should be helpful!

Turn any experience into a fully instrumented, state-aware experience with a visual debugging panel.

## Quick Start

### 1. Install Dependencies
```bash
pip install anthropic python-dotenv flask flask-cors watchdog
```
*(Ensure you have an `ANTHROPIC_API_KEY` set in your environment or `.env` file)*

### 2. Generate the Panel
Run the main script on your HTML file:
```bash
python generate_state_panel.py index.html
```
This performs a full AI analysis and outputs `index_with_panel.html` + `states_schema.json`.

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

## System Architecture

The system consists of three main components that work together to "understand" and instrument your code.

### 1. The Orchestrator: `generate_state_panel.py`
Main entry point. Coordinates the entire process:
1. Calls **The Brain** (`state_analyzer.py`) to analyze your code.
2. Takes the resulting blueprint (`states_schema.json`).
3. Calls **The Builder** (`panel_generator.py`) to generate the final HTML.

Supports two modes:
```bash
# Full analysis from scratch (default)
python generate_state_panel.py index.html

# Incremental analysis (updates existing schema — faster, cheaper)
python generate_state_panel.py index.html --mode incremental
```

### 2. The Brain: `state_analyzer.py` (AI Agent)
Uses Claude (Anthropic API) to act as an expert code analyst.
- **State Detection**: Identifies distinct behavioral states (e.g., "Intro", "Game Over", "Loading").
- **Logic Extraction**: Figures out the exact JavaScript conditions that trigger each state.
- **Asset Identification**: Finds interactive elements and key variables relevant to each state.
- **Hook Discovery**: Identifies where in your code variables change, so we can instrument them.
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
- **Panel toolbar**: The generated panel includes two buttons:
  - **Incremental Analysis** — sends existing schema + new code to AI for a context-aware update (~15-25s)
  - **Full Analysis** — from-scratch AI analysis (~20-30s)

### API Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/reanalyze` | Trigger re-analysis. Body: `{"mode": "incremental"}` or `{"mode": "full"}` |
| `GET` | `/api/status` | Check current analysis status |
| `GET` | `/api/events` | SSE stream for live reload notifications |

### Workflow with a coding agent
1. Start the dev server: `python dev_server.py`
2. Open `http://localhost:8000/index_with_panel.html`
3. Copy state info from the panel, paste it into your coding agent (e.g., Claude Code) as context
4. Agent edits `index.html` — the dev server detects the change, re-analyzes, and live-reloads the panel automatically

---

## Files

| File | Description |
|------|-------------|
| `index.html` | Your original source file |
| `index_with_panel.html` | Generated output — your app + state panel + monitoring logic |
| `states_schema.json` | AI-generated blueprint of your app's states and logic |
| `generate_state_panel.py` | CLI orchestrator (entry point) |
| `state_analyzer.py` | AI analysis engine (calls Claude API) |
| `panel_generator.py` | Code generator (builds panel HTML/CSS/JS) |
| `dev_server.py` | Dev server with file watching + live reload |
| `server.py` | Simple static HTTP server |
| `tests/` | Example HTML experiences for testing |

---

## Advanced Usage

### Re-generating ONLY the Panel (Skip AI)
If you've manually edited `states_schema.json` and want to update the HTML without an AI call:
```bash
python panel_generator.py
```

### Custom Output Filename
```bash
python generate_state_panel.py input.html my_debug_version.html
```

### Custom Schema Output Path
```bash
python generate_state_panel.py index.html --schema-output my_schema.json
```
