"""
Playwright Session Recorder

Records user interactions with a web application and saves them to a JSON file
for later replay.

Usage:
    python record_session.py --html index.html --output my_session.json
"""

import argparse
import json
import time
import os
import re
from datetime import datetime
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Error: Playwright not installed.")
    print("Install it with: pip install playwright")
    print("Then run: python -m playwright install chromium")
    exit(1)

try:
    from instagram_config import INSTAGRAM_STATE, get_stage_info
    SNAPSHOTS_AVAILABLE = True
except ImportError:
    SNAPSHOTS_AVAILABLE = False

# Load states schema
STATES_SCHEMA = None
try:
    schema_path = Path(__file__).parent.parent / 'states_schema.json'
    if schema_path.exists():
        with open(schema_path, 'r') as f:
            STATES_SCHEMA = json.load(f)
except:
    pass


class SessionRecorder:
    """Records user interactions with a web application"""
    
    def __init__(self, html_path, capture_snapshots=False):
        """
        Initialize recorder
        
        Args:
            html_path: Path to HTML file or URL
            capture_snapshots: Whether to capture stage snapshots
        """
        self.html_path = html_path
        self.capture_snapshots = capture_snapshots
        self.recording = {
            'session_id': f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'timestamp': datetime.now().isoformat(),
            'html_path': html_path,
            'events': []
        }
        self.start_time = None
        self.snapshots = {}
        self.last_stage = -1
    
    def record_with_script(self, script_path):
        """Record session by executing actions from a script"""
        # Load script
        with open(script_path, 'r') as f:
            script = json.load(f)
        
        actions = script.get('actions', [])
        
        print("\n🤖 Starting Automated Recording Session")
        print("=" * 50)
        print(f"📄 HTML: {self.html_path}")
        print(f"📜 Script: {script_path}")
        print(f"🎯 Actions: {len(actions)}")
        print("\n" + "=" * 50 + "\n")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()
            
            # Inject recording script
            recording_script = self._get_recording_script()
            page.add_init_script(recording_script)
            
            # Navigate to page
            if self.html_path.startswith('http'):
                page.goto(self.html_path)
            else:
                file_url = f"file://{Path(self.html_path).resolve()}"
                page.goto(file_url)
            
            page.wait_for_load_state('domcontentloaded')
            
            print("✅ Browser opened. Executing actions...\n")
            
            self.start_time = time.time()
            
            # Execute actions from script
            for i, action in enumerate(actions, 1):
                action_type = action['type']
                
                # Wait if specified
                if 'wait' in action:
                    time.sleep(action['wait'])
                
                # Execute action
                try:
                    if action_type == 'click':
                        selector = action['selector']
                        print(f"[{i}/{len(actions)}] 🖱️  Click: {selector}")
                        try:
                            page.click(selector, timeout=2000)
                        except:
                            # Fallback to coordinates
                            page.mouse.click(action['x'], action['y'])
                    
                    elif action_type == 'scroll':
                        scrollY = action['scrollY']
                        scrollX = action.get('scrollX', 0)
                        print(f"[{i}/{len(actions)}] 📜 Scroll: {scrollY}px")
                        page.evaluate(f"window.scrollTo({scrollX}, {scrollY})")
                    
                    elif action_type == 'keypress':
                        key = action['key']
                        print(f"[{i}/{len(actions)}] ⌨️  Keypress: {key}")
                        page.keyboard.press(key)
                    
                    # Small pause between actions
                    time.sleep(0.1)
                    
                except Exception as e:
                    print(f"⚠️  Error executing action {i}: {e}")
            
            print("\n✅ All actions executed!")
            
            # Collect final events
            print("💾 Collecting recorded events...")
            try:
                final_events = page.evaluate('window.recordedEvents || []')
                self.recording['events'] = final_events
                print(f"✅ Collected {len(final_events)} events")
            except:
                print("⚠️  Could not retrieve events")
            
            try:
                browser.close()
            except:
                pass
        
        self.recording['duration_seconds'] = time.time() - self.start_time if self.start_time else 0
        
        return self.recording
    
    def record(self):
        """Start recording session"""
        print("\n🎬 Starting Recording Session")
        print("=" * 50)
        print(f"📄 HTML: {self.html_path}")
        print("\n📝 Instructions:")
        print("   • Interact with the app normally")
        print("   • Press Ctrl+S to save and stop")
        print("   • Or close browser to auto-save")
        print("\n" + "=" * 50 + "\n")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()
            
            # Inject recording script BEFORE navigation
            recording_script = self._get_recording_script()
            page.add_init_script(recording_script)
            
            # Navigate to page
            if self.html_path.startswith('http'):
                page.goto(self.html_path)
            else:
                file_url = f"file://{Path(self.html_path).resolve()}"
                page.goto(file_url)
            
            # Wait for page to be fully loaded
            page.wait_for_load_state('domcontentloaded')
            
            # Verify injection worked
            try:
                is_ready = page.evaluate('typeof window.recordedEvents !== "undefined"')
                if is_ready:
                    print("✅ Browser opened. Recording script loaded!")
                else:
                    print("⚠️  Warning: Recording script may not have loaded")
            except:
                print("⚠️  Warning: Could not verify recording script")
            
            self.start_time = time.time()
            
            print("🔴 Recording... 0 events\n")
            
            # Poll for events and show live counter
            try:
                while not page.is_closed():
                    # Collect events periodically
                    try:
                        events = page.evaluate('window.recordedEvents || []')
                        self.recording['events'] = events
                        
                        # Check for stage changes and capture snapshots
                        self._check_stage_change(page)
                        
                        # Check if user pressed Ctrl+S
                        should_stop = page.evaluate('window.shouldStopRecording || false')
                        if should_stop:
                            print(f"\r🔴 Recording... {len(events)} events")
                            print("\n💾 Ctrl+S detected! Stopping recording...")
                            break
                        
                        # Update live counter (overwrite same line)
                        print(f"\r🔴 Recording... {len(events)} events", end='', flush=True)
                        
                    except:
                        # Page might be closing
                        break
                    
                    # Wait a bit before next poll
                    time.sleep(0.5)
                    
            except KeyboardInterrupt:
                print("\n\n⚠️  Interrupted! Saving events...")
            except:
                pass
            
            # Final collection of events
            print("\n\n💾 Collecting final events...")
            try:
                final_events = page.evaluate('window.recordedEvents || []')
                self.recording['events'] = final_events
                print(f"✅ Collected {len(final_events)} events")
            except:
                print("⚠️  Could not retrieve final events")
                if len(self.recording['events']) > 0:
                    print(f"   Using last known state: {len(self.recording['events'])} events")
            
            try:
                browser.close()
            except:
                pass
        
        self.recording['duration_seconds'] = time.time() - self.start_time if self.start_time else 0
        
        return self.recording
    
    def _capture_snapshot(self, page):
        """Capture current state snapshot"""
        if not self.capture_snapshots or not SNAPSHOTS_AVAILABLE:
            return None
        
        try:
            config = INSTAGRAM_STATE
            snapshot = {}
            
            # Capture all state variables
            for var_name in config['variables']:
                try:
                    value = page.evaluate(f'typeof {var_name} !== "undefined" ? {var_name} : null')
                    if value is not None:
                        snapshot[var_name] = value
                except:
                    pass
            
            # Capture DOM
            try:
                content_id = config['content_id']
                dom = page.evaluate(f'document.getElementById("{content_id}") ? document.getElementById("{content_id}").innerHTML : ""')
                snapshot['dom'] = dom
            except:
                pass
            
            # Add timestamp
            snapshot['timestamp'] = time.time() - self.start_time if self.start_time else 0
            
            return snapshot
        except Exception as e:
            print(f"⚠️  Error capturing snapshot: {e}")
            return None
    
    def _check_stage_change(self, page):
        """Check if state has changed and capture snapshot if needed"""
        if not self.capture_snapshots or not SNAPSHOTS_AVAILABLE:
            return
        
        try:
            # Use states_schema.json if available for detection
            if STATES_SCHEMA:
                current_state = self._detect_current_state(page)
            else:
                # Fallback to old method
                current_state = page.evaluate('typeof stage !== "undefined" ? stage : -1')
            
            # If state changed, capture snapshot
            if current_state != self.last_stage and current_state >= 0:
                snapshot = self._capture_snapshot(page)
                if snapshot:
                    self.snapshots[current_state] = snapshot
                    
                    # Get state name from schema or fallback
                    if STATES_SCHEMA:
                        state_info = next((s for s in STATES_SCHEMA['states'] if s['id'] == current_state), None)
                        state_name = state_info['name'] if state_info else f'State {current_state}'
                    else:
                        state_info = get_stage_info(current_state)
                        state_name = state_info['name']
                    
                    print(f"\n📸 Captured snapshot: State {current_state} ({state_name})")
                
                self.last_stage = current_state
        except Exception as e:
            pass
    
    def _detect_current_state(self, page):
        """Detect current state using states_schema.json detection conditions"""
        if not STATES_SCHEMA:
            return -1
        
        try:
            # Check each state's detection condition
            for state in STATES_SCHEMA['states']:
                state_id = state['id']
                condition = state['detection_condition']
                
                # Evaluate the detection condition
                try:
                    # For State 5 (Flood Overlay), check if overlay is visible
                    if state_id == 5:
                        notif_count = page.evaluate('typeof notificationCount !== "undefined" ? notificationCount : 0')
                        overlay_visible = page.evaluate('document.getElementById("floodOverlay") && document.getElementById("floodOverlay").style.display === "flex"')
                        if notif_count >= 150 and overlay_visible:
                            return 5
                    
                    # For State 4 (Hell Mode), check stage and isHellMode
                    elif state_id == 4:
                        stage = page.evaluate('typeof stage !== "undefined" ? stage : -1')
                        is_hell = page.evaluate('typeof isHellMode !== "undefined" ? isHellMode : false')
                        if stage == 4 and is_hell:
                            return 4
                    
                    # For States 0-3, check stage variable
                    else:
                        stage = page.evaluate('typeof stage !== "undefined" ? stage : -1')
                        if stage == state_id:
                            return state_id
                
                except:
                    continue
            
            return -1
        except:
            return -1
    
    def _save_snapshots(self, session_id):
        """Save snapshots to files"""
        if not self.snapshots:
            return
        
        # Create snapshots directory
        snapshot_dir = Path('snapshots') / session_id
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        
        # Save each snapshot
        for stage_num, snapshot in self.snapshots.items():
            if stage_num >= 0:  # Don't save initial state
                stage_file = snapshot_dir / f'stage_{stage_num}.json'
                with open(stage_file, 'w') as f:
                    json.dump(snapshot, f, indent=2)
        
        # Save metadata
        metadata = {
            'session_id': session_id,
            'stages_captured': len(self.snapshots),
            'stage_numbers': sorted([s for s in self.snapshots.keys() if s >= 0])
        }
        metadata_file = snapshot_dir / 'metadata.json'
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"\n📸 Snapshots saved: {snapshot_dir}")
        print(f"   Stages captured: {len([s for s in self.snapshots.keys() if s >= 0])}")
    
    def _get_recording_script(self):
        """Get the recording JavaScript code"""
        return """
window.recordedEvents = [];
window.shouldStopRecording = false;
const startTime = Date.now();

// Helper to get unique selector
function getSelector(element) {
    if (element.id) return '#' + element.id;
    if (element.className) {
        const classes = element.className.split(' ').filter(c => c);
        if (classes.length > 0) return '.' + classes.join('.');
    }
    return element.tagName.toLowerCase();
}

// Listen for Ctrl+S to stop recording
document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        window.shouldStopRecording = true;
        console.log('💾 Ctrl+S pressed - Saving and stopping...');
        document.body.style.border = '5px solid green';
        setTimeout(() => {
            document.body.style.border = '';
        }, 500);
        return;
    }
    
    // Record other keypresses
    window.recordedEvents.push({
        type: 'keypress',
        key: e.key,
        code: e.code,
        timestamp: (Date.now() - startTime) / 1000
    });
    console.log('🔴 Recorded keypress:', e.key);
});

// Record clicks
document.addEventListener('click', (e) => {
    window.recordedEvents.push({
        type: 'click',
        selector: getSelector(e.target),
        x: e.clientX,
        y: e.clientY,
        timestamp: (Date.now() - startTime) / 1000
    });
    console.log('🔴 Recorded click:', getSelector(e.target));
}, true);

// Record scrolls
let scrollTimeout;
window.addEventListener('scroll', () => {
    clearTimeout(scrollTimeout);
    scrollTimeout = setTimeout(() => {
        window.recordedEvents.push({
            type: 'scroll',
            scrollY: window.scrollY,
            scrollX: window.scrollX,
            timestamp: (Date.now() - startTime) / 1000
        });
        console.log('🔴 Recorded scroll:', window.scrollY);
    }, 100);
});

// Record mouse movements (throttled)
let mouseMoveTimeout;
document.addEventListener('mousemove', (e) => {
    clearTimeout(mouseMoveTimeout);
    mouseMoveTimeout = setTimeout(() => {
        window.recordedEvents.push({
            type: 'mousemove',
            x: e.clientX,
            y: e.clientY,
            timestamp: (Date.now() - startTime) / 1000
        });
    }, 200);
});

console.log('🎬 Recording started!');
console.log('💡 Press Ctrl+S to save and stop recording');
"""
    
    def save(self, output_path):
        """Save recording to file"""
        with open(output_path, 'w') as f:
            json.dump(self.recording, f, indent=2)
        
        print(f"\n✅ Recording saved: {output_path}")
        print(f"📊 Summary:")
        print(f"   • Duration: {self.recording['duration_seconds']:.1f} seconds")
        print(f"   • Events recorded: {len(self.recording['events'])}")
        print(f"   • Session ID: {self.recording['session_id']}")


def get_next_session_number(recordings_dir='recordings'):
    """Get the next available session number"""
    if not os.path.exists(recordings_dir):
        return 1
    
    # Find all session_XXX.json files
    session_files = []
    for filename in os.listdir(recordings_dir):
        match = re.match(r'session_(\d+)\.json', filename)
        if match:
            session_files.append(int(match.group(1)))
    
    if not session_files:
        return 1
    
    return max(session_files) + 1


def get_auto_filename(recordings_dir='recordings'):
    """Generate auto-numbered filename"""
    # Create recordings directory if it doesn't exist
    os.makedirs(recordings_dir, exist_ok=True)
    
    session_num = get_next_session_number(recordings_dir)
    filename = f"session_{session_num:03d}.json"
    return os.path.join(recordings_dir, filename)


def list_recordings(recordings_dir='recordings'):
    """List all recordings with details"""
    if not os.path.exists(recordings_dir):
        print(f"\n📁 No recordings found. Directory '{recordings_dir}/' doesn't exist yet.")
        print("   Create your first recording with: python record_session.py --html <file>\n")
        return
    
    # Get all recording files
    recordings = []
    for filename in os.listdir(recordings_dir):
        if filename.endswith('.json'):
            filepath = os.path.join(recordings_dir, filename)
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    recordings.append({
                        'filename': filename,
                        'duration': data.get('duration_seconds', 0),
                        'events': len(data.get('events', [])),
                        'timestamp': data.get('timestamp', 'Unknown')
                    })
            except:
                pass
    
    if not recordings:
        print(f"\n📁 No recordings found in '{recordings_dir}/'")
        print("   Create your first recording with: python record_session.py --html <file>\n")
        return
    
    # Sort by filename
    recordings.sort(key=lambda x: x['filename'])
    
    print(f"\n📁 Recordings in '{recordings_dir}/':")
    print("=" * 70)
    for i, rec in enumerate(recordings, 1):
        print(f"   {i}. {rec['filename']}")
        print(f"      Duration: {rec['duration']:.1f}s | Events: {rec['events']} | {rec['timestamp']}")
    print("=" * 70)
    print(f"\n💡 To replay: python replay_session.py --recording {recordings_dir}/<filename>\n")


def main():
    parser = argparse.ArgumentParser(
        description='Record user interactions with a web application'
    )
    parser.add_argument(
        '--html',
        help='Path to HTML file or URL'
    )
    parser.add_argument(
        '--output',
        help='Output file for recording (default: auto-numbered in recordings/ folder)'
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='List all recordings'
    )
    parser.add_argument(
        '--script',
        help='Action script to execute automatically (instead of manual interaction)'
    )
    parser.add_argument(
        '--capture-snapshots',
        action='store_true',
        help='Capture stage snapshots for stage isolation testing (Instagram app only)'
    )
    
    args = parser.parse_args()
    
    # Handle --list command
    if args.list:
        list_recordings()
        return
    
    # Require --html for recording
    if not args.html:
        parser.error("--html is required for recording (or use --list to view recordings)")
    
    # Check if HTML file exists (if local path)
    if not args.html.startswith('http'):
        if not Path(args.html).exists():
            print(f"Error: HTML file not found: {args.html}")
            exit(1)
    
    # Determine output path
    if args.output:
        # Manual output path - still save in recordings/ if not absolute path
        if not os.path.isabs(args.output) and not args.output.startswith('recordings/'):
            output_path = os.path.join('recordings', args.output)
            os.makedirs('recordings', exist_ok=True)
        else:
            output_path = args.output
    else:
        # Auto-numbered output
        output_path = get_auto_filename()
    
    # Check snapshot capture availability
    if args.capture_snapshots and not SNAPSHOTS_AVAILABLE:
        print("⚠️  Warning: Snapshot capture requires instagram_config.py")
        print("   Continuing without snapshot capture...")
        args.capture_snapshots = False
    
    # Check if script mode
    if args.script:
        # Check if script exists
        if not Path(args.script).exists():
            print(f"Error: Script file not found: {args.script}")
            exit(1)
        
        # Record with script
        recorder = SessionRecorder(args.html, capture_snapshots=args.capture_snapshots)
        recorder.record_with_script(args.script)
        recorder.save(output_path)
        
        # Save snapshots if captured
        if args.capture_snapshots:
            recorder._save_snapshots(recorder.recording['session_id'])
        
        print(f"\n💡 To replay: python replay_session.py --recording {output_path}")
    else:
        # Manual recording
        recorder = SessionRecorder(args.html, capture_snapshots=args.capture_snapshots)
        recorder.record()
        recorder.save(output_path)
        
        # Save snapshots if captured
        if args.capture_snapshots:
            recorder._save_snapshots(recorder.recording['session_id'])
            print(f"\n💡 To test a stage: python test_stage.py --session {recorder.recording['session_id']} --stage <N> --html {args.html}")
        
        print(f"\n💡 To replay: python replay_session.py --recording {output_path}")
        print(f"💡 To convert to script: python convert_to_script.py --recording {output_path}")


if __name__ == "__main__":
    main()
