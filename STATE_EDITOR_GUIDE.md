# 🎨 Stage Editor System - Complete Guide

Visual editor for modifying individual stages with persistent changes through Cline integration.

## 🌟 Overview

The Stage Editor System provides a **visual interface** for editing stage-specific code with changes that **persist** to your `index.html` file through Cline integration.

### The Workflow:

```
Browser Editor → Save to MD → Ask Cline → Apply to index.html → Test Changes
```

---

## 🚀 Quick Start

### Step 1: Record a Session (One Time)

```bash
cd /Users/riya/Desktop/anushka_project/AI-State-Analyzer/playwright_recorder
source venv/bin/activate
python record_session.py --html ../index.html --capture-snapshots
```

**What to do:**
- Interact with your app through all stages
- Press Ctrl+S when done
- Snapshots are saved automatically

### Step 2: Start the Enhanced Server

```bash
cd /Users/riya/Desktop/anushka_project/AI-State-Analyzer
python server_enhanced.py
```

The browser will open automatically to the Stage Editor.

### Step 3: Edit a Stage

1. **Select a session** from the dropdown
2. **Click on a stage** (e.g., "Stage 2: FOMO")
3. **Edit the code** in the editor
4. **Click "Save Changes"**
5. **Ask Cline**: "Apply the stage modifications from stage_modifications.md"
6. **Click "Test Stage"** to see your changes

---

## 📋 Complete Workflow Example

### Scenario: Making Stage 2 More Intense

**1. Open Stage Editor**
```bash
python server_enhanced.py
```

**2. Select Stage 2**
- Session: `session_001`
- Click: "Stage 2: FOMO"
- Code loads automatically

**3. Modify the Code**

Find this line:
```javascript
}, Math.max(notificationSpeed, 400));
```

Change to:
```javascript
}, Math.max(notificationSpeed, 200));  // Faster!
```

Find this line:
```javascript
if (Math.random() < 0.3) {
```

Change to:
```javascript
if (Math.random() < 0.6) {  // More frequent!
```

**4. Save Changes**
- Click "💾 Save Changes"
- You'll see: "✅ Saved! Now ask Cline: ..."

**5. Apply with Cline**

In Cline chat, say:
```
Apply the stage modifications from stage_modifications.md
```

Cline will:
- Read the MD file
- Find `startStage2()` in `index.html`
- Replace it with your modified version
- Save the file

**6. Test Your Changes**
- Click "▶️ Test Stage"
- Stage 2 loads instantly
- See your modifications in action!

---

## 🎯 System Components

### 1. Enhanced Server (`server_enhanced.py`)

**Features:**
- Serves the Stage Editor UI
- API endpoints for saving modifications
- Loads snapshots and function code
- Saves changes to MD files

**API Endpoints:**
- `POST /api/save-modification` - Save stage modifications
- `GET /api/snapshots` - List available sessions
- `GET /api/load-stage/<session>/<stage>` - Load stage snapshot
- `GET /api/get-function/<name>` - Get function code

### 2. Stage Editor UI (`stage_editor_panel.html`)

**Features:**
- Visual stage selection
- Code editor with syntax highlighting
- One-click stage loading
- Save to MD file
- Test stage button

**Interface:**
```
┌─────────────────────────────────────────────────┐
│  🎨 Stage Editor                                │
├──────────────┬──────────────────────────────────┤
│ Select Stage │ Edit Code                        │
│              │                                  │
│ Session:     │ function startStage2() {         │
│ [dropdown]   │   var interval = setInterval...  │
│              │   ...                            │
│ Stage 0      │   }, Math.max(speed, 400));     │
│ Stage 1      │ }                                │
│ Stage 2 ●    │                                  │
│ Stage 3      │ [🔄 Reload] [▶️ Test] [💾 Save] │
│ Stage 4      │                                  │
└──────────────┴──────────────────────────────────┘
```

### 3. MD File Format (`stage_modifications.md`)

**Purpose:** Intermediary between browser and Cline

**Structure:**
```markdown
# Stage Modification Request

## Metadata
- Stage: 2
- Function: startStage2()
- Timestamp: 2024-01-15 14:30:00
- Status: Pending ⏳

## Modified Function Code

```javascript
function startStage2() {
    // Your modified code here
}
```

## Instructions for Cline

Please apply these changes to `index.html`:
1. Locate the `startStage2()` function
2. Replace it with the modified version above
3. Save the file
```

### 4. Modification History (`stage_modifications_history.md`)

**Purpose:** Track all modifications over time

**Example:**
```markdown
# Stage Modification History

## 2024-01-15 14:30:00 - Stage 2 (startStage2)
**Changes:**
- User modified the function code in the visual editor
**Status:** Applied ✅

## 2024-01-15 15:00:00 - Stage 3 (startStage3)
**Changes:**
- Increased chaos level
**Status:** Pending ⏳
```

---

## 🔧 Stage Configuration

### Stage-to-Function Mapping

| Stage | Name | Function | Description |
|-------|------|----------|-------------|
| 0 | Idle | `startHell()` | Initial positive notifications |
| 1 | Questioning | `startHell()` | Questioning and FOMO begins |
| 2 | FOMO | `startStage2()` | Fear of missing out intensifies |
| 3 | Chaos | `startStage3()` | Notification chaos |
| 4 | Hell | `startHell4()` | Notification hell mode |

### Common Modifications

#### Speed Changes
```javascript
// BEFORE:
}, Math.max(notificationSpeed, 400));

// AFTER (slower):
}, Math.max(notificationSpeed, 800));

// AFTER (faster):
}, Math.max(notificationSpeed, 200));
```

#### Probability Changes
```javascript
// BEFORE:
if (Math.random() < 0.3) {  // 30% chance

// AFTER (more frequent):
if (Math.random() < 0.6) {  // 60% chance

// AFTER (less frequent):
if (Math.random() < 0.1) {  // 10% chance
```

#### Threshold Changes
```javascript
// BEFORE:
if (notificationCount >= 50) {  // Transition at 50

// AFTER (earlier):
if (notificationCount >= 40) {  // Transition at 40

// AFTER (later):
if (notificationCount >= 60) {  // Transition at 60
```

---

## 💡 Tips & Best Practices

### When to Re-record

**Re-record if you:**
- Added new state variables
- Changed stage transition thresholds significantly
- Restructured the DOM
- Want fresh, accurate snapshots

**Don't re-record if you:**
- Just tweaking timing/speed
- Changing visual styles
- Modifying message content
- Making small behavior adjustments

### Editing Tips

1. **Start Small** - Make one change at a time
2. **Test Frequently** - Use "Test Stage" button after each change
3. **Save Often** - Save modifications before testing
4. **Check History** - Review `stage_modifications_history.md` to track changes

### Cline Integration

**Best Practices:**
- Be specific: "Apply the stage modifications from stage_modifications.md"
- Verify: Ask Cline to confirm changes were applied
- Update status: Ask Cline to mark modifications as "Applied ✅"

---

## 🆘 Troubleshooting

### "No sessions found"

**Problem:** No snapshots available

**Solution:**
```bash
cd playwright_recorder
source venv/bin/activate
python record_session.py --html ../index.html --capture-snapshots
```

### "Error loading function"

**Problem:** Function not found in index.html

**Solution:**
- Check that the function name is correct
- Verify `index.html` exists
- Make sure the function hasn't been renamed

### "Snapshot not found"

**Problem:** Stage snapshot doesn't exist

**Solution:**
- Record a session with `--capture-snapshots`
- Make sure you progressed through all stages
- Check `playwright_recorder/snapshots/` directory

### Changes not persisting

**Problem:** Modifications don't save to index.html

**Solution:**
1. Click "Save Changes" in editor
2. Ask Cline to apply modifications
3. Wait for Cline to confirm
4. Refresh browser to see changes

### Server won't start

**Problem:** Port 8000 already in use

**Solution:**
```bash
# Kill existing server
lsof -ti:8000 | xargs kill -9

# Or use different port (edit server_enhanced.py)
PORT = 8001
```

---

## 📊 File Structure

```
AI-State-Analyzer/
├── server_enhanced.py              # Enhanced Flask server
├── stage_editor_panel.html         # Visual editor UI
├── stage_modifications.md          # Current modifications (generated)
├── stage_modifications_history.md  # Modification history (generated)
├── index.html                      # Your app (modified by Cline)
└── playwright_recorder/
    ├── snapshots/
    │   └── session_001/
    │       ├── stage_0.json
    │       ├── stage_1.json
    │       ├── stage_2.json
    │       ├── stage_3.json
    │       └── stage_4.json
    ├── record_session.py
    ├── test_stage.py
    └── extract_stage.py
```

---

## 🎯 Command Reference

### Recording
```bash
# Record with snapshots
cd playwright_recorder
source venv/bin/activate
python record_session.py --html ../index.html --capture-snapshots
```

### Server
```bash
# Start enhanced server
cd /Users/riya/Desktop/anushka_project/AI-State-Analyzer
python server_enhanced.py
```

### Testing (Command Line)
```bash
# Test a specific stage
cd playwright_recorder
source venv/bin/activate
python test_stage.py --session session_001 --stage 2 --html ../index.html
```

### Cline Commands
```
# Apply modifications
"Apply the stage modifications from stage_modifications.md"

# Check status
"Show me the contents of stage_modifications.md"

# Verify changes
"Confirm that the changes to startStage2() were applied successfully"
```

---

## ✅ Benefits

1. **Visual Editing** - Edit code in browser, not text editor
2. **Persistent Changes** - Modifications saved to index.html via Cline
3. **Rapid Testing** - Test stages instantly without replaying
4. **Change Tracking** - History of all modifications
5. **Safe Workflow** - Cline reviews changes before applying
6. **No File Access Issues** - Browser saves to MD, Cline applies to files

---

## 🚀 Next Steps

1. **Record your first session** with snapshots
2. **Start the enhanced server**
3. **Edit a stage** in the visual editor
4. **Save and apply** with Cline
5. **Test your changes** instantly

For more information:
- Stage Isolation: `playwright_recorder/STAGE_ISOLATION.md`
- Main README: `README.md`
- Commands: `COMMANDS.txt`

---

**Happy Editing! 🎨**
