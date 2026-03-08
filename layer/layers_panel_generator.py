import json
import os
import sys
from pathlib import Path

# Add parent directory to path so we can import panel_generator
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from panel_generator import StatePanelGenerator


class AestheticsPanelGenerator:
    def __init__(self, aesthetics_schema, states_schema):
        """
        Initialize the aesthetics panel generator.

        Args:
            aesthetics_schema (dict): The combined layers JSON data (emotions + strategy per state)
            states_schema (dict): The states JSON data from StateDetectionAnalyzer
        """
        self.aesthetics = aesthetics_schema
        self.states_schema = states_schema
        self.aesthetics_states = aesthetics_schema.get('states', []) if aesthetics_schema else []
        self.metadata = (aesthetics_schema or {}).get('metadata', {})
        self.state_list = states_schema.get('states', [])

    def _has_strategy_data(self):
        """Check if any state has strategy data."""
        return any('strategy' in s for s in self.aesthetics_states)

    def generate_aesthetics_panel_css(self):
        """Generate CSS for the aesthetics panel."""
        css = """
        .aesthetics-panel {
            flex: 1;
            min-width: 0;
            background: rgba(20, 20, 20, 0.95);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            overflow: hidden;
        }

        .aes-state-card {
            padding: 14px;
            border-bottom: 2px solid rgba(255, 255, 255, 0.1);
            box-sizing: border-box;
        }

        .aes-state-card:last-child {
            border-bottom: none;
        }

        .aes-state-header {
            color: white;
            font-size: 13px;
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 4px;
        }

        /* AI Reasoning Dropdown */
        .aes-reasoning {
            margin: 8px 0 12px 0;
        }

        .aes-reasoning summary {
            cursor: pointer;
            font-size: 11px;
            font-weight: 600;
            color: rgba(255, 255, 255, 0.7);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            padding: 6px 10px;
            background: rgba(0, 0, 0, 0.3);
            border-radius: 4px;
            list-style: none;
            display: flex;
            align-items: center;
            gap: 6px;
            transition: background 0.2s;
        }

        .aes-reasoning summary::-webkit-details-marker {
            display: none;
        }

        .aes-reasoning summary::before {
            content: '\\25B6';
            font-size: 8px;
            transition: transform 0.2s;
            display: inline-block;
        }

        .aes-reasoning[open] summary::before {
            transform: rotate(90deg);
        }

        .aes-reasoning summary:hover {
            background: rgba(0, 0, 0, 0.5);
        }

        .aes-confidence {
            margin-left: auto;
            font-weight: 700;
            font-size: 10px;
            padding: 2px 6px;
            border-radius: 3px;
        }

        .aes-confidence.high {
            color: #2ecc71;
            background: rgba(46, 204, 113, 0.15);
        }

        .aes-confidence.medium {
            color: #f39c12;
            background: rgba(243, 156, 18, 0.15);
        }

        .aes-confidence.low {
            color: #e74c3c;
            background: rgba(231, 76, 60, 0.15);
        }

        .aes-reasoning-text {
            padding: 10px 12px;
            margin-top: 6px;
            font-size: 11px;
            line-height: 1.5;
            color: rgba(255, 255, 255, 0.7);
            background: rgba(0, 0, 0, 0.2);
            border-radius: 4px;
            border-left: 3px solid rgba(255, 255, 255, 0.2);
        }

        /* Emotion-Description Table */
        .aes-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 11px;
        }

        .aes-table th {
            text-align: left;
            padding: 8px 10px;
            font-size: 10px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: rgba(255, 255, 255, 0.5);
            background: rgba(0, 0, 0, 0.4);
            border-bottom: 1px solid rgba(255, 255, 255, 0.15);
        }

        .aes-table th:first-child {
            width: 30%;
            border-right: 1px solid rgba(255, 255, 255, 0.1);
        }

        .aes-table td {
            padding: 0;
            vertical-align: top;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        }

        .aes-table tr:last-child td {
            border-bottom: none;
        }

        .aes-emotion-cell {
            padding: 10px;
            font-weight: 600;
            color: rgba(255, 255, 255, 0.9);
            font-size: 12px;
            border-right: 1px solid rgba(255, 255, 255, 0.1);
        }

        .aes-desc-cell {
            padding: 10px;
            color: rgba(255, 255, 255, 0.7);
            font-size: 11px;
            line-height: 1.5;
        }

        .aes-desc-cell .detail-list {
            margin: 0;
            padding-left: 14px;
            list-style: disc;
        }

        .aes-desc-cell .detail-list li {
            margin-bottom: 2px;
        }
"""

        # Generate state-specific colors (reuse from states_schema)
        for state in self.state_list:
            state_id = state['id']
            colors = state['color_theme']

            css += f"""
        .aes-state-card.aes-state-{state_id} {{
            background: linear-gradient(135deg, {colors['primary']} 0%, {colors['primary']} 100%);
        }}
"""

        return css

    def generate_aesthetics_panel_html(self):
        """Generate HTML for the aesthetics panel."""
        html = '<div class="aesthetics-panel" id="aestheticsPanel">\n'

        # Build lookup for state names from states schema
        state_names = {s['id']: s['name'] for s in self.state_list}

        for aes_state in sorted(self.aesthetics_states, key=lambda x: x['state_id']):
            state_id = aes_state['state_id']
            state_name = aes_state.get('state_name', state_names.get(state_id, f'State {state_id}'))
            reasoning = aes_state.get('ai_reasoning', {})
            explanation = reasoning.get('explanation', '')
            confidence = reasoning.get('confidence', 0)
            emotions = aes_state.get('emotions', [])

            # Confidence class
            if confidence >= 0.8:
                conf_class = 'high'
            elif confidence >= 0.6:
                conf_class = 'medium'
            else:
                conf_class = 'low'
            conf_pct = int(confidence * 100)

            html += f'  <div class="aes-state-card aes-state-{state_id}" data-state-id="{state_id}">\n'
            html += f'    <div class="aes-state-header">State {state_id}: {state_name}</div>\n'

            # AI Reasoning dropdown
            html += f'    <details class="aes-reasoning">\n'
            html += f'      <summary>AI Reasoning <span class="aes-confidence {conf_class}">CONF: {conf_pct}%</span></summary>\n'
            html += f'      <div class="aes-reasoning-text">{explanation}</div>\n'
            html += f'    </details>\n'

            # Emotion → Description table
            if emotions:
                html += '    <table class="aes-table">\n'
                html += '      <thead><tr><th>Emotion</th><th>Implementation Details</th></tr></thead>\n'
                html += '      <tbody>\n'

                for emotion in emotions:
                    name = emotion.get('name', '')
                    # Support both new schema (description string) and old schema (implementation array)
                    description = emotion.get('description', '')
                    if not description and 'implementation' in emotion:
                        # Fallback: render old-format implementation array as comma-separated text
                        details = [item.get('detail', '') for item in emotion['implementation']]
                        description = ', '.join(d for d in details if d)

                    # Split comma-separated descriptions into list items
                    parts = [p.strip() for p in description.split(', ') if p.strip()]
                    if len(parts) > 1:
                        items_html = ''.join(f'<li>{p}</li>' for p in parts)
                        cell_content = f'<ul class="detail-list">{items_html}</ul>'
                    else:
                        cell_content = description

                    html += f'        <tr>\n'
                    html += f'          <td class="aes-emotion-cell">{name}</td>\n'
                    html += f'          <td class="aes-desc-cell">{cell_content}</td>\n'
                    html += f'        </tr>\n'

                html += '      </tbody>\n'
                html += '    </table>\n'

            html += '  </div>\n'

        html += '</div>\n'
        return html

    def generate_strategy_panel_css(self):
        """Generate CSS for the strategy panel."""
        css = """
        .strategy-panel {
            flex: 1;
            min-width: 0;
            background: rgba(20, 20, 20, 0.95);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            overflow: hidden;
        }

        .strat-state-card {
            padding: 14px;
            border-bottom: 2px solid rgba(255, 255, 255, 0.1);
            box-sizing: border-box;
        }

        .strat-state-card:last-child {
            border-bottom: none;
        }

        .strat-state-header {
            color: white;
            font-size: 13px;
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 4px;
        }

        /* AI Reasoning Dropdown */
        .strat-reasoning {
            margin: 8px 0 12px 0;
        }

        .strat-reasoning summary {
            cursor: pointer;
            font-size: 11px;
            font-weight: 600;
            color: rgba(255, 255, 255, 0.7);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            padding: 6px 10px;
            background: rgba(0, 0, 0, 0.3);
            border-radius: 4px;
            list-style: none;
            display: flex;
            align-items: center;
            gap: 6px;
            transition: background 0.2s;
        }

        .strat-reasoning summary::-webkit-details-marker {
            display: none;
        }

        .strat-reasoning summary::before {
            content: '\\25B6';
            font-size: 8px;
            transition: transform 0.2s;
            display: inline-block;
        }

        .strat-reasoning[open] summary::before {
            transform: rotate(90deg);
        }

        .strat-reasoning summary:hover {
            background: rgba(0, 0, 0, 0.5);
        }

        .strat-confidence {
            margin-left: auto;
            font-weight: 700;
            font-size: 10px;
            padding: 2px 6px;
            border-radius: 3px;
        }

        .strat-confidence.high {
            color: #2ecc71;
            background: rgba(46, 204, 113, 0.15);
        }

        .strat-confidence.medium {
            color: #f39c12;
            background: rgba(243, 156, 18, 0.15);
        }

        .strat-confidence.low {
            color: #e74c3c;
            background: rgba(231, 76, 60, 0.15);
        }

        .strat-reasoning-text {
            padding: 10px 12px;
            margin-top: 6px;
            font-size: 11px;
            line-height: 1.5;
            color: rgba(255, 255, 255, 0.7);
            background: rgba(0, 0, 0, 0.2);
            border-radius: 4px;
            border-left: 3px solid rgba(255, 255, 255, 0.2);
        }

        /* Strategy Category-Description Table */
        .strat-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 11px;
        }

        .strat-table th {
            text-align: left;
            padding: 8px 10px;
            font-size: 10px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: rgba(255, 255, 255, 0.5);
            background: rgba(0, 0, 0, 0.4);
            border-bottom: 1px solid rgba(255, 255, 255, 0.15);
        }

        .strat-table th:first-child {
            width: 30%;
            border-right: 1px solid rgba(255, 255, 255, 0.1);
        }

        .strat-table td {
            padding: 0;
            vertical-align: top;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        }

        .strat-table tr:last-child td {
            border-bottom: none;
        }

        .strat-category-cell {
            padding: 10px;
            font-weight: 600;
            color: rgba(255, 255, 255, 0.9);
            font-size: 12px;
            border-right: 1px solid rgba(255, 255, 255, 0.1);
        }

        .strat-desc-cell {
            padding: 10px;
            color: rgba(255, 255, 255, 0.7);
            font-size: 11px;
            line-height: 1.5;
        }

        .strat-desc-cell .detail-list {
            margin: 0;
            padding-left: 14px;
            list-style: disc;
        }

        .strat-desc-cell .detail-list li {
            margin-bottom: 2px;
        }
"""

        # Generate state-specific colors (reuse from states_schema)
        for state in self.state_list:
            state_id = state['id']
            colors = state['color_theme']

            css += f"""
        .strat-state-card.strat-state-{state_id} {{
            background: linear-gradient(135deg, {colors['primary']} 0%, {colors['primary']} 100%);
        }}
"""

        return css

    def generate_strategy_panel_html(self):
        """Generate HTML for the strategy panel. Reads strategy from the same states array."""
        html = '<div class="strategy-panel" id="strategyPanel">\n'

        # Build lookup for state names from states schema
        state_names = {s['id']: s['name'] for s in self.state_list}

        for strat_state in sorted(self.aesthetics_states, key=lambda x: x['state_id']):
            state_id = strat_state['state_id']
            state_name = strat_state.get('state_name', state_names.get(state_id, f'State {state_id}'))
            reasoning = strat_state.get('ai_reasoning', {})
            explanation = reasoning.get('explanation', '')
            confidence = reasoning.get('confidence', 0)
            strategy_items = strat_state.get('strategy', [])

            if not strategy_items:
                continue

            # Confidence class
            if confidence >= 0.8:
                conf_class = 'high'
            elif confidence >= 0.6:
                conf_class = 'medium'
            else:
                conf_class = 'low'
            conf_pct = int(confidence * 100)

            html += f'  <div class="strat-state-card strat-state-{state_id}" data-state-id="{state_id}">\n'
            html += f'    <div class="strat-state-header">State {state_id}: {state_name}</div>\n'

            # AI Reasoning dropdown
            html += f'    <details class="strat-reasoning">\n'
            html += f'      <summary>AI Reasoning <span class="strat-confidence {conf_class}">CONF: {conf_pct}%</span></summary>\n'
            html += f'      <div class="strat-reasoning-text">{explanation}</div>\n'
            html += f'    </details>\n'

            # Strategy Category → Description table
            html += '    <table class="strat-table">\n'
            html += '      <thead><tr><th>Category</th><th>Description</th></tr></thead>\n'
            html += '      <tbody>\n'

            for item in strategy_items:
                category = item.get('category', '')
                description = item.get('description', '')

                # Split comma-separated descriptions into list items
                parts = [p.strip() for p in description.split(', ') if p.strip()]
                if len(parts) > 1:
                    items_html = ''.join(f'<li>{p}</li>' for p in parts)
                    cell_content = f'<ul class="detail-list">{items_html}</ul>'
                else:
                    cell_content = description

                html += f'        <tr>\n'
                html += f'          <td class="strat-category-cell">{category}</td>\n'
                html += f'          <td class="strat-desc-cell">{cell_content}</td>\n'
                html += f'        </tr>\n'

            html += '      </tbody>\n'
            html += '    </table>\n'

            html += '  </div>\n'

        html += '</div>\n'
        return html

    def _generate_copy_js(self):
        """Generate minimal JS for copy functions needed by the state panel."""
        # Build data maps from states_schema
        code_blocks_map = {}
        reference_data_map = {}
        descriptions_map = {}
        trigger_logic_map = {}

        for state in self.state_list:
            sid = state['id']
            code_blocks_map[sid] = state.get('source_code_blocks', [])
            reference_data_map[sid] = {
                'name': state['name'],
                'trigger_logic': state.get('trigger_logic', ''),
                'related_functions': state.get('related_functions', [])
            }
            descriptions_map[sid] = state.get('user_facing_description', '')
            trigger_logic_map[sid] = state.get('trigger_logic', '')

        return f"""
    var stateCodeBlocks = {json.dumps(code_blocks_map)};
    var stateReferenceData = {json.dumps(reference_data_map)};
    var stateDescriptions = {json.dumps(descriptions_map)};
    var stateTriggerLogic = {json.dumps(trigger_logic_map)};

    function writeToClipboard(text) {{
        if (navigator.clipboard && navigator.clipboard.writeText) {{
            return navigator.clipboard.writeText(text);
        }}
        return new Promise(function(resolve, reject) {{
            var textarea = document.createElement('textarea');
            textarea.value = text;
            textarea.style.position = 'fixed';
            textarea.style.opacity = '0';
            document.body.appendChild(textarea);
            textarea.select();
            try {{
                document.execCommand('copy');
                resolve();
            }} catch(e) {{
                reject(e);
            }}
            document.body.removeChild(textarea);
        }});
    }}

    function findVariable(varName) {{
        try {{
            if (typeof window[varName] !== 'undefined') return window[varName];
        }} catch(e) {{}}
        return null;
    }}

    function copyElementHTML(selector) {{
        var value = findVariable(selector);
        var text = (typeof value !== 'undefined' && value !== null) ? selector + ' = ' + JSON.stringify(value) : selector + ' = undefined';
        writeToClipboard(text).then(function() {{
            if (event && event.target) {{
                var icon = event.target;
                icon.classList.add('copied');
                setTimeout(function() {{ icon.classList.remove('copied'); }}, 500);
            }}
        }}).catch(function() {{}});
    }}

    function copyDescription(stateId) {{
        writeToClipboard(stateDescriptions[stateId] || '').then(function() {{
            if (event && event.target) {{
                var icon = event.target;
                icon.classList.add('copied');
                setTimeout(function() {{ icon.classList.remove('copied'); }}, 500);
            }}
        }}).catch(function() {{}});
    }}

    function copyTriggerLogic(stateId) {{
        writeToClipboard(stateTriggerLogic[stateId] || '').then(function() {{
            if (event && event.target) {{
                var icon = event.target;
                icon.classList.add('copied');
                setTimeout(function() {{ icon.classList.remove('copied'); }}, 500);
            }}
        }}).catch(function() {{}});
    }}

    function copyStateCode(stateId) {{
        var blocks = stateCodeBlocks[stateId];
        if (!blocks || blocks.length === 0) {{
            writeToClipboard('No source code blocks available for State ' + stateId);
            return;
        }}
        var fullCode = blocks.map(function(block) {{
            return '// === ' + block.label + ' ===\\n' + block.code;
        }}).join('\\n\\n');
        writeToClipboard(fullCode).then(function() {{
            if (event && event.target) {{
                var btn = event.target.closest('button') || event.target;
                var orig = btn.textContent;
                btn.textContent = 'Copied!';
                btn.style.background = 'rgba(46, 204, 113, 0.3)';
                setTimeout(function() {{ btn.textContent = orig; btn.style.background = ''; }}, 1000);
            }}
        }}).catch(function() {{}});
    }}

    function copyStateReference(stateId) {{
        var ref = stateReferenceData[stateId];
        if (!ref) {{ writeToClipboard('No reference data for State ' + stateId); return; }}
        var funcStr = (ref.related_functions || []).join(', ') || 'N/A';
        var text = '## State ' + stateId + ': ' + ref.name + '\\n' +
            '**File:** index.html\\n' +
            '**Trigger Condition:** ' + ref.trigger_logic + '\\n' +
            '**Related Functions:** ' + funcStr;
        writeToClipboard(text).then(function() {{
            if (event && event.target) {{
                var btn = event.target.closest('button') || event.target;
                var orig = btn.textContent;
                btn.textContent = 'Copied!';
                btn.style.background = 'rgba(46, 204, 113, 0.3)';
                setTimeout(function() {{ btn.textContent = orig; btn.style.background = ''; }}, 1000);
            }}
        }}).catch(function() {{}});
    }}
"""

    def generate_layers_html(self):
        """
        Generate the complete layers.html page with state panel + aesthetics + strategy panels.
        Uses the real StatePanelGenerator output for the state panel.
        Sticky headers, whole-page scrolling, height-synchronized state cards.

        Returns:
            str: Complete HTML for layers.html
        """
        has_aesthetics = len(self.aesthetics_states) > 0
        has_strategy = self._has_strategy_data()

        # Get the real state panel CSS and HTML from StatePanelGenerator
        spg = StatePanelGenerator(self.states_schema)
        state_panel_css = spg.generate_panel_css()
        state_panel_html = spg.generate_panel_html()

        # Get copy JS functions
        copy_js = self._generate_copy_js()

        page_title = 'Layers'

        # Build extra CSS sections
        extra_css = ''
        if has_aesthetics:
            extra_css += '\n    /* Aesthetics panel CSS */\n' + self.generate_aesthetics_panel_css()
        if has_strategy:
            extra_css += '\n    /* Strategy panel CSS */\n' + self.generate_strategy_panel_css()

        # Build headers
        headers_html = '    <div class="layer-header">State Layer</div>\n'
        if has_aesthetics:
            headers_html += '    <div class="layer-header">Aesthetic Layer</div>\n'
        if has_strategy:
            headers_html += '    <div class="layer-header">Strategy Layer</div>\n'

        # Build panels
        panels_html = state_panel_html + '\n'
        if has_aesthetics:
            panels_html += '    ' + self.generate_aesthetics_panel_html() + '\n'
        if has_strategy:
            panels_html += '    ' + self.generate_strategy_panel_html() + '\n'
        # Sidebar is added separately in the page layout, not inside layers-container

        # Build height sync JS
        sync_js = self._generate_height_sync_js(has_aesthetics, has_strategy)

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{page_title}</title>
<style>
    * {{
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }}

    body {{
        background: #0d0d0d;
        color: rgba(255, 255, 255, 0.9);
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        min-height: 100vh;
        padding: 0 28px 28px 28px;
    }}

    /* Sticky header row */
    .layers-headers {{
        position: sticky;
        top: 0;
        z-index: 100;
        display: flex;
        gap: 24px;
        padding: 20px 0 12px 0;
        background: #0d0d0d;
    }}

    .layer-header {{
        flex: 1;
        background: rgba(10, 10, 10, 0.98);
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 6px;
        padding: 10px 16px;
        font-size: 13px;
        font-weight: 700;
        color: rgba(255, 255, 255, 0.9);
        text-transform: uppercase;
        letter-spacing: 1.5px;
        text-align: center;
    }}

    .page-title {{
        font-size: 18px;
        font-weight: 700;
        color: rgba(255, 255, 255, 0.75);
        text-transform: uppercase;
        letter-spacing: 2px;
    }}

    .page-layout {{
        display: flex;
        gap: 24px;
        align-items: stretch;
    }}

    .panels-area {{
        flex: 1;
        min-width: 0;
    }}

    .layers-container {{
        display: flex;
        gap: 24px;
        align-items: flex-start;
    }}

    .sidebar-column {{
        flex: 1;
        min-width: 0;
        min-height: 200px;
        border-left: 1px solid rgba(255, 255, 255, 0.12);
        padding-left: 24px;
        display: none;
    }}

    .sidebar-column.visible {{
        display: block;
    }}

    .page-top-bar {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 18px 0 0 0;
    }}

    .chat-toggle {{
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 6px;
        padding: 6px 16px;
        font-size: 12px;
        font-weight: 600;
        color: rgba(255, 255, 255, 0.7);
        cursor: pointer;
        text-transform: uppercase;
        letter-spacing: 1px;
        transition: background 0.2s, color 0.2s;
    }}

    .chat-toggle:hover {{
        background: rgba(255, 255, 255, 0.15);
        color: rgba(255, 255, 255, 0.9);
    }}

    .chat-toggle.active {{
        background: rgba(255, 255, 255, 0.18);
        color: rgba(255, 255, 255, 0.95);
        border-color: rgba(255, 255, 255, 0.3);
    }}

    /* === Override state panel for layers layout === */
    .view-toggle-container {{ display: none !important; }}
    .original-view-container {{ display: none !important; }}
    .reanalyze-toolbar {{ display: none !important; }}
    .branching-map-container {{ display: none !important; }}
    #analysis-content-area {{ display: none !important; }}

    .state-panel {{
        position: static !important;
        width: auto !important;
        flex: 1 !important;
        min-width: 0 !important;
        height: auto !important;
        border-left: none !important;
        box-shadow: none !important;
        overflow-y: visible !important;
        background: rgba(20, 20, 20, 0.95) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 8px !important;
    }}

    /* Real state panel CSS */
    {state_panel_css}

    /* === Layers-specific overrides === */
    /* Fix: remove body overflow hidden from state panel CSS */
    body {{ overflow: auto !important; }}
    /* Fix: all states equal — no active highlight in layers */
    .stage-segment {{ opacity: 1 !important; }}
    .stage-segment.active {{
        box-shadow: none !important;
        border-color: transparent !important;
    }}
{extra_css}
</style>
</head>
<body>

<div class="page-top-bar">
    <div class="page-title">Layers</div>
    <button class="chat-toggle" id="chatToggle" onclick="toggleChat()">Chat</button>
</div>

<div class="page-layout">

<div class="panels-area">
<div class="layers-headers">
{headers_html}</div>
<div class="layers-container">
    {panels_html}</div>
</div>

<div class="sidebar-column" id="sidebarColumn"></div>

</div>

<script>
{copy_js}
{sync_js}

function toggleChat() {{
    var sidebar = document.getElementById('sidebarColumn');
    var btn = document.getElementById('chatToggle');
    var panelsArea = document.querySelector('.panels-area');
    sidebar.classList.toggle('visible');
    btn.classList.toggle('active');
    if (sidebar.classList.contains('visible')) {{
        panelsArea.style.flex = '3';
    }} else {{
        panelsArea.style.flex = '1';
    }}
    setTimeout(syncStateHeights, 50);
}}
</script>

</body>
</html>"""

        return html

    def _generate_height_sync_js(self, has_aesthetics, has_strategy):
        """Generate JS for height synchronization across all active panels."""
        js = """
// Height synchronization: equalize state card heights across all panels
function syncStateHeights() {
    var stateCards = document.querySelectorAll('.state-panel .stage-segment');"""

        if has_aesthetics:
            js += """
    var aesCards = document.querySelectorAll('.aesthetics-panel .aes-state-card');"""
        if has_strategy:
            js += """
    var stratCards = document.querySelectorAll('.strategy-panel .strat-state-card');"""

        # Reset heights
        js += """

    // Reset heights first
    stateCards.forEach(function(card) { card.style.minHeight = ''; });"""
        if has_aesthetics:
            js += """
    aesCards.forEach(function(card) { card.style.minHeight = ''; });"""
        if has_strategy:
            js += """
    stratCards.forEach(function(card) { card.style.minHeight = ''; });"""

        # Build map
        js += """

    // Build map by state ID
    var stateMap = {};
    stateCards.forEach(function(card) {
        var match = card.id && card.id.match(/^state(\\d+)$/);
        if (match) stateMap[match[1]] = { stateCard: card };
    });"""

        if has_aesthetics:
            js += """
    aesCards.forEach(function(card) {
        var id = card.getAttribute('data-state-id');
        if (id !== null) {
            if (!stateMap[id]) stateMap[id] = {};
            stateMap[id].aesCard = card;
        }
    });"""

        if has_strategy:
            js += """
    stratCards.forEach(function(card) {
        var id = card.getAttribute('data-state-id');
        if (id !== null) {
            if (!stateMap[id]) stateMap[id] = {};
            stateMap[id].stratCard = card;
        }
    });"""

        # Equalize
        js += """

    // Equalize heights
    Object.keys(stateMap).forEach(function(key) {
        var entry = stateMap[key];
        var heights = [];
        if (entry.stateCard) heights.push(entry.stateCard.offsetHeight);"""

        if has_aesthetics:
            js += """
        if (entry.aesCard) heights.push(entry.aesCard.offsetHeight);"""
        if has_strategy:
            js += """
        if (entry.stratCard) heights.push(entry.stratCard.offsetHeight);"""

        js += """
        if (heights.length > 1) {
            var maxH = Math.max.apply(null, heights);
            if (entry.stateCard) entry.stateCard.style.minHeight = maxH + 'px';"""

        if has_aesthetics:
            js += """
            if (entry.aesCard) entry.aesCard.style.minHeight = maxH + 'px';"""
        if has_strategy:
            js += """
            if (entry.stratCard) entry.stratCard.style.minHeight = maxH + 'px';"""

        js += """
        }
    });
}

// Run on load and resize
window.addEventListener('DOMContentLoaded', function() {
    setTimeout(syncStateHeights, 100);
});
window.addEventListener('resize', syncStateHeights);"""

        return js

    def save_layers_html(self, output_path="layers.html"):
        """
        Generate and save the layers.html page.

        Args:
            output_path (str): Path to save the output HTML
        """
        html = self.generate_layers_html()

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

        print(f"[OK] Generated layers page: {output_path}")
