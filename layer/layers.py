import os
import google.generativeai as genai
import json
import re
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class AestheticsAnalyzer:
    def __init__(self, api_key=None):
        """
        Initialize the aesthetics analyzer with Google Gemini API key.

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

    def analyze_emotions(self, code_content, states_schema, file_type="html"):
        """
        Analyze the emotional arc AND strategic design of an interactive experience.

        Given the experience code and its detected states, identifies emotions
        the creator intends to evoke at each state, plus the strategy behind
        each state (narrative, user role, directives, choices, world state).

        Args:
            code_content (str): The full source code of the experience
            states_schema (dict): The states schema from StateDetectionAnalyzer
            file_type (str): The type of code file (html, js, css, etc.)

        Returns:
            dict: JSON schema containing emotions, strategy, and details per state
        """

        # Build a compact states summary for the prompt
        states_summary = []
        for s in states_schema.get('states', []):
            states_summary.append({
                "id": s["id"],
                "name": s["name"],
                "description": s.get("description", ""),
                "interactive_elements": [
                    {"name": e["name"], "selector": e["selector"]}
                    for e in s.get("interactive_elements", [])
                ],
                "key_variables": [
                    {"name": v["name"], "value": v.get("value"), "purpose": v.get("purpose", "")}
                    for v in s.get("key_variables", [])
                ],
                "transitions": [
                    {"target": t.get("target_state_name", ""), "trigger": t.get("trigger", {}).get("description", "")}
                    for t in s.get("transitions", [])
                ]
            })

        prompt = f"""You are an experience design analyst specializing in the emotional and strategic dimensions of interactive digital experiences.

You are given:
1. The full source code of an interactive {file_type.upper()} experience
2. A summary of the detected behavioral states in this experience

Your task has TWO parts:

PART A — AESTHETIC LAYER (Emotions):
Analyze the EMOTIONAL ARC that the human creator intends participants to feel as they move through this experience. For each state, surface the emotions and the specific implementation details that contribute to evoking those emotions.

PART B — STRATEGY LAYER:
Analyze the STRATEGY behind each state — from the experience perspective, NOT the code. What is the strategy being followed, what role does the user play, what are they directed to do, what choices exist, and what is the world/environment state.

STATES SUMMARY:
{json.dumps(states_summary, indent=2)}

SOURCE CODE:
```{file_type}
{code_content}
```

INSTRUCTIONS:

=== PART A: EMOTIONS ===
1. For each state, identify 2-4 UMBRELLA emotions the creator intends to evoke. Use broad, recognizable terms (e.g. "curiosity", "anxiety", "delight", "tension", "nostalgia", "overwhelm", "comfort", "dread", "empowerment", "confusion"). Do NOT use overly specific or academic terms when a simpler umbrella term captures it.

2. For each emotion, provide a single "description" string — a comma-separated list of descriptive phrases explaining WHAT the implementation does visually and interactionally to evoke that emotion.
   - Use plain, human-readable language. Describe what the user sees/feels, not code.
   - GOOD: "Full-screen overlay, z-index dominance, no close button"
   - GOOD: "Deep crimson red, monochromatic, high-contrast white text"
   - BAD: "z-index: 9999" (code value)
   - BAD: "startStage3() function" (function name)

=== PART B: STRATEGY ===
3. For each state, provide exactly 5 strategy categories. Keep descriptions SHORT — max 80 characters each, comma-separated phrases, NOT full sentences.

   Categories:
   - **Strategy**: The strategy being followed in this state — what is the experience doing and why
   - **User Role**: What role the user plays (short label, e.g. "Observer", "Decision-maker")
   - **Directives**: What the experience wants the user to do (e.g. "Click continue, read message, wait")
   - **Choices**: Available decisions and where they lead (e.g. "Accept → escalation, Reject → exit")
   - **World State**: Environment, mood, stakes at this point (e.g. "High tension, red visuals, countdown active")

=== SHARED ===
4. For each state, provide:
   - "ai_reasoning": a 1-2 sentence explanation of WHY you believe these emotions and strategy correspond to this state
   - "confidence": 0.0-1.0 score for how confident you are in this analysis

5. Also provide an "overall_arc" string summarizing the emotional journey across ALL states (e.g. "Curiosity → Engagement → Anxiety → Overwhelm → Dread")

CRITICAL OUTPUT FORMAT — respond with ONLY a JSON object (no markdown fences, no explanation):
{{
  "metadata": {{
    "total_states": <number>,
    "experience_name": "<short name for this experience>",
    "overall_arc": "<Emotion1 → Emotion2 → ... → EmotionN>"
  }},
  "states": [
    {{
      "state_id": <number matching the state id>,
      "state_name": "<state name>",
      "ai_reasoning": {{
        "explanation": "<1-2 sentence reasoning>",
        "confidence": <0.0-1.0>
      }},
      "emotions": [
        {{
          "name": "<Emotion Name>",
          "description": "<comma-separated descriptive phrases>"
        }}
      ],
      "strategy": [
        {{ "category": "Strategy", "description": "<max 80 chars>" }},
        {{ "category": "User Role", "description": "<max 80 chars>" }},
        {{ "category": "Directives", "description": "<max 80 chars>" }},
        {{ "category": "Choices", "description": "<max 80 chars>" }},
        {{ "category": "World State", "description": "<max 80 chars>" }}
      ]
    }}
  ]
}}

Ensure every state from the states summary appears in your output.
The response MUST be valid JSON and fit within 20000 tokens."""

        print("Sending layers analysis request to Gemini...")

        config = genai.types.GenerationConfig(
            max_output_tokens=20000,
            temperature=0.1,
        )

        chat = self.model.start_chat()
        response = chat.send_message(prompt, generation_config=config)

        # Check if response was truncated
        if response.candidates[0].finish_reason.name == 'MAX_TOKENS':
            print("[WARN] Response truncated (hit max_tokens). Retrying with concise mode...")
            response = chat.send_message(
                "Your response was truncated. Please return the COMPLETE JSON but with fewer details per emotion (max 3 each) and shorter strategy descriptions. Return ONLY the complete JSON.",
                generation_config=config
            )

        response_text = response.text

        # Try to parse the response as JSON
        json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = response_text

        try:
            aesthetics_data = json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"[ERROR] Failed to parse layers JSON: {e}")
            print(f"[DEBUG] Response preview: {response_text[:500]}")
            raise

        # Validate basic structure
        if not self._validate_aesthetics_json(aesthetics_data):
            print("[WARN] Layers JSON validation failed, but continuing with parsed data")

        return aesthetics_data

    def _validate_aesthetics_json(self, data):
        """Validate that the layers JSON has the expected structure."""
        try:
            if not isinstance(data, dict):
                return False
            if "metadata" not in data or "states" not in data:
                return False
            if not isinstance(data["states"], list) or len(data["states"]) == 0:
                return False
            for state in data["states"]:
                if "state_id" not in state or "state_name" not in state:
                    return False
                if "emotions" not in state or not isinstance(state["emotions"], list):
                    return False
                if "ai_reasoning" not in state:
                    return False
                for emotion in state["emotions"]:
                    if "name" not in emotion:
                        return False
                if "strategy" not in state or not isinstance(state["strategy"], list):
                    return False
                for item in state["strategy"]:
                    if "category" not in item:
                        return False
            return True
        except Exception:
            return False

    def analyze_from_file(self, code_file_path, states_schema_path):
        """
        Analyze emotions from files on disk.

        Args:
            code_file_path (str): Path to the experience code file
            states_schema_path (str): Path to the states schema JSON

        Returns:
            dict: Aesthetics schema
        """
        code_path = Path(code_file_path)
        schema_path = Path(states_schema_path)

        if not code_path.exists():
            raise FileNotFoundError(f"Code file {code_path} does not exist.")
        if not schema_path.exists():
            raise FileNotFoundError(f"States schema {schema_path} does not exist.")

        file_type = code_path.suffix.lstrip('.') or "txt"

        with open(code_path, 'r', encoding='utf-8') as f:
            code_content = f.read()

        with open(schema_path, 'r', encoding='utf-8') as f:
            states_schema = json.load(f)

        print(f"Analyzing emotions for {code_path.name}...")
        print("=" * 50)

        return self.analyze_emotions(code_content, states_schema, file_type)

    def save_aesthetics_json(self, aesthetics_data, output_path="layer/layers_schema.json"):
        """
        Save the aesthetics analysis to a JSON file.

        Args:
            aesthetics_data (dict): The aesthetics schema data
            output_path (str): Path to save the JSON file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(aesthetics_data, f, indent=2)

        print(f"[OK] Saved layers schema: {output_path}")
