# runpod-3d-ai-template

A complete 3D character production pipeline for RunPod, combining AI-powered texture generation, automatic rigging, motion capture, and sprite generation in a modern web interface.

## 🎬 Features

### 🖥️ Web-Based Pipeline GUI (Port 7860)
Modern, responsive web interface for the complete 3D character pipeline:
- **Project Management**: Create and manage multiple character projects
- **File Upload**: Drag-and-drop mesh files, UDIM textures, style and pose references
- **3D Viewer**: Real-time Three.js viewer with animation playback and material preview
- **ComfyUI Model Manager**: Browse, upload, validate, and select AI models
- **Pipeline Execution**: One-click pipeline with real-time status and logs
- **Dark/Light Theme**: System-aware theme with manual toggle

### 🤖 AI-Powered Workflows
- **Texture Generation**: SDXL-based PBR texture creation (albedo, normal, roughness, metallic, AO)
- **Style Transfer**: IP-Adapter integration for reference-based texturing
- **2D Sprite Generation**: AI-powered character sprites from 3D animations
  - OpenPose and Depth ControlNet for pose preservation
  - Character style modifications via prompts
  - Multiple camera angles (front, side, back, diagonal)
  - Automatic background removal

### 🎨 3D Pipeline Stages
1. **Texture Generation** (ComfyUI): AI-generated PBR materials
2. **Rigging** (UniRig): Automatic skeletal rigging
3. **Animation** (Hy-Motion): Motion prompt-based animation
4. **Export**: Package ready-to-use assets
5. **Sprite Generation**: 2D game sprites from 3D (optional)

### 📦 ComfyUI Model Management
- Upload/download models (checkpoints, LoRAs, ControlNet, VAE, IP-Adapter)
- Automatic model validation for workflows
- Last-used model memory and auto-selection
- Organized by type with size and date info

### ⚙️ Pipeline Features
- **Mesh Type Tagging**: Skeletal vs static (skips rigging/animation for props)
- **Motion Prompt Library**: 70+ preset animations (locomotion, combat, cinematic, etc.)
- **Conditional Execution**: Only runs required stages based on mesh type
- **Real-time Status**: Live progress tracking with stage indicators
- **Log Viewer**: Detailed pipeline execution logs

### 🛠️ Services
- **Pipeline GUI**: Port `7860` - Main web interface
- **ComfyUI**: Port `8188` - Stable diffusion backend
- **File Browser**: Port `8080` - File management interface

### 📚 AI Tools Included
- **ComfyUI**: Node-based stable diffusion with custom workflows
- **UniRig**: Advanced automatic 3D rigging
- **TripoSR**: 3D reconstruction from images
- **Hy-Motion**: Text-to-motion animation generation
- **Blender**: Headless 3D rendering and processing

## 🚀 Quick Start

### Local Development
```bash
# Start the pipeline GUI
cd pipeline
python api_server.py

# Access at http://localhost:7860
```

### Building Docker Image
```bash
# Full build with all tools
docker build -t runpod-3d-ai -f Dockerfile .

# Runtime-only build (smaller, for deployment)
docker build -t runpod-3d-ai-runtime -f Dockerfile.runpod .
```

### Running Locally with Docker
```bash
docker run -it --gpus all \
  -p 7860:7860 \
  -p 8188:8188 \
  -p 8080:8080 \
  -v $(pwd)/workspace:/workspace \
  runpod-3d-ai
```

**Access Points**:
- Pipeline GUI: http://localhost:7860
- ComfyUI: http://localhost:8188
- File Browser: http://localhost:8080

## 📋 RunPod Deployment

### Template Configuration

**Container Image**: `ghcr.io/your-username/runpod-3d-ai-template:latest`

**Port Mappings**:
- `7860` - Pipeline GUI (HTTPS access via RunPod proxy)
- `8188` - ComfyUI
- `8080` - File Browser

**Volume Mount**: `/workspace` (persistent storage)

**Environment Variables**:
| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8188` | ComfyUI port |
| `PIPELINE_GUI_PORT` | `7860` | Pipeline web GUI port |
| `FILE_BROWSER_PORT` | `8080` | File browser port |
| `MODEL_DOWNLOAD_ON_START` | `0` | Auto-download models on startup |
| `COMFYUI_PATH` | `/workspace/ComfyUI` | ComfyUI installation path |

### First-Time Setup on RunPod

1. **Start Pod**: Launch your RunPod instance with the template
2. **Upload Models**: Access port 7860, click "Manage Models", upload required models:
   - SDXL checkpoint (e.g., `sdxl_base_1.0.safetensors`)
   - IP-Adapter model (e.g., `ip-adapter_sdxl.safetensors`)
   - ControlNet models (e.g., `openpose_sdxl.safetensors`, `depth_sdxl.safetensors`)
3. **Create Project**: Click "+ New Project" in the GUI
4. **Upload Character Mesh**: Drag FBX/OBJ into mesh upload area
5. **Configure & Run**: Set mesh type, select workflow models, click "Run Pipeline"

### Model Requirements

**For Texture Generation**:
- ✅ SDXL Checkpoint (~6.5GB)
- ✅ IP-Adapter for SDXL (~2.5GB)

**For Sprite Generation** (additional):
- ✅ ControlNet OpenPose SDXL (~2.5GB)
- ✅ ControlNet Depth SDXL (~2.5GB)

Models can be uploaded via the GUI or placed directly in `/workspace/ComfyUI/models/` folders.

## 📖 Documentation

- [Pipeline Integration Guide](pipeline/POD_INTEGRATION.md)
- [Mesh Type & Sprite Generation](pipeline/MESH_TYPE_AND_SPRITES.md)
- [GUI Deployment Guide](pipeline/RUNPOD_GUI_DEPLOYMENT.md)
- [Implementation Summary](pipeline/IMPLEMENTATION_SUMMARY.md)

## 🎮 Usage Examples

### Example 1: Skeletal Character with Animation
1. Upload character mesh (FBX with bind pose)
2. Select "Skeletal" mesh type
3. Upload style reference images
4. Choose motion preset (e.g., "Idle - Breathing")
5. Enable sprite generation with "Front + Side" angles
6. Click "Run Pipeline"

**Output**: Textured, rigged, animated FBX + sprite sheets

### Example 2: Static Prop
1. Upload prop mesh (OBJ)
2. Select "Static" mesh type
3. Upload UDIM texture tiles
4. Click "Run Pipeline"

**Output**: Textured model (skips rigging/animation)

### Example 3: Custom Animation
1. Upload rigged character
2. Select "Custom" motion category
3. Enter motion prompt: "walking slowly, tired, heavy backpack"
4. Set style: "realistic, weight distribution"
5. Set constraints: "30 frames, looping"
6. Run pipeline

## 🔧 Development

### Project Structure
```
pipeline/
├── api_server.py              # Flask REST API
├── model_manager.py           # ComfyUI model management
├── run_pipeline.py            # Pipeline orchestrator
├── project_init.py            # Project initialization
├── bootstrap.py               # Setup utilities
├── comfui_workflows/          # ComfyUI workflow JSON files
│   ├── texture_workflow.json
│   └── sprite_generation_workflow.json
├── hy_motion_prompts/         # Motion prompt library
│   └── prompt_library.json
├── tools/                     # Pipeline scripts
│   ├── generate_sprites.py
│   ├── hy_motion.py
│   ├── retarget.py
│   └── ...
└── web_ui/                    # Frontend
    ├── index.html
    └── static/
        ├── app.js
        └── style.css
```

### Adding Custom Workflows

1. Create workflow JSON in `comfui_workflows/`
2. Add requirements to `model_manager.py`:
```python
REQUIRED_MODELS = {
    'my_workflow': {
        'checkpoints': ['sdxl'],
        'loras': ['my_lora']
    }
}
```
3. Add to GUI workflow selector in `index.html`

## � Documentation

- **[DEPENDENCIES.md](DEPENDENCIES.md)** - Installing Pillow, UniRig, and HY-Motion
- **[COMFYUI_INSTALLATION.md](COMFYUI_INSTALLATION.md)** - ComfyUI custom nodes and models setup
- **[SPRITE_PIPELINE.md](SPRITE_PIPELINE.md)** - AI-enhanced sprite generation guide
- **[UNIRIG_HYMOTION_INTEGRATION.md](UNIRIG_HYMOTION_INTEGRATION.md)** - Auto-rigging and animation integration
- **[RUNPOD_DEPLOYMENT.md](RUNPOD_DEPLOYMENT.md)** - RunPod template configuration

## 🔧 Installation & Setup

⚠️ **POST-LAUNCH SETUP**: Run these commands **AFTER** deploying your RunPod pod to keep the container image small.

### 1. Core Dependencies (Required)

SSH into your RunPod container and install Pillow, UniRig, and HY-Motion:

```bash
# SSH into pod (use RunPod's SSH button or terminal)
cd /workspace
chmod +x install_dependencies.sh
./install_dependencies.sh
```

✅ **Installation completes in ~5 minutes** (without model downloads)

Or install manually - see **[DEPENDENCIES.md](DEPENDENCIES.md)** for detailed instructions.

### 2. ComfyUI Dependencies (For Sprite Generation)

Install custom nodes and AI models - see **[COMFYUI_INSTALLATION.md](COMFYUI_INSTALLATION.md)** or click **⚙️ ComfyUI Setup** in the web UI.

Required:
- 6 custom nodes (AnimateDiff, IP-Adapter, ControlNet, etc.)
- ~20 GB AI models (motion, ControlNet, checkpoints)

### 3. AI Model Downloads (Optional - For Production)

⚠️ **Skip for testing**: The pipeline works in fallback mode without these models.

**UniRig Models** (~5 GB):
- Visit: https://github.com/VAST-AI-Research/UniRig#download-models
- Place in: `/workspace/unirig/models/`
- Without models: Uses fallback armature (20 bones, auto weights)

**HY-Motion Models** (~15 GB):
- Visit: https://github.com/Tencent-Hunyuan/HY-Motion-1.0#model-download
- Place in: `/workspace/hy-motion/models/`
- Without models: Creates placeholder animations

💡 **Download inside the pod** to save bandwidth on pod restarts (models persist in `/workspace` volume).

## 🐛 Troubleshooting

**Pillow not found**:
```bash
/opt/blender/4.0/python/bin/python3.10 -m pip install Pillow
```

**UniRig/HY-Motion warnings**:
- Pipeline works with fallback modes (basic rigging/placeholder animations)
- Download models for full functionality (see above)

**Models not validating**:
- Check model files are in correct ComfyUI folders
- Click "Refresh" in model manager
- Try "Auto-Select" in Select Models tab

**Pipeline fails at rigging**:
- Ensure mesh is in T-pose or bind pose
- Check mesh has no non-manifold geometry
- Try "Static" mesh type if rigging not needed

**Sprites not generating**:
- Verify ControlNet models are uploaded
- Check animation completed successfully
- Review pipeline log for errors

**ComfyUI errors**:
- Check ComfyUI is running on port 8188
- Verify all workflow nodes are installed
- Check GPU memory availability





