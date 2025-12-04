#!/usr/bin/env python3
"""
Extract a specific stage from a recorded session.
Creates a stage-specific file that can be used for isolated testing.
"""

import argparse
import json
import os
from pathlib import Path
from instagram_config import INSTAGRAM_STATE, get_stage_info


def extract_stage(session_name, stage_number, output_dir='snapshots'):
    """
    Extract a specific stage from a session's snapshots.
    
    Args:
        session_name: Name of the session (e.g., 'session_001')
        stage_number: Stage number to extract (0-4)
        output_dir: Directory containing snapshots
    
    Returns:
        Path to extracted stage file
    """
    # Construct paths
    snapshot_dir = Path(output_dir) / session_name
    stage_file = snapshot_dir / f'stage_{stage_number}.json'
    
    # Check if snapshot exists
    if not stage_file.exists():
        raise FileNotFoundError(
            f"Snapshot not found: {stage_file}\n"
            f"Make sure you've recorded a session with --capture-snapshots"
        )
    
    # Load the snapshot
    with open(stage_file, 'r') as f:
        snapshot = json.load(f)
    
    # Get stage info
    stage_info = get_stage_info(stage_number)
    
    print(f"✅ Extracted Stage {stage_number}: {stage_info['name']}")
    print(f"   Description: {stage_info['description']}")
    print(f"   Range: {stage_info['range']}")
    print(f"   Snapshot file: {stage_file}")
    
    return str(stage_file)


def list_available_sessions(output_dir='snapshots'):
    """List all available sessions with snapshots."""
    snapshot_path = Path(output_dir)
    
    if not snapshot_path.exists():
        print("No snapshots directory found.")
        return []
    
    sessions = []
    for session_dir in snapshot_path.iterdir():
        if session_dir.is_dir():
            # Count stage files
            stage_files = list(session_dir.glob('stage_*.json'))
            if stage_files:
                sessions.append({
                    'name': session_dir.name,
                    'stages': len(stage_files),
                    'path': str(session_dir)
                })
    
    return sessions


def list_session_stages(session_name, output_dir='snapshots'):
    """List all stages available for a session."""
    snapshot_dir = Path(output_dir) / session_name
    
    if not snapshot_dir.exists():
        print(f"Session not found: {session_name}")
        return []
    
    stages = []
    for stage_file in sorted(snapshot_dir.glob('stage_*.json')):
        stage_num = int(stage_file.stem.split('_')[1])
        stage_info = get_stage_info(stage_num)
        
        # Load snapshot to get details
        with open(stage_file, 'r') as f:
            snapshot = json.load(f)
        
        stages.append({
            'number': stage_num,
            'name': stage_info['name'],
            'description': stage_info['description'],
            'notification_count': snapshot.get('notificationCount', 0),
            'file': str(stage_file)
        })
    
    return stages


def main():
    parser = argparse.ArgumentParser(
        description='Extract a specific stage from a recorded session'
    )
    parser.add_argument(
        '--session',
        help='Session name (e.g., session_001)'
    )
    parser.add_argument(
        '--stage',
        type=int,
        help='Stage number to extract (0-4)'
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='List all available sessions'
    )
    parser.add_argument(
        '--list-stages',
        help='List all stages for a specific session'
    )
    
    args = parser.parse_args()
    
    # List all sessions
    if args.list:
        print("=" * 70)
        print("AVAILABLE SESSIONS")
        print("=" * 70)
        
        sessions = list_available_sessions()
        
        if not sessions:
            print("No sessions found.")
            print("\nRecord a session with snapshots:")
            print("  python record_session.py --html ../index.html --capture-snapshots")
        else:
            for session in sessions:
                print(f"\n📁 {session['name']}")
                print(f"   Stages: {session['stages']}")
                print(f"   Path: {session['path']}")
        
        print()
        return
    
    # List stages for a session
    if args.list_stages:
        print("=" * 70)
        print(f"STAGES IN {args.list_stages}")
        print("=" * 70)
        
        stages = list_session_stages(args.list_stages)
        
        if not stages:
            print(f"No stages found for session: {args.list_stages}")
        else:
            for stage in stages:
                print(f"\n{stage['number']}. {stage['name']}")
                print(f"   {stage['description']}")
                print(f"   Notifications: {stage['notification_count']}")
                print(f"   File: {stage['file']}")
        
        print()
        return
    
    # Extract a specific stage
    if not args.session or args.stage is None:
        parser.print_help()
        print("\nExamples:")
        print("  # List all sessions")
        print("  python extract_stage.py --list")
        print()
        print("  # List stages in a session")
        print("  python extract_stage.py --list-stages session_001")
        print()
        print("  # Extract a specific stage")
        print("  python extract_stage.py --session session_001 --stage 2")
        return
    
    try:
        stage_file = extract_stage(args.session, args.stage)
        print(f"\n✅ Stage {args.stage} ready for testing!")
        print(f"\nTo test this stage:")
        print(f"  python test_stage.py --session {args.session} --stage {args.stage} --html ../index.html")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == '__main__':
    main()
