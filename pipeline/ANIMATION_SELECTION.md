# Multi-Animation Selection Feature

## Overview
Added comprehensive multi-animation selection interface to prevent accidental batch generation of all animations in the library. Users can now selectively choose which animations to generate with visual warnings and time estimates.

## Features

### 1. **Animation Mode Selector**
- **Library Selection**: Choose from pre-built animation library with checkboxes
- **Custom Prompt**: Manual prompt entry for custom animations

### 2. **Multi-Selection Interface**
- **Category-Level Selection**: Each category has a "Select All" checkbox
  - Checkboxes show indeterminate state when partially selected
  - Category counters show selected/total (e.g., "3/10")

- **Individual Animation Selection**: 
  - Checkboxes for each animation in the library
  - Organized by category (locomotion, idle, combat, etc.)
  - Responsive grid layout

- **Selection Management**:
  - Real-time counter showing total selected animations
  - "Clear All" button to deselect everything
  - Selection state persists during session

### 3. **Warning System**
Visual warnings appear based on selection count:

- **No Selection**: Warning shown on pipeline run
- **1-5 Animations**: Info message (sequential generation)
- **6-10 Animations**: Warning with time estimate (30-100 minutes)
- **11+ Animations**: Error-level warning (several hours)

### 4. **Pipeline Validation**
Before running pipeline, users are prompted to confirm if:
- No animations selected for skeletal mesh
- Multiple animations selected (shows time estimate)
- 10+ animations selected (strong warning about duration)

## User Experience

### Selection Flow
1. Select project and set mesh type to "Skeletal"
2. In Animation section, choose "Library Selection" mode
3. Browse categories and check desired animations
4. Counter updates: "5 selected"
5. Warning box appears: "5 animations selected. Estimated time: 25-50 minutes"
6. Click "Run Pipeline"
7. Confirmation prompt: "5 animations will be generated sequentially. Continue?"

### Time Estimates
- Single animation: ~5-10 minutes
- Multiple animations: 5-10 minutes each (sequential)
- 10+ animations: Several hours

## Technical Implementation

### Frontend (app.js)
- `selectedAnimations`: Set tracking selected animation keys
- `populateAnimationCheckboxes()`: Generates checkbox UI from prompt library
- `toggleCategory(category, checked)`: Handles category-level selection
- `toggleAnimation(category, animKey, checked)`: Handles individual selection
- `updateAnimationUI()`: Updates counters and warnings
- `getSelectedAnimations()`: Returns array of selected animation objects
- `clearAllAnimations()`: Deselects all animations

### Configuration (saveConfig)
Animation config structure:
```javascript
hy_motion_prompt: {
    mode: 'library',           // or 'custom'
    selections: [              // Array of selected animations
        {
            category: 'locomotion',
            name: 'walk_cycle',
            motion: '...',
            style: '...',
            // ... other fields
        }
    ],
    enabled: true
}
```

### Styling (style.css)
- `.animation-checkbox-container`: Scrollable checkbox container
- `.animation-category`: Category grouping
- `.category-header`: Sticky header with select-all checkbox
- `.animation-list`: Responsive grid of checkboxes
- `.warning-box`: Color-coded warnings (info/warning/error)

## Backend Integration

### Expected Changes to `run_pipeline.py`
The animation stage should:
1. Check `config['hy_motion_prompt']['mode']`
2. If mode is 'library', iterate through `selections` array
3. Generate each animation sequentially
4. Save each animation with unique naming (e.g., `walk_cycle.fbx`, `run_cycle.fbx`)
5. Log progress for each animation

### Configuration Structure
```json
{
  "hy_motion_prompt": {
    "mode": "library",
    "selections": [
      {
        "category": "locomotion",
        "name": "walk_cycle",
        "motion": "A natural, neutral walk cycle...",
        "style": "Realistic weight transfer...",
        "constraints": "Loopable start and end pose...",
        "camera": "Locked, neutral.",
        "output": "30 frames, 30fps, seamless loop."
      },
      {
        "category": "idle",
        "name": "idle_breathing",
        "motion": "Standing idle with slow breathing...",
        "style": "Subtle clavicle lift...",
        "constraints": "Loopable, no jitter...",
        "camera": "Locked.",
        "output": "60 frames, 30fps."
      }
    ],
    "enabled": true
  }
}
```

## Benefits
1. **Prevents Accidents**: No more accidentally generating 100+ animations
2. **User Control**: Explicit selection of desired animations
3. **Transparency**: Clear warnings and time estimates
4. **Flexibility**: Can still use custom prompts for one-off animations
5. **Efficiency**: Only generate what's needed

## Future Enhancements
- Batch generation with parallel processing
- Animation preview thumbnails
- Favorites/presets for common animation sets
- Progress bar showing which animation is currently generating
- Ability to pause/resume batch generation
