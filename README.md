# AI State Analyzer & Panel Generator

Anushka's Note: There are some test vibe-coded examples in the `tests` folder. Just copy-paste that code into `index.html` to run the experience each time. The commands below should be helpful!

Turn any experience into a fully instrumented, state-aware experience with a visual debugging panel.

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install anthropic python-dotenv
```
*(Ensure you have an `ANTHROPIC_API_KEY` set in your environment or `.env` file)*

### 2. Generate the Panel
Run the main script on your HTML file:
```bash
python generate_state_panel.py index.html
```

### 3. View the Result
Open the generated file in your browser:
```bash
# On Windows
start index_with_panel.html
# On Mac
open index_with_panel.html
```
You will see your original application with a new **State Progression Panel** on the right side.

---

## 🧠 System Architecture: How It Works

The system consists of three main components that work together to "understand" and instrument your code.

### 1. The Orchestrator: `generate_state_panel.py`
This is the main entry point. It coordinates the entire process:
1.  Calls **The Brain** (`state_analyzer.py`) to analyze your code.
2.  Takes the resulting blueprint (`states_schema.json`).
3.  Calls **The Builder** (`panel_generator.py`) to generate the final HTML.

### 2. The Brain: `state_analyzer.py` (AI Agent)
This script uses an AI agent (Claude via Anthropic API) to act as an expert code analyst.
*   **Role**: It reads your raw source code to understand its logic.
*   **Process**:
    *   **State Detection**: Identifies distinct "behavioral states" (e.g., "Intro", "Game Over", "Loading").
    *   **Logic Extraction**: Figures out the exact JavaScript conditions that trigger each state (e.g., `score > 100`).
    *   **Asset Identification**: Finds interactive elements (buttons) and key variables (scores, counters) relevant to each state.
    *   **Hook Discovery**: Identifies where in your code variables change, so we can "spy" on them.
*   **Output**: Generates **`states_schema.json`**, a structured blueprint of your application's logic.

### 3. The Builder: `panel_generator.py` (Code Generator)
This script takes the AI's blueprint and programmatically constructs the debugging tools.
*   **Role**: It injects monitoring code and builds the visual interface.
*   **Process**:
    *   **Code Injection**: It inserts a "Runtime Monitor" (`window.__ai_state_monitor`) into your HTML. It uses the **Hooks** found by the AI to inject reporting lines (e.g., `report('score', score)`) right after variables change in your original code.
    *   **Panel Construction**: It builds the HTML/CSS for the side panel, creating a section for each state defined in the schema.
    *   **Logic Embedding**: It embeds the JavaScript logic to constantly evaluate the "Trigger Logic" and update the panel in real-time.
*   **Output**: Generates **`index_with_panel.html`**.

---

## 📂 The Files

*   **`index.html`**: Your original source file.
*   **`index_with_panel.html`**: The **Generated Output**. This is a self-contained file containing your full application PLUS the state panel and monitoring logic. You can open this anywhere; it doesn't need a server.
*   **`states_schema.json`**: The **Blueprint**. A JSON file containing the AI's understanding of your app. You can manually edit this file to tweak descriptions or logic, then re-run `panel_generator.py` to update the HTML without re-running the AI.

---

## 🛠 Advanced Usage

### Re-generating ONLY the Panel (Skip AI)
If you have manually edited `states_schema.json` and want to update the HTML without paying for AI tokens:
```bash
python panel_generator.py
```
This will read the existing schema and regenerate `index_with_panel.html`.

### Custom Output Filename
```bash
python generate_state_panel.py input.html my_debug_version.html
```
