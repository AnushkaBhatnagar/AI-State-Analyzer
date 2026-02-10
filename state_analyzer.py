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

1. **State Identification & Specificity (CRITICAL):**
   - State ID (0, 1, 2, etc.)
   - State name (e.g., "Idle", "Active", "Loading")
   - **Specificity Rank (0-100):** Assign a priority number. High numbers check FIRST.
     * 100: Critical Overrides (Game Over, Error Screens, Modals)
     * 80: Specific Modes/Stages (Stage 3, Boss Fight)
     * 50: General Active States (Stage 1, Playing)
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
   - Identify the function or block where it is updated.
   - Provide a unique 'search_pattern' (exact code string) that occurs just after the variable update.
   - This allows us to inject `window.__ai_state_monitor.report('varName', varName)` at runtime.

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
      "search_pattern": "exact code line to find",
      "injection_type": "after", 
      "scope_context": "function name or description"
    }}
  ],
  "states": [
    {{
      "id": 0,
      "name": "State Name",
      "specificity_rank": 10,
      "trigger_logic": "findVariable('stage') === 0",
      "description": "Short technical desc",
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
        "active": "rgba(r, g, b, 0.3)",
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
