"""
Instagram Notification App Configuration
Defines state variables and structure for stage isolation
"""

# Instagram app state configuration
INSTAGRAM_STATE = {
    # State variables to capture in snapshots
    'variables': [
        'stage',
        'notificationCount',
        'tapCount',
        'notificationSpeed',
        'escapeAttempts',
        'rewardStreak',
        'totalRewards',
        'isHellMode',
        'urgentTimers'
    ],
    
    # Primary variable that tracks stage progression
    'stage_variable': 'stage',
    
    # DOM element that contains the main content
    'content_id': 'contentArea',
    
    # Counter display element
    'counter_id': 'counter',
    
    # Stage definitions - 6 states matching index_with_panel.html
    'stages': {
        0: {
            'name': 'Initial',
            'description': 'Before user clicks start',
            'range': 'stage=0, notificationCount=0'
        },
        1: {
            'name': 'Positive Hook',
            'description': 'Positive notifications',
            'range': 'stage=1, 1-14 notifications'
        },
        2: {
            'name': 'Addictive Mechanics',
            'description': 'Dark patterns begin',
            'range': 'stage=2, 15-49 notifications'
        },
        3: {
            'name': 'Acceleration',
            'description': 'Chaos intensifies',
            'range': 'stage=3, 50-99 notifications'
        },
        4: {
            'name': 'Hell Mode',
            'description': 'Full hell mode',
            'range': 'stage=4, 100-149 notifications'
        },
        5: {
            'name': 'Flood Overlay',
            'description': 'Final overlay',
            'range': '150+ notifications, overlay visible'
        }
    }
}

def get_stage_info(stage_num):
    """Get information about a specific stage"""
    return INSTAGRAM_STATE['stages'].get(stage_num, {
        'name': f'Stage {stage_num}',
        'description': 'Unknown stage',
        'range': 'Unknown'
    })

def get_all_stages():
    """Get list of all stage numbers"""
    return sorted(INSTAGRAM_STATE['stages'].keys())
