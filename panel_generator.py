import json
from pathlib import Path

class StatePanelGenerator:
    def __init__(self, states_json):
        """
        Initialize the panel generator with states JSON schema.
        
        Args:
            states_json (dict): The states JSON data from StateDetectionAnalyzer
        """
        self.states = states_json
        self.metadata = states_json.get('metadata', {})
        self.state_list = states_json.get('states', [])
    
    def generate_panel_css(self):
        """
        Generate CSS for the state panel with dynamic colors for each state.
        
        Returns:
            str: CSS code for the panel
        """
        css = """
        body {
            zoom: 0.7;
        }
        
        .view-toggle-container {
            position: fixed;
            top: 20px;
            left: 20px;
            z-index: 10000;
            background: rgba(20, 20, 20, 0.95);
            border-radius: 8px;
            padding: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
            display: flex;
            gap: 8px;
        }
        
        .view-toggle-btn {
            background: rgba(255, 255, 255, 0.1);
            color: rgba(255, 255, 255, 0.7);
            border: 1px solid rgba(255, 255, 255, 0.2);
            padding: 8px 16px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .view-toggle-btn:hover {
            background: rgba(255, 255, 255, 0.2);
            color: rgba(255, 255, 255, 0.9);
        }
        
        .view-toggle-btn.active {
            background: #667eea;
            color: white;
            border-color: #667eea;
        }
        
        .original-view-container {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: 9999;
            background: white;
            display: none;
        }
        
        .original-view-container.active {
            display: block;
        }
        
        .original-view-iframe {
            width: 100%;
            height: 100%;
            border: none;
        }
        
        .state-panel {
            position: fixed;
            right: 0;
            top: 0;
            bottom: 0;
            width: 450px;
            background: rgba(20, 20, 20, 0.95);
            border-left: 2px solid rgba(255, 255, 255, 0.1);
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            box-shadow: -5px 0 15px rgba(0, 0, 0, 0.5);
            z-index: 1000;
        }

        .stage-segment {
            flex: 1;
            border-bottom: 2px solid rgba(255, 255, 255, 0.1);
            padding: 12px;
            display: flex;
            flex-direction: column;
            transition: all 0.3s ease;
            opacity: 0.5;
        }
        
        .segment-content {
            display: flex;
            gap: 12px;
            flex: 1;
        }
        
        .logging-column {
            flex: 0 0 160px;
        }
        
        .params-column {
            flex: 1;
            overflow-y: auto;
        }
        
        .param-item {
            background: rgba(0, 0, 0, 0.3);
            border-radius: 6px;
            padding: 8px;
            margin-bottom: 8px;
            font-size: 11px;
            line-height: 1.4;
            position: relative;
            transition: all 0.3s ease;
        }
        
        .param-item.highlighted {
            border: 2px solid #2ecc71;
            box-shadow: 0 0 10px rgba(46, 204, 113, 0.5);
            background: rgba(46, 204, 113, 0.15);
        }
        
        .param-name {
            color: rgba(255, 255, 255, 0.9);
            font-weight: bold;
            margin-bottom: 3px;
            font-size: 12px;
        }
        
        .param-id, .param-state, .param-mod {
            color: rgba(255, 255, 255, 0.6);
            font-size: 10px;
        }
        
        .param-id {
            color: rgba(100, 200, 255, 0.8);
            position: relative;
        }
        
        .copy-icon {
            position: absolute;
            top: 6px;
            right: 6px;
            cursor: pointer;
            opacity: 0.8;
            transition: all 0.2s;
            font-size: 18px;
            color: rgba(255, 255, 255, 0.9);
            z-index: 10;
        }
        
        .copy-icon:hover {
            opacity: 1;
            color: rgba(100, 200, 255, 1);
            transform: scale(1.15);
        }
        
        .copy-icon.copied {
            color: #2ecc71;
        }

        .stage-segment:last-child {
            border-bottom: none;
        }

        .stage-segment.active {
            opacity: 1;
            box-shadow: inset 0 0 20px rgba(255, 255, 255, 0.1);
            border: 2px solid rgba(255, 255, 255, 0.3);
        }

        .stage-header {
            color: white;
            font-size: 13px;
            font-weight: bold;
            margin-bottom: 4px;
            text-transform: uppercase;
            letter-spacing: 1px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .jump-button {
            background: rgba(255, 255, 255, 0.1);
            color: rgba(255, 255, 255, 0.8);
            border: 1px solid rgba(255, 255, 255, 0.2);
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 10px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .jump-button:hover {
            background: rgba(255, 255, 255, 0.2);
            border-color: rgba(255, 255, 255, 0.4);
            transform: scale(1.05);
        }
        
        .jump-button:active {
            transform: scale(0.95);
        }

        .stage-range {
            color: rgba(255, 255, 255, 0.6);
            font-size: 10px;
            margin-bottom: 8px;
        }

        .dots-container {
            display: flex;
            flex-wrap: wrap;
            gap: 5px;
            align-content: flex-start;
        }

        .dot {
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.6);
            animation: dotAppear 0.3s ease-out;
        }

        @keyframes dotAppear {
            from {
                transform: scale(0);
                opacity: 0;
            }
            to {
                transform: scale(1);
                opacity: 1;
            }
        }

        .state-highlight {
            border: 2px solid #2ecc71 !important;
            box-shadow: 0 0 15px rgba(46, 204, 113, 0.6) !important;
            animation: highlightPulse 2s infinite;
        }

        @keyframes highlightPulse {
            0%, 100% { box-shadow: 0 0 15px rgba(46, 204, 113, 0.6); }
            50% { box-shadow: 0 0 25px rgba(46, 204, 113, 0.9); }
        }
"""
        
        # Generate state-specific CSS
        for state in self.state_list:
            state_id = state['id']
            colors = state['color_theme']
            
            css += f"""
        .stage-segment.stage-{state_id} {{
            background: linear-gradient(135deg, {colors['primary']} 0%, {colors['primary']} 100%);
        }}

        .stage-segment.stage-{state_id}.active {{
            background: linear-gradient(135deg, {colors['active']} 0%, {colors['active']} 100%);
            border-color: {colors['border']};
            box-shadow: inset 0 0 30px {colors['active']};
        }}

        .stage-{state_id} .dot {{
            background: {colors['border']};
            box-shadow: 0 0 5px {colors['border']};
        }}
"""
        
        return css
    
    def generate_panel_html(self):
        """
        Generate HTML for the state panel segments.
        
        Returns:
            str: HTML code for the panel
        """
        # Add view toggle buttons and iframe container
        html = '''
<!-- View Toggle Controls -->
<div class="view-toggle-container">
    <button class="view-toggle-btn active" id="analysisViewBtn" onclick="switchToAnalysisView()">
        Analysis View
    </button>
    <button class="view-toggle-btn" id="originalViewBtn" onclick="switchToOriginalView()">
        Original View
    </button>
</div>

<!-- Original View (iframe) -->
<div class="original-view-container" id="originalViewContainer">
    <iframe class="original-view-iframe" id="originalViewIframe" src="index.html"></iframe>
</div>

'''
        
        html += '<div class="state-panel" id="statePanel">\n'
        
        for state in self.state_list:
            state_id = state['id']
            state_name = state['name']
            state_desc = state.get('range_description', state['description'])
            
            # Determine if this is the initial active state
            active_class = ' active' if state_id == 0 else ''
            
            html += f'''
    <div class="stage-segment stage-{state_id}{active_class}" id="state{state_id}">
        <div class="stage-header">
            State {state_id}: {state_name}
            <button class="jump-button" onclick="jumpToState({state_id})">Jump</button>
        </div>
        <div class="stage-range">{state_desc}</div>
        <div class="segment-content">
            <div class="logging-column">
                <div class="dots-container" id="state{state_id}Dots"></div>
            </div>
            <div class="params-column">
'''
            
            # Add interactive elements
            for element in state.get('interactive_elements', []):
                selector = element['selector']
                name = element['name']
                elem_state = element.get('state', 'N/A')
                onclick = element.get('onclick', 'N/A')
                
                html += f'''
                <div class="param-item">
                    <span class="copy-icon" onclick="copyElementHTML('{selector}')" title="Copy HTML">⎘</span>
                    <div class="param-name">{name}</div>
                    <div class="param-id">Selector: {selector}</div>
                    <div class="param-state">State: {elem_state}</div>
                    <div class="param-mod">Action: {onclick}</div>
                </div>
'''
            
            # Add key variables
            for variable in state.get('key_variables', []):
                var_name = variable['name']
                var_value = variable.get('value', 'N/A')
                var_purpose = variable.get('purpose', 'N/A')
                
                html += f'''
                <div class="param-item">
                    <span class="copy-icon" onclick="copyElementHTML('{var_name}')" title="Copy value">⎘</span>
                    <div class="param-name">{var_name}</div>
                    <div class="param-id">Variable</div>
                    <div class="param-state">Value: {var_value}</div>
                    <div class="param-mod">Purpose: {var_purpose}</div>
                </div>
'''
            
            html += '''
            </div>
        </div>
    </div>
'''
        
        html += '</div>\n'
        return html
    
    def generate_tracking_js(self):
        """
        Generate JavaScript for state tracking and UI updates.
        
        Returns:
            str: JavaScript code for tracking
        """
        state_var = self.metadata.get('state_variable', 'stage')
        counter_var = self.metadata.get('primary_counter', 'count')
        
        # Create state name mapping for console logs
        state_names_map = {state['id']: state['name'] for state in self.state_list}
        
        js = f"""
    var currentTrackedState = 0;
    var stateSegments = {{}};
    var stateNames = {json.dumps(state_names_map)};
    
    function initStatePanel() {{
        stateSegments = {{
"""
        
        for state in self.state_list:
            state_id = state['id']
            js += f"            {state_id}: document.getElementById('state{state_id}Dots'),\n"
        
        js += """        };
    }
    
    // Variable finder - searches window object for variables in any scope
    function findVariable(varName) {
        // Try direct global access first
        try {
            if (typeof window[varName] !== 'undefined') {
                return window[varName];
            }
        } catch(e) {}
        
        // Search through window properties for objects containing the variable
        try {
            for (let key in window) {
                if (window[key] && typeof window[key] === 'object') {
                    try {
                        if (varName in window[key]) {
                            return window[key][varName];
                        }
                    } catch(e) {}
                }
            }
        } catch(e) {}
        
        return undefined;
    }
    
    function getCurrentState() {
        // Hybrid detection: Try variable-based first, fall back to DOM-based
"""
        
        # Generate hybrid detection for each state
        for i, state in enumerate(self.state_list):
            state_id = state['id']
            condition = state.get('detection_condition', '')
            dom_detection = state.get('dom_detection', {})
            
            js += f"""        
        // State {state_id}: {state['name']}
        try {{
            // Try variable-based detection
"""
            
            if condition:
                # Extract variable names from the condition
                import re
                variables = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', condition)
                
                # Generate variable lookups
                for var in set(variables):
                    if var not in ['true', 'false', 'null', 'undefined', 'Array', 'Math']:
                        js += f"            const {var} = findVariable('{var}');\n"
                
                js += f"            if ({condition}) return {state_id};\n"
            
            js += """        } catch(e) {
            // Variables not accessible, try DOM-based detection
        }
        
        try {
            // DOM-based fallback detection
"""
            
            # Generate DOM detection logic
            if dom_detection:
                checks = []
                
                # Check visible elements
                visible_elements = dom_detection.get('visible_elements', [])
                for selector in visible_elements:
                    checks.append(f"checkVisible('{selector}')")
                
                # Check hidden elements
                hidden_elements = dom_detection.get('hidden_elements', [])
                for selector in hidden_elements:
                    checks.append(f"checkHidden('{selector}')")
                
                # Check classes
                has_class = dom_detection.get('has_class', [])
                for item in has_class:
                    if isinstance(item, dict):
                        selector = item.get('selector', '')
                        class_name = item.get('class', '')
                        checks.append(f"checkClass('{selector}', '{class_name}')")
                
                # Check text content
                text_content = dom_detection.get('text_content', [])
                for item in text_content:
                    if isinstance(item, dict):
                        selector = item.get('selector', '')
                        contains = item.get('contains', '')
                        # Escape single quotes in the text content
                        contains_escaped = contains.replace("'", "\\'")
                        checks.append(f"checkText('{selector}', '{contains_escaped}')")
                
                if checks:
                    js += f"            if ({' && '.join(checks)}) return {state_id};\n"
            
            js += """        } catch(e) {
            // DOM detection also failed
        }
"""
        
        js += f"""        
        // If all detection fails, stay in current state
        return currentTrackedState;
    }}
    
    // Helper function to get formatted timestamp
    function getTimestamp() {{
        const now = new Date();
        return now.toLocaleTimeString('en-US', {{ 
            hour: '2-digit', 
            minute: '2-digit', 
            second: '2-digit', 
            hour12: true 
        }});
    }}
    
    // DOM detection helper functions
    function checkVisible(selector) {{
        const el = document.querySelector(selector);
        if (!el) return false;
        const style = window.getComputedStyle(el);
        return style.display !== 'none' && 
               style.visibility !== 'hidden' && 
               el.offsetParent !== null &&
               !el.classList.contains('hidden');
    }}
    
    function checkHidden(selector) {{
        const el = document.querySelector(selector);
        if (!el) return true; // Element not existing counts as hidden
        const style = window.getComputedStyle(el);
        return style.display === 'none' || 
               style.visibility === 'hidden' || 
               el.offsetParent === null ||
               el.classList.contains('hidden');
    }}
    
    function checkClass(selector, className) {{
        const el = document.querySelector(selector);
        return el ? el.classList.contains(className) : false;
    }}
    
    function checkText(selector, text) {{
        const el = document.querySelector(selector);
        return el ? el.textContent.includes(text) : false;
    }}
    
    function updateStateHighlight() {{
        var newState = getCurrentState();
        if (newState !== currentTrackedState) {{
            var oldState = currentTrackedState;
            currentTrackedState = newState;
            
            // Console log the state change with timestamp and state names
            var timestamp = getTimestamp();
            var oldStateName = stateNames[oldState] || 'Unknown';
            var newStateName = stateNames[newState] || 'Unknown';
            console.log(
                '%c[State Change] ' + timestamp + ' %c| State ' + oldState + ' (' + oldStateName + ') → State ' + newState + ' (' + newStateName + ')',
                'color: #2ecc71; font-weight: bold;',
                'color: #3498db;'
            );
            
            // Update state panel highlighting
            for (var i = 0; i < {len(self.state_list)}; i++) {{
                var segment = document.getElementById('state' + i);
                if (segment) {{
                    if (i === currentTrackedState) {{
                        segment.classList.add('active');
                    }} else {{
                        segment.classList.remove('active');
                    }}
                }}
            }}
            
            // Highlight UI elements when state changes
            highlightUIElements(currentTrackedState);
        }}
    }}
    
    function highlightUIElements(state) {{
        // Remove all previous highlights from page elements
        var allElements = document.querySelectorAll('.state-highlight');
        allElements.forEach(function(el) {{
            el.classList.remove('state-highlight');
        }});
        
        // Remove all previous highlights from panel items
        var allPanelItems = document.querySelectorAll('.param-item.highlighted');
        allPanelItems.forEach(function(item) {{
            item.classList.remove('highlighted');
        }});
        
        // Add highlights based on current state
        var stateConfig = getStateConfig(state);
        if (stateConfig && stateConfig.elements) {{
            stateConfig.elements.forEach(function(elementInfo) {{
                // Skip disabled elements
                if (elementInfo.state === 'disabled') return;
                
                var selector = elementInfo.selector;
                
                // Highlight page elements
                var elements = document.querySelectorAll(selector);
                elements.forEach(function(el) {{
                    el.classList.add('state-highlight');
                }});
                
                // Highlight corresponding panel items
                var panelItems = document.querySelectorAll('.param-item');
                panelItems.forEach(function(item) {{
                    var selectorText = item.querySelector('.param-id');
                    if (selectorText && selectorText.textContent.includes(selector)) {{
                        item.classList.add('highlighted');
                    }}
                }});
            }});
        }}
    }}
    
    function getStateConfig(stateId) {{
        var configs = {{
"""
        
        for state in self.state_list:
            state_id = state['id']
            # Include both selector and state info
            elements = [
                {'selector': elem['selector'], 'state': elem.get('state', 'enabled')} 
                for elem in state.get('interactive_elements', [])
            ]
            js += f"            {state_id}: {{ elements: {json.dumps(elements)} }},\n"
        
        js += """        };
        return configs[stateId];
    }
    
    function logNotificationDot() {
        var stateToLog = getCurrentState();
        var dotsContainer = stateSegments[stateToLog];
        if (dotsContainer) {
            var dot = document.createElement('div');
            dot.className = 'dot';
            dotsContainer.appendChild(dot);
        }
        
        updateStateHighlight();
    }
    
    function copyElementHTML(selector) {
        var element;
        
        // Handle different selector types
        if (selector.startsWith('#') || selector.startsWith('.')) {
            element = document.querySelector(selector);
        } else {
            // Variable name - try to get its value
            try {
                var value = eval(selector);
                navigator.clipboard.writeText(selector + ' = ' + JSON.stringify(value));
                
                // Visual feedback
                if (event && event.target) {
                    var icon = event.target;
                    icon.classList.add('copied');
                    setTimeout(function() {
                        icon.classList.remove('copied');
                    }, 500);
                }
                return;
            } catch(e) {
                console.warn('Could not evaluate:', selector);
                return;
            }
        }
        
        if (element) {
            var html = element.outerHTML;
            navigator.clipboard.writeText(html).then(function() {
                // Visual feedback
                if (event && event.target) {
                    var icon = event.target;
                    icon.classList.add('copied');
                    setTimeout(function() {
                        icon.classList.remove('copied');
                    }, 500);
                }
            }).catch(function(err) {
                console.error('Failed to copy:', err);
            });
        } else {
            console.warn('Element not found:', selector);
        }
    }
    
    // Set variable value in any scope
    function setVariable(varName, value) {
        // Try direct global set
        try {
            window[varName] = value;
            return true;
        } catch(e) {}
        
        // Search through window properties for objects containing the variable
        try {
            for (let key in window) {
                if (window[key] && typeof window[key] === 'object') {
                    try {
                        if (varName in window[key]) {
                            window[key][varName] = value;
                            return true;
                        }
                    } catch(e) {}
                }
            }
        } catch(e) {}
        
        return false;
    }
    
    function jumpToState(targetState) {
        console.log('Jump to state', targetState, '- functionality not implemented');
    }
    
    // View switching functions
    function switchToOriginalView() {
        // Show iframe container
        document.getElementById('originalViewContainer').classList.add('active');
        
        // Update button states
        document.getElementById('originalViewBtn').classList.add('active');
        document.getElementById('analysisViewBtn').classList.remove('active');
    }
    
    function switchToAnalysisView() {
        // Hide iframe container
        document.getElementById('originalViewContainer').classList.remove('active');
        
        // Update button states
        document.getElementById('analysisViewBtn').classList.add('active');
        document.getElementById('originalViewBtn').classList.remove('active');
    }
    
    // Initialize on page load
    window.addEventListener('DOMContentLoaded', function() {
        initStatePanel();
        updateStateHighlight();
        // Highlight initial state elements
        highlightUIElements(currentTrackedState);
        
        // Set up MutationObserver to watch for dynamically created elements
        var observer = new MutationObserver(function(mutations) {
            // Re-highlight when new elements are added to DOM
            highlightUIElements(currentTrackedState);
        });
        
        // Observe the main content area (exclude the state panel itself)
        var mainContent = document.body;
        if (mainContent) {
            observer.observe(mainContent, {
                childList: true,  // Watch for added/removed children
                subtree: true      // Watch entire tree
            });
        }
    });
    
    // Periodically check for state changes (lighter polling for state detection only)
    setInterval(updateStateHighlight, 500);
"""
        
        return js
    
    def generate_complete_html(self, original_html_path):
        """
        Generate the complete HTML file with injected state panel.
        
        Args:
            original_html_path (str): Path to the original HTML file
            
        Returns:
            str: Complete HTML with state panel injected
        """
        # Read original HTML
        with open(original_html_path, 'r', encoding='utf-8') as f:
            original_html = f.read()
        
        # Generate components
        css = self.generate_panel_css()
        panel_html = self.generate_panel_html()
        tracking_js = self.generate_tracking_js()
        
        # Inject CSS
        if '<style>' in original_html:
            original_html = original_html.replace('<style>', f'<style>\n{css}\n')
        else:
            # Add style tag in head
            original_html = original_html.replace('</head>', f'<style>\n{css}\n</style>\n</head>')
        
        # Inject panel HTML - find the appropriate insertion point
        # Try to inject before closing body tag
        if '</body>' in original_html:
            original_html = original_html.replace('</body>', f'{panel_html}\n</body>')
        else:
            original_html += panel_html
        
        # Inject tracking JavaScript
        if '</script>' in original_html:
            # Find the last script tag
            last_script_pos = original_html.rfind('</script>')
            original_html = (original_html[:last_script_pos + 9] + 
                           f'\n<script>\n{tracking_js}\n</script>' + 
                           original_html[last_script_pos + 9:])
        else:
            # Add before closing body tag
            original_html = original_html.replace('</body>', f'<script>\n{tracking_js}\n</script>\n</body>')
        
        return original_html
    
    def save_to_file(self, output_path, original_html_path):
        """
        Generate and save the complete HTML file.
        
        Args:
            output_path (str): Path to save the output HTML
            original_html_path (str): Path to the original HTML file
        """
        try:
            complete_html = self.generate_complete_html(original_html_path)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(complete_html)
            
            print(f"[OK] Generated state panel HTML: {output_path}")
            
        except Exception as e:
            raise Exception(f"Error saving HTML: {str(e)}")


def main():
    """
    Test function to generate panel from states_schema.json
    """
    try:
        # Load the states JSON
        with open('states_schema.json', 'r', encoding='utf-8') as f:
            states_data = json.load(f)
        
        print("Generating state panel...")
        print("=" * 50)
        
        # Initialize generator
        generator = StatePanelGenerator(states_data)
        
        # Generate and save complete HTML
        generator.save_to_file(
            output_path='index_with_panel.html',
            original_html_path='index.html'
        )
        
        print("\n[OK] Panel generation complete!")
        print("[OK] Open index_with_panel.html to view the result")
        
    except FileNotFoundError:
        print("Error: states_schema.json not found.")
        print("Run state_analyzer.py first to generate the schema.")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
