#!/usr/bin/env python3
"""
Main script to generate state progression panel for any HTML file.

Usage:
    python generate_state_panel.py input.html output.html
    
Or with custom API key:
    python generate_state_panel.py input.html output.html --api-key YOUR_KEY
"""

import argparse
import sys
from pathlib import Path
from state_analyzer import StateDetectionAnalyzer
from panel_generator import StatePanelGenerator


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
    print()
    
    try:
        # Step 1: Detect states with AI
        print("Step 1/3: Analyzing code with AI to detect states...")
        print("-" * 70)
        
        analyzer = StateDetectionAnalyzer(api_key=args.api_key)
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
        
        # Step 2: Save schema
        print("Step 2/3: Saving state schema...")
        print("-" * 70)
        
        analyzer.save_states_json(states_data, args.schema_output)
        print()
        
        # Step 3: Generate panel
        print("Step 3/3: Generating state progression panel...")
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
