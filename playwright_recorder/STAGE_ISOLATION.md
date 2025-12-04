# Stage Isolation System

Complete guide to using stage isolation for rapid iterative development on the Instagram notification app.

## Overview

The stage isolation system allows you to:
1. **Record once** - Capture snapshots at each stage boundary
2. **Modify any stage** - Edit code for a specific stage
3. **Test instantly** - Jump directly to that stage without replaying previous stages
4. **Iterate rapidly** - Test changes in ~30 seconds instead of 3+ minutes

## Quick Start

### 1. Record a Session with Snapshots

```bash
cd playwright_recorder
source venv/bin/activate
python record_session.py --html ../index.html --capture-snapshots
```

**What happens:**
- Browser opens with your Instagram app
- Interact through all stages (0 → 1 → 2 → 3 → 4)
- Snapshots are automatically captured at each stage transition
- Press Ctrl+S to save

**Output:**
- `recordings/session_001.json` - Full recording
- `snapshots/session_001/stage_0.json` - Stage 0 snapshot
- `snapshots/session_001/stage_1.json` - Stage 1 snapshot
- `snapshots/session_001/stage_2.json` - Stage 2 snapshot
- `snapshots/session_001/stage_3.json` - Stage 3 snapshot
- `snapshots/session_001/stage_4.json` - Stage 4 snapshot

### 2. List Available Sessions

```bash
python extract_stage.py --list
```

### 3. List Stages in a Session

```bash
python extract_stage.py --list-stages session_001
```

### 4. Test a Specific Stage

```bash
python test_stage.py --session session_001 --stage 2 --html ../index.html
```

**What happens:**
- Browser opens
- State from end of Stage 1 is restored instantly
- Stage 2 begins
- You can interact and see your modifications

## Development Workflow

### Scenario: Modifying Stage 2 (FOMO Stage)

**Step 1: Record Once (One Time)**
```bash
python record_session.py --html ../index.html --capture-snapshots
# Interact through all stages, press Ctrl+S
```

**Step 2: Modify Stage 2 Code**
```bash
# Open index.html in your editor
# Find startStage2() function
# Make your changes (e.g., change notification speed)
```

**Step 3: Test Stage 2**
```bash
python test_stage.py --session session_001 --stage 2 --html ../index.html
# Stage 2 loads instantly with your changes!
```

**Step 4: Iterate**
```bash
# Modify code again
# Test again (30 seconds)
# Repeat until perfect
```

## Stage Information

### Stage 0: Idle
- **Range:** 0-15 notifications
- **Description:** Initial positive notifications
- **Function:** `startHell()` (initial part)

### Stage 1: Questioning  
- **Range:** 16-50 notifications
- **Description:** Questioning and FOMO begins
- **Function:** `startStage2()` (transition logic)

### Stage 2: FOMO
- **Range:** 51-100 notifications
- **Description:** Fear of missing out intensifies
- **Function:** `startStage2()`

### Stage 3: Chaos
- **Range:** 101-150 notifications
- **Description:** Notification chaos
- **Function:** `startStage3()`

### Stage 4: Hell
- **Range:** 150+ notifications
- **Description:** Notification hell mode
- **Function:** `startHell4()`

## What Gets Captured in Snapshots

Each snapshot contains:
- **State variables:**
  - `stage` - Current stage number
  - `notificationCount` - Number of notifications
  - `tapCount` - Number of taps
  - `notificationSpeed` - Current speed
  - `escapeAttempts` - Escape button clicks
  - `rewardStreak` - Reward streak count
  - `totalRewards` - Total rewards earned
  - `isHellMode` - Hell mode flag
  
- **DOM state:**
  - Complete HTML of `contentArea`
  - All visible notifications
  - Their positions and styles

## Common Commands

### Recording
```bash
# Record with snapshots
python record_session.py --html ../index.html --capture-snapshots

# Record from URL
python record_session.py --html http://localhost:8000/index.html --capture-snapshots
```

### Listing
```bash
# List all sessions
python extract_stage.py --list

# List stages in a session
python extract_stage.py --list-stages session_001
```

### Testing
```bash
# Test Stage 0
python test_stage.py --session session_001 --stage 0 --html ../index.html

# Test Stage 2
python test_stage.py --session session_001 --stage 2 --html ../index.html

# Test Stage 4 (hell mode)
python test_stage.py --session session_001 --stage 4 --html ../index.html
```

## Tips & Best Practices

### When to Re-record

**Re-record if you:**
- Added new state variables
- Changed stage transition thresholds significantly
- Restructured the DOM
- Want clean, accurate snapshots

**Don't re-record if you:**
- Just tweaking timing/speed
- Changing visual styles
- Modifying message content
- Making small behavior adjustments

### Modifying Code

**Safe modifications (no re-recording needed):**
- Notification speed/timing
- Colors and animations
- Message text
- Probabilities and frequencies

**Risky modifications (may need re-recording):**
- Adding new variables
- Changing stage transition logic
- Removing variables
- Changing DOM structure

### Time Savings

**Without stage isolation:**
- Modify Stage 3 → Wait through Stages 0, 1, 2 → Test Stage 3 (3+ minutes)
- 10 iterations = 30+ minutes

**With stage isolation:**
- Modify Stage 3 → Test Stage 3 directly (30 seconds)
- 10 iterations = 5 minutes
- **6x faster!**

## Troubleshooting

### "Snapshot not found"
```bash
# Make sure you recorded with --capture-snapshots
python record_session.py --html ../index.html --capture-snapshots
```

### "No module named instagram_config"
```bash
# Make sure you're in the playwright_recorder directory
cd playwright_recorder
source venv/bin/activate
```

### Stage doesn't load correctly
```bash
# The snapshot might be outdated after major code changes
# Re-record to get fresh snapshots
python record_session.py --html ../index.html --capture-snapshots
```

### Variables are undefined
```bash
# Add default values in your code:
if (typeof anxietyLevel === 'undefined') {
    anxietyLevel = 0;
}
```

## File Structure

```
playwright_recorder/
├── recordings/
│   └── session_001.json          # Full recording
├── snapshots/
│   └── session_001/               # Session snapshots
│       ├── stage_0.json           # Stage 0 state
│       ├── stage_1.json           # Stage 1 state
│       ├── stage_2.json           # Stage 2 state
│       ├── stage_3.json           # Stage 3 state
│       ├── stage_4.json           # Stage 4 state
│       └── metadata.json          # Session metadata
├── instagram_config.py            # Instagram app configuration
├── record_session.py              # Recording tool
├── extract_stage.py               # Stage extraction tool
├── test_stage.py                  # Stage testing tool
└── STAGE_ISOLATION.md            # This file
```

## Advanced Usage

### Programmatic Access

```python
from test_stage import load_snapshot, restore_state

# Load a snapshot
snapshot = load_snapshot('session_001', 2)

# Access snapshot data
print(f"Stage: {snapshot['stage']}")
print(f"Notifications: {snapshot['notificationCount']}")
print(f"Taps: {snapshot['tapCount']}")
```

### Custom Stage Testing

```python
from playwright.sync_api import sync_playwright
from test_stage import restore_state, load_snapshot

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto('file:///path/to/index.html')
    
    # Load and restore Stage 2
    snapshot = load_snapshot('session_001', 2)
    restore_state(page, snapshot)
    
    # Now interact or test
    page.click('.notification')
    
    browser.close()
```

## Next Steps

1. **Record your first session with snapshots**
2. **Try modifying a stage**
3. **Test it with stage isolation**
4. **Experience the speed improvement!**

For more information, see the main [README.md](README.md).
