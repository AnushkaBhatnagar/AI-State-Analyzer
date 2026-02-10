#!/usr/bin/env python3
"""
Enhanced server for AI State Analyzer with fully data-driven state editor.
Dynamically extracts code based on states_schema.json without hardcoded mappings.
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
try:
    with open(BASE_DIR / 'states_schema.json', 'r', encoding='utf-8') as f:
        STATES_SCHEMA = json.load(f)
except Exception as e:
    print(f"Error loading states_schema.json: {e}")
    STATES_SCHEMA = {"states": []}

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
        # Reload schema to ensure fresh data
        with open(BASE_DIR / 'states_schema.json', 'r', encoding='utf-8') as f:
            current_schema = json.load(f)
            
        return jsonify({
            'success': True,
            'states': current_schema.get('states', []),
            'metadata': current_schema.get('metadata', {}),
            'injection_hooks': current_schema.get('injection_hooks', [])
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
        # Reload schema
        with open(BASE_DIR / 'states_schema.json', 'r', encoding='utf-8') as f:
            current_schema = json.load(f)
            
        # Find the state in schema
        state = next((s for s in current_schema['states'] if s['id'] == state_id), None)
        if not state:
            return jsonify({
                'success': False,
                'error': f'State {state_id} not found in schema'
            }), 404
        
        # Read index.html
        index_file = BASE_DIR / 'index.html'
        with open(index_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract code based on state metadata
        state_code = extract_state_code_dynamic(content, state, current_schema)
        
        return jsonify({
            'success': True,
            'state': state,
            'code': state_code,
            'extracted_functions': state_code.get('functions', []),
            'extracted_variables': state_code.get('variables', [])
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
        
        # Reload schema
        with open(BASE_DIR / 'states_schema.json', 'r', encoding='utf-8') as f:
            current_schema = json.load(f)
            
        # Find the state
        state = next((s for s in current_schema['states'] if s['id'] == state_id), None)
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

## State Details from Schema

**Detection Condition:**
```javascript
{state.get('detection_condition', 'N/A')}
```

**Range Description:**
{state.get('range_description', 'N/A')}

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
                if 'onclick' in elem:
                    md_content += f"  - OnClick: `{elem['onclick']}`\n"
        
        md_content += f"""

---

## Instructions for Cline

Please apply these changes to `index.html` for **State {state_id} ({state['name']})**:

1. Locate the functions and code that apply to this state based on the context provided above.
2. Replace with the modified version.
3. Ensure proper formatting and syntax.
4. Save the file.

---

**Generated by:** AI State Analyzer - Data-Driven State Editor
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
                f.write("# Stage Modification History\n\n")
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

def extract_function_code(content, func_name):
    """Extract a single function's code from content"""
    # Try different function definition styles
    patterns = [
        rf'function {func_name}\s*\([^)]*\)\s*\{{',  # function name() {
        rf'(?:const|let|var)\s+{func_name}\s*=\s*(?:async\s*)?function\s*\([^)]*\)\s*\{{',  # const name = function() {
        rf'(?:const|let|var)\s+{func_name}\s*=\s*(?:async\s*)?\([^)]*\)\s*=>\s*\{{',  # const name = () => {
    ]
    
    for pattern in patterns:
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
                return content[start_pos:pos]
    
    return None

def extract_state_code_dynamic(content, state, full_schema):
    """
    Dynamically extract code relevant to a state based on the JSON schema.
    No hardcoded mappings allowed!
    """
    code_info = {
        'state_id': state['id'],
        'state_name': state['name'],
        'functions': [],
        'variables': [],
        'full_code': ''
    }
    
    # 1. Identify relevant function names from schema
    relevant_function_names = set()
    
    # From interactive_elements (onclick handlers)
    if state.get('interactive_elements'):
        for elem in state['interactive_elements']:
            if 'onclick' in elem:
                # Extract function name from onclick string (e.g. "terminalAction('start')")
                # Matches "name(" or "name ("
                onclick = elem['onclick']
                match = re.match(r'([a-zA-Z0-9_]+)\s*\(', onclick)
                if match:
                    relevant_function_names.add(match.group(1))
    
    # From injection_hooks (if any exist globally that reference this state's variables)
    if full_schema.get('injection_hooks'):
        state_vars = {v['name'] for v in state.get('key_variables', [])}
        for hook in full_schema['injection_hooks']:
            # If the hook modifies a variable used in this state
            if hook.get('variable') in state_vars:
                # Extract function name from scope_context (e.g. "showScene function")
                scope = hook.get('scope_context', '')
                match = re.match(r'([a-zA-Z0-9_]+)\s+function', scope)
                if match:
                    relevant_function_names.add(match.group(1))
    
    # From detection_strategy (primary_checks)
    if state.get('detection_strategy') and state['detection_strategy'].get('primary_checks'):
        for check in state['detection_strategy']['primary_checks']:
             # Extract function name from check string (e.g. "checkVisible('#terminal')")
            match = re.match(r'([a-zA-Z0-9_]+)\s*\(', check)
            if match:
                relevant_function_names.add(match.group(1))

    # 2. Extract code for identified functions
    for func_name in relevant_function_names:
        func_code = extract_function_code(content, func_name)
        if func_code:
            code_info['functions'].append({
                'name': func_name,
                'code': func_code,
                'source': 'schema_inference'
            })
    
    # 3. Extract variable declarations (naive approach)
    if state.get('key_variables'):
        for var in state['key_variables']:
            var_name = var['name']
            # Look for "let name =" or "var name =" or "const name ="
            pattern = rf'(?:let|var|const)\s+{var_name}\s*=[^;]*;'
            match = re.search(pattern, content)
            if match:
                code_info['variables'].append({
                    'name': var_name,
                    'code': match.group(0),
                    'source': 'variable_declaration'
                })
    
    # 4. Build full code snippet
    full_code = f"// State {state['id']}: {state['name']}\n"
    full_code += f"// {state.get('description', '')}\n\n"
    
    if code_info['variables']:
        full_code += "// --- Key Variables ---\n"
        for var in code_info['variables']:
            full_code += var['code'] + "\n"
        full_code += "\n"
        
    if code_info['functions']:
        full_code += "// --- Related Functions (Extracted from Schema) ---\n"
        for func in code_info['functions']:
            full_code += func['code'] + "\n\n"
    
    if not code_info['functions'] and not code_info['variables']:
        full_code += "// No specific functions or variables identified in schema for this state.\n"
        full_code += "// Please check states_schema.json 'interactive_elements' or 'key_variables'.\n"
        full_code += "// Showing a snippet of index.html instead:\n\n"
        full_code += content[:500] + "\n..."
            
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
    print("AI STATE ANALYZER - DATA-DRIVEN SERVER")
    print("="*70)
    print(f"Server running at: http://localhost:{PORT}/")
    print(f"Serving directory: {BASE_DIR}")
    print()
    print("Available endpoints:")
    print(f"  • http://localhost:{PORT}/ - Main app")
    print(f"  • http://localhost:{PORT}/state-editor - State editor panel")
    print(f"  • http://localhost:{PORT}/api/states - Get all states (JSON)")
    print(f"  • http://localhost:{PORT}/api/state/<id>/code - Get dynamic state code")
    print(f"  • http://localhost:{PORT}/api/state/<id>/save - Save state modifications")
    print()
    print("Configuration:")
    print(f"  • Loading schema from: states_schema.json")
    if STATES_SCHEMA:
        print(f"  • Found {len(STATES_SCHEMA.get('states', []))} states")
    else:
        print("  • WARNING: states_schema.json not found or invalid")
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
