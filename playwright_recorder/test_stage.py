#!/usr/bin/env python3
"""
Test a specific stage in isolation.
Loads the stage snapshot and allows testing without replaying previous stages.
"""

import argparse
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright
from instagram_config import INSTAGRAM_STATE, get_stage_info


def load_snapshot(session_name, stage_number, output_dir='snapshots'):
    """Load a stage snapshot from file."""
    snapshot_dir = Path(output_dir) / session_name
    stage_file = snapshot_dir / f'stage_{stage_number}.json'
    
    if not stage_file.exists():
        raise FileNotFoundError(
            f"Snapshot not found: {stage_file}\n"
            f"Run: python extract_stage.py --session {session_name} --stage {stage_number}"
        )
    
    with open(stage_file, 'r') as f:
        return json.load(f)


def restore_state(page, snapshot):
    """
    Restore the application state from a snapshot.
    Sets all variables and DOM to match the snapshot.
    """
    config = INSTAGRAM_STATE
    
    # Build JavaScript to restore all variables
    restore_script = []
    
    for var_name in config['variables']:
        if var_name in snapshot:
            value = snapshot[var_name]
            
            # Handle different types
            if isinstance(value, str):
                restore_script.append(f"{var_name} = '{value}';")
            elif isinstance(value, bool):
                restore_script.append(f"{var_name} = {'true' if value else 'false'};")
            elif isinstance(value, (int, float)):
                restore_script.append(f"{var_name} = {value};")
            elif isinstance(value, list):
                restore_script.append(f"{var_name} = {json.dumps(value)};")
            else:
                # For complex objects, use JSON
                restore_script.append(f"{var_name} = {json.dumps(value)};")
    
    # Restore DOM if present
    if 'dom' in snapshot:
        content_id = config['content_id']
        # Escape the HTML for JavaScript
        dom_html = snapshot['dom'].replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n')
        restore_script.append(f"document.getElementById('{content_id}').innerHTML = '{dom_html}';")
    
    # Update counter display
    if 'notificationCount' in snapshot:
        counter_id = config['counter_id']
        restore_script.append(f"document.getElementById('{counter_id}').textContent = {snapshot['notificationCount']};")
    
    # Execute all restore commands
    full_script = '\n'.join(restore_script)
    page.evaluate(full_script)
    
    print(f"✅ State restored:")
    print(f"   Stage: {snapshot.get('stage', 'unknown')}")
    print(f"   Notifications: {snapshot.get('notificationCount', 0)}")
    print(f"   Taps: {snapshot.get('tapCount', 0)}")


def test_stage(session_name, stage_number, html_path, headless=False):
    """
    Test a specific stage in isolation.
    
    Args:
        session_name: Name of the session
        stage_number: Stage number to test
        html_path: Path to HTML file
        headless: Run in headless mode
    """
    stage_info = get_stage_info(stage_number)
    
    print("=" * 70)
    print(f"TESTING STAGE {stage_number}: {stage_info['name']}")
    print("=" * 70)
    print(f"Description: {stage_info['description']}")
    print(f"Range: {stage_info['range']}")
    print()
    
    # Load snapshot
    print("Loading snapshot...")
    snapshot = load_snapshot(session_name, stage_number)
    print(f"✅ Snapshot loaded from session: {session_name}")
    print()
    
    # Launch browser
    print("Launching browser...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()
        
        # Navigate to HTML
        if html_path.startswith('http'):
            page.goto(html_path)
        else:
            page.goto(f'file://{Path(html_path).absolute()}')
        
        print(f"✅ Loaded: {html_path}")
        print()
        
        # Wait for page to load
        time.sleep(1)
        
        # Restore state from snapshot
        print("Restoring state...")
        restore_state(page, snapshot)
        print()
        
        print("=" * 70)
        print(f"✅ STAGE {stage_number} LOADED")
        print("=" * 70)
        print()
        print("The app is now at the beginning of Stage", stage_number)
        print("All previous stages' state has been restored.")
        print()
        print("You can now:")
        print("  - Interact with the app")
        print("  - See your modifications in action")
        print("  - Test stage-specific behavior")
        print()
        print("Browser will stay open. Close it when done testing.")
        print()
        
        # Keep browser open for testing
        try:
            page.wait_for_timeout(3600000)  # Wait up to 1 hour
        except:
            pass
        
        browser.close()


def main():
    parser = argparse.ArgumentParser(
        description='Test a specific stage in isolation'
    )
    parser.add_argument(
        '--session',
        required=True,
        help='Session name (e.g., session_001)'
    )
    parser.add_argument(
        '--stage',
        type=int,
        required=True,
        help='Stage number to test (0-4)'
    )
    parser.add_argument(
        '--html',
        required=True,
        help='Path to HTML file or URL'
    )
    parser.add_argument(
        '--headless',
        action='store_true',
        help='Run in headless mode'
    )
    
    args = parser.parse_args()
    
    try:
        test_stage(args.session, args.stage, args.html, args.headless)
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        print()
        print("Available sessions:")
        print("  python extract_stage.py --list")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
