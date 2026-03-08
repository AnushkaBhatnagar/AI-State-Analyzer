#!/usr/bin/env python3
"""
Main script to generate state progression panel for any HTML file.

Usage:
    python generate_state_panel.py index.html
    python generate_state_panel.py index.html output.html --api-key YOUR_KEY

Optional features (opt-in):
    python generate_state_panel.py index.html --jump-code
    python generate_state_panel.py index.html --flow-diagram
    python generate_state_panel.py index.html --jump-code --flow-diagram

Incremental mode (updates existing schema instead of from-scratch):
    python generate_state_panel.py index.html --mode incremental

Skip layers analysis (aesthetics + strategy):
    python generate_state_panel.py index.html --skip-layers
"""

import argparse
import json
import sys
from pathlib import Path
from dotenv import load_dotenv
from state_analyzer import StateDetectionAnalyzer
from panel_generator import StatePanelGenerator

from layer.layers import AestheticsAnalyzer
from layer.layers_panel_generator import AestheticsPanelGenerator

# Load environment variables from .env file
load_dotenv()


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Generate state progression panel for HTML files'
    )
    parser.add_argument(
        'input_file',
        help='Input HTML file to analyze'
    )
    parser.add_argument(
        'output_file',
        nargs='?',
        default=None,
        help='Output HTML file with state panel (default: input_with_panel.html)'
    )
    parser.add_argument(
        '--api-key',
        default=None,
        help='Google API key (or set GOOGLE_API_KEY environment variable)'
    )
    parser.add_argument(
        '--schema-output',
        default='states_schema.json',
        help='Output path for states JSON schema (default: states_schema.json)'
    )
    parser.add_argument(
        '--mode',
        choices=['full', 'incremental'],
        default='full',
        help='Analysis mode: full (from scratch) or incremental (update existing schema)'
    )
    parser.add_argument(
        '--jump-code',
        action='store_true',
        default=False,
        help='Enable AI jump code generation (produces jump-states/state_jumper.js transitions)'
    )
    parser.add_argument(
        '--flow-diagram',
        action='store_true',
        default=False,
        help='Enable Mermaid flow diagram generation (produces state-flow-diagram/state_flow_diagram.js + state_flow_map.html)'
    )
    parser.add_argument(
        '--skip-layers',
        action='store_true',
        default=False,
        help='Skip AI layers analysis (no aesthetics/strategy, no layers.html)'
    )
    parser.add_argument(
        '--layers-schema',
        default='layer/layers_schema.json',
        help='Output path for layers schema (default: layer/layers_schema.json)'
    )
    parser.add_argument(
        '--layers-only',
        action='store_true',
        default=False,
        help='Run only the layers analysis (aesthetics + strategy AI) using existing states_schema.json, then generate layers.html'
    )

    args = parser.parse_args()

    # Validate input file
    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"[ERROR] Input file '{args.input_file}' not found")
        sys.exit(1)

    # Determine output file
    if args.output_file:
        output_path = args.output_file
    else:
        # Generate default output name
        output_path = str(input_path.stem) + '_with_panel' + input_path.suffix

    # --- Layers-only mode: skip state analysis, just run aesthetics + strategy ---
    if args.layers_only:
        print("=" * 70)
        print("LAYERS-ONLY MODE")
        print("=" * 70)
        print()

        schema_path = Path(args.schema_output)
        if not schema_path.exists():
            print(f"[ERROR] States schema '{args.schema_output}' not found. Run full analysis first.")
            sys.exit(1)

        try:
            states_data = json.loads(schema_path.read_text(encoding='utf-8'))
            print(f"[OK] Loaded existing states schema ({states_data['metadata']['total_states']} states)")
            print()

            with open(args.input_file, 'r', encoding='utf-8') as f:
                source_code = f.read()

            layers_schema_path = args.layers_schema

            print("Step 1/3: Running AI layers analysis (aesthetics + strategy)...")
            print("-" * 70)
            layers_analyzer = AestheticsAnalyzer(api_key=args.api_key)
            layers_data = layers_analyzer.analyze_emotions(source_code, states_data)
            print()
            print("[OK] Layers analysis complete!")
            print(f"  Overall arc: {layers_data.get('metadata', {}).get('overall_arc', 'N/A')}")
            print()

            print("Step 2/3: Saving layers schema...")
            print("-" * 70)
            layers_analyzer.save_aesthetics_json(layers_data, layers_schema_path)
            print()

            print("Step 3/3: Generating layers page...")
            print("-" * 70)
            layers_generator = AestheticsPanelGenerator(layers_data, states_data)
            layers_generator.save_layers_html("layers.html")
            print()

            print("=" * 70)
            print("SUCCESS!")
            print("=" * 70)
            print()
            print(f"Files created:")
            print(f"  - {layers_schema_path} - Layers schema JSON (aesthetics + strategy)")
            print(f"  - layers.html - Layers page (state + aesthetics + strategy)")
            print()
            print(f"Open layers.html to view the layers side by side")
            print()

        except Exception as e:
            print()
            print("=" * 70)
            print("ERROR")
            print("=" * 70)
            print()
            print(f"Error: {str(e)}")
            print()
            sys.exit(1)

        return

    print("=" * 70)
    print("STATE PROGRESSION PANEL GENERATOR")
    print("=" * 70)
    print()
    print(f"Input:  {input_path}")
    print(f"Output: {output_path}")
    print(f"Schema: {args.schema_output}")
    print(f"Mode:   {args.mode}")
    print(f"Jump code:    {'enabled (--jump-code)' if args.jump_code else 'disabled'}")
    print(f"Flow diagram: {'enabled (--flow-diagram)' if args.flow_diagram else 'disabled'}")
    print(f"Layers:       {'disabled (--skip-layers)' if args.skip_layers else 'enabled'}")
    print()

    total_steps = 3  # state detection, save schema, generate panel
    if args.jump_code:
        total_steps += 1
    if args.flow_diagram:
        total_steps += 1
    if not args.skip_layers:
        total_steps += 3  # analyze + save + generate layers.html

    try:
        step = 0
        analyzer = StateDetectionAnalyzer(api_key=args.api_key)

        # Step: Detect states with AI
        step += 1
        if args.mode == 'incremental':
            print(f"Step {step}/{total_steps}: Running incremental AI analysis (updating existing schema)...")
            print("-" * 70)
            states_data = analyzer.update_states_from_file(
                args.input_file,
                existing_schema_path=args.schema_output
            )
        else:
            print(f"Step {step}/{total_steps}: Running full AI analysis (from scratch)...")
            print("-" * 70)
            states_data = analyzer.detect_states_from_file(args.input_file)

        print()
        print("[OK] State detection complete!")
        print(f"  Found {states_data['metadata']['total_states']} states")
        print()

        # Show summary
        print("Detected States:")
        for state in states_data['states']:
            print(f"  - State {state['id']}: {state['name']}")
            print(f"    {state.get('range_description', state['description'])}")
        print()

        # Step: Generate jump codes (only if --jump-code)
        if args.jump_code:
            step += 1
            print(f"Step {step}/{total_steps}: Generating AI jump codes...")
            print("-" * 70)
            with open(args.input_file, 'r', encoding='utf-8') as f:
                source_code = f.read()
            schema_file = Path(args.schema_output)
            if args.mode == 'incremental' and schema_file.exists():
                old_schema = json.loads(schema_file.read_text(encoding='utf-8'))
                states_data = analyzer.update_jump_codes(source_code, states_data, old_schema)
            else:
                states_data = analyzer.generate_jump_codes(source_code, states_data)
            n_pairs = len(states_data.get('jump_transitions', {}))
            print(f"[OK] {n_pairs} jump transition(s) generated")
            print()
        else:
            states_data.setdefault('jump_setup', '')
            states_data.setdefault('jump_transitions', {})

        # Step: Generate flow diagram (only if --flow-diagram)
        if args.flow_diagram:
            step += 1
            print(f"Step {step}/{total_steps}: Generating Mermaid flow diagram...")
            print("-" * 70)
            mermaid_code = analyzer.generate_mermaid_diagram(states_data)
            states_data["mermaid_diagram"] = mermaid_code
            print("[OK] Mermaid diagram generated")
            print()

        # Step: Save schema
        step += 1
        print(f"Step {step}/{total_steps}: Saving state schema...")
        print("-" * 70)

        analyzer.save_states_json(states_data, args.schema_output)
        print()

        # Step: Generate panel
        step += 1
        print(f"Step {step}/{total_steps}: Generating state progression panel...")
        print("-" * 70)

        generator = StatePanelGenerator(states_data)
        generator.save_to_file(
            output_path=output_path,
            original_html_path=args.input_file
        )
        print()

        # Steps: Layers analysis (if not skipped)
        layers_schema_path = args.layers_schema
        if not args.skip_layers:
            step += 1
            print(f"Step {step}/{total_steps}: Running AI layers analysis (aesthetics + strategy)...")
            print("-" * 70)

            with open(args.input_file, 'r', encoding='utf-8') as f:
                source_code = f.read()

            layers_analyzer = AestheticsAnalyzer(api_key=args.api_key)
            layers_data = layers_analyzer.analyze_emotions(
                source_code, states_data
            )

            print()
            print("[OK] Layers analysis complete!")
            print(f"  Overall arc: {layers_data.get('metadata', {}).get('overall_arc', 'N/A')}")
            print()

            step += 1
            print(f"Step {step}/{total_steps}: Saving layers schema...")
            print("-" * 70)

            layers_analyzer.save_aesthetics_json(
                layers_data, layers_schema_path
            )
            print()

            step += 1
            print(f"Step {step}/{total_steps}: Generating layers page...")
            print("-" * 70)

            layers_generator = AestheticsPanelGenerator(layers_data, states_data)
            layers_generator.save_layers_html("layers.html")
            print()
        else:
            print("[SKIP] Layers analysis skipped (--skip-layers)")
            print()

        print(flush=True)
        print("=" * 70, flush=True)
        print("SUCCESS!", flush=True)
        print("=" * 70, flush=True)
        print(flush=True)
        print(f"State panel generated successfully!", flush=True)
        print(flush=True)
        print(f"Files created:", flush=True)
        print(f"  - {output_path} - HTML with state panel", flush=True)
        print(f"  - {args.schema_output} - State schema JSON", flush=True)
        if args.jump_code:
            print(f"  - jump-states/state_jumper.js - Jump transition codes", flush=True)
        if args.flow_diagram:
            print(f"  - state-flow-diagram/state_flow_diagram.js - Mermaid diagram data", flush=True)
            print(f"  - state-flow-diagram/state_flow_map.html - Standalone flow map page", flush=True)
        if not args.skip_layers:
            print(f"  - {layers_schema_path} - Layers schema JSON (aesthetics + strategy)", flush=True)
            print(f"  - layers.html - Layers page (state + aesthetics + strategy)", flush=True)
        print(flush=True)
        print(f"Open {output_path} in your browser to view the result", flush=True)
        if not args.skip_layers:
            print(f"Open layers.html to view the layers side by side", flush=True)
        print(flush=True)

    except Exception as e:
        print()
        print("=" * 70)
        print("ERROR")
        print("=" * 70)
        print()
        print(f"Error: {str(e)}")
        print()
        sys.exit(1)


if __name__ == "__main__":
    main()
