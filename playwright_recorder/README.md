# Playwright Session Recorder

Record and replay user interactions with web applications automatically.

## Features

✅ **Simple Recording** - Just interact naturally, everything is captured  
✅ **Perfect Replay** - Replays your exact actions with precise timing  
✅ **Generic** - Works with ANY web application  
✅ **Adjustable Speed** - Replay at 2x, 0.5x, or any speed  
✅ **No Code Required** - Just point and click  

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers (one time)
python -m playwright install chromium
```

## Quick Start

### Step 1: Record a Session

```bash
python record_session.py --html ../index.html --output my_recording.json
```

**What happens:**
1. Browser opens with your app
2. **Live counter shows events being recorded** (updates in real-time!)
3. You interact normally (click, scroll, type, etc.)
4. Every action is recorded automatically
5. **Press Ctrl+S to save and stop** OR close browser to auto-save
6. Recording is saved to JSON file

**New Features:**
- 🔴 **Live Event Counter** - See exactly how many events are recorded in real-time
- ⌨️ **Ctrl+S Shortcut** - Save and stop without closing browser (green border flash confirms)
- 💾 **Smart Auto-Save** - Closes gracefully and saves all events automatically
- 🔄 **Continuous Polling** - Events are collected every 0.5s, nothing is lost

### Step 2: Replay the Session

```bash
python replay_session.py --recording my_recording.json
```

**What happens:**
1. Browser opens with your app
2. Your exact actions replay automatically
3. Same timing, same clicks, same everything
4. Browser stays open to see the result

## Usage

### Recording

```bash
# Basic recording
python record_session.py --html index.html --output recording.json

# Record from URL
python record_session.py --html http://localhost:8000/index.html --output recording.json

# Custom output name
python record_session.py --html app.html --output user_test_001.json
```

### Replaying

```bash
# Basic replay (uses HTML from recording)
python replay_session.py --recording recording.json

# Replay on different HTML (testing code changes)
python replay_session.py --recording recording.json --html index_v2.html

# Replay at 2x speed
python replay_session.py --recording recording.json --speed 2.0

# Replay in slow motion (0.5x)
python replay_session.py --recording recording.json --speed 0.5
```

## What Gets Recorded

The recorder captures:
- 🖱️ **Clicks** - Every click with position and target element
- 📜 **Scrolls** - Scroll position changes
- ⌨️ **Keypresses** - All keyboard input
- 🖱️ **Mouse movements** - Cursor position (throttled)

## Recording Format

Recordings are saved as JSON:

```json
{
  "session_id": "session_20251119_201600",
  "timestamp": "2025-11-19T20:16:00",
  "html_path": "index.html",
  "duration_seconds": 45.3,
  "events": [
    {
      "type": "click",
      "selector": ".start-button",
      "x": 187,
      "y": 400,
      "timestamp": 0.5
    },
    {
      "type": "click",
      "selector": ".notification",
      "x": 200,
      "y": 250,
      "timestamp": 3.2
    },
    {
      "type": "scroll",
      "scrollY": 300,
      "scrollX": 0,
      "timestamp": 8.1
    }
  ]
}
```

## Use Cases

### 1. Bug Reproduction
```bash
# User reports bug
# Record their session
python record_session.py --html index.html --output bug_report.json

# Developer replays to see bug
python replay_session.py --recording bug_report.json
```

### 2. Regression Testing
```bash
# Record on version 1
python record_session.py --html index_v1.html --output test_flow.json

# After making changes, replay on version 2
python replay_session.py --recording test_flow.json --html index_v2.html
# Does it still work the same way?
```

### 3. User Studies
```bash
# Record 10 participants
python record_session.py --html index.html --output participant_001.json
python record_session.py --html index.html --output participant_002.json
# ... etc

# Analyze later by replaying
python replay_session.py --recording participant_001.json
```

### 4. Documentation/Demos
```bash
# Record the "correct" usage
python record_session.py --html index.html --output demo.json

# Replay for presentations
python replay_session.py --recording demo.json --speed 1.5
```

## Example: Recording Your Notification Hell App

```bash
# Terminal 1: Start server (if needed)
cd ..
python server.py

# Terminal 2: Record session
cd playwright_recorder
python record_session.py --html http://localhost:8000/index.html --output notification_session.json

# Browser opens
# You interact:
# - Click Start
# - Click some notifications  
# - Try escape button
# - See what happens
# Close browser when done

# Output:
# ✅ Recording saved: notification_session.json
# 📊 Summary:
#    • Duration: 45.3 seconds
#    • Events recorded: 87
#    • Session ID: session_20251119_201600

# Later, replay it:
python replay_session.py --recording notification_session.json
```

## Tips

**For Recording:**
- Interact naturally - the recorder captures everything
- You can take your time - timing is preserved
- Close browser to finish recording
- Console shows what's being captured in real-time

**For Replay:**
- Use `--speed 2.0` to speed through long recordings
- Use `--speed 0.5` to see details in slow motion
- Replay on modified HTML to test changes
- Browser stays open after replay to inspect results

## Troubleshooting

### Browser doesn't open
```bash
python -m playwright install chromium
```

### Recording not saving
Make sure you close the browser window (don't just press Ctrl+C)

### Replay doesn't work on modified HTML
Some selectors may have changed. The recorder tries coordinates as fallback.

### Events not capturing
Open browser console during recording - you should see "🔴 Recorded..." messages

## Advanced Usage

### Programmatic Access

```python
from record_session import SessionRecorder
from replay_session import SessionReplayer

# Record
recorder = SessionRecorder('index.html')
recorder.record()
recorder.save('output.json')

# Replay
replayer = SessionReplayer('output.json')
replayer.replay(speed=2.0)
```

### Analyzing Recordings

```python
import json

with open('recording.json') as f:
    data = json.load(f)

# Count click events
clicks = [e for e in data['events'] if e['type'] == 'click']
print(f"Total clicks: {len(clicks)}")

# Find when user tried to escape
escape_clicks = [e for e in clicks if 'escape' in e['selector'].lower()]
print(f"Escape attempts: {len(escape_clicks)}")
```

## Research Applications

- **Engagement Metrics** - How long until users try to escape?
- **A/B Testing** - Same user flow on different versions
- **Bug Detection** - Capture exact reproduction steps
- **UX Analysis** - What do users click most?
- **Code Quality** - Do changes break existing flows?

## License

MIT License - Free to use for research and commercial purposes

## Credits

Built for AI code analysis research - recording user interactions with AI-generated applications.
