"""
Playwright Session Replayer

Replays a recorded session on a web application.

Usage:
    python replay_session.py --recording my_session.json --html index.html
"""

import argparse
import json
import time
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Error: Playwright not installed.")
    print("Install it with: pip install playwright")
    print("Then run: python -m playwright install chromium")
    exit(1)


class SessionReplayer:
    """Replays recorded user interactions"""
    
    def __init__(self, recording_path, html_path=None):
        """
        Initialize replayer
        
        Args:
            recording_path: Path to recording JSON file
            html_path: Optional override for HTML path
        """
        self.recording_path = recording_path
        self.html_path = html_path
        self.recording = self._load_recording()
        
        # Use HTML from recording if not overridden
        if not self.html_path:
            self.html_path = self.recording.get('html_path')
    
    def _load_recording(self):
        """Load recording from file"""
        with open(self.recording_path, 'r') as f:
            return json.load(f)
    
    def replay(self, speed=1.0):
        """
        Replay the recorded session
        
        Args:
            speed: Playback speed multiplier (1.0 = normal, 2.0 = 2x faster, etc.)
        """
        print("\n🎬 Replaying Session")
        print("=" * 50)
        print(f"📄 HTML: {self.html_path}")
        print(f"📼 Recording: {self.recording_path}")
        print(f"⏱️  Duration: {self.recording.get('duration_seconds', 0):.1f} seconds")
        print(f"📊 Events: {len(self.recording['events'])}")
        print(f"⚡ Speed: {speed}x")
        print("\n" + "=" * 50 + "\n")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()
            
            # Navigate to page
            if self.html_path.startswith('http'):
                page.goto(self.html_path)
            else:
                file_url = f"file://{Path(self.html_path).resolve()}"
                page.goto(file_url)
            
            print("✅ Browser opened. Starting replay...\n")
            
            # Replay events
            start_time = time.time()
            events = self.recording['events']
            
            for i, event in enumerate(events):
                # Wait until correct time
                target_time = event['timestamp'] / speed
                elapsed = time.time() - start_time
                wait_time = target_time - elapsed
                
                if wait_time > 0:
                    time.sleep(wait_time)
                
                # Execute event
                try:
                    self._execute_event(page, event, i + 1, len(events))
                except Exception as e:
                    print(f"⚠️  Error replaying event {i + 1}: {e}")
            
            print(f"\n✅ Replay complete! Duration: {time.time() - start_time:.1f}s")
            
            # Pause the app after replay
            self._pause_app(page)
            
            # Keep browser open
            print("⏸️  App paused (all timers stopped).")
            print("   (Browser will stay open. Close it when done.)")
            try:
                page.wait_for_timeout(300000)  # Wait 5 minutes
            except:
                pass
            
            browser.close()
    
    def _pause_app(self, page):
        """Pause the app after replay completes (generic for any app)"""
        try:
            page.evaluate("""
                // Stop all intervals and timeouts (generic - works for any app)
                for (let i = 1; i < 99999; i++) {
                    window.clearInterval(i);
                    window.clearTimeout(i);
                }
                console.log('⏸️ Replay complete - App paused (all timers cleared)');
            """)
        except Exception as e:
            print(f"⚠️  Could not pause app: {e}")
    
    def _execute_event(self, page, event, event_num, total_events):
        """Execute a single recorded event"""
        event_type = event['type']
        
        if event_type == 'click':
            selector = event['selector']
            print(f"[{event_num}/{total_events}] 🖱️  Click: {selector}")
            
            try:
                page.click(selector, timeout=2000)
            except:
                # Fallback: click by coordinates
                page.mouse.click(event['x'], event['y'])
        
        elif event_type == 'scroll':
            print(f"[{event_num}/{total_events}] 📜 Scroll: {event['scrollY']}px")
            page.evaluate(f"window.scrollTo({event.get('scrollX', 0)}, {event['scrollY']})")
        
        elif event_type == 'keypress':
            key = event['key']
            print(f"[{event_num}/{total_events}] ⌨️  Keypress: {key}")
            page.keyboard.press(key)
        
        elif event_type == 'mousemove':
            # Only log every 10th mousemove to avoid spam
            if event_num % 10 == 0:
                print(f"[{event_num}/{total_events}] 🖱️  Mouse move: ({event['x']}, {event['y']})")
            page.mouse.move(event['x'], event['y'])


def main():
    parser = argparse.ArgumentParser(
        description='Replay a recorded session'
    )
    parser.add_argument(
        '--recording',
        required=True,
        help='Path to recording JSON file'
    )
    parser.add_argument(
        '--html',
        help='HTML file or URL to replay on (optional, uses recording default)'
    )
    parser.add_argument(
        '--speed',
        type=float,
        default=1.0,
        help='Playback speed multiplier (default: 1.0)'
    )
    
    args = parser.parse_args()
    
    # Check if recording file exists
    if not Path(args.recording).exists():
        print(f"Error: Recording file not found: {args.recording}")
        exit(1)
    
    # Replay session
    replayer = SessionReplayer(args.recording, args.html)
    replayer.replay(speed=args.speed)


if __name__ == "__main__":
    main()
