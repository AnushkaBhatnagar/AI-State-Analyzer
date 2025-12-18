#!/usr/bin/env python3
"""
Enhanced server for Instagram AI State Analyzer with state-based code editor
Provides API endpoints for editing code specific to each state defined in states_schema.json
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json
import os
from pathlib import Path
from datetime import datetime
import webbrowser
import threading
import time
import re

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

PORT = 8000
BASE_DIR = Path(__file__).parent

# Load states schema
STATES_SCHEMA = None
with open(BASE_DIR / 'states_schema.json', 'r') as f:
    STATES_SCHEMA = json.load(f)

# Serve static files
@app.route('/')
def index():
    return send_from_directory(BASE_DIR, 'index.html')

@app.route('/state-editor')
def state_editor():
    """Serve the state editor panel"""
    return send_from_directory(BASE_DIR, 'state_editor_panel.html')

@app.route('/states_schema.json')
def states_schema():
    """Serve the states schema"""
    return send_from_directory(BASE_DIR, 'states_schema.json')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(BASE_DIR, path)

# API: Get all states with their metadata
@app.route('/api/states', methods=['GET'])
def get_states():
    try:
        return jsonify({
            'success': True,
            'states': STATES_SCHEMA.get('states', []),
            'metadata': STATES_SCHEMA.get('metadata', {})
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# API: Get code for a specific state
@app.route('/api/state/<int:state_id>/code', methods=['GET'])
def get_state_code(state_id):
    try:
        # Find the state in schema
        state = next((s for s in STATES_SCHEMA['states'] if s['id'] == state_id), None)
        if not state:
            return jsonify({
                'success': False,
                'error': f'State {state_id} not found in schema'
            }), 404
        
        # Read index.html
        index_file = BASE_DIR / 'index.html'
        with open(index_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract code based on state
        state_code = extract_state_code(content, state_id, state)
        
        return jsonify({
            'success': True,
            'state': state,
            'code': state_code,
            'functions': state_code.get('functions', []),
            'variables': state_code.get('variables', [])
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# API: Save state code modification
@app.route('/api/state/<int:state_id>/save', methods=['POST'])
def save_state_code(state_id):
    try:
        data = request.json
        modified_code = data.get('code', '')
        changes_description = data.get('changes', [])
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Find the state
        state = next((s for s in STATES_SCHEMA['states'] if s['id'] == state_id), None)
        if not state:
            return jsonify({
                'success': False,
                'error': f'State {state_id} not found'
            }), 404
        
        # Create MD file for this state modification
        md_content = f"""# State {state_id} - {state['name']} Modification Request

## Metadata
- **State ID:** {state_id}
- **State Name:** {state['name']}
- **Description:** {state['description']}
- **Timestamp:** {timestamp}
- **Status:** Pending ⏳

---

## State Details

**Detection Condition:**
```
{state['detection_condition']}
```

**Range Description:**
{state['range_description']}

**Key Variables:**
"""
        
        if state.get('key_variables'):
            for var in state['key_variables']:
                md_content += f"- `{var['name']}` ({var['type']}): {var['purpose']}\n"
        
        md_content += f"""

---

## Changes Requested

"""
        
        if changes_description:
            for i, change in enumerate(changes_description, 1):
                md_content += f"{i}. {change}\n"
        else:
            md_content += "User modified the state code directly.\n"
        
        md_content += f"""

---

## Modified Code for State {state_id}

```javascript
{modified_code}
```

---

## Interactive Elements in this State

"""
        
        if state.get('interactive_elements'):
            for elem in state['interactive_elements']:
                md_content += f"- **{elem['name']}** (selector: `{elem['selector']}`): {elem['type']}\n"
        
        md_content += f"""

---

## Instructions for Cline

Please apply these changes to `index.html` for **State {state_id} ({state['name']})**:

1. Locate the functions and code that apply to this state
2. Replace with the modified version above
3. Ensure proper formatting and syntax
4. Test that the state transitions work correctly
5. Save the file

**Functions typically involved in State {state_id}:**
"""
        
        # Add relevant function hints based on state
        if state_id == 0:
            md_content += "- `document.addEventListener('DOMContentLoaded', ...)` - Signup form setup\n"
            md_content += "- Check input validation\n"
        elif state_id == 1:
            md_content += "- `loadFeed()` - Load initial posts\n"
            md_content += "- `createPost()` - Create post elements\n"
            md_content += "- `handleLike()` - Handle like interactions\n"
            md_content += "- `startNotificationTimer()` - Start notifications\n"
        elif state_id == 2:
            md_content += "- `setupChat()` - Initialize chat\n"
            md_content += "- `openChat()` - Open chat overlay\n"
            md_content += "- `sendChatMessage()` - Send messages\n"
            md_content += "- `getAIChatResponse()` - Get AI responses\n"
        elif state_id == 3:
            md_content += "- `upgradeCategory()` - Escalate posts\n"
            md_content += "- `showIOSNotification()` - Show notifications\n"
            md_content += "- `processRevealQueue()` - Show escalated posts\n"
        
        md_content += f"""

---

## After Applying

Once you've applied these changes:
1. Confirm the changes were applied successfully
2. Update this file's status to "Applied ✅"
3. Test State {state_id} ({state['name']}) transitions

---

**Generated by:** Instagram AI State Analyzer - State Editor
**File:** state_{state_id}_modifications.md
**Created:** {timestamp}
"""
        
        # Save to MD file
        md_filename = f'state_{state_id}_modifications.md'
        md_file = BASE_DIR / md_filename
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        # Also append to history
        history_file = BASE_DIR / 'state_modifications_history.md'
        history_entry = f"""
## {timestamp} - State {state_id} ({state['name']})

**Changes:**
"""
        if changes_description:
            for change in changes_description:
                history_entry += f"- {change}\n"
        else:
            history_entry += "- Direct code modification\n"
        
        history_entry += f"**Status:** Pending ⏳\n**File:** {md_filename}\n\n---\n"
        
        # Append to history (create if doesn't exist)
        if history_file.exists():
            with open(history_file, 'a', encoding='utf-8') as f:
                f.write(history_entry)
        else:
            with open(history_file, 'w', encoding='utf-8') as f:
                f.write("# State Modification History\n\n")
                f.write(history_entry)
        
        return jsonify({
            'success': True,
            'message': f'State {state_id} modification saved to {md_filename}',
            'file': str(md_file),
            'instruction': f'Ask Cline: "Apply the state {state_id} modifications from {md_filename}"'
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# API: Get function code from index.html
@app.route('/api/get-function/<function_name>', methods=['GET'])
def get_function(function_name):
    try:
        index_file = BASE_DIR / 'index.html'
        
        if not index_file.exists():
            return jsonify({
                'success': False,
                'error': 'index.html not found'
            }), 404
        
        with open(index_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract function code using brace counting for proper nesting
        pattern = rf'function {function_name}\s*\([^)]*\)\s*\{{'
        match = re.search(pattern, content)
        
        if match:
            start_pos = match.start()
            brace_start = match.end() - 1  # Position of opening brace
            
            # Count braces to find matching closing brace
            brace_count = 1
            pos = brace_start + 1
            
            while pos < len(content) and brace_count > 0:
                if content[pos] == '{':
                    brace_count += 1
                elif content[pos] == '}':
                    brace_count -= 1
                pos += 1
            
            if brace_count == 0:
                function_code = content[start_pos:pos]
                return jsonify({
                    'success': True,
                    'code': function_code
                })
        
        return jsonify({
            'success': False,
            'error': f'Function {function_name} not found'
        }), 404
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def extract_state_code(content, state_id, state):
    """Extract relevant code for a given state"""
    code_info = {
        'state_id': state_id,
        'state_name': state['name'],
        'functions': [],
        'variables': [],
        'full_code': ''
    }
    
    # Define function mappings for each state
    state_functions = {
        0: [  # Signup State
            'DOMContentLoaded event listener',
            'nameInput event listener',
            'usernameInput event listener',
            'signupBtn click handler',
            'checkInputs function'
        ],
        1: [  # Feed State
            'loadFeed',
            'createPost',
            'setupInteractions',
            'handleLike',
            'showMeanDM',
            'startNotificationTimer',
            'scheduleNextNotification'
        ],
        2: [  # Chat State
            'setupChat',
            'openChat',
            'closeChat',
            'sendChatMessage',
            'getAIChatResponse',
            'addChatMessage'
        ],
        3: [  # Escalated Feed State
            'upgradeCategory',
            'processRevealQueue',
            'showIOSNotification',
            'handleLike'
        ]
    }
    
    # Extract relevant functions
    functions = state_functions.get(state_id, [])
    for func_name in functions:
        pattern = rf'function {func_name}\s*\([^)]*\)\s*\{{'
        match = re.search(pattern, content)
        if match:
            start_pos = match.start()
            brace_start = match.end() - 1
            brace_count = 1
            pos = brace_start + 1
            
            while pos < len(content) and brace_count > 0:
                if content[pos] == '{':
                    brace_count += 1
                elif content[pos] == '}':
                    brace_count -= 1
                pos += 1
            
            if brace_count == 0:
                func_code = content[start_pos:pos]
                code_info['functions'].append({
                    'name': func_name,
                    'code': func_code
                })
    
    # Extract relevant variables
    if state.get('key_variables'):
        for var in state['key_variables']:
            code_info['variables'].append({
                'name': var['name'],
                'type': var['type'],
                'purpose': var['purpose'],
                'initial_value': var['value']
            })
    
    # Build full code snippet
    full_code = f"// State {state_id}: {state['name']}\n"
    full_code += f"// {state['description']}\n\n"
    
    for func in code_info['functions']:
        full_code += func['code'] + "\n\n"
    
    code_info['full_code'] = full_code
    
    return code_info

def open_browser():
    """Open browser after server starts"""
    time.sleep(1.5)
    url = f"http://localhost:{PORT}/state-editor"
    print(f"\n🌐 Opening State Editor: {url}\n")
    webbrowser.open(url)

def main():
    print("\n" + "="*70)
    print("INSTAGRAM AI STATE ANALYZER - STATE EDITOR SERVER")
    print("="*70)
    print(f"Server running at: http://localhost:{PORT}/")
    print(f"Serving directory: {BASE_DIR}")
    print()
    print("Available endpoints:")
    print(f"  • http://localhost:{PORT}/ - Main app")
    print(f"  • http://localhost:{PORT}/state-editor - State editor panel")
    print(f"  • http://localhost:{PORT}/api/states - Get all states")
    print(f"  • http://localhost:{PORT}/api/state/<id>/code - Get state code")
    print(f"  • http://localhost:{PORT}/api/state/<id>/save - Save state modifications")
    print()
    print("States (from states_schema.json):")
    if STATES_SCHEMA:
        for state in STATES_SCHEMA.get('states', []):
            print(f"  • State {state['id']}: {state['name']} - {state['description']}")
    print()
    print("="*70)
    print("Press Ctrl+C to stop the server")
    print("="*70 + "\n")
    
    # Open browser in background
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()
    
    # Start Flask server
    app.run(host='0.0.0.0', port=PORT, debug=False)

if __name__ == '__main__':
    main()
