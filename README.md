# AI State Analyzer / Experience Editing

A system for analyzing, recording, and debugging state machines in web applications. This project combines state machine analysis with automated interaction recording using Playwright.

## Features

### State Machine Analysis
- Automatically analyze HTML/JavaScript for state machine patterns
- Generate state schemas and visualizations
- Create debug panels for real-time state inspection

### Playwright Session Recorder
- Record user interactions automatically
- Replay sessions with precise timing
- Convert recordings to reusable test scripts
- Test code changes with recorded interactions

### Debug Tools
- Visual state panel overlay
- Live event tracking
- Session management and analysis

## Quick Start

### Installation

```bash
# Install Python dependencies
pip install playwright flask python-dotenv

# Install Playwright browsers (one-time setup)
python -m playwright install chromium
```

### Environment Setup

Create a `.env` file in the project root to store your Anthropic API key:

```bash
# Copy the example file
cp .env.example .env

# Edit .env and add your API key
# ANTHROPIC_API_KEY=your-api-key-here
```

### Running the Application

```bash
# Start the local web server
python server.py

# Server runs at http://localhost:8000
```

### Recording a Session

```bash
cd playwright_recorder
python record_session.py --html ../index.html
```

Browser opens → Interact with app → Press Ctrl+S to save → Recording saved to `recordings/` folder

### Replaying a Session

```bash
python replay_session.py --recording recordings/session_001.json
```

## Project Structure

```
ai-state-analyzer/
├── server.py                 # Local web server
├── state_analyzer.py         # State machine analyzer
├── panel_generator.py        # Debug panel generator
├── generate_state_panel.py   # Panel HTML generator
├── index.html                # Main application
├── art-index.html            # Alternative version
├── COMMANDS.txt              # Complete command reference
├── playwright_recorder/      # Session recorder toolkit
│   ├── record_session.py     # Record interactions
│   ├── replay_session.py     # Replay sessions
│   ├── convert_to_script.py  # Convert to scripts
│   ├── README.md             # Detailed recorder docs
│   └── requirements.txt      # Recorder dependencies
└── README.md                 # This file
```

## Documentation

- **[COMMANDS.txt](COMMANDS.txt)** - Complete command reference with examples
- **[Playwright Recorder README](playwright_recorder/README.md)** - Detailed recorder documentation

## Use Cases

- **Bug Reproduction** - Record exact steps to reproduce issues
- **Regression Testing** - Test code changes against recorded interactions
- **User Studies** - Analyze user interaction patterns
- **State Machine Debugging** - Visualize and debug application states
- **Automated Testing** - Create reusable test scripts

## Common Commands

### State Analysis
```bash
# Analyze state machine
python state_analyzer.py index.html

# Generate debug panel
python generate_state_panel.py index.html
```

### Recording & Replay
```bash
# Record session
cd playwright_recorder
python record_session.py --html ../index.html

# Replay at 2x speed
python replay_session.py --recording recordings/session_001.json --speed 2.0

# Convert to reusable script
python convert_to_script.py --recording recordings/session_001.json --output actions.json
```

## Requirements

- Python 3.7+
- Playwright
- Flask (optional, for advanced features)
- python-dotenv (for environment variable management)
