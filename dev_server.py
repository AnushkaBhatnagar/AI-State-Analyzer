#!/usr/bin/env python3
"""
Development server with file watching, live reload, and auto re-analysis.

Watches index.html for changes, automatically re-runs AI analysis,
regenerates index_with_panel.html, and live-reloads the browser.

Usage:
    python dev_server.py
    python dev_server.py --port 8080
    python dev_server.py --no-watch          # Disable file watching
    python dev_server.py --debounce 5        # 5 second debounce
"""

import argparse
import json
import os
import sys
import time
import threading
import queue
import webbrowser
from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from dotenv import load_dotenv

from state_analyzer import StateDetectionAnalyzer
from panel_generator import StatePanelGenerator

load_dotenv()

app = Flask(__name__)
CORS(app)

BASE_DIR = Path(__file__).parent

# --- Global State ---
sse_clients = []
sse_clients_lock = threading.Lock()
analysis_status = {"running": False, "last_run": None, "error": None}


def broadcast_sse(data):
    """Send an event to all connected SSE clients."""
    message = f"data: {json.dumps(data)}\n\n"
    dead_clients = []
    with sse_clients_lock:
        for client_queue in sse_clients:
            try:
                client_queue.put_nowait(message)
            except queue.Full:
                dead_clients.append(client_queue)
        for dc in dead_clients:
            sse_clients.remove(dc)


def run_analysis(mode="incremental"):
    """
    Run state analysis and regenerate panel HTML.

    Args:
        mode: "incremental" (uses existing schema as context) or "full" (from scratch)
    """
    global analysis_status

    if analysis_status["running"]:
        print("[SKIP] Analysis already in progress")
        return

    analysis_status = {"running": True, "last_run": None, "error": None}
    broadcast_sse({"type": "analysis_started", "mode": mode})

    try:
        analyzer = StateDetectionAnalyzer()
        index_path = BASE_DIR / "index.html"
        schema_path = BASE_DIR / "states_schema.json"
        output_path = BASE_DIR / "index_with_panel.html"

        if not index_path.exists():
            raise FileNotFoundError("index.html not found")

        code_content = index_path.read_text(encoding="utf-8")

        if mode == "incremental" and schema_path.exists():
            existing_schema = json.loads(schema_path.read_text(encoding="utf-8"))
            states_data = analyzer.update_states(code_content, existing_schema)
        else:
            states_data = analyzer.detect_states(code_content)

        # Save updated schema
        analyzer.save_states_json(states_data, str(schema_path))

        # Regenerate panel HTML
        generator = StatePanelGenerator(states_data)
        generator.save_to_file(
            output_path=str(output_path),
            original_html_path=str(index_path)
        )

        analysis_status = {
            "running": False,
            "last_run": time.time(),
            "error": None
        }
        broadcast_sse({
            "type": "analysis_complete",
            "states": states_data["metadata"]["total_states"],
            "mode": mode
        })
        print(f"[OK] {mode.capitalize()} analysis complete — {states_data['metadata']['total_states']} states")

    except Exception as e:
        analysis_status = {
            "running": False,
            "last_run": time.time(),
            "error": str(e)
        }
        broadcast_sse({"type": "analysis_error", "error": str(e)})
        print(f"[ERROR] Analysis failed: {e}")


def run_quick_regen():
    """Re-run panel_generator only (no AI call). Fast and free."""
    schema_path = BASE_DIR / "states_schema.json"
    index_path = BASE_DIR / "index.html"
    output_path = BASE_DIR / "index_with_panel.html"

    if not schema_path.exists():
        raise FileNotFoundError("states_schema.json not found — run full analysis first")

    states_data = json.loads(schema_path.read_text(encoding="utf-8"))
    generator = StatePanelGenerator(states_data)
    generator.save_to_file(
        output_path=str(output_path),
        original_html_path=str(index_path)
    )
    broadcast_sse({"type": "regen_complete"})
    print("[OK] Quick regen complete")


# --- File Watcher ---

class IndexFileHandler(FileSystemEventHandler):
    """Watches index.html for changes and triggers re-analysis with debounce."""

    def __init__(self, debounce_seconds=2.0):
        self.debounce_seconds = debounce_seconds
        self._timer = None
        self._lock = threading.Lock()

    def _handle_change(self, path):
        filename = os.path.basename(path)
        if filename == "index.html":
            with self._lock:
                if self._timer:
                    self._timer.cancel()
                self._timer = threading.Timer(
                    self.debounce_seconds,
                    self._trigger_rebuild
                )
                self._timer.start()
                print(f"[WATCH] index.html changed — rebuilding in {self.debounce_seconds}s...")

    def on_modified(self, event):
        if not event.is_directory:
            self._handle_change(event.src_path)

    def on_moved(self, event):
        """Handle atomic writes (temp file renamed to index.html)."""
        if not event.is_directory:
            self._handle_change(event.dest_path)

    def _trigger_rebuild(self):
        threading.Thread(target=run_analysis, args=("incremental",), daemon=True).start()


# --- Flask Routes ---

@app.route('/')
def index():
    return send_from_directory(BASE_DIR, 'index.html')


@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(BASE_DIR, path)


@app.route('/api/events')
def sse_stream():
    """SSE endpoint for live reload notifications."""
    client_queue = queue.Queue(maxsize=50)
    with sse_clients_lock:
        sse_clients.append(client_queue)

    def generate():
        try:
            while True:
                try:
                    message = client_queue.get(timeout=30)
                    yield message
                except queue.Empty:
                    yield ": keepalive\n\n"
        except GeneratorExit:
            with sse_clients_lock:
                if client_queue in sse_clients:
                    sse_clients.remove(client_queue)

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'}
    )


@app.route('/api/reanalyze', methods=['POST'])
def trigger_reanalysis():
    """Manual trigger for re-analysis. Body: {"mode": "incremental"|"full"}"""
    data = request.json or {}
    mode = data.get("mode", "incremental")

    if mode not in ("incremental", "full"):
        return jsonify({"success": False, "error": "mode must be 'incremental' or 'full'"}), 400

    if analysis_status["running"]:
        return jsonify({"success": False, "error": "Analysis already running"}), 409

    threading.Thread(target=run_analysis, args=(mode,), daemon=True).start()
    return jsonify({"success": True, "message": f"Analysis started ({mode} mode)"})


@app.route('/api/quick-regen', methods=['POST'])
def quick_regen():
    """Fast tier: re-run panel_generator only, no AI call."""
    try:
        run_quick_regen()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/status')
def get_status():
    """Get current analysis status."""
    return jsonify(analysis_status)


# --- Main ---

def main():
    parser = argparse.ArgumentParser(description='AI State Analyzer - Dev Server')
    parser.add_argument('--port', type=int, default=8000, help='Port to serve on (default: 8000)')
    parser.add_argument('--no-watch', action='store_true', help='Disable file watching')
    parser.add_argument('--debounce', type=float, default=2.0, help='Debounce seconds for file watcher (default: 2.0)')
    parser.add_argument('--no-browser', action='store_true', help='Do not auto-open browser')
    args = parser.parse_args()

    port = args.port
    index_path = BASE_DIR / "index.html"
    panel_path = BASE_DIR / "index_with_panel.html"

    if not index_path.exists():
        print("[ERROR] index.html not found in current directory")
        sys.exit(1)

    if not panel_path.exists():
        print("[WARNING] index_with_panel.html not found")
        print("          Run 'python generate_state_panel.py index.html' first")
        print()

    # Start file watcher
    observer = None
    if not args.no_watch:
        event_handler = IndexFileHandler(debounce_seconds=args.debounce)
        observer = Observer()
        observer.schedule(event_handler, str(BASE_DIR), recursive=False)
        observer.start()

    print()
    print("=" * 60)
    print("AI STATE ANALYZER - DEV SERVER")
    print("=" * 60)
    print(f"  Server:    http://localhost:{port}/")
    print(f"  Panel:     http://localhost:{port}/index_with_panel.html")
    print(f"  Watching:  {'index.html' if not args.no_watch else 'DISABLED'}")
    print(f"  Debounce:  {args.debounce}s")
    print(f"  SSE:       http://localhost:{port}/api/events")
    print()
    print("  API Endpoints:")
    print(f"    POST /api/reanalyze    — trigger AI re-analysis")
    print(f"    POST /api/quick-regen  — fast panel regeneration (no AI)")
    print(f"    GET  /api/status       — check analysis status")
    print()
    print("=" * 60)
    print("  Press Ctrl+C to stop")
    print("=" * 60)
    print()

    # Open browser
    if not args.no_browser:
        def open_browser():
            time.sleep(1.5)
            url = f"http://localhost:{port}/index_with_panel.html"
            print(f"Opening: {url}")
            webbrowser.open(url)
        threading.Thread(target=open_browser, daemon=True).start()

    try:
        app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
    except OSError as e:
        if e.errno in (48, 10048):
            print(f"\n[ERROR] Port {port} is already in use!")
            print(f"        Try: python dev_server.py --port {port + 1}")
            sys.exit(1)
        raise
    except KeyboardInterrupt:
        print("\n\nServer stopped.")
    finally:
        if observer:
            observer.stop()
            observer.join()


if __name__ == "__main__":
    main()
