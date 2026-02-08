import os
import anthropic
import json
import re
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class StateDetectionAnalyzer:
    def __init__(self, api_key=None):
        """
        Initialize the state detection analyzer with Anthropic API key.
        
        Args:
            api_key (str, optional): Anthropic API key. If not provided, 
                                   will look for ANTHROPIC_API_KEY environment variable.
        """
        if api_key:
            self.api_key = api_key
        else:
            self.api_key = os.getenv('ANTHROPIC_API_KEY')
            
        if not self.api_key:
            raise ValueError("Anthropic API key is required. Set ANTHROPIC_API_KEY environment variable or pass api_key parameter.")
            
        self.client = anthropic.Anthropic(api_key=self.api_key)
    
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

IMPORTANT: Keep all text descriptions CONCISE and BRIEF:
- description: max 100 characters
- purpose: max 50 characters  
- range_description: max 100 characters
- Be clear but brief

For EACH state you identify, provide:

1. **State Identification:**
   - State ID (0, 1, 2, etc.)
   - State name (e.g., "Idle", "Active", "Loading")
   - Clear description of what this state represents
   - Range or boundary description (e.g., "0-15 notifications", "Before user action")
   - **User-facing description (2-3 lines, non-technical):** Explain what's happening in simple terms that a non-developer can understand. Focus on the user experience and what changes in this state.

2. **Visual Theme:**
   - Primary color (as rgba or hex)
   - Active state color (slightly brighter/more opaque)
   - Border color for highlighting
   - Suggest appropriate colors that reflect the state's mood/purpose

3. **Interactive Elements:**
   For each interactive element visible/active in this state:
   - Element name (human-readable)
   - CSS selector (ID or class)
   - Element type (button, input, div, etc.)
   - Visibility state (visible/hidden)
   - Enabled state (enabled/disabled/conditional)
   - Associated function/onclick handler
   - What properties can be modified

4. **Key Variables:**
   - Variable name
   - Current/initial value in this state
   - Variable type (number, boolean, string, array, object)
   - Purpose/what it controls

5. **State Transitions:**
   - What condition triggers transition to next state?
   - What specific code/function causes the transition?
   - Is there a numeric threshold or flag that changes?

6. **State Detection Logic:**
   - What variable(s) determine the current state?
   - What are the exact conditions to be in this state?
   - How can we programmatically detect when app enters this state?

7. **Detection Strategy Analysis (CRITICAL):**
   For EACH state, analyze and determine the BEST method(s) to detect it in real-time:
   
   Evaluate these detection methods in order of reliability:
   a) **Variable-based:** Are there global/window-accessible variables that define this state? (e.g., window.stage, window.currentSection)
   b) **DOM-based:** Are there specific visible/hidden elements unique to this state? (e.g., .chapter[data-section="2"] visible only in state 2)
   c) **Scroll-based:** Can we detect this state by scroll position? (e.g., section starts at scrollY = 2000)
   d) **CSS-based:** Are there unique CSS classes/styles visible in this state? (e.g., .active class)
   e) **Event-based:** Is this state triggered by specific user events?
   f) **Attribute-based:** Do elements have data-attributes marking this state?
   
   For the BEST method identified:
   - Explain WHY it's most reliable for this state
   - Provide the exact detection logic/checks needed
   - Suggest a fallback method if primary fails
   
   **CRITICAL - MUTUAL EXCLUSIVITY:**
   Each state's detection condition MUST be mutually exclusive from other states.
   For example, if State 0 checks "overlay is visible", State 1 MUST check "overlay is hidden AND currentSection === 0".
   This ensures states are properly sequential and never overlap.
   Include NEGATION of previous state conditions to enforce exclusivity.
   
   **CRITICAL - PRIMARY_CHECKS MUST USE HELPER FUNCTIONS:**
   The primary_checks array MUST contain ONLY calls to the provided helper function library.
   DO NOT write raw JavaScript selectors, getComputedStyle, or DOM API calls.
   ONLY call the pre-defined helper functions, which are ALWAYS available:
   
   Available Helper Functions:
   - checkVisible(selector) - checks if element is visible
   - checkHidden(selector) - checks if element is hidden  
   - checkStyleProperty(selector, property, value) - checks inline or computed style
   - checkTextContent(selector, text, exact=false) - checks if text content includes/equals text
   - checkClass(selector, className) - checks if element has class
   - checkAttribute(selector, attribute, value=null) - checks element attribute
   - checkComputedStyle(selector, property, value) - checks computed CSS property
   - checkElementExists(selector) - checks if element exists in DOM
   
   Example CORRECT primary_checks (use helpers):
   ```
   "primary_checks": [
     "checkElementExists('#scene-indicator')",
     "checkTextContent('#scene-indicator', 'Chapter 1')",
     "checkStyleProperty('#progress', 'width', '10%')"
   ]
   ```
   
   Example INCORRECT primary_checks (DO NOT DO THIS):
   ```
   "primary_checks": [
     "!!document.getElementById('scene-indicator')",  // NO raw DOM calls
     "window.getComputedStyle(el).width"  // NO getComputedStyle
   ]
   ```
   
   **WHY:** Helper functions abstract implementation details and work with ANY experience.
   Helper functions are pre-injected in the generated HTML and handle all edge cases automatically.
   
   Example output:
   ```
   "detection_strategy": {{
     "primary_method": "DOM",
     "primary_reason": "State 2 is uniquely identified by visible .chapter[data-section='2'] element",
     "primary_checks": ["checkVisible('.chapter[data-section=\\"2\\"]')", "checkInViewport('.chapter[data-section=\\"2\\"]')"],
     "fallback_method": "scroll_position",
     "fallback_reason": "Sections align with scroll boundaries",
     "confidence": 0.95
   }}
   ```

8. **DOM-Based Detection (Fallback):**
   - What elements are VISIBLE in this state? (provide selectors)
   - What elements are HIDDEN in this state? (provide selectors)
   - What classes are PRESENT on elements? (element selector + class name)
   - What text content is visible? (element selector + expected text)
   - This is critical for when variables are inaccessible due to scope
   
9. **Injection Hooks (Advanced Variable Capture):**
   If key state variables are inside closures or private scopes, identify EXACT code locations where we can inject a reporting line.
   
   For each crucial state variable that is NOT global:
   - Identify the function or block where it is updated.
   - Provide a unique 'search_pattern' (exact code string) that occurs just after the variable update.
   - This allows us to inject `window.__ai_state_monitor.report('varName', varName)` at runtime.
   
   Example:
   If code is: `function update() {{ score++; checkWin(); }}`
   Hook: `{{ "variable": "score", "search_pattern": "score++;", "injection_type": "after" }}`

IMPORTANT: Return your analysis as a valid JSON object with this EXACT structure:

{{
  "metadata": {{
    "total_states": <number>,
    "state_variable": "<primary variable that tracks state>",
    "primary_counter": "<main counter variable if exists>"
  }},
  "injection_hooks": [
    {{
      "variable": "variableName",
      "search_pattern": "exact code line to find",
      "injection_type": "after", 
      "scope_context": "function name or description"
    }}
  ],
  "states": [
    {{
      "id": 0,
      "name": "State Name",
      "description": "What this state represents",
      "range_description": "Boundary or range (e.g., '0-15 items', 'Before start')",
      "user_facing_description": "2-3 line non-technical explanation of what's happening in this state and what the user experiences. Use simple language.",
      "detection_condition": "JavaScript condition to detect this state (e.g., 'stage === 0', 'count >= 0 && count < 15')",
      "dom_detection": {{
        "visible_elements": ["#selector1", ".selector2"],
        "hidden_elements": ["#selector3"],
        "has_class": [{{"selector": "#element", "class": "active"}}],
        "text_content": [{{"selector": "#element", "contains": "some text"}}]
      }},
      "weighted_dom_signals": [
        {{ "check": "checkVisible('#start-btn')", "weight": 2 }},
        {{ "check": "checkHidden('.game-layer')", "weight": 1 }},
        {{ "check": "checkTextContent('h1', 'Welcome')", "weight": 1 }}
      ],
      "color_theme": {{
        "primary": "rgba(r, g, b, 0.15)",
        "active": "rgba(r, g, b, 0.3)",
        "border": "rgba(r, g, b, 0.6)"
      }},
      "interactive_elements": [
        {{
          "name": "Element Name",
          "selector": ".class-name or #id-name",
          "type": "button/div/input/etc",
          "visibility": "visible/hidden/conditional",
          "state": "enabled/disabled/conditional",
          "onclick": "functionName() or null"
        }}
      ],
      "key_variables": [
        {{
          "name": "variableName",
          "value": "initial value",
          "type": "number/boolean/string/array/object",
          "purpose": "What this variable controls"
        }}
      ],
      "transition_to_next": {{
        "condition": "Human-readable condition",
        "trigger": "Specific function or code that causes transition",
        "threshold": "Numeric value if applicable, or null"
      }},
      "detection_strategy": {{
        "primary_method": "DOM or variable or scroll or css or event or attribute",
        "primary_reason": "Why this method is most reliable for this state",
        "primary_checks": ["check1()", "check2()"],
        "fallback_method": "Alternative detection method if primary fails",
        "fallback_reason": "Why this fallback would work",
        "confidence": 0.95
      }}
    }}
  ]
}}

Code to analyze:

{code_content}

Return ONLY the JSON object, no additional text or explanation.
"""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=6000,
                temperature=0.1,
                messages=[
                    {
                        "role": "user",
                        "content": state_detection_prompt
                    }
                ]
            )
            
            # Extract JSON from response
            response_text = response.content[0].text
            
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
    # API key should be set via ANTHROPIC_API_KEY environment variable
    # or passed as command line argument
    
    try:
        # Initialize analyzer (will use ANTHROPIC_API_KEY env var)
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
