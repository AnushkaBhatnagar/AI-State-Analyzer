import os
import google.generativeai as genai
import json
import re
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class StateDetectionAnalyzer:
    def __init__(self, api_key=None):
        """
        Initialize the state detection analyzer with Google Gemini API key.

        Args:
            api_key (str, optional): Google API key. If not provided,
                                   will look for GOOGLE_API_KEY environment variable.
        """
        if api_key:
            self.api_key = api_key
        else:
            self.api_key = os.getenv('GOOGLE_API_KEY')

        if not self.api_key:
            raise ValueError("Google API key is required. Set GOOGLE_API_KEY environment variable or pass api_key parameter.")

        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel("gemini-2.5-pro")
    
    def detect_states(self, code_content, file_type="html"):
        """
        Analyze code to detect distinct states/stages and their properties.
        
        Args:
            code_content (str): The code content to analyze
            file_type (str): The type of code file (html, js, css, etc.)
            
        Returns:
            dict: JSON schema containing detected states and their properties
        """
        
        state_detection_prompt = f"""
You are a code analysis expert specializing in identifying behavioral states and stages in interactive applications.

Analyze the following {file_type.upper()} code and detect ALL distinct behavioral states or stages in the application.

CRITICAL OUTPUT SIZE LIMITS — the response MUST fit in 16000 tokens:
- description: max 60 characters — VERY SPECIFIC, surface the user's choice or action where applicable, written so that someone with zero knowledge of the experience immediately knows what this state is. Format: "User [does X] — [what this state is]", e.g. "User makes a choice to CONTINUE — first escalation gate". Prioritize user-facing moments over technical details.
- purpose: max 40 characters
- range_description: max 60 characters
- user_facing_description: max 1 sentence (80 chars)
- trigger descriptions: max 40 characters
- source_code_blocks: max 2 blocks per state, max 5 lines each. Truncate with "// ..."
- Be as concise as possible everywhere

For EACH state you identify, provide:

1. **State Identification & Specificity (CRITICAL):**
   - State ID (0, 1, 2, etc.)
   - State name (e.g., "Idle", "Active", "Loading")
   - **NAMING RULES (CRITICAL):**
     * State names must be DESCRIPTIVE — do NOT include sequential numbers or the word "stage" in state names.
       WRONG: "Stage 1 - Warm", "Stage 3 - Intense", "Warm Stage"
       RIGHT: "Welcome Screen", "Warm Notifications", "Stress Phase", "Intense Phase", "Hell Mode"
     * Transition/bridge states that connect two other states must reference the STATE IDs
       they connect, NOT conceptual stage numbers.
       Example: If a transition screen sits between state 1 (Warm Notifications) and state 3 (Stress Phase),
       name it "Transition 1-3" — NOT "Transition Screen 1-2".
     * The numbers in transition names must match the actual state IDs visible in the flow map.
   - **Specificity Rank (0-100):** Assign a priority number. High numbers check FIRST.
     * 100: Critical Overrides (Game Over, Error Screens, Modals)
     * 80: Specific Modes (Boss Fight, Transition Screens)
     * 50: General Active States (Playing, Active Phase)
     * 10: Default/Idle States
   - **User-facing description (2-3 lines, non-technical):** Explain what's happening in simple terms.

2. **Trigger Logic (The "Condition Always True" Fix):**
   - `trigger_logic`: A single JavaScript condition string that returns TRUE if this state is active.
   - **Hierarchy Rule:** Since we evaluate High Specificity first, you don't need to manually exclude higher states.
     * Example: If State 4 is `count > 100` (Rank 80) and State 1 is `count > 0` (Rank 10).
     * State 1's logic can just be `count > 0`. We will check State 4 first, so if it's > 100, State 4 wins.
   - Use `findVariable('varName')` to access variables safely.

3. **Experience Archetype Analysis:**
   - Determine if this is:
     * "VARIABLE": Driven by global variables (e.g. `stage`, `level`).
     * "OBJECT": Driven by a state object or specific function calls (e.g. `storyData`).
     * "SCROLL": Driven by scroll position.
     * "DOM": Driven by visual changes only.

   4. **Visual Theme & Elements:**
   - Primary/Active/Border colors (rgba/hex) reflecting mood.
   - Interactive Elements: List ALL elements that the user can interact with (click, tap, input) in this state.
     * Include static elements (buttons, links).
     * Include DYNAMIC elements created by JS (e.g., notifications, items).
     * Provide specific selectors (e.g., '.notification', '.item').

5. **Detection Strategy Analysis:**
   For EACH state, analyze and determine the BEST method(s) to detect it in real-time:
   
   Evaluate these detection methods in order of reliability:
   a) **Variable-based:** Global/window-accessible variables.
   b) **DOM-based:** specific visible/hidden elements.
   c) **Scroll-based:** Scroll position.
   d) **CSS-based:** Unique CSS classes.
   e) **Event-based:** User events.
   
   **CRITICAL - PRIMARY_CHECKS MUST USE HELPER FUNCTIONS:**
   The primary_checks array MUST contain ONLY calls to the provided helper function library.
   
   Available Helper Functions:
   - checkVisible(selector)
   - checkHidden(selector)
   - checkStyleProperty(selector, property, value)
   - checkTextContent(selector, text, exact=false)
   - checkClass(selector, className)
   - checkAttribute(selector, attribute, value=null)
   - checkComputedStyle(selector, property, value)
   - checkElementExists(selector)
   
   Example CORRECT primary_checks:
   `["checkElementExists('#scene-indicator')", "checkTextContent('#scene-indicator', 'Chapter 1')"]`

6. **Injection Hooks (Variable Access):**
   If key state variables are inside closures, identify EXACT code locations where we can inject a reporting line.
   For each crucial state variable that is NOT global:
   - Identify EVERY function or block where it is updated (not just the primary one).
   - Provide a unique 'search_pattern' (exact code string) for EACH update location.
   - IMPORTANT: Include ALL locations where the variable changes — both when it's SET and when it's RESET/CLEARED.
     Example: If `currentTantrum` is set in `triggerTantrum()` AND cleared in `resolveTantrum()`, provide hooks for BOTH.
   - The injection engine automatically resolves the full property access path
     (e.g., `this.gameState.needsHug`), so just provide the bare variable name in the hook.

6b. **State Tracking Code (CRITICAL for framework-based experiences):**
   Provide `state_tracking_code`: a JavaScript snippet (as a string) that continuously monitors
   the primary state variable and reports it via `window.__ai_state_monitor.report('varName', value)`.

   This is ESSENTIAL when state changes happen via METHOD CALLS (e.g., Phaser `scene.start()`,
   React `setState()`, router navigation) rather than simple variable assignments that
   injection hooks can capture.

   Guidelines:
   - Use `setInterval(function() {{ ... }}, 200)` to poll framework-specific state APIs
   - Reference framework objects by their local variable name (they may use `const`/`let` and NOT be on `window`)
   - Wrap everything in `try/catch` so it never breaks the experience
   - Report ALL variables used in `trigger_logic` that aren't captured by injection hooks
   - The snippet will be injected inside the SAME `<script>` tag as the original code, so closure-scoped
     variables (like `const game = new Phaser.Game(...)`) ARE accessible

   Examples by framework:
   - Phaser: `setInterval(function() {{ try {{ var s = game.scene.getScenes(true); if (s.length) window.__ai_state_monitor.report('currentScene', s[0].scene.key); }} catch(e) {{}} }}, 200);`
   - React Router: `setInterval(function() {{ try {{ window.__ai_state_monitor.report('route', window.location.pathname); }} catch(e) {{}} }}, 200);`
   - Scroll-based: `setInterval(function() {{ try {{ window.__ai_state_monitor.report('scrollY', window.scrollY); }} catch(e) {{}} }}, 200);`
   - Vanilla JS classes: `setInterval(function() {{ try {{ window.__ai_state_monitor.report('state', app.state); }} catch(e) {{}} }}, 200);`

7. **Source Code Blocks:**
   For each state, provide `source_code_blocks` - max 2 objects per state, each containing:
   - `label`: A short label (e.g., "startStage3() function")
   - `code`: The first 5 lines of the function/block, then append "// ... (truncated)"
   Do NOT include full functions. Only the first 5 lines to identify the code.

8. **Related Functions:**
   For each state, provide `related_functions` - an array of function name strings that trigger, manage, or are called during this state.
   Example: ["startStage3", "handleUrgentClick", "checkCountdown"]

9. **Transitions & User Choices:**
   For EACH state, identify ALL possible transitions OUT of this state:

   a) **User-Driven Transitions:** Actions a user can take that change the state.
      - What element they interact with (CSS selector)
      - What action type (click, input, scroll, key_press)
      - What state it leads to (target state ID and name)
      - Any branching: if the same action can lead to DIFFERENT states based on conditions
        (e.g., random outcome, variable check), list ALL possible branches with outcomes.

   b) **Automatic Transitions:** Conditions that trigger state changes without user action.
      - Threshold conditions (e.g., counter >= 50)
      - Timer-based transitions (e.g., after timeout)
      - The target state ID and name

   c) **Branching Transitions:** When one action can lead to multiple outcomes:
      - Set target_state_id to null at the top level
      - List each possible outcome in the "branches" array
      - Include the target state ID/name and probability/condition for each branch

   Rules:
   - Only include transitions that CHANGE the state (not actions that stay in the same state)
   - Use state IDs that match the states you defined above
   - If a state has NO outgoing transitions (terminal state), use an empty array []
   - Look at the ACTUAL CODE (function calls, variable assignments, setTimeout chains) to find transitions
   - Keep trigger descriptions concise (max 40 chars)

IMPORTANT: Return your analysis as a valid JSON object with this EXACT structure:

{{
  "metadata": {{
    "total_states": <number>,
    "archetype": "VARIABLE | OBJECT | SCROLL | DOM",
    "state_variable": "<primary variable if exists>",
    "primary_counter": "<main counter if exists>"
  }},
  "injection_hooks": [
    {{
      "variable": "variableName",
      "search_pattern": "exact code line where variable is SET",
      "injection_type": "after",
      "scope_context": "function that sets the variable"
    }},
    {{
      "variable": "variableName",
      "search_pattern": "exact code line where variable is RESET/CLEARED",
      "injection_type": "after",
      "scope_context": "function that resets the variable"
    }}
  ],
  "state_tracking_code": "setInterval(function() {{ try {{ /* poll framework state and report via window.__ai_state_monitor.report('varName', value) */ }} catch(e) {{}} }}, 200);",
  "transitions": [
    {{
      "id": "t_<from_id>_<to_id>",
      "from_state_id": 0,
      "from_state_name": "Source State Name",
      "type": "user_action | automatic",
      "trigger": {{
        "action": "click | input | scroll | threshold | timer | key_press",
        "element": ".selector-or-null",
        "description": "Short human-readable label (max 40 chars)"
      }},
      "target_state_id": "<number or null if branching>",
      "target_state_name": "Target State Name or null",
      "condition": "optional JS condition or null",
      "branches": "null OR array of {{ outcome, target_state_id, target_state_name, probability }}"
    }}
  ],
  "states": [
    {{
      "id": 0,
      "name": "State Name",
      "specificity_rank": 10,
      "trigger_logic": "findVariable('stage') === 0",
      "description": "User makes a choice to CONTINUE — first escalation gate",
      "range_description": "Boundary desc",
      "user_facing_description": "Non-technical desc",
      "detection_condition": "Legacy condition string (keep for reference)",
      "dom_detection": {{
        "visible_elements": ["#selector1"],
        "hidden_elements": [],
        "has_class": [],
        "text_content": []
      }},
      "weighted_dom_signals": [
        {{ "check": "checkVisible('#start-btn')", "weight": 2 }}
      ],
      "color_theme": {{
        "primary": "rgba(r, g, b, 0.15)",
        "border": "rgba(r, g, b, 0.6)"
      }},
      "interactive_elements": [
        {{
          "name": "Element Name",
          "selector": ".class-name",
          "type": "button",
          "visibility": "visible",
          "state": "enabled",
          "onclick": "functionName()"
        }}
      ],
      "key_variables": [
        {{
          "name": "variableName",
          "value": "initial value",
          "type": "number",
          "purpose": "What this variable controls"
        }}
      ],
      "detection_strategy": {{
        "primary_method": "DOM",
        "primary_reason": "Reasoning",
        "primary_checks": ["check1()"],
        "fallback_method": "SCROLL",
        "confidence": 0.95
      }},
      "source_code_blocks": [
        {{
          "label": "function name or description",
          "code": "exact source code text"
        }}
      ],
      "related_functions": ["functionName1", "functionName2"],
      "transitions": [
        {{
          "id": "t_<from_id>_<to_id>",
          "type": "user_action | automatic",
          "trigger": {{
            "action": "click | input | scroll | threshold | timer | key_press",
            "element": ".selector-or-null",
            "description": "Short label (max 40 chars)"
          }},
          "target_state_id": "<number or null if branching>",
          "target_state_name": "Target State Name or null",
          "condition": "optional condition or null",
          "branches": "null OR [{{ outcome, target_state_id, target_state_name, probability }}]"
        }}
      ]
    }}
  ]
}}

Code to analyze:

{code_content}

Return ONLY the JSON object, no additional text or explanation.
"""

        try:
            config = genai.types.GenerationConfig(
                max_output_tokens=16000,
                temperature=0.1,
            )
            chat = self.model.start_chat()
            response = chat.send_message(state_detection_prompt, generation_config=config)

            # Check if response was truncated
            if response.candidates[0].finish_reason.name == 'MAX_TOKENS':
                print("[WARN] Response truncated (hit max_tokens). Retrying with concise mode...")
                response = chat.send_message(
                    "Your response was truncated. Please return the COMPLETE JSON but make source_code_blocks shorter (max 5 lines each, truncate with '// ...'). Return ONLY the complete JSON.",
                    generation_config=config
                )

            # Extract JSON from response
            response_text = response.text

            # Try to parse the response as JSON
            # Sometimes AI might wrap JSON in markdown code blocks
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find JSON object directly
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    json_str = response_text
            
            # Parse JSON
            states_data = json.loads(json_str)
            
            # Validate the structure
            if not self._validate_states_json(states_data):
                raise ValueError("Invalid JSON structure returned from AI")
            
            return states_data
            
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response: {e}")
            print(f"Raw response: {response_text[:500]}...")
            raise
        except Exception as e:
            raise Exception(f"Error detecting states: {str(e)}")

    def update_states(self, code_content, existing_schema, file_type="html"):
        """
        Incrementally update an existing state schema based on changed code.
        Sends existing schema + new code to AI, which updates only what changed.
        Falls back to full detect_states() if incremental update fails.

        Args:
            code_content (str): The NEW full code content
            existing_schema (dict): The existing states_schema.json data
            file_type (str): File type (html, js, etc.)

        Returns:
            dict: Updated JSON schema
        """

        existing_schema_str = json.dumps(existing_schema, indent=2)

        update_prompt = f"""You are updating an existing state analysis for a {file_type.upper()} application.
The code has been modified. Your job is to produce an UPDATED state schema that reflects the new code.

## EXISTING ANALYSIS (states_schema.json):
{existing_schema_str}

## UPDATED CODE:
{code_content}

## INSTRUCTIONS:
1. Compare the updated code against the existing analysis.
2. **Preserve state IDs and names** where the underlying logic hasn't fundamentally changed.
   **NAMING RULES:** State names must be descriptive without sequential numbers or the word "stage" (e.g., "Warm Notifications" not "Stage 1 - Warm"). Transition states must reference the STATE IDs they bridge (e.g., "Transition 1-3" not "Transition Screen 1-2").
3. **Update these fields** to reflect the NEW code exactly:
   - `source_code_blocks`: Max 2 blocks per state, max 5 lines each. Truncate longer code with "// ... (truncated)".
   - `trigger_logic`: Update if the conditions changed.
   - `key_variables`: Update values/purposes if they changed.
   - `interactive_elements`: Update if elements were added/removed/changed.
   - `injection_hooks`: Update search_patterns to match the NEW code exactly.
   - `related_functions`: Update if functions were added/removed/renamed.
   - `weighted_dom_signals`: Update if DOM structure changed.
   - `detection_strategy`: Update if detection approach should change.
   - `transitions`: Update per-state and top-level transitions if state transitions changed, states were added/removed, or interactive elements changed.
4. If NEW states were added in the code, append them with the next available ID.
5. If states were REMOVED from the code, remove them from the schema.
6. Update `metadata.total_states` to match the actual number of states.
7. Rebuild the top-level `transitions` array from per-state transitions to keep them in sync.
8. Keep descriptions CONCISE (description: max 100 chars, purpose: max 50 chars).

IMPORTANT: Return the COMPLETE updated JSON schema in the EXACT same format as the existing one.
Return ONLY the JSON object, no additional text or explanation."""

        try:
            print("Running incremental state analysis...")
            config = genai.types.GenerationConfig(
                max_output_tokens=16000,
                temperature=0.1,
            )
            chat = self.model.start_chat()
            response = chat.send_message(update_prompt, generation_config=config)

            # Check if response was truncated
            if response.candidates[0].finish_reason.name == 'MAX_TOKENS':
                print("[WARN] Incremental response truncated. Retrying with concise mode...")
                response = chat.send_message(
                    "Your response was truncated. Please return the COMPLETE JSON but make source_code_blocks shorter (max 5 lines each, truncate with '// ...'). Return ONLY the complete JSON.",
                    generation_config=config
                )

            response_text = response.text

            # Parse JSON from response
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    json_str = response_text

            states_data = json.loads(json_str)

            if not self._validate_states_json(states_data):
                raise ValueError("Invalid JSON structure returned from incremental analysis")

            print(f"[OK] Incremental update: {states_data['metadata']['total_states']} states")
            return states_data

        except Exception as e:
            print(f"[WARN] Incremental update failed ({e}), falling back to full analysis")
            return self.detect_states(code_content, file_type)

    def generate_jump_codes(self, code_content, states_schema, file_type="html"):
        """
        AI jump analysis agent. Analyzes the experience code and existing state schema,
        then produces JavaScript jump codes for each FROM->TO state pair.

        The AI freely determines the strategy — no hardcoded approach. It may use
        global variable assignment, existing init functions, DOM manipulation, or any
        other technique appropriate for this specific experience.

        Args:
            code_content (str): Full original experience code
            states_schema (dict): Existing states schema from detect_states()
            file_type (str): File type for context

        Returns:
            dict: states_schema extended with:
                  - "jump_setup": str (one-time JS run when jumper loads)
                  - "jump_transitions": dict mapping "fromId_toId" -> { code, confidence, notes }
        """
        states_schema_json = json.dumps(states_schema, indent=2)

        state_ids = [s['id'] for s in states_schema.get('states', [])]
        # Hub-and-spoke: only generate transitions to/from state 0
        # For N states this gives 2*(N-1) pairs instead of N²-N
        base_state = state_ids[0] if state_ids else 0
        all_pairs = (
            [(base_state, t) for t in state_ids if t != base_state] +
            [(f, base_state) for f in state_ids if f != base_state]
        )
        pairs_list_str = ', '.join(f'"{f}_{t}"' for f, t in all_pairs)

        jump_prompt = f"""You are a JavaScript execution expert and code analyst. Your task is to analyze an interactive {file_type.upper()} experience and produce "jump codes" — one per FROM->TO state pair — that allow a user to teleport the running application from any current state to any target state, without reloading the page.

## EXPERIENCE CODE:
{code_content}

## STATE SCHEMA (already analyzed — use this to understand states):
{states_schema_json}

## YOUR JOB

Deeply analyze the code. Understand how state is actually controlled in THIS specific experience. It may use:
- Global variables accessible via window
- Variables declared with var at script top-level (these leak to window in browsers)
- Variables inside closures or IIFEs (NOT accessible from outside)
- DOM-based state (CSS classes, visibility, element presence)
- Object properties on instances
- Timer/interval-based progression
- A combination of the above

## REQUIRED PAIRS (hub-and-spoke model)

We use a hub-and-spoke model where State {base_state} is the hub. You only need to produce transitions TO and FROM State {base_state}:
- Forward: State {base_state} → each other state (to set up that state)
- Backward: each other state → State {base_state} (to reset back)

The jump UI will automatically chain through State {base_state} for non-hub jumps (e.g., State 2→3 becomes 2→{base_state} then {base_state}→3).

Produce a jump code for each of these {len(all_pairs)} pairs:
{pairs_list_str}

For each pair, produce a JavaScript code string that:
- Takes the app from from_state to to_state
- Is safe to execute at any time during the experience
- Handles whatever cleanup or setup is needed for this specific transition
- Leverages the experience's own existing mechanisms where possible

You decide the strategy completely. There is no prescribed approach. Ask yourself:
- Does the target state have an existing init/setup function you can call?
- What variables need what values?
- What DOM elements need to be in what state?
- Does something need to be cleaned up first (timers, DOM elements, etc.)?
- Are the variables accessible from outside (window-level) or locked in closures?

You may also produce a jump_setup — a one-time JavaScript block that runs when the jump tool first loads (before any jumps). Use it to expose otherwise inaccessible things: wrap existing functions to add hooks, expose closure-scoped variables via window properties, or register helper utilities. The per-pair jump codes can then reference what jump_setup prepared.

## OUTPUT FORMAT

Return ONLY a valid JSON object with this exact structure:

{{
  "jump_setup": "/* optional one-time JS block, empty string if not needed */",
  "jump_transitions": {{
    "0_1": {{ "code": "/* JS to jump from state 0 to state 1 */", "confidence": 0.95, "notes": "brief explanation" }},
    "0_2": {{ "code": "/* JS to jump from state 0 to state 2 */", "confidence": 0.9, "notes": "..." }},
    "1_0": {{ "code": "/* JS to jump from state 1 back to state 0 */", "confidence": 0.95, "notes": "..." }},
    "2_0": {{ "code": "/* JS to jump from state 2 back to state 0 */", "confidence": 0.85, "notes": "..." }}
  }}
}}

Keys in jump_transitions are "fromId_toId" strings. Only hub pairs (to/from State {base_state}) are needed.
Omit pairs where jumping is not feasible.

RULES:
- Never reload the page or navigate away
- Never modify or touch any element inside #statePanel (the debug panel UI)
- Each code string must be self-contained and safely runnable via new Function(code)()
- confidence: 0.0 = not jumpable, 0.5 = partial/risky, 0.9+ = reliable
- Return ONLY the JSON object, no additional text or markdown"""

        try:
            print("Running AI jump code analysis...")
            config = genai.types.GenerationConfig(
                max_output_tokens=12000,
                temperature=0.1,
            )
            chat = self.model.start_chat()
            response = chat.send_message(jump_prompt, generation_config=config)

            if response.candidates[0].finish_reason.name == 'MAX_TOKENS':
                print("[WARN] Jump code response truncated. Retrying with fewer pairs...")
                response = chat.send_message(
                    "Your response was truncated. Please return the COMPLETE JSON including ALL required pairs. Do not skip any pairs. Return ONLY the complete valid JSON.",
                    generation_config=config
                )

            response_text = response.text

            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    json_str = response_text

            jump_data = json.loads(json_str)

            states_schema['jump_setup'] = jump_data.get('jump_setup', '')
            states_schema['jump_transitions'] = jump_data.get('jump_transitions', {})

            n_pairs = len(states_schema['jump_transitions'])
            print(f"[OK] Jump codes generated: {n_pairs} transition pair(s)")
            return states_schema

        except json.JSONDecodeError as e:
            print(f"[WARN] Failed to parse jump codes response: {e}")
            print("[WARN] Jump codes will not be available")
            states_schema.setdefault('jump_setup', '')
            states_schema.setdefault('jump_transitions', {})
            return states_schema
        except Exception as e:
            print(f"[WARN] Jump code generation failed: {e}")
            states_schema.setdefault('jump_setup', '')
            states_schema.setdefault('jump_transitions', {})
            return states_schema

    def update_jump_codes(self, code_content, new_schema, old_schema, file_type="html"):
        """
        Incrementally update jump codes. Only regenerates pairs involving changed states.
        Falls back to full generate_jump_codes() if >50% of states changed.

        Args:
            code_content (str): Full updated experience code
            new_schema (dict): Updated states schema (from update_states())
            old_schema (dict): Previous states schema (with existing jump_transitions)
            file_type (str): File type for context

        Returns:
            dict: new_schema extended with updated jump_setup + jump_transitions
        """
        old_states = {s['id']: s for s in old_schema.get('states', [])}
        new_states = {s['id']: s for s in new_schema.get('states', [])}
        old_ids = set(old_states.keys())
        new_ids = set(new_states.keys())

        added = new_ids - old_ids
        removed = old_ids - new_ids
        changed = set()
        for sid in old_ids & new_ids:
            if json.dumps(old_states[sid], sort_keys=True) != json.dumps(new_states[sid], sort_keys=True):
                changed.add(sid)

        affected = added | changed

        # Nothing changed — reuse existing jump codes as-is
        if not affected and not removed:
            new_schema['jump_setup'] = old_schema.get('jump_setup', '')
            new_schema['jump_transitions'] = dict(old_schema.get('jump_transitions', {}))
            print(f"[OK] Jump codes unchanged (no states modified)")
            return new_schema

        print(f"[INFO] States changed: {sorted(affected)}" +
              (f", removed: {sorted(removed)}" if removed else ""))

        # Too many changes — full regen is more efficient
        if len(affected) > len(new_ids) * 0.5:
            print(f"[INFO] {len(affected)}/{len(new_ids)} states affected, running full jump code generation")
            return self.generate_jump_codes(code_content, new_schema, file_type)

        # Start from existing transitions, purge stale pairs
        existing = dict(old_schema.get('jump_transitions', {}))
        for key in list(existing.keys()):
            parts = key.split('_')
            f_id, t_id = int(parts[0]), int(parts[1])
            if f_id in removed or t_id in removed or f_id not in new_ids or t_id not in new_ids:
                del existing[key]

        # Compute hub-and-spoke pairs that need regeneration
        sorted_ids = sorted(new_ids)
        base_state = sorted_ids[0] if sorted_ids else 0
        all_hub_pairs = (
            [(base_state, t) for t in sorted_ids if t != base_state] +
            [(f, base_state) for f in sorted_ids if f != base_state]
        )
        pairs_to_regen = [(f, t) for f, t in all_hub_pairs
                          if f in affected or t in affected]

        if not pairs_to_regen:
            new_schema['jump_setup'] = old_schema.get('jump_setup', '')
            new_schema['jump_transitions'] = existing
            print(f"[OK] Jump codes unchanged after pruning")
            return new_schema

        pairs_list_str = ', '.join(f'"{f}_{t}"' for f, t in pairs_to_regen)
        new_schema_json = json.dumps(new_schema, indent=2)

        update_prompt = f"""You are a JavaScript execution expert. An interactive {file_type.upper()} experience has been updated and some state jump codes need regeneration.

## UPDATED EXPERIENCE CODE:
{code_content}

## UPDATED STATE SCHEMA:
{new_schema_json}

## EXISTING JUMP SETUP (from previous analysis — may need updating):
{old_schema.get('jump_setup', '')}

## YOUR JOB

States {sorted(affected)} have changed. You need to regenerate jump codes for pairs that involve these states.

Deeply analyze the UPDATED code. Understand how state is controlled in this experience.

## REQUIRED PAIRS

You MUST produce a jump code for EVERY one of these {len(pairs_to_regen)} pairs:
{pairs_list_str}

Do not skip any pair. For each pair, produce a JavaScript code string that:
- Takes the app from from_state (currently running) to to_state
- Is safe to execute at any time during the experience
- Handles whatever cleanup or setup is needed for this specific transition
- Leverages the experience's own existing mechanisms where possible

You decide the strategy completely. Ask yourself:
- Does the target state have an existing init/setup function you can call?
- What variables need what values?
- What DOM elements need to be in what state?
- Does something need to be cleaned up first (timers, DOM elements, etc.)?
- Are the variables accessible from outside (window-level) or locked in closures?

Also update jump_setup if needed (one-time JS that runs when the jumper loads).

## OUTPUT FORMAT

Return ONLY a valid JSON object:

{{
  "jump_setup": "/* updated one-time JS block, or same as before if no change needed */",
  "jump_transitions": {{
    "0_1": {{ "code": "/* JS */", "confidence": 0.95, "notes": "brief explanation" }}
  }}
}}

Keys in jump_transitions are "fromId_toId" strings.

RULES:
- Never reload the page or navigate away
- Never modify or touch any element inside #statePanel
- Each code string must be self-contained and safely runnable via new Function(code)()
- confidence: 0.0 = not jumpable, 0.5 = partial/risky, 0.9+ = reliable
- Return ONLY the JSON object, no additional text or markdown"""

        try:
            print(f"Running incremental jump code analysis ({len(pairs_to_regen)} pairs)...")
            config = genai.types.GenerationConfig(
                max_output_tokens=12000,
                temperature=0.1,
            )
            chat = self.model.start_chat()
            response = chat.send_message(update_prompt, generation_config=config)

            if response.candidates[0].finish_reason.name == 'MAX_TOKENS':
                print("[WARN] Incremental jump response truncated. Retrying...")
                response = chat.send_message(
                    "Your response was truncated. Please return the COMPLETE JSON including ALL required pairs. Do not skip any pairs. Return ONLY the complete valid JSON.",
                    generation_config=config
                )

            response_text = response.text

            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    json_str = response_text

            jump_data = json.loads(json_str)

            # Merge: overwrite affected pairs, keep unaffected
            for key, value in jump_data.get('jump_transitions', {}).items():
                existing[key] = value

            new_schema['jump_setup'] = jump_data.get('jump_setup', old_schema.get('jump_setup', ''))
            new_schema['jump_transitions'] = existing

            n_updated = len(jump_data.get('jump_transitions', {}))
            n_total = len(existing)
            print(f"[OK] Jump codes updated: {n_updated} regenerated, {n_total} total")
            return new_schema

        except json.JSONDecodeError as e:
            print(f"[WARN] Failed to parse incremental jump response: {e}")
            print("[WARN] Falling back to full jump code generation")
            return self.generate_jump_codes(code_content, new_schema, file_type)
        except Exception as e:
            print(f"[WARN] Incremental jump code update failed: {e}")
            print("[WARN] Falling back to full jump code generation")
            return self.generate_jump_codes(code_content, new_schema, file_type)

    def update_states_from_file(self, file_path, existing_schema_path="states_schema.json"):
        """
        Incrementally update states from a code file and existing schema on disk.

        Args:
            file_path (str): Path to the updated code file
            existing_schema_path (str): Path to existing states_schema.json

        Returns:
            dict: Updated JSON schema
        """
        file_path = Path(file_path)
        schema_path = Path(existing_schema_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File {file_path} does not exist.")

        if not schema_path.exists():
            print(f"[INFO] No existing schema at {schema_path}, running full analysis")
            return self.detect_states_from_file(str(file_path))

        file_type = file_path.suffix.lstrip('.') or "txt"

        with open(file_path, 'r', encoding='utf-8') as f:
            code_content = f.read()

        with open(schema_path, 'r', encoding='utf-8') as f:
            existing_schema = json.load(f)

        print(f"Updating states for {file_path.name} (incremental)...")
        print("=" * 50)

        return self.update_states(code_content, existing_schema, file_type)

    def _validate_states_json(self, data):
        """
        Validate that the JSON has the expected structure.
        
        Args:
            data (dict): The parsed JSON data
            
        Returns:
            bool: True if valid, False otherwise
        """
        try:
            # Check top-level structure
            if not isinstance(data, dict):
                return False
            
            if "metadata" not in data or "states" not in data:
                return False
            
            # Check metadata
            metadata = data["metadata"]
            if not isinstance(metadata, dict):
                return False
            
            if "total_states" not in metadata:
                return False
            
            # Check states array
            states = data["states"]
            if not isinstance(states, list):
                return False
            
            if len(states) == 0:
                return False
            
            # Validate each state has required fields
            for state in states:
                required_fields = ["id", "name", "description", "color_theme"]
                for field in required_fields:
                    if field not in state:
                        return False

            # Validate transitions if present (soft - not required)
            if "transitions" in data:
                top_transitions = data["transitions"]
                if not isinstance(top_transitions, list):
                    return False
                for t in top_transitions:
                    if not isinstance(t, dict):
                        return False
                    if "from_state_id" not in t or "type" not in t:
                        return False

            for state in states:
                if "transitions" in state:
                    if not isinstance(state["transitions"], list):
                        return False
                    for t in state["transitions"]:
                        if not isinstance(t, dict):
                            return False
                        if "type" not in t or "trigger" not in t:
                            return False

            return True
            
        except Exception:
            return False
    
    def detect_states_from_file(self, file_path):
        """
        Detect states from a code file on disk.
        
        Args:
            file_path (str): Path to the code file
            
        Returns:
            dict: JSON schema containing detected states
        """
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                raise FileNotFoundError(f"File {file_path} does not exist.")
            
            # Determine file type from extension
            file_type = file_path.suffix.lstrip('.')
            if not file_type:
                file_type = "txt"
            
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as file:
                code_content = file.read()
            
            print(f"Detecting states in {file_path.name}...")
            print("=" * 50)
            
            states_data = self.detect_states(code_content, file_type)
            
            print(f"\n[OK] Detected {states_data['metadata']['total_states']} states")
            
            return states_data
            
        except Exception as e:
            raise Exception(f"Error reading file: {str(e)}")
    
    def generate_mermaid_diagram(self, schema: dict) -> str:
        """
        Dedicated AI call to generate a Mermaid flowchart from states/transitions.
        Generalized — works for any experience analyzed by this tool.

        Args:
            schema (dict): The full states schema (output of detect_states)

        Returns:
            str: Raw Mermaid flowchart code
        """
        states_summary = [
            {
                "id": s["id"],
                "name": s["name"],
                "description": s.get("description", ""),
                "fill_color": s["color_theme"]["primary"],
                "stroke_color": s["color_theme"]["border"]
            }
            for s in schema.get("states", [])
        ]
        transitions = schema.get("transitions", [])

        prompt = f"""You are generating a Mermaid diagram for a state machine extracted from an interactive experience.

STATES:
{json.dumps(states_summary, indent=2)}

TRANSITIONS:
{json.dumps(transitions, indent=2)}

Generate a Mermaid `flowchart TD` diagram following these rules exactly:
1. Node IDs must be exactly: S0, S1, S2, ... matching each state's `id` field
2. Node label format: S0["0 · StateName\\nshort description"] — keep labels concise, max 30 chars per line
3. user_action transitions: solid arrow with label, e.g. S0 -->|"label"| S1
4. automatic transitions: dashed arrow with label, e.g. S0 -.->|"⚡ label"| S1
5. Self-loops and back-edges are fine — show them explicitly
6. For each transition, use trigger.description as the edge label (truncate to 25 chars if needed)
7. Add a classDef for each state. Use stroke_color for stroke. For fill, convert fill_color rgba to a dark opaque hex (e.g. rgba(255,183,197,0.15) → #2a1a1e). Keep the dark aesthetic.
8. Apply class to each node: `class S0 s0style` etc.
9. Style the active state via a separate classDef named `active` with bright white stroke and glow.

Output ONLY the raw Mermaid code. No markdown fences. No explanation."""

        response = self.model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=3000,
                temperature=0.1,
            ),
            safety_settings=[
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
        )
        # Handle blocked or empty responses
        if not response.candidates or not response.candidates[0].content.parts:
            raise RuntimeError(f"Gemini returned no content (finish_reason: {response.candidates[0].finish_reason if response.candidates else 'unknown'})")
        raw = response.text.strip()
        # Strip markdown fences if the model wrapped the output anyway
        raw = re.sub(r'^```[a-z]*\n?', '', raw, flags=re.MULTILINE)
        raw = re.sub(r'^```\s*$', '', raw, flags=re.MULTILINE)
        return raw.strip()

    def save_states_json(self, states_data, output_path="states_schema.json"):
        """
        Save the detected states to a JSON file.

        Args:
            states_data (dict): The states JSON data
            output_path (str): Path to save the JSON file
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(states_data, f, indent=2)

            print(f"[OK] Saved states schema to {output_path}")

        except Exception as e:
            raise Exception(f"Error saving JSON: {str(e)}")


def main():
    """
    Test function to detect states in index.html
    """
    # API key should be set via GOOGLE_API_KEY environment variable
    # or passed as command line argument

    try:
        # Initialize analyzer (will use GOOGLE_API_KEY env var)
        analyzer = StateDetectionAnalyzer()
        
        # Detect states from Instagram example
        states_data = analyzer.detect_states_from_file("index.html")
        
        # Print summary
        print("\n" + "="*80)
        print("DETECTED STATES SUMMARY")
        print("="*80)
        
        for state in states_data["states"]:
            print(f"\n{state['id']}. {state['name']}")
            print(f"   Description: {state['description']}")
            print(f"   Range: {state.get('range_description', 'N/A')}")
            print(f"   Interactive Elements: {len(state.get('interactive_elements', []))}")
            print(f"   Key Variables: {len(state.get('key_variables', []))}")
        
        # Save to file
        analyzer.save_states_json(states_data, "states_schema.json")
        
        print("\n[OK] State detection complete!")
        print("[OK] Review states_schema.json for full details")
        
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
