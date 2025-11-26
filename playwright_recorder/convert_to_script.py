"""
Recording to Script Converter

Converts a recorded session into a reusable action script.

Usage:
    python convert_to_script.py --recording session_001.json --output actions.json
"""

import argparse
import json
from pathlib import Path


def convert_recording_to_script(recording_path, output_path=None):
    """
    Convert a recording to an action script
    
    Args:
        recording_path: Path to recording JSON file
        output_path: Path to save action script
    """
    # Load recording
    with open(recording_path, 'r') as f:
        recording = json.load(f)
    
    events = recording.get('events', [])
    
    # Filter and convert events to actions
    actions = []
    last_time = 0
    
    for event in events:
        event_type = event['type']
        timestamp = event['timestamp']
        
        # Calculate wait time since last action
        wait_time = timestamp - last_time if last_time > 0 else 0
        
        # Skip mouse movements (too noisy)
        if event_type == 'mousemove':
            continue
        
        # Convert event to action
        if event_type == 'click':
            action = {
                'type': 'click',
                'selector': event['selector'],
                'x': event['x'],
                'y': event['y']
            }
            if wait_time > 0.1:  # Only add wait if significant
                action['wait'] = round(wait_time, 1)
            actions.append(action)
            last_time = timestamp
        
        elif event_type == 'scroll':
            action = {
                'type': 'scroll',
                'scrollY': event['scrollY'],
                'scrollX': event.get('scrollX', 0)
            }
            if wait_time > 0.1:
                action['wait'] = round(wait_time, 1)
            actions.append(action)
            last_time = timestamp
        
        elif event_type == 'keypress':
            # Only include actual keys, not control keys recorded separately
            if event['key'] not in ['Control', 'Meta', 'Shift', 'Alt']:
                action = {
                    'type': 'keypress',
                    'key': event['key']
                }
                if wait_time > 0.1:
                    action['wait'] = round(wait_time, 1)
                actions.append(action)
                last_time = timestamp
    
    # Create script
    script = {
        'description': f"Converted from {recording_path}",
        'source_recording': str(recording_path),
        'total_actions': len(actions),
        'actions': actions
    }
    
    # Save script
    if output_path:
        with open(output_path, 'w') as f:
            json.dump(script, f, indent=2)
        print(f"\n✅ Action script created: {output_path}")
    else:
        output_path = recording_path.replace('.json', '_script.json')
        with open(output_path, 'w') as f:
            json.dump(script, f, indent=2)
        print(f"\n✅ Action script created: {output_path}")
    
    print(f"📊 Summary:")
    print(f"   • Total actions: {len(actions)}")
    print(f"   • Clicks: {sum(1 for a in actions if a['type'] == 'click')}")
    print(f"   • Scrolls: {sum(1 for a in actions if a['type'] == 'scroll')}")
    print(f"   • Keypresses: {sum(1 for a in actions if a['type'] == 'keypress')}")
    
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description='Convert a recording to a reusable action script'
    )
    parser.add_argument(
        '--recording',
        required=True,
        help='Path to recording JSON file'
    )
    parser.add_argument(
        '--output',
        help='Output path for action script (default: <recording>_script.json)'
    )
    
    args = parser.parse_args()
    
    # Check if recording exists
    if not Path(args.recording).exists():
        print(f"Error: Recording file not found: {args.recording}")
        exit(1)
    
    # Convert
    output_path = convert_recording_to_script(args.recording, args.output)
    
    print(f"\n💡 To use this script:")
    print(f"   python record_session.py --html <file> --script {output_path}")


if __name__ == "__main__":
    main()
