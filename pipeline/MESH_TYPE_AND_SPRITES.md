# Mesh Type Tagging and Sprite Generation

## Overview

This document describes the new features added to the 3D Character Pipeline:

1. **Mesh Type Tagging** - Allows users to specify if a mesh is skeletal or static, controlling which pipeline stages execute
2. **2D Sprite Generation** - Generates 2D character sprites from 3D animations using ComfyUI for character style overlays

---

## 1. Mesh Type Tagging

### Purpose
Not all 3D models require rigging and animation. Static meshes (props, buildings, etc.) only need texture generation. This feature allows the pipeline to skip unnecessary processing steps based on mesh type.

### UI Components

**Location**: Left sidebar, appears after mesh upload

**Options**:
- **Skeletal** (default): Full pipeline with rigging, animation, and export
- **Static**: Texture generation and export only, skips rigging and animation

### Pipeline Behavior

| Mesh Type | Textures | Rigging | Animation | Export | Sprites |
|-----------|----------|---------|-----------|--------|---------|
| Skeletal  | ✅       | ✅      | ✅        | ✅     | ✅*     |
| Static    | ✅       | ⊘ Skip  | ⊘ Skip    | ✅     | ⊘ Skip  |

*Sprites only run if enabled in configuration

### Implementation

**Configuration Storage**: `pipeline/config.json`
```json
{
  "mesh_type": "skeletal",
  ...
}
```

**Pipeline Orchestrator**: `pipeline/run_pipeline.py`
- Reads mesh_type from config
- Conditionally executes stages based on mesh requirements
- Logs skipped stages with reason

**Files**:
- [pipeline/web_ui/index.html](pipeline/web_ui/index.html#L48-L55) - Mesh type selector UI
- [pipeline/web_ui/static/app.js](pipeline/web_ui/static/app.js#L1195-L1211) - `updateMeshType()` function
- [pipeline/run_pipeline.py](pipeline/run_pipeline.py#L54-L74) - Stage execution logic

---

## 2. 2D Sprite Generation

### Purpose
Generate 2D character sprites from 3D animations by rendering frames from multiple angles and applying character style modifications using AI image generation.

### Use Cases
- Game sprite sheets for 2D games
- Character portraits and avatar variations
- Animation reference sheets
- Style transfer from 3D to 2D art

### Configuration Options

**Location**: Right sidebar, "2D Sprite Generation" section

| Option | Description | Default |
|--------|-------------|---------|
| Enable Sprite Generation | Toggle sprite generation on/off | Off |
| Frame Interval | Capture every Nth frame (1-4) | 2 |
| Camera Angles | Views to render (multi-select) | Front |
| Character Prompt | Modifications to apply | "" |
| Negative Prompt | Elements to avoid | "blurry, low quality" |
| Resolution | Output sprite size | 512x512 |
| Generate Spritesheet | Combine into sprite sheet | Off |

### Camera Angles

Available angles:
- **Front**: Forward-facing view
- **Side**: Profile view
- **Back**: Rear view
- **Diagonal**: 45° angles (front-left, front-right, back-left, back-right)

### Workflow

1. **3D Render Phase** (Blender)
   - Load animated FBX from `3_animation/`
   - Setup camera and lighting for clean sprite renders
   - Render frames at specified interval with transparent background
   - Save renders to `4_export/sprite_renders/`

2. **Character Generation Phase** (ComfyUI)
   - Load 3D render as ControlNet reference (pose + depth)
   - Apply character prompt modifications
   - Use optional style reference images
   - Generate 2D character sprite maintaining pose
   - Remove background for sprite use
   - Save to `4_export/sprites/`

3. **Spritesheet Assembly** (Optional)
   - Combine individual frames into grid layout
   - Save to `4_export/spritesheets/`
   - Generate metadata JSON with frame info

### Example Configuration

**Character Prompt**:
```
female character, green hair, ponytail, fantasy armor, 
anime style, 2d game art, vibrant colors, clean lines
```

**Negative Prompt**:
```
3d render, blurry, low quality, watermark, realistic, 
depth of field, motion blur
```

**Frame Interval = 2** (for 30fps animation):
- Captures every 2nd frame = 15fps sprite animation
- 90 frame animation → 45 sprite frames
- Reduces file count while maintaining smooth motion

### Output Structure

```
4_export/
├── sprite_renders/          # 3D renders
│   ├── render_front_frame_0001.png
│   ├── render_front_frame_0003.png
│   └── ...
├── sprites/                 # Generated 2D sprites
│   ├── sprite_front_frame_0001.png
│   ├── sprite_front_frame_0003.png
│   └── sprite_generation_info.json
└── spritesheets/           # Combined sprite sheets
    ├── spritesheet_front.png
    ├── spritesheet_side.png
    └── ...
```

### ComfyUI Workflow

**File**: `pipeline/comfui_workflows/sprite_generation_workflow.json`

**Key Nodes**:
1. **LoadImage** (id:1) - 3D render frame
2. **OpenPosePreprocessor** (id:19) - Extract pose from render
3. **DepthAnythingPreprocessor** (id:21) - Extract depth map
4. **ControlNetApply** (id:9, 22) - Apply pose and depth control
5. **IPAdapterApply** (id:17) - Apply style reference (optional)
6. **CLIPTextEncode** (id:3) - Character prompt
7. **KSampler** (id:5) - Generate character image
8. **RemoveBackground** (id:13) - Transparent background for sprite
9. **SaveImage** (id:14) - Output sprite

**Control Methods**:
- **OpenPose**: Maintains character pose from 3D render
- **Depth**: Preserves spatial relationships and volume
- **IP-Adapter**: Applies visual style from reference images

### Script Usage

**Manual Execution** (Blender):
```bash
blender --background --python pipeline/tools/generate_sprites.py -- <project_path>
```

**Pipeline Integration** (Automatic):
- Runs automatically after animation stage if enabled
- Configure via GUI before running pipeline

### Files

- [pipeline/tools/generate_sprites.py](pipeline/tools/generate_sprites.py) - Main sprite generation script
- [pipeline/comfui_workflows/sprite_generation_workflow.json](pipeline/comfui_workflows/sprite_generation_workflow.json) - ComfyUI workflow
- [pipeline/web_ui/index.html](pipeline/web_ui/index.html#L275-L336) - Sprite configuration UI
- [pipeline/web_ui/static/app.js](pipeline/web_ui/static/app.js#L1213-L1229) - `toggleSpriteOptions()` function

---

## Pipeline Orchestrator

### Overview

The `run_pipeline.py` script orchestrates the complete 3D character pipeline, handling:
- Stage execution based on mesh type
- Input validation
- Output directory management
- Error handling and logging
- Status tracking

### Usage

**Via GUI** (Recommended):
1. Configure project settings
2. Click "Run Pipeline" button
3. Monitor status in real-time
4. View logs for detailed progress

**Via Command Line**:
```bash
python pipeline/run_pipeline.py <project_path>
```

### API Endpoints

**Start Pipeline**:
```http
POST /api/pipeline/run
Content-Type: application/json

{
  "project_name": "my_character"
}
```

**Get Status**:
```http
GET /api/pipeline/status/<project_name>
```

Response:
```json
{
  "project": "my_character",
  "mesh_type": "skeletal",
  "stages": {
    "textures": {
      "name": "Texture Generation",
      "required": true,
      "completed": true
    },
    "rigging": {
      "name": "Rigging",
      "required": true,
      "completed": true
    },
    ...
  }
}
```

**Get Log**:
```http
GET /api/pipeline/log/<project_name>?lines=50
```

### Log Format

```
[2024-01-18 09:30:15] Starting pipeline for project: my_character
[2024-01-18 09:30:15] Mesh type: skeletal
[2024-01-18 09:30:15] Starting stage: Texture Generation
[2024-01-18 09:30:15]   Script: tools/generate_textures.py
[2024-01-18 09:31:45]   ✓ Texture Generation completed successfully
[2024-01-18 09:31:45] Starting stage: Rigging
[2024-01-18 09:31:45]   Skipping Animation (not required for static mesh)
```

### Files

- [pipeline/run_pipeline.py](pipeline/run_pipeline.py) - Main orchestrator
- [pipeline/api_server.py](pipeline/api_server.py#L600-L687) - API endpoints
- [pipeline/web_ui/static/app.js](pipeline/web_ui/static/app.js#L1337-L1512) - Frontend integration

---

## Technical Details

### Dependencies

**Python Packages**:
- `bpy` (Blender Python API) - 3D rendering
- `Pillow` - Image processing
- `requests` - ComfyUI API calls

**External Services**:
- **Blender** (3.x+) - 3D rendering and frame capture
- **ComfyUI** (running on port 8188) - AI image generation
- **ComfyUI Models Required**:
  - `sdxl_base_1.0.safetensors` - Base SDXL model
  - `controlnet_openpose_sdxl.safetensors` - Pose control
  - `controlnet_depth_sdxl.safetensors` - Depth control
  - `ip-adapter_sdxl.safetensors` - Style transfer

### Performance Considerations

**Sprite Generation Time**:
- 3D Render: ~2-5 seconds per frame
- ComfyUI Generation: ~8-15 seconds per frame
- Total: ~10-20 seconds per sprite

**Optimizations**:
- Frame interval reduces total frame count
- Multiple angles processed sequentially (could be parallelized)
- Background removal uses efficient U2-Net model
- GPU acceleration for both Blender and ComfyUI

**Disk Space**:
- 3D renders: ~500KB per frame (PNG with transparency)
- 2D sprites: ~300KB per frame (PNG with transparency)
- Spritesheets: ~2-5MB depending on frame count

### Error Handling

The pipeline includes comprehensive error handling:
- Input validation before execution
- Stage timeouts (1 hour per stage)
- Graceful degradation for optional stages
- Detailed error logging
- Status tracking for recovery

---

## Future Enhancements

### Planned Features

1. **Parallel Rendering**
   - Render multiple camera angles simultaneously
   - Batch ComfyUI requests for better throughput

2. **Advanced Sprite Options**
   - Custom camera positions and FOV
   - Multiple lighting setups
   - Outline/cel-shading post-processing
   - Automatic shadow generation

3. **Spritesheet Formats**
   - JSON metadata for game engines (Unity, Godot, etc.)
   - Texture atlas packing
   - Animation timing data export

4. **Style Libraries**
   - Preset style templates (anime, pixel art, etc.)
   - LoRA support for consistent character styles
   - Multi-style generation from single 3D animation

### Known Limitations

1. **ComfyUI Dependency**: Requires ComfyUI server running and models installed
2. **Sequential Processing**: Angles rendered one at a time
3. **No Preview**: Can't preview sprites before full generation
4. **Fixed Camera Setup**: Limited camera angle customization

---

## Troubleshooting

### Common Issues

**Sprites not generating**:
- Check ComfyUI is running on port 8188
- Verify required models are installed
- Check `pipeline/pipeline_log.txt` for errors

**Pipeline skips rigging/animation for skeletal mesh**:
- Verify mesh type is set to "skeletal"
- Check config saved correctly
- Reload project to refresh configuration

**Low quality sprites**:
- Increase resolution (try 768 or 1024)
- Improve character prompt with more detail
- Use high-quality style reference images
- Adjust CFG scale in ComfyUI workflow

**Inconsistent character appearance**:
- Lower CFG scale for more consistency
- Increase ControlNet strength
- Use seed control in ComfyUI
- Provide detailed character description

---

## References

- [Pipeline Integration Guide](POD_INTEGRATION.md)
- [GUI Deployment Guide](RUNPOD_GUI_DEPLOYMENT.md)
- [Implementation Summary](IMPLEMENTATION_SUMMARY.md)
- [ComfyUI Documentation](https://github.com/comfyanonymous/ComfyUI)
- [ControlNet Guide](https://github.com/lllyasviel/ControlNet)
- [IP-Adapter Documentation](https://github.com/tencent-ailab/IP-Adapter)
