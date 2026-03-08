import json
import os
from pathlib import Path
import re

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
        self.injection_hooks = states_json.get('injection_hooks', [])
    
    def inject_code_hooks(self, html_content):
        """
        Inject reporting hooks using both manual patterns and intelligent auto-detection.
        """
        # 1. Manual Hooks (from AI)
        modified_content = self._inject_manual_hooks(html_content)
        
        # 2. Auto-Discovery Hooks (Tokenizer-based)
        modified_content = self._inject_auto_hooks(modified_content)
        
        return modified_content

    def _inject_manual_hooks(self, html_content):
        """Process explicit hooks defined in the schema"""
        if not self.injection_hooks:
            return html_content
            
        print(f"Injecting {len(self.injection_hooks)} manual code hooks...")
        modified_content = html_content
        
        for hook in self.injection_hooks:
            variable = hook.get('variable')
            pattern = hook.get('search_pattern')
            injection_type = hook.get('injection_type', 'after')
            
            if not variable or not pattern:
                continue
            
            # Extract full access path from search_pattern (e.g. "this.gameState.currentTantrum")
            lhs_match = re.search(r'([\w$]+(?:\.[\w$]+)*\.' + re.escape(variable) + r')\b', pattern)
            full_access = lhs_match.group(1) if lhs_match else variable
            report_code = f" try {{ window.__ai_state_monitor.report('{variable}', {full_access}); }} catch(e) {{}} "
            safe_pattern = re.escape(pattern).replace(r'\ ', r'\s*') # More flexible whitespace
            
            try:
                if injection_type == 'after':
                    modified_content = re.sub(
                        safe_pattern, 
                        lambda m: m.group(0) + report_code, 
                        modified_content, 
                        count=1
                    )
                elif injection_type == 'before':
                    modified_content = re.sub(
                        safe_pattern, 
                        lambda m: report_code + m.group(0), 
                        modified_content, 
                        count=1
                    )
            except Exception as e:
                print(f"Warning: Failed to inject hook for {variable}: {e}")
                
        return modified_content

    def _inject_auto_hooks(self, html_content):
        """
        Intelligently scan JS code for variable assignments and inject reporting hooks.
        Uses a robust tokenizer approach to avoid comments and strings.
        """
        # Collect target variables
        target_vars = set()
        
        # From metadata
        if 'state_variable' in self.metadata:
            target_vars.add(self.metadata['state_variable'])
        if 'primary_counter' in self.metadata:
            target_vars.add(self.metadata['primary_counter'])
            
        # From states
        for state in self.state_list:
            for var in state.get('key_variables', []):
                if isinstance(var, dict) and 'name' in var:
                    target_vars.add(var['name'])
                    
        if not target_vars:
            return html_content
            
        print(f"Auto-injecting hooks for {len(target_vars)} variables: {', '.join(target_vars)}")
        
        # Split HTML to find scripts
        # Simple split by <script> tags
        parts = re.split(r'(<script[^>]*>.*?</script>)', html_content, flags=re.DOTALL | re.IGNORECASE)
        
        processed_parts = []
        for part in parts:
            if part.lower().startswith('<script') and not 'src=' in part.lower():
                # Extract content inside script tag
                match = re.match(r'(<script[^>]*>)(.*?)(</script>)', part, re.DOTALL | re.IGNORECASE)
                if match:
                    start_tag, script_code, end_tag = match.groups()
                    modified_code = self._process_script_content(script_code, target_vars)
                    processed_parts.append(f"{start_tag}{modified_code}{end_tag}")
                else:
                    processed_parts.append(part)
            else:
                processed_parts.append(part)
                
        return "".join(processed_parts)

    def _process_script_content(self, code, target_vars):
        """
        Tokenize and inject hooks into JavaScript code.
        """
        result = []
        i = 0
        length = len(code)
        last_append = 0
        
        def peek(offset=1):
            if i + offset < length:
                return code[i + offset]
            return ''

        while i < length:
            char = code[i]
            
            # Skip Strings
            if char in ('"', "'", "`"):
                quote = char
                i += 1
                while i < length:
                    if code[i] == '\\':
                        i += 2 # Skip escaped char
                        continue
                    if code[i] == quote:
                        i += 1
                        break
                    i += 1
                continue
                
            # Skip Comments
            if char == '/':
                if peek() == '/': # Single line
                    i += 2
                    while i < length and code[i] != '\n':
                        i += 1
                    continue
                elif peek() == '*': # Multi line
                    i += 2
                    while i < length - 1:
                        if code[i] == '*' and code[i+1] == '/':
                            i += 2
                            break
                        i += 1
                    continue
            
            # Check for Identifiers
            if char.isalpha() or char == '_' or char == '$':
                # Read full identifier
                start = i
                while i < length and (code[i].isalnum() or code[i] == '_' or code[i] == '$'):
                    i += 1
                identifier = code[start:i]
                
                # If it's a target variable
                if identifier in target_vars:
                    # Look ahead for assignment
                    # Skip whitespace
                    j = i
                    while j < length and code[j].isspace():
                        j += 1
                    
                    is_assignment = False
                    is_unary = False
                    
                    # Check for ++ or --
                    if j < length - 1 and code[j:j+2] in ('++', '--'):
                        is_unary = True
                        j += 2
                    # Check for =, +=, -=, *=, /=
                    elif j < length and code[j] == '=':
                        if j > 0 and code[j-1] in ('!', '<', '>', '='): # !=, <=, >=, ==, ===
                            pass # Not assignment
                        else:
                            is_assignment = True
                            j += 1
                    elif j < length - 1 and code[j+1] == '=' and code[j] in ('+', '-', '*', '/', '%'):
                        is_assignment = True
                        j += 2
                        
                    if is_assignment or is_unary:
                        # Found assignment!
                        end_pos = j
                        
                        if is_unary:
                            end_pos = j
                        else:
                            # Scan until ; or newline
                            paren_depth = 0
                            brace_depth = 0
                            in_val_string = False
                            val_quote = ''
                            
                            while end_pos < length:
                                c = code[end_pos]
                                
                                if in_val_string:
                                    if c == '\\':
                                        end_pos += 2
                                        continue
                                    if c == val_quote:
                                        in_val_string = False
                                    end_pos += 1
                                    continue
                                
                                if c in ('"', "'", "`"):
                                    in_val_string = True
                                    val_quote = c
                                    end_pos += 1
                                    continue
                                
                                if c == '(': paren_depth += 1
                                elif c == ')': paren_depth -= 1
                                elif c == '{': brace_depth += 1
                                elif c == '}': brace_depth -= 1
                                elif c == ';' and paren_depth == 0 and brace_depth == 0:
                                    end_pos += 1 # Include semicolon
                                    break
                                elif c == '\n' and paren_depth == 0 and brace_depth == 0:
                                    break
                                
                                end_pos += 1
                        
                        # Inject hook — use full property access chain (e.g. this.gameState.needsHug)
                        result.append(code[last_append:end_pos])

                        # Look backwards from identifier to capture "this.gameState." prefix
                        full_expr_start = start
                        while full_expr_start > 0 and code[full_expr_start - 1] == '.':
                            dot_pos = full_expr_start - 1
                            ident_end = dot_pos
                            ident_start = ident_end - 1
                            while ident_start >= 0 and (code[ident_start].isalnum() or code[ident_start] in ('_', '$')):
                                ident_start -= 1
                            ident_start += 1
                            if ident_start < ident_end:
                                full_expr_start = ident_start
                            else:
                                break
                        full_lhs = code[full_expr_start:i]

                        hook = f"; try {{ window.__ai_state_monitor.report('{identifier}', {full_lhs}); }} catch(e) {{}} "
                        result.append(hook)
                        
                        last_append = end_pos
                        i = end_pos # Continue scanning from here
                        continue

            i += 1
            
        result.append(code[last_append:])
        return "".join(result)

    def generate_panel_css(self):
        """
        Generate CSS for the state panel with dynamic colors for each state.
        
        Returns:
            str: CSS code for the panel
        """
        css = """

        body {
            justify-content: flex-start !important;
            overflow: hidden !important;
        }
        #analysis-content-area {
            width: calc(100% - 450px);
            height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            overflow: hidden;
        }
        #game-container {
            transform-origin: center center;
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
            display: none;
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
        
        .param-item.full-width {
            width: 100%;
            margin-bottom: 12px;
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
        
        .header-button {
            background: rgba(255, 255, 255, 0.1);
            color: rgba(255, 255, 255, 0.8);
            border: 1px solid rgba(255, 255, 255, 0.2);
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 10px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .header-button:hover {
            background: rgba(255, 255, 255, 0.2);
            border-color: rgba(255, 255, 255, 0.4);
            transform: scale(1.05);
        }

        .header-button:active {
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

        .reanalyze-toolbar {
            position: sticky;
            top: 0;
            z-index: 1001;
            background: rgba(10, 10, 10, 0.98);
            border-bottom: 1px solid rgba(255, 255, 255, 0.15);
            padding: 8px 12px;
            display: flex;
            align-items: center;
            gap: 8px;
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            flex-shrink: 0;
        }

        .reanalyze-status {
            flex: 1;
            font-size: 11px;
            color: rgba(255, 255, 255, 0.6);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .reanalyze-status.running {
            color: #f39c12;
        }

        .reanalyze-status.error {
            color: #e74c3c;
        }

        .reanalyze-status.complete {
            color: #2ecc71;
        }

        .reanalyze-btn {
            background: rgba(255, 255, 255, 0.1);
            color: rgba(255, 255, 255, 0.8);
            border: 1px solid rgba(255, 255, 255, 0.2);
            padding: 5px 10px;
            border-radius: 4px;
            font-size: 10px;
            cursor: pointer;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            transition: all 0.2s;
            white-space: nowrap;
        }

        .reanalyze-btn:hover {
            background: rgba(255, 255, 255, 0.2);
        }

        .reanalyze-btn:disabled {
            opacity: 0.4;
            cursor: not-allowed;
        }

        .reanalyze-btn-primary {
            background: rgba(102, 126, 234, 0.3);
            border-color: #667eea;
        }

        .reanalyze-btn-full {
            background: rgba(231, 76, 60, 0.2);
            border-color: rgba(231, 76, 60, 0.5);
        }

        /* === Transitions / User Choices Section === */
        .transitions-section {
            margin-top: 10px;
            background: rgba(0, 0, 0, 0.5);
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 4px;
            padding: 10px 12px;
        }

        .transitions-label {
            color: rgba(255, 255, 255, 0.95);
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 8px;
        }

        .trans-group-label {
            font-size: 10px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin: 8px 0 6px 0;
            padding: 3px 8px;
            border-radius: 3px;
        }

        .trans-group-label.user-actions {
            color: rgba(0, 210, 211, 0.95);
            background: rgba(0, 210, 211, 0.1);
            border-bottom: 1px solid rgba(0, 210, 211, 0.3);
        }

        .trans-group-label.auto-transitions {
            color: rgba(241, 196, 15, 0.95);
            background: rgba(241, 196, 15, 0.08);
            border-bottom: 1px solid rgba(241, 196, 15, 0.25);
        }

        .transition-item {
            background: rgba(255, 255, 255, 0.04);
            border-radius: 5px;
            padding: 8px 10px;
            margin-bottom: 5px;
            font-size: 12px;
            border-left: 3px solid rgba(0, 210, 211, 0.5);
        }

        .transition-item.automatic {
            border-left-color: rgba(241, 196, 15, 0.6);
        }

        .transition-item.branching {
            border-left-color: rgba(0, 210, 211, 0.7);
        }

        .trans-flow {
            display: flex;
            align-items: center;
            gap: 6px;
            flex-wrap: wrap;
            font-size: 12px;
        }

        .trans-action-inline {
            color: rgba(255, 255, 255, 0.95);
            font-weight: 600;
        }

        .trans-element-inline {
            color: rgba(0, 210, 211, 0.6);
            font-family: monospace;
            font-size: 11px;
        }

        .trans-condition-inline {
            color: rgba(241, 196, 15, 0.8);
            font-family: monospace;
            font-size: 11px;
        }

        .trans-arrow, .branch-arrow {
            color: rgba(0, 210, 211, 0.9);
            font-weight: bold;
            font-size: 14px;
        }

        .target-state, .branch-target {
            color: rgba(0, 210, 211, 0.95);
            font-weight: 600;
            cursor: pointer;
        }

        .target-state:hover, .branch-target:hover {
            text-decoration: underline;
            color: #00d2d3;
        }

        .trans-auto-icon {
            font-size: 14px;
        }

        .trans-branch-container {
            margin-top: 6px;
            padding-left: 10px;
            border-left: 2px solid rgba(0, 210, 211, 0.25);
        }

        .trans-branch {
            display: flex;
            align-items: center;
            gap: 6px;
            margin-bottom: 5px;
            font-size: 12px;
        }

        .branch-outcome {
            background: rgba(0, 210, 211, 0.15);
            color: rgba(0, 210, 211, 0.95);
            padding: 2px 8px;
            border-radius: 8px;
            font-size: 10px;
            font-weight: 600;
            white-space: nowrap;
        }

        .branch-prob {
            color: rgba(255, 255, 255, 0.4);
            font-size: 10px;
            font-style: italic;
        }

        /* === Highlight Toggle Button === */
        .highlight-toggle-btn.active {
            background: rgba(46, 204, 113, 0.3);
            border-color: #2ecc71;
            color: #2ecc71;
        }

        .highlight-toggle-btn:not(.active) {
            background: rgba(255, 255, 255, 0.05);
            border-color: rgba(255, 255, 255, 0.2);
            color: rgba(255, 255, 255, 0.4);
        }

        /* === Global Branching Map === */
        .branching-map-container {
            position: sticky;
            top: 41px;
            z-index: 1000;
            background: rgba(10, 10, 10, 0.6);
            border-bottom: 2px solid rgba(255, 255, 255, 0.15);
            flex-shrink: 0;
        }

        .branching-map-header {
            color: rgba(255, 255, 255, 0.9);
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            padding: 10px 12px;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 6px;
            background: rgba(30, 30, 30, 0.8);
        }

        .branching-map-header:hover {
            background: rgba(40, 40, 40, 0.8);
        }


        .flow-diagram {
            padding: 12px;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 0;
        }

        .flow-node {
            width: 85%;
            max-width: 350px;
            padding: 8px 12px;
            border-radius: 6px;
            border: 2px solid;
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 13px;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .flow-node:hover {
            transform: scale(1.02);
            box-shadow: 0 0 10px rgba(255, 255, 255, 0.15);
        }

        .flow-node-active {
            box-shadow: 0 0 12px rgba(46, 204, 113, 0.5) !important;
            border-color: #2ecc71 !important;
        }

        .flow-node-id {
            background: rgba(0, 0, 0, 0.4);
            color: white;
            width: 22px;
            height: 22px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 12px;
            flex-shrink: 0;
        }

        .flow-node-name {
            color: rgba(255, 255, 255, 0.9);
            font-weight: 600;
            font-size: 13px;
        }

        .flow-node-text {
            display: flex;
            flex-direction: column;
            gap: 1px;
            min-width: 0;
            overflow: hidden;
        }

        .flow-node-desc {
            font-size: 11px;
            color: rgba(255, 255, 255, 0.5);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            font-weight: 400;
        }

        .flow-edge {
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 4px 0;
            min-height: 30px;
        }

        .flow-edge-label {
            font-size: 11px;
            color: rgba(255, 255, 255, 0.6);
            background: rgba(0, 0, 0, 0.3);
            padding: 2px 8px;
            border-radius: 10px;
            max-width: 300px;
            text-align: center;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .flow-arrow-down {
            color: rgba(46, 204, 113, 0.6);
            font-size: 14px;
            line-height: 1;
        }

        .branching-edge {
            background: rgba(155, 89, 182, 0.08);
            border-radius: 4px;
            padding: 4px 8px;
            width: 85%;
            max-width: 350px;
        }

        .flow-branches {
            display: flex;
            flex-direction: column;
            gap: 2px;
            padding-left: 12px;
        }

        .flow-branch-line {
            display: flex;
            align-items: center;
            gap: 4px;
            font-size: 9px;
        }

        .flow-branch-outcome {
            color: rgba(155, 89, 182, 0.9);
            font-weight: 600;
        }

        .flow-arrow {
            color: rgba(46, 204, 113, 0.6);
        }

        .flow-branch-target {
            color: rgba(46, 204, 113, 0.9);
            font-weight: 600;
            cursor: pointer;
        }

        .state-highlight {
            animation: highlightPulse 2s ease-out;
        }

        @keyframes highlightPulse {
            0% { box-shadow: 0 0 20px rgba(46, 204, 113, 0.8); }
            100% { box-shadow: none; }
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
            background: linear-gradient(135deg, {colors['primary']} 0%, {colors['primary']} 100%);
            border-color: {colors['border']};
        }}

        .stage-{state_id} .dot {{
            background: {colors['border']};
            box-shadow: 0 0 5px {colors['border']};
        }}
"""
        
        return css

    def generate_branching_map_html(self):
        """Render a button that opens the state flow map in a new tab."""
        if not self.states.get('mermaid_diagram', '').strip():
            return ''

        return '''
<div class="branching-map-container">
    <div class="branching-map-header" onclick="window.open('state-flow-diagram/state_flow_map.html','_blank')">
        STATE FLOW MAP &#8599;
    </div>
</div>
'''

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

        html += '<div class="state-panel" id="statePanel">'

        # Re-analysis toolbar (inside state panel, sticky at top)
        html += '''
<!-- Re-Analysis Toolbar -->
<div class="reanalyze-toolbar" id="reanalyzeToolbar">
    <div class="reanalyze-status" id="reanalyzeStatus">Ready</div>
    <button class="reanalyze-btn reanalyze-btn-primary" onclick="triggerReanalysis('incremental')" title="Incremental AI re-analysis (~15-25s)">Incremental Analysis</button>
    <button class="reanalyze-btn reanalyze-btn-full" onclick="triggerReanalysis('full')" title="Full from-scratch AI analysis (~20-30s)">Full Analysis</button>
    <button class="reanalyze-btn highlight-toggle-btn active" id="highlightToggleBtn" onclick="toggleExperienceHighlights()" title="Toggle element highlights on the experience">Highlights</button>
</div>
'''

        # Add global branching map at top of panel (sticky below toolbar)
        html += self.generate_branching_map_html()

        for state in self.state_list:
            state_id = state['id']
            state_name = state['name']
            state_desc = state.get('range_description', state['description'])
            
            # Get new fields
            user_desc = state.get('user_facing_description', 'No description available.')
            trigger_logic = state.get('trigger_logic', 'false')

            # Determine if this is the initial active state
            active_class = ' active' if state_id == 0 else ''

            html += f'''
    <div class="stage-segment stage-{state_id}{active_class}" id="state{state_id}">
        <div class="stage-header">
            State {state_id}: {state_name}
            <div style="display: flex; gap: 4px;">
                <button class="header-button" onclick="copyStateCode({state_id})">Copy Code</button>
                <button class="header-button" onclick="copyStateReference({state_id})">Copy Ref</button>
            </div>
        </div>
        <div class="stage-range">{state_desc}</div>

        <!-- State Logic & Description (Full Width) -->
        <div style="margin-top: 10px; margin-bottom: 10px;">
            <div class="param-item full-width" style="border-left: 3px solid #3498db; margin-bottom: 8px;">
                <span class="copy-icon" onclick="copyDescription({state_id})" title="Copy Description">⎘</span>
                <div class="param-name">Description</div>
                <div class="param-id" style="white-space: pre-wrap; color: rgba(255,255,255,0.8); font-size: 12px;">{user_desc}</div>
            </div>

            <div class="param-item full-width" style="border-left: 3px solid #f39c12; margin-bottom: 8px;">
                <span class="copy-icon" onclick="copyTriggerLogic({state_id})" title="Copy Logic">⎘</span>
                <div class="param-name">Trigger Logic</div>
                <div class="param-id" style="font-family: monospace; color: #f39c12; font-size: 11px;">{trigger_logic}</div>
            </div>
        </div>

        <div class="segment-content">
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

            # Add transitions / user choices (always visible, no dropdown)
            transitions = state.get('transitions', [])
            if transitions:
                user_transitions = [t for t in transitions if t.get('type') == 'user_action']
                auto_transitions = [t for t in transitions if t.get('type') == 'automatic']

                html += f'''
                <div class="transitions-section">
                    <div class="transitions-label">User Choices &amp; Transitions ({len(transitions)})</div>
'''

                if user_transitions:
                    html += '                    <div class="trans-group-label user-actions">User Actions</div>\n'
                    for t in user_transitions:
                        trigger = t.get('trigger', {})
                        action_desc = trigger.get('description', 'Unknown action')
                        element = trigger.get('element', '')
                        branches = t.get('branches')

                        if branches:
                            elem_html = f' <span class="trans-element-inline">{element}</span>' if element else ''
                            html += f'''
                    <div class="transition-item branching">
                        <div class="trans-flow" style="margin-bottom: 4px;">
                            <span class="trans-action-inline">{action_desc}</span>{elem_html}
                        </div>
                        <div class="trans-branch-container">
'''
                            for branch in branches:
                                target_name = branch.get('target_state_name', '?')
                                target_id = branch.get('target_state_id', '?')
                                outcome = branch.get('outcome', '')
                                prob = branch.get('probability', '')
                                prob_html = f' <span class="branch-prob">{prob}</span>' if prob else ''
                                html += f'''
                            <div class="trans-branch">
                                <span class="branch-outcome">{outcome}</span>
                                <span class="branch-arrow">&#8594;</span>
                                <span class="branch-target" data-state="{target_id}">State {target_id}: {target_name}</span>{prob_html}
                            </div>
'''
                            html += '                        </div>\n                    </div>\n'
                        else:
                            target_name = t.get('target_state_name', '?')
                            target_id = t.get('target_state_id', '?')
                            condition = t.get('condition', '')
                            elem_html = f' <span class="trans-element-inline">{element}</span>' if element else ''
                            cond_html = f' <span class="trans-condition-inline">if: {condition}</span>' if condition else ''
                            html += f'''
                    <div class="transition-item simple">
                        <div class="trans-flow">
                            <span class="trans-action-inline">{action_desc}</span>{elem_html}{cond_html}
                            <span class="trans-arrow">&#8594;</span>
                            <span class="target-state" data-state="{target_id}">State {target_id}: {target_name}</span>
                        </div>
                    </div>
'''

                if auto_transitions:
                    html += '                    <div class="trans-group-label auto-transitions">Automatic Transitions</div>\n'
                    for t in auto_transitions:
                        trigger = t.get('trigger', {})
                        desc = trigger.get('description', 'Unknown condition')
                        target_name = t.get('target_state_name', '?')
                        target_id = t.get('target_state_id', '?')
                        html += f'''
                    <div class="transition-item automatic">
                        <div class="trans-flow">
                            <span class="trans-auto-icon">&#9889;</span>
                            <span class="trans-action-inline">{desc}</span>
                            <span class="trans-arrow">&#8594;</span>
                            <span class="target-state" data-state="{target_id}">State {target_id}: {target_name}</span>
                        </div>
                    </div>
'''

                html += '''
                </div>
'''

            html += '''
            </div>
        </div>
    </div>
'''
        
        html += '</div>'
        return html
    
    def generate_helper_functions(self):
        """
        Generate comprehensive, parameterized helper functions for state detection.
        These are reusable across ANY experience without modification.
        
        Returns:
            str: JavaScript code for helper functions
        """
        js = """
    // ===== COMPREHENSIVE HELPER FUNCTION LIBRARY =====
    // These helpers work with ANY experience - no modifications needed
    
    function checkVisible(selector) {
        const el = document.querySelector(selector);
        if (!el) return false;
        const style = window.getComputedStyle(el);
        return style.display !== 'none' && 
               style.visibility !== 'hidden' && 
               el.offsetParent !== null &&
               !el.classList.contains('hidden');
    }
    
    function checkHidden(selector) {
        const el = document.querySelector(selector);
        if (!el) return true;
        const style = window.getComputedStyle(el);
        return style.display === 'none' || 
               style.visibility === 'hidden' || 
               el.offsetParent === null ||
               el.classList.contains('hidden');
    }
    
    function checkStyleProperty(selector, property, value) {
        const el = document.querySelector(selector);
        if (!el) return false;
        // Try direct style first, then computed
        const directValue = el.style[property];
        const computedValue = window.getComputedStyle(el)[property];
        return directValue === value || 
               directValue.includes(value) ||
               computedValue === value || 
               computedValue.includes(value);
    }
    
    function checkTextContent(selector, text, exact = false) {
        const el = document.querySelector(selector);
        if (!el) return false;
        const content = el.textContent.trim();
        return exact ? content === text : content.includes(text);
    }
    
    function checkClass(selector, className) {
        const el = document.querySelector(selector);
        return el ? el.classList.contains(className) : false;
    }
    
    function checkAttribute(selector, attribute, value = null) {
        const el = document.querySelector(selector);
        if (!el) return false;
        if (value === null) return el.hasAttribute(attribute);
        return el.getAttribute(attribute) === value;
    }
    
    function checkComputedStyle(selector, property, value) {
        const el = document.querySelector(selector);
        if (!el) return false;
        const computedValue = window.getComputedStyle(el)[property];
        return computedValue === value || computedValue.includes(value);
    }
    
    function checkElementExists(selector) {
        return document.querySelector(selector) !== null;
    }
"""
        return js
    
    def generate_tracking_js(self):
        """
        Generate JavaScript for state tracking and UI updates using adaptive detection strategies.
        
        Returns:
            str: JavaScript code for tracking
        """
        state_var = self.metadata.get('state_variable', 'stage')
        counter_var = self.metadata.get('primary_counter', 'count')
        
        # Create state name mapping for console logs
        state_names_map = {state['id']: state['name'] for state in self.state_list}

        # Build source code blocks map for Copy Code button
        code_blocks_map = {}
        for state in self.state_list:
            code_blocks_map[state['id']] = state.get('source_code_blocks', [])

        # Build reference data map for Copy Ref button
        reference_data_map = {}
        for state in self.state_list:
            reference_data_map[state['id']] = {
                'name': state['name'],
                'trigger_logic': state.get('trigger_logic', ''),
                'related_functions': state.get('related_functions', [])
            }

        # Build description and trigger logic maps for copy buttons
        state_descriptions_map = {}
        state_trigger_logic_map = {}
        for state in self.state_list:
            state_descriptions_map[state['id']] = state.get('user_facing_description', '')
            state_trigger_logic_map[state['id']] = state.get('trigger_logic', '')

        js = f"""
    var currentTrackedState = 0;
    var stateNames = {json.dumps(state_names_map)};
    var stateCodeBlocks = {json.dumps(code_blocks_map)};
    var stateReferenceData = {json.dumps(reference_data_map)};
    var stateDescriptions = {json.dumps(state_descriptions_map)};
    var stateTriggerLogic = {json.dumps(state_trigger_logic_map)};
    
    // AI State Monitor - Receives reports from injected code
    window.__ai_state_monitor = {{
        capturedVariables: {{}},
        report: function(varName, value) {{
            this.capturedVariables[varName] = value;
            // Force state re-evaluation when a variable changes
            debouncedUpdate();
        }},
        get: function(varName) {{
            return this.capturedVariables[varName];
        }}
    }};
    
    function initStatePanel() {{
        // Initial setup if needed
    }}
    
    // Variable finder - searches window object and injected captures
    function findVariable(varName) {{
        // 1. Check AI Monitor (Injected variables)
        if (typeof window.__ai_state_monitor !== 'undefined') {{
            const captured = window.__ai_state_monitor.get(varName);
            if (typeof captured !== 'undefined') return captured;
        }}

        // 2. Try direct global access
        try {{
            if (typeof window[varName] !== 'undefined') {{
                return window[varName];
            }}
        }} catch(e) {{}}
        
        // 3. Search through window properties
        try {{
            for (let key in window) {{
                if (window[key] && typeof window[key] === 'object') {{
                    try {{
                        if (varName in window[key]) {{
                            return window[key][varName];
                        }}
                    }} catch(e) {{}}
                }}
            }}
        }} catch(e) {{}}
        
        return null;  // Return null (not undefined) so !== null checks fail when var is not found
    }}
    
    function getCurrentState() {{
        // HYBRID PRIORITY SCORE LOGIC
        // Combines Specificity Rank (New) with weighted signals (Legacy)
        // Score = (Rank * 100) + (LogicMatch ? 1000 : 0) + (DOMSignals)
        
        let bestStateId = currentTrackedState;
        let maxScore = -10000;
        
        try {{
"""
        
        # Sort by ID to ensure deterministic order
        sorted_states = sorted(self.state_list, key=lambda x: x['id'])
        
        for state in sorted_states:
            state_id = state['id']
            state_name = state['name']
            rank = state.get('specificity_rank', 0)
            
            # Use new 'trigger_logic' if available, otherwise fall back to 'detection_condition'
            logic = state.get('trigger_logic', state.get('detection_condition', 'false'))
            
            # Fallback: If logic is empty or None, ensure it's false
            if not logic:
                logic = 'false'
                
            # Fallback: If using legacy condition, try to wrap variable access
            if 'trigger_logic' not in state and 'findVariable' not in logic:
                pass
            
            # --- Weighted DOM Signals ---
            weighted_signals = state.get('weighted_dom_signals', [])
            weighted_signals_js = ""
            for signal in weighted_signals:
                check = signal.get('check', 'false')
                weight = signal.get('weight', 1)
                if 'querySelector' in check and '!!' not in check:
                    check = f"!!{check}"
                weighted_signals_js += f"if ({check}) score += {weight};\n            "

            js += f"""
        // --- State {state_id} ({state_name}) ---
        {{
            let score = 0;
            
            try {{
                if ({logic}) {{
                    score += 1000;
                    score += {rank} * 100;
                }}
            }} catch(e) {{}}
            
            // DOM Signals
            {weighted_signals_js}
            
            if (score > maxScore) {{
                maxScore = score;
                bestStateId = {state_id};
            }}
        }}
"""

        js += """
        } catch(e) {
            console.error("State detection error:", e);
        }
        
        return bestStateId;
    }
"""
        
        js += f"""
    // Debounce function to prevent rapid-fire updates
    function debounce(func, wait) {{
        let timeout;
        return function(...args) {{
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        }};
    }}

    // Debounced update function
    const debouncedUpdate = debounce(updateStateHighlight, 50);

    // Setup SAFE global listeners (no monkey patching)
    function setupGlobalListeners() {{
        document.addEventListener('click', () => debouncedUpdate());
        document.addEventListener('keydown', () => debouncedUpdate());
        document.addEventListener('input', () => debouncedUpdate());
        document.addEventListener('change', () => debouncedUpdate());
        document.addEventListener('scroll', () => debouncedUpdate()); 
        window.addEventListener('hashchange', () => debouncedUpdate());
        window.addEventListener('popstate', () => debouncedUpdate());
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

            // Auto-scroll active state card into view
            var activeCard = document.getElementById('state' + currentTrackedState);
            if (activeCard) {{
                activeCard.scrollIntoView({{ behavior: 'smooth', block: 'nearest' }});
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

                // Highlight page elements (only if toggle is on)
                if (experienceHighlightsEnabled) {{
                    var elements = document.querySelectorAll(selector);
                    elements.forEach(function(el) {{
                        el.classList.add('state-highlight');
                    }});
                }}

                // Highlight corresponding panel items (always active)
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
    
    function writeToClipboard(text) {
        if (navigator.clipboard && navigator.clipboard.writeText) {
            return navigator.clipboard.writeText(text);
        }
        return new Promise(function(resolve, reject) {
            var textarea = document.createElement('textarea');
            textarea.value = text;
            textarea.style.position = 'fixed';
            textarea.style.opacity = '0';
            document.body.appendChild(textarea);
            textarea.select();
            try {
                document.execCommand('copy');
                resolve();
            } catch(e) {
                reject(e);
            }
            document.body.removeChild(textarea);
        });
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
            // Variable name - use findVariable to access closure-scoped vars
            var value = findVariable(selector);
            var text = (typeof value !== 'undefined') ? selector + ' = ' + JSON.stringify(value) : selector + ' = undefined';
            writeToClipboard(text).then(function() {
                if (event && event.target) {
                    var icon = event.target;
                    icon.classList.add('copied');
                    setTimeout(function() {
                        icon.classList.remove('copied');
                    }, 500);
                }
            }).catch(function(err) {
                console.warn('Could not copy variable:', selector, err);
            });
            return;
        }
        
        if (element) {
            var html = element.outerHTML;
            writeToClipboard(html).then(function() {
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

    function copyToClipboard(text) {
        writeToClipboard(text).then(function() {
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
    }

    function copyDescription(stateId) {
        var text = stateDescriptions[stateId] || '';
        writeToClipboard(text).then(function() {
            if (event && event.target) {
                var icon = event.target;
                icon.classList.add('copied');
                setTimeout(function() { icon.classList.remove('copied'); }, 500);
            }
        }).catch(function(err) {
            console.error('Failed to copy description:', err);
        });
    }

    function copyTriggerLogic(stateId) {
        var text = stateTriggerLogic[stateId] || '';
        writeToClipboard(text).then(function() {
            if (event && event.target) {
                var icon = event.target;
                icon.classList.add('copied');
                setTimeout(function() { icon.classList.remove('copied'); }, 500);
            }
        }).catch(function(err) {
            console.error('Failed to copy trigger logic:', err);
        });
    }

    function copyStateCode(stateId) {
        var blocks = stateCodeBlocks[stateId];
        if (!blocks || blocks.length === 0) {
            copyToClipboard('No source code blocks available for State ' + stateId);
            return;
        }
        var fullCode = blocks.map(function(block) {
            return '// === ' + block.label + ' ===\\n' + block.code;
        }).join('\\n\\n');

        writeToClipboard(fullCode).then(function() {
            if (event && event.target) {
                var btn = event.target.closest('button') || event.target;
                var originalText = btn.textContent;
                btn.textContent = 'Copied!';
                btn.style.background = 'rgba(46, 204, 113, 0.3)';
                setTimeout(function() {
                    btn.textContent = originalText;
                    btn.style.background = '';
                }, 1000);
            }
        }).catch(function(err) {
            console.error('Failed to copy code:', err);
        });
    }

    function copyStateReference(stateId) {
        var ref = stateReferenceData[stateId];
        if (!ref) {
            copyToClipboard('No reference data available for State ' + stateId);
            return;
        }

        var funcStr = (ref.related_functions || []).join(', ') || 'N/A';

        var text = '## State ' + stateId + ': ' + ref.name + '\\n' +
            '**File:** index.html\\n' +
            '**Trigger Condition:** ' + ref.trigger_logic + '\\n' +
            '**Related Functions:** ' + funcStr;

        writeToClipboard(text).then(function() {
            if (event && event.target) {
                var btn = event.target.closest('button') || event.target;
                var originalText = btn.textContent;
                btn.textContent = 'Copied!';
                btn.style.background = 'rgba(46, 204, 113, 0.3)';
                setTimeout(function() {
                    btn.textContent = originalText;
                    btn.style.background = '';
                }, 1000);
            }
        }).catch(function(err) {
            console.error('Failed to copy reference:', err);
        });
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
    
    // === Transitions & Branching Map Functions ===

    var experienceHighlightsEnabled = true;

    function toggleExperienceHighlights() {
        experienceHighlightsEnabled = !experienceHighlightsEnabled;
        var btn = document.getElementById('highlightToggleBtn');
        if (experienceHighlightsEnabled) {
            btn.classList.add('active');
            highlightUIElements(currentTrackedState);
        } else {
            btn.classList.remove('active');
            // Remove ONLY experience highlights, not panel highlights
            document.querySelectorAll('.state-highlight').forEach(function(el) {
                if (!el.closest('#statePanel') && !el.closest('.state-panel')) {
                    el.classList.remove('state-highlight');
                }
            });
        }
    }

    // Click-to-scroll: clicking a target state in transitions scrolls to that state card
    document.addEventListener('click', function(e) {
        var target = e.target.closest('[data-state]');
        if (target) {
            var stateId = target.getAttribute('data-state');
            var stateCard = document.getElementById('state' + stateId);
            if (stateCard) {
                stateCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
                stateCard.classList.add('state-highlight');
                setTimeout(function() { stateCard.classList.remove('state-highlight'); }, 2000);
            }
        }
    });

    // Clicking a flow node scrolls to corresponding state card
    document.addEventListener('click', function(e) {
        var node = e.target.closest('.flow-node');
        if (node) {
            var stateId = node.getAttribute('data-state-id');
            var stateCard = document.getElementById('state' + stateId);
            if (stateCard) {
                stateCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
                stateCard.classList.add('state-highlight');
                setTimeout(function() { stateCard.classList.remove('state-highlight'); }, 2000);
            }
        }
    });

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
    
    // === Live Reload & Re-Analysis ===
    var _sseSource = null;

    function connectSSE() {
        if (_sseSource) _sseSource.close();
        try {
            _sseSource = new EventSource('/api/events');
        } catch(e) {
            return; // Not running on dev server
        }

        _sseSource.onmessage = function(event) {
            var data = JSON.parse(event.data);
            var statusEl = document.getElementById('reanalyzeStatus');
            if (!statusEl) return;

            if (data.type === 'analysis_started') {
                statusEl.textContent = 'Analyzing (' + data.mode + ')...';
                statusEl.className = 'reanalyze-status running';
                setReanalyzeButtons(true);
            } else if (data.type === 'analysis_complete') {
                statusEl.textContent = 'Done! ' + data.states + ' states. Reloading...';
                statusEl.className = 'reanalyze-status complete';
                setReanalyzeButtons(false);
                setTimeout(function() { location.reload(); }, 1000);
            } else if (data.type === 'analysis_error') {
                statusEl.textContent = 'Error: ' + data.error;
                statusEl.className = 'reanalyze-status error';
                setReanalyzeButtons(false);
            } else if (data.type === 'regen_complete') {
                statusEl.textContent = 'Regen complete. Reloading...';
                statusEl.className = 'reanalyze-status complete';
                setTimeout(function() { location.reload(); }, 500);
            }
        };

        _sseSource.onerror = function() {
            var statusEl = document.getElementById('reanalyzeStatus');
            if (statusEl) {
                statusEl.textContent = 'Server disconnected';
                statusEl.className = 'reanalyze-status error';
            }
        };
    }

    function setReanalyzeButtons(disabled) {
        var btns = document.querySelectorAll('.reanalyze-btn');
        btns.forEach(function(btn) { btn.disabled = disabled; });
    }

    function triggerReanalysis(mode) {
        fetch('/api/reanalyze', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({mode: mode})
        }).then(function(r) { return r.json(); })
        .then(function(data) {
            if (!data.success) {
                var statusEl = document.getElementById('reanalyzeStatus');
                if (statusEl) {
                    statusEl.textContent = data.error || 'Failed';
                    statusEl.className = 'reanalyze-status error';
                }
            }
        }).catch(function(err) {
            var statusEl = document.getElementById('reanalyzeStatus');
            if (statusEl) {
                statusEl.textContent = 'Not using dev server';
                statusEl.className = 'reanalyze-status error';
            }
        });
    }

    // Try connecting SSE (gracefully fails if not using dev server)
    connectSSE();

    // Initialize on page load
    window.addEventListener('DOMContentLoaded', function() {
        initStatePanel();
        setupGlobalListeners(); // <--- SAFE Global Listeners
        updateStateHighlight();
        // Highlight initial state elements
        highlightUIElements(currentTrackedState);
        
        // Set up MutationObserver to watch for dynamically created elements
        var observer = new MutationObserver(function(mutations) {
            let shouldUpdate = false;
            for (let mutation of mutations) {
                // Ignore changes to the panel itself
                if (mutation.target.closest && mutation.target.closest('#statePanel')) continue;
                // Ignore changes to highlight classes to PREVENT LOOPS
                if (mutation.attributeName === 'class' && 
                    (mutation.target.classList.contains('state-highlight') || 
                     mutation.target.classList.contains('active') ||
                     mutation.target.classList.contains('highlighted'))) continue;
                     
                shouldUpdate = true;
                break; 
            }
            
            if (shouldUpdate) {
                // Re-highlight when new elements are added to DOM
                highlightUIElements(currentTrackedState);
                debouncedUpdate(); // <--- Check state on DOM change (Debounced)
            }
        });
        
        // Observe the main content area (exclude the state panel itself)
        var mainContent = document.body;
        if (mainContent) {
            observer.observe(mainContent, {
                childList: true,  // Watch for added/removed children
                subtree: true,     // Watch entire tree
                attributes: true   // Watch for class changes etc
            });
        }
    });
    
    // Periodically check for state changes (lighter polling for state detection only)
    setInterval(updateStateHighlight, 1000); // Slower polling since we have events

    // ===== RESPONSIVE CONTENT SCALING =====
    function adjustGameScale() {
        var area = document.getElementById('analysis-content-area');
        if (!area) return;
        var areaW = area.clientWidth;
        var areaH = area.clientHeight;
        // Find main visual content (first non-script/style child)
        var main = null;
        for (var i = 0; i < area.children.length; i++) {
            var tag = area.children[i].tagName;
            if (tag !== 'SCRIPT' && tag !== 'STYLE') { main = area.children[i]; break; }
        }
        if (!main) return;
        var w = main.offsetWidth;
        var h = main.offsetHeight;
        if (!w || !h) return;
        var scale = Math.min(areaW / w, areaH / h, 1) * 0.95;
        main.style.transform = 'scale(' + scale + ')';
        main.style.transformOrigin = 'center center';
    }
    window.addEventListener('resize', adjustGameScale);
    setTimeout(adjustGameScale, 500);
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
        
        # --- NEW: Inject Code Hooks into User Script ---
        original_html = self.inject_code_hooks(original_html)

        # Wrap all body content in analysis-content-area for side-by-side layout
        import re
        original_html = re.sub(
            r'(<body[^>]*>)',
            r'\1\n<div id="analysis-content-area">',
            original_html,
            count=1
        )
        original_html = original_html.replace(
            '</body>',
            '</div><!-- /analysis-content-area -->\n</body>'
        )

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
        
        # Inject AI-generated state tracking code into the SAME script block
        # as the original code, so it can access closure-scoped variables (e.g., const game)
        tracking_snippet = self.states.get('state_tracking_code', '')
        if tracking_snippet and '</script>' in original_html:
            last_script_pos = original_html.rfind('</script>')
            original_html = (original_html[:last_script_pos] +
                           f'\n// AI-generated state tracking\n{tracking_snippet}\n' +
                           original_html[last_script_pos:])

        # Inject helper functions and tracking JavaScript
        helper_js = self.generate_helper_functions()
        combined_js = helper_js + tracking_js

        if '</script>' in original_html:
            # Find the last script tag (after tracking injection)
            last_script_pos = original_html.rfind('</script>')
            original_html = (original_html[:last_script_pos + 9] +
                           f'\n<script>\n{combined_js}\n</script>' +
                           original_html[last_script_pos + 9:])
        else:
            # Add before closing body tag
            original_html = original_html.replace('</body>', f'<script>\n{combined_js}\n</script>\n</body>')

        # Always inject state_jumper.js — buttons show "No path" when transitions are missing,
        # which is more informative than invisible buttons
        jumper_tag = '<script src="jump-states/state_jumper.js"></script>\n'
        original_html = original_html.replace('</body>', jumper_tag + '</body>')

        return original_html
    
    def generate_jump_js(self):
        """
        Generate the content of state_jumper.js — a self-contained, self-injecting
        plugin that adds Jump buttons to the panel and executes AI-generated jump codes.

        state_jumper.js is NOT referenced in index_with_panel.html. Load it on demand:
          var s=document.createElement('script');s.src='jump-states/state_jumper.js';document.body.appendChild(s);

        Returns:
            str: Complete JavaScript content for jump-states/state_jumper.js
        """
        jump_transitions = self.states.get('jump_transitions', {})
        jump_setup = self.states.get('jump_setup', '')
        jump_transitions_json = json.dumps(jump_transitions, indent=2)

        return f"""// state_jumper.js — generated by AI State Analyzer
// AI-generated jump codes for state navigation. Do not edit manually.
// Regenerate: python generate_state_panel.py <your-file.html>
//
// HOW TO USE:
//   1. Open index_with_panel.html in your browser (via dev server)
//   2. Open DevTools console (F12)
//   3. Paste this line and press Enter:
//        var s=document.createElement('script');s.src='jump-states/state_jumper.js';document.body.appendChild(s);
//   4. "Jump" buttons will appear on each state card in the panel

(function () {{
    // ── 1. Inject CSS ──────────────────────────────────────────────────────────
    var style = document.createElement('style');
    style.textContent = [
        '.jump-btn {{ background: rgba(155,89,182,0.2); color: rgba(200,150,255,0.9); border: 1px solid rgba(155,89,182,0.5); padding: 4px 10px; border-radius: 12px; font-size: 10px; font-weight: 600; cursor: pointer; transition: all 0.3s ease; text-transform: uppercase; letter-spacing: 0.5px; margin-left: 2px; }}',
        '.jump-btn:hover {{ background: rgba(155,89,182,0.4); border-color: rgba(155,89,182,0.8); transform: scale(1.05); box-shadow: 0 0 8px rgba(155,89,182,0.4); }}',
        '.jump-btn:active {{ transform: scale(0.95); }}',
        '.jump-btn.jumping {{ background: rgba(241,196,15,0.3); border-color: rgba(241,196,15,0.7); color: rgba(241,196,15,0.9); cursor: not-allowed; }}',
        '.jump-btn.jump-success {{ background: rgba(46,204,113,0.3); border-color: rgba(46,204,113,0.7); color: rgba(46,204,113,0.9); }}',
        '.jump-btn.jump-error {{ background: rgba(231,76,60,0.3); border-color: rgba(231,76,60,0.7); color: rgba(231,76,60,0.9); }}'
    ].join('\\n');
    document.head.appendChild(style);

    // ── 2. AI jump transition data ────────────────────────────────────────────
    var stateJumpTransitions = {jump_transitions_json};

    // ── 3. AI jump setup (one-time init, if any) ──────────────────────────────
    (function () {{
        {jump_setup}
    }})();

    // ── 4. Inject Jump buttons into each state card ───────────────────────────
    function injectButtons() {{
        document.querySelectorAll('.stage-segment').forEach(function (card) {{
            var match = card.id && card.id.match(/^state(\\d+)$/);
            if (!match) return;
            var stateId = parseInt(match[1]);
            var btnGroup = card.querySelector('.stage-header > div');
            if (!btnGroup || btnGroup.querySelector('.jump-btn')) return;
            var btn = document.createElement('button');
            btn.className = 'jump-btn';
            btn.id = 'jumpBtn' + stateId;
            btn.textContent = 'Jump';
            btn.title = 'Jump to this state from current state';
            btn.onclick = (function (id) {{ return function () {{ jumpToState(id); }}; }})(stateId);
            btnGroup.appendChild(btn);
        }});
    }}

    // ── 5. Core jump logic ────────────────────────────────────────────────────
    window.jumpToState = function (targetStateId) {{
        var fromStateId = (typeof getCurrentState === 'function') ? getCurrentState() : -1;
        var key = fromStateId + '_' + targetStateId;
        var transition = stateJumpTransitions[key];
        var btn = document.getElementById('jumpBtn' + targetStateId);

        // Hub-and-spoke fallback: chain through state 0 if no direct path
        if ((!transition || !transition.code) && fromStateId !== 0 && targetStateId !== 0) {{
            var toHub = stateJumpTransitions[fromStateId + '_0'];
            var fromHub = stateJumpTransitions['0_' + targetStateId];
            if (toHub && toHub.code && fromHub && fromHub.code) {{
                transition = {{
                    code: toHub.code + ';\\n' + fromHub.code,
                    confidence: Math.min(toHub.confidence || 0, fromHub.confidence || 0),
                    notes: 'chained via state 0'
                }};
            }}
        }}

        if (!transition || !transition.code) {{
            if (btn) {{
                btn.classList.add('jump-error');
                btn.textContent = (fromStateId === targetStateId) ? 'Here!' : 'No path';
                setTimeout(function () {{ btn.classList.remove('jump-error'); btn.textContent = 'Jump'; }}, 1500);
            }}
            console.warn('[Jump] No transition code for ' + fromStateId + ' \\u2192 ' + targetStateId +
                '. Available: ' + Object.keys(stateJumpTransitions).join(', '));
            return;
        }}

        document.querySelectorAll('.jump-btn').forEach(function (b) {{ b.disabled = true; }});
        if (btn) {{ btn.classList.add('jumping'); btn.textContent = 'Jumping\\u2026'; }}

        console.log(
            '%c[Jump] State ' + fromStateId + ' \\u2192 State ' + targetStateId +
            ' (confidence: ' + Math.round((transition.confidence || 0) * 100) + '%' +
            (transition.notes ? ' \\u2014 ' + transition.notes : '') + ')',
            'color:#9b59b6;font-weight:bold'
        );

        setTimeout(function () {{
            try {{
                (new Function(transition.code))();
            }} catch (e) {{
                console.error('[Jump] Execution error:', e);
                _jumpFinalize(btn, targetStateId, false);
                return;
            }}
            setTimeout(function () {{
                if (typeof debouncedUpdate === 'function') debouncedUpdate();
                if (typeof updateStateHighlight === 'function') setTimeout(updateStateHighlight, 500);
                _jumpFinalize(btn, targetStateId, true);
            }}, 300);
        }}, 20);
    }};

    function _jumpFinalize(btn, stateId, success) {{
        document.querySelectorAll('.jump-btn').forEach(function (b) {{
            b.disabled = false;
            b.classList.remove('jumping');
        }});
        if (!btn) return;
        btn.classList.add(success ? 'jump-success' : 'jump-error');
        btn.textContent = success ? 'Jumped!' : 'Failed';
        setTimeout(function () {{
            btn.classList.remove('jump-success', 'jump-error');
            btn.textContent = 'Jump';
        }}, 1500);
        if (success) {{
            var card = document.getElementById('state' + stateId);
            if (card) card.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
        }}
    }}

    // ── 6. Initialize ─────────────────────────────────────────────────────────
    injectButtons();
    var n = Object.keys(stateJumpTransitions).length;
    console.log(
        '%c[StateJumper] Loaded \\u2014 ' + n + ' jump transition' + (n === 1 ? '' : 's') + ' available',
        'color:#9b59b6;font-weight:bold;font-size:13px'
    );
    if (n === 0) {{
        console.warn('[StateJumper] No transitions found. Re-run the analyzer to generate jump codes.');
    }}
}})();
"""

    def save_to_file(self, output_path, original_html_path):
        """
        Generate and save the complete HTML file.
        Also writes jump-states/state_jumper.js and state-flow-diagram/state_flow_diagram.js alongside it.

        Args:
            output_path (str): Path to save the output HTML
            original_html_path (str): Path to the original HTML file
        """
        try:
            complete_html = self.generate_complete_html(original_html_path)

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(complete_html)

            print(f"[OK] Generated state panel HTML: {output_path}")

            # Write state_jumper.js only if jump data was generated
            if self.states.get('jump_transitions') or self.states.get('jump_setup'):
                jumper_dir = Path(output_path).parent / 'jump-states'
                jumper_dir.mkdir(exist_ok=True)
                jumper_path = jumper_dir / 'state_jumper.js'
                with open(jumper_path, 'w', encoding='utf-8') as f:
                    f.write(self.generate_jump_js())
                n_pairs = len(self.states.get('jump_transitions', {}))
                print(f"[OK] Generated jump codes:       {jumper_path}  ({n_pairs} transitions)")

            # Write Mermaid diagram to external JS file and standalone HTML page
            mermaid_code = self.states.get('mermaid_diagram', '').strip()
            if mermaid_code:
                output_dir = os.path.dirname(os.path.abspath(output_path))
                diagram_dir = os.path.join(output_dir, 'state-flow-diagram')
                os.makedirs(diagram_dir, exist_ok=True)

                # state_flow_diagram.js — diagram data only
                diagram_path = os.path.join(diagram_dir, 'state_flow_diagram.js')
                escaped = mermaid_code.replace('\\', '\\\\').replace('`', '\\`').replace('${', '\\${')
                js_content = f"""// Auto-generated by panel_generator.py — do not edit
window.STATE_FLOW_DIAGRAM = `{escaped}`;

// Render diagram on first call
var _mermaidRendered = false;
window.renderMermaidDiagram = function() {{
    if (_mermaidRendered || typeof mermaid === 'undefined') return;
    var el = document.getElementById('stateFlowMermaid');
    if (el && window.STATE_FLOW_DIAGRAM) {{
        el.textContent = window.STATE_FLOW_DIAGRAM;
        mermaid.run({{ nodes: [el] }});
        _mermaidRendered = true;
    }}
}};
"""
                with open(diagram_path, 'w', encoding='utf-8') as f:
                    f.write(js_content)
                print(f"[OK] Generated Mermaid diagram: state-flow-diagram/state_flow_diagram.js")

                # state_flow_map.html — standalone page for viewing the diagram
                map_path = os.path.join(diagram_dir, 'state_flow_map.html')
                map_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>State Flow Map</title>
<script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
<script>mermaid.initialize({{ startOnLoad: false, theme: "dark", securityLevel: "loose", flowchart: {{ useMaxWidth: false }} }});</script>
<script src="state_flow_diagram.js"></script>
<style>
    body {{
        margin: 0;
        background: #1a1a2e;
        display: flex;
        justify-content: center;
        align-items: flex-start;
        min-height: 100vh;
        padding: 40px 20px;
    }}
    .mermaid {{
        width: 90vw;
    }}
    .mermaid svg {{
        width: 100%;
        height: auto;
    }}
</style>
</head>
<body>
<div class="mermaid" id="stateFlowMermaid"></div>
<script>
    window.addEventListener('DOMContentLoaded', function() {{
        if (typeof window.renderMermaidDiagram === 'function') window.renderMermaidDiagram();
    }});
</script>
</body>
</html>
"""
                with open(map_path, 'w', encoding='utf-8') as f:
                    f.write(map_html)
                print(f"[OK] Generated flow map page:   state-flow-diagram/state_flow_map.html")

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
