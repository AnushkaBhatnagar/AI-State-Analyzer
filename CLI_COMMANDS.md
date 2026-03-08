# AI State Analyzer — CLI Commands Reference

## Environment Setup

All AI-powered features require a Google Gemini API key.

```
# Set via environment variable
export GOOGLE_API_KEY=your_key_here

# Or create a .env file in the project root
echo "GOOGLE_API_KEY=your_key_here" > .env
```

---

## State Analysis & Panel Generation

### `generate_state_panel.py`

Main pipeline: detects states, generates panel. Optional flags enable jump codes, flow diagrams, and aesthetics analysis.

```bash
# Base analysis (state detection + panel only)
python generate_state_panel.py index.html

# Custom output file
python generate_state_panel.py index.html output.html

# Incremental mode (updates existing schema — faster, cheaper)
python generate_state_panel.py index.html --mode incremental

# Enable jump code generation
python generate_state_panel.py index.html --jump-code

# Enable flow diagram generation
python generate_state_panel.py index.html --flow-diagram

# Enable all optional features
python generate_state_panel.py index.html --jump-code --flow-diagram

# Skip layers analysis (aesthetics + strategy)
python generate_state_panel.py index.html --skip-layers

# Run only layers analysis (reuses existing states_schema.json)
python generate_state_panel.py index.html --layers-only

# Provide API key directly
python generate_state_panel.py index.html --api-key YOUR_KEY

# Custom schema output paths
python generate_state_panel.py index.html --schema-output custom_schema.json
python generate_state_panel.py index.html --layers-schema custom_layers.json
```

**Arguments:**

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `input_file` | Yes | — | HTML file to analyze |
| `output_file` | No | `input_with_panel.html` | Output HTML with state panel |
| `--api-key` | No | `GOOGLE_API_KEY` env var | Google Gemini API key |
| `--schema-output` | No | `states_schema.json` | Path for states schema JSON |
| `--mode` | No | `full` | `full` or `incremental` |
| `--jump-code` | No | `false` | Enable AI jump code generation (`jump-states/state_jumper.js`) |
| `--flow-diagram` | No | `false` | Enable Mermaid flow diagram (`state-flow-diagram/state_flow_diagram.js`, `state_flow_map.html`) |
| `--skip-layers` | No | `false` | Skip layers analysis (aesthetics + strategy) |
| `--layers-only` | No | `false` | Run only layers analysis using existing `states_schema.json`, then generate `layers.html` |
| `--layers-schema` | No | `layer/layers_schema.json` | Path for layers schema |

**Output files:**
- `index_with_panel.html` — Experience + state panel
- `states_schema.json` — State detection schema
- `jump-states/state_jumper.js` — Jump transition codes
- `state-flow-diagram/state_flow_diagram.js` — Mermaid diagram data
- `state-flow-diagram/state_flow_map.html` — Standalone flow map page
- `layer/layers_schema.json` — Layers schema (aesthetics + strategy)
- `layers.html` — State + aesthetics + strategy panels side by side

---

## Development Servers

### `dev_server.py`

Development server with file watching, auto re-analysis, and live reload via SSE.

```bash
# Start with defaults (port 8000, file watching enabled)
python dev_server.py

# Custom port
python dev_server.py --port 8080

# Disable file watching
python dev_server.py --no-watch

# Custom debounce interval for file watcher
python dev_server.py --debounce 5

# Don't auto-open browser
python dev_server.py --no-browser
```

**Arguments:**

| Argument | Default | Description |
|----------|---------|-------------|
| `--port` | `8000` | Port to serve on |
| `--no-watch` | `false` | Disable file watching |
| `--debounce` | `2.0` | Debounce seconds for file watcher |
| `--no-browser` | `false` | Don't auto-open browser |

**API Endpoints:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/reanalyze` | POST | Trigger AI re-analysis. Body: `{"mode": "incremental"\|"full"}` |
| `/api/quick-regen` | POST | Fast panel regeneration (no AI call) |
| `/api/status` | GET | Check analysis status |
| `/api/events` | GET | SSE stream for live reload |

---

### `server.py`

Simple HTTP server that auto-opens both `index.html` and `index_with_panel.html` in the browser.

```bash
python server.py
# Starts on http://localhost:8000
```

No arguments — runs with hardcoded port 8000.

---

### `server-enhanced-new.py`

Flask server with state editor API. Dynamically extracts code based on states_schema.json.

```bash
python server-enhanced-new.py
# Starts on http://localhost:8000
```

**API Endpoints:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/states` | GET | Get all states with metadata |
| `/api/state/<id>/code` | GET | Get code for a specific state |
| `/api/state/<id>/save` | POST | Save state code modification |
| `/state-editor` | GET | Serve state editor panel |
| `/states_schema.json` | GET | Serve states schema |

---

## AI Notification Server

### `ai_notif_server.py`

Flask server that generates AI-powered notifications using Gemini.

```bash
python ai_notif_server.py
# Starts on http://localhost:5000
```

**API Endpoints:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/generate-notification` | POST | Generate notification. Body: `{category, level (1-5), username, like_count}` |
| `/chat` | POST | Generate chat response. Body: `{message, dm_context, history}` |
| `/health` | GET | Health check |
| `/` | GET | Serve index.html |

**Categories:** `travel`, `food`, `professional`, `relationships`, `wellness`
**Levels:** 1 (mild) to 5 (intense)

---

## Playwright Recorder

All recorder scripts are in the `playwright_recorder/` directory.

### `record_session.py`

Records user interactions with a web application.

```bash
cd playwright_recorder

# Record interactions on an HTML file
python record_session.py --html ../index.html

# Custom output file
python record_session.py --html ../index.html --output my_session.json

# Execute an automated action script
python record_session.py --html ../index.html --script actions.json

# Capture stage snapshots
python record_session.py --html ../index.html --capture-snapshots

# List all recordings
python record_session.py --list
```

| Argument | Description |
|----------|-------------|
| `--html` | Path to HTML file or URL to record |
| `--output` | Output file for recording (default: auto-numbered) |
| `--script` | Action script to execute automatically |
| `--capture-snapshots` | Capture stage snapshots |
| `--list` | List all recordings |

---

### `replay_session.py`

Replays a recorded session.

```bash
cd playwright_recorder

# Replay a recording
python replay_session.py --recording my_session.json

# Replay on a specific HTML file
python replay_session.py --recording my_session.json --html ../index.html

# 2x speed replay
python replay_session.py --recording my_session.json --speed 2.0
```

| Argument | Description |
|----------|-------------|
| `--recording` | Path to recording JSON file (required) |
| `--html` | HTML file or URL to replay on |
| `--speed` | Playback speed multiplier (default: 1.0) |

---

### `convert_to_script.py`

Converts a recorded session into a reusable action script.

```bash
cd playwright_recorder

python convert_to_script.py --recording session_001.json
python convert_to_script.py --recording session_001.json --output actions.json
```

| Argument | Description |
|----------|-------------|
| `--recording` | Path to recording JSON file (required) |
| `--output` | Output path for action script |

---

### `extract_stage.py`

Extracts a specific stage/snapshot from a recorded session.

```bash
cd playwright_recorder

# List all sessions
python extract_stage.py --list

# List stages for a session
python extract_stage.py --list-stages session_001

# Extract a specific stage
python extract_stage.py --session session_001 --stage 2
```

| Argument | Description |
|----------|-------------|
| `--list` | List all available sessions |
| `--list-stages` | List all stages for a session |
| `--session` | Session name (e.g., session_001) |
| `--stage` | Stage number to extract (0-4) |

---

### `test_stage.py`

Tests a specific stage in isolation by loading a snapshot.

```bash
cd playwright_recorder

python test_stage.py --session session_001 --stage 2 --html ../index.html
python test_stage.py --session session_001 --stage 0 --html ../index.html --headless
```

| Argument | Description |
|----------|-------------|
| `--session` | Session name (required) |
| `--stage` | Stage number to test (required) |
| `--html` | Path to HTML file or URL (required) |
| `--headless` | Run in headless mode |
