#!/usr/bin/env python3
"""
Main script to generate state progression panel for any HTML file.

Usage:
    python generate_state_panel.py index.html
    python generate_state_panel.py index.html output.html --api-key YOUR_KEY

Incremental mode (updates existing schema instead of from-scratch):
    python generate_state_panel.py index.html --mode incremental
"""

import argparse
import json
import sys
from pathlib import Path
from dotenv import load_dotenv
from state_analyzer import StateDetectionAnalyzer
from panel_generator import StatePanelGenerator

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
        help='Anthropic API key (or set ANTHROPIC_API_KEY environment variable)'
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
        '--skip-jump-codes',
        action='store_true',
        default=False,
        help='Skip AI jump code generation (faster pipeline, no state_jumper.js transitions)'
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
    
    print("=" * 70)
    print("STATE PROGRESSION PANEL GENERATOR")
    print("=" * 70)
    print()
    print(f"Input:  {input_path}")
    print(f"Output: {output_path}")
    print(f"Schema: {args.schema_output}")
    print(f"Mode:   {args.mode}")
    print(f"Jumper: {'disabled (--skip-jump-codes)' if args.skip_jump_codes else 'enabled'}")
    print()

    try:
        # Step 1: Detect states with AI
        analyzer = StateDetectionAnalyzer(api_key=args.api_key)

        if args.mode == 'incremental':
            print("Step 1/4: Running incremental AI analysis (updating existing schema)...")
            print("-" * 70)
            states_data = analyzer.update_states_from_file(
                args.input_file,
                existing_schema_path=args.schema_output
            )
        else:
            print("Step 1/4: Running full AI analysis (from scratch)...")
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

        # Step 2: Generate jump codes
        print("Step 2/4: Generating AI jump codes...")
        print("-" * 70)
        if not args.skip_jump_codes:
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
        else:
            print("[SKIP] Jump code generation skipped (--skip-jump-codes)")
            states_data.setdefault('jump_setup', '')
            states_data.setdefault('jump_transitions', {})
        print()

        # Step 3: Save schema
        print("Step 3/4: Saving state schema...")
        print("-" * 70)

        analyzer.save_states_json(states_data, args.schema_output)
        print()

        # Step 4: Generate panel
        print("Step 4/4: Generating state progression panel...")
        print("-" * 70)
        
        generator = StatePanelGenerator(states_data)
        generator.save_to_file(
            output_path=output_path,
            original_html_path=args.input_file
        )
        
        print()
        print("=" * 70)
        print("SUCCESS!")
        print("=" * 70)
        print()
        print(f"State panel generated successfully!")
        print()
        print(f"Files created:")
        print(f"  - {output_path} - HTML with state panel")
        print(f"  - {args.schema_output} - State schema JSON")
        print()
        print(f"Open {output_path} in your browser to view the result")
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


if __name__ == "__main__":
    main()
