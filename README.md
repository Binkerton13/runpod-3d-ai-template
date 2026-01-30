
<div align="center">
	<h1 style="font-family: 'Segoe UI', Arial, sans-serif; font-weight: 700; letter-spacing: 1px;">SpriteForge</h1>
	<h2 style="font-family: 'Fira Sans', 'Segoe UI', Arial, sans-serif; font-weight: 400; color: #4a90e2;">AI‑Driven 2D Animation & Sprite Generation Pipeline</h2>
	<strong style="font-family: 'Fira Mono', monospace; font-size: 1.1em;">HY‑Motion → Frames → ComfyUI → Sprites</strong>
</div>

SpriteForge is a modular, production‑ready pipeline for generating game‑ready 2D sprites using AI‑driven motion generation and image synthesis.
It is designed for:

- Game developers and technical artists who want to automate 2D sprite creation
- Researchers and tinkerers exploring AI-based animation workflows
- Teams seeking a modern, containerized, and extensible pipeline for 2D asset production

**Intended Use:**

SpriteForge is intended to be run as a Docker container, either locally or on cloud GPU platforms (such as Runpod). It provides a unified web GUI for managing the full animation-to-sprite workflow, including motion generation, frame extraction, AI-based sprite synthesis, and sprite sheet assembly. All major steps are accessible from the browser, with persistent workspace storage for assets and models.

SpriteForge is a modular, production‑ready pipeline for generating game‑ready 2D sprites using AI‑driven motion generation and image synthesis.  
It replaces traditional 3D rigging workflows with a clean, modern stack built around:

- **HY‑Motion** for motion generation  
- **ComfyUI** for image generation  
- **Custom nodes** for identity locking, temporal consistency, and background removal  
- **A unified SpriteForge GUI** for orchestration  

---


## Features

### <span style="font-family: 'Fira Sans', Arial, sans-serif; font-weight: 600;">Animation & Motion</span>
- HY‑Motion 1.0 integration  
- Motion presets (walk, run, stealth, interact, etc.)  
- Frame extraction and management  
- Optional frame interpolation for smoother motion  

### <span style="font-family: 'Fira Sans', Arial, sans-serif; font-weight: 600;">Image & Sprite Generation</span>
- ComfyUI baked into the container  
- AnimateDiff‑Evolved for temporal consistency  
- IP‑Adapter Plus for character identity locking  
- ControlNet Aux for pose/depth/normal preprocessing  
- Background removal (rembg + essentials)  
- Sprite sheet assembly (coming soon)  

### <span style="font-family: 'Fira Sans', Arial, sans-serif; font-weight: 600;">Unified GUI (Port 5000)</span>
- Animation generation  
- Frame preview  
- Sprite generation  
- Model management (checkpoints, LoRAs, IP‑Adapters, VAEs)  
- Settings & logs  

### <span style="font-family: 'Fira Sans', Arial, sans-serif; font-weight: 600;">Developer‑Friendly</span>
- Clean Dockerfile  
- Idempotent installers  
- Persistent workspace  
- Modular folder structure  
- Easy to extend  

---


## Architecture Overview


<span style="font-family: 'Fira Mono', monospace; font-size: 1.1em;">HY‑Motion → Frames → ComfyUI → SpriteForge GUI → Sprites</span>

### <span style="font-family: 'Fira Sans', Arial, sans-serif; font-weight: 600;">Services & Ports</span>
| Service | Port | Description |
|--------|------|-------------|
| ComfyUI | 8188 | Image generation engine |
| File Browser | 8080 | Workspace file explorer |
| SpriteForge GUI | 5000 | Unified control panel |
| Frontend Dev (optional) | 3000 | React/Vue dev server |

---


## Folder Structure

/workspace
/pipeline
start.sh
install_dependencies.sh
supervisord.conf
/gui
app.py
/routes
/templates
/static
/services
/models
/scripts
install_custom_nodes.sh
/env_patches
sitecustomize.py

/custom_nodes
/models
/checkpoints
/loras
/vae
/controlnet
/unet

/animations
/sprites
/logs

///spriteforge/
├── .dockerignore
├── .git/
├── .github/
├── .gitignore
├── .hintrc
├── animations/
├── Dockerfile
├── file_browser.py
├── pipeline/
│   ├── .version
│   ├── env_patches/
│   ├── gui/
│   │   ├── app.py
│   │   ├── frontend/
│   │   │   ├── docs/
│   │   │   ├── index.html
│   │   │   ├── node_modules/
│   │   │   ├── package-lock.json
│   │   │   ├── package.json
│   │   │   ├── src/
│   │   │   │   ├── api/
│   │   │   │   ├── App.vue
│   │   │   │   ├── components/
│   │   │   │   │   ├── FileBrowser/
│   │   │   │   │   │   ├── FileBrowserModal.vue
│   │   │   │   │   │   ├── FileList.vue
│   │   │   │   │   │   ├── FilePreview.vue
│   │   │   │   │   │   └── FileUpload.vue
│   │   │   │   │   ├── ModelActiveSelector.vue
│   │   │   │   │   ├── ModelList.vue
│   │   │   │   │   ├── ModelTypeTabs.vue
│   │   │   │   │   ├── ModelUploadButton.vue
│   │   │   │   │   ├── nodes/
│   │   │   │   │   │   ├── NodeCreateMenu.vue
│   │   │   │   │   │   └── WorkflowNode.vue
│   │   │   │   │   ├── ProjectAssetList.vue
│   │   │   │   │   ├── ProjectCreateModal.vue
│   │   │   │   │   ├── ProjectList.vue
│   │   │   │   │   ├── ProjectMetadataEditor.vue
│   │   │   │   │   ├── SettingsModal.vue
│   │   │   │   │   ├── Sidebar.vue
│   │   │   │   │   ├── SpriteFrameGrid.vue
│   │   │   │   │   ├── SpriteGenerationSettings.vue
│   │   │   │   │   ├── SpriteModelSelector.vue
│   │   │   │   │   ├── SpritePanel.vue
│   │   │   │   │   ├── SpriteSheetAssembler.vue
│   │   │   │   │   ├── SpriteStyleSelector.vue
│   │   │   │   │   ├── TaskQueue.vue
│   │   │   │   │   ├── ToastContainer.vue
│   │   │   │   │   ├── WorkflowList.vue
│   │   │   │   │   └── WorkFlowPanel.vue
│   │   │   │   ├── health.js
│   │   │   │   ├── Layout/
│   │   │   │   │   ├── AppLayout.vue
│   │   │   │   │   ├── Sidebar.vue
│   │   │   │   │   └── TopBar.vue
│   │   │   │   ├── main.js
│   │   │   │   ├── pages/
│   │   │   │   │   ├── ModelPage.vue
│   │   │   │   │   ├── MotionPage.vue
│   │   │   │   │   ├── ProjectPage.vue
│   │   │   │   │   ├── SpritePage.vue
│   │   │   │   │   └── WorkflowGraphPage.vue
│   │   │   │   ├── router.js
│   │   │   │   ├── shortcuts.js
│   │   │   │   ├── stores/
│   │   │   │   │   ├── files.js
│   │   │   │   │   ├── health.js
│   │   │   │   │   ├── models.js
│   │   │   │   │   ├── motion.js
│   │   │   │   │   ├── notify.js
│   │   │   │   │   ├── projects.js
│   │   │   │   │   ├── settings.js
│   │   │   │   │   ├── sprites.js
│   │   │   │   │   ├── tasks.js
│   │   │   │   │   └── workflows.js
│   │   │   │   └── theme.css
│   │   │   └── vite.config.js
│   │   ├── models/
│   │   ├── routes/
│   │   ├── services/
│   │   ├── static/
│   │   └── templates/
│   ├── install_dependencies.sh
│   ├── project.json
│   ├── scripts/
│   ├── VERSION
│   └── workflows/
├── README.md
├── requirements.txt
├── sprites/
├── start.sh
├── supervisord.conf
├── validate.py///
---


## Installation

### 1. Clone the repository
```bash
git clone https://github.com/<yourname>/SpriteForge.git
cd SpriteForge

### 2. Build the container

docker build -t spriteforge .

### 3. Run the container

docker run --gpus all -p 8188:8188 -p 8080:8080 -p 5000:5000 -v ./workspace:/workspace spriteforge


## Usage

**SpriteForge GUI (recommended):**

1. Open your browser at: [http://localhost:5000](http://localhost:5000)
2. Use the web interface to:
	- <span style="font-family: 'Fira Sans', Arial, sans-serif; font-weight: 600;">Generate animations</span>
	- <span style="font-family: 'Fira Sans', Arial, sans-serif; font-weight: 600;">Extract frames</span>
	- <span style="font-family: 'Fira Sans', Arial, sans-serif; font-weight: 600;">Generate sprites</span>
	- <span style="font-family: 'Fira Sans', Arial, sans-serif; font-weight: 600;">Manage models</span>
	- <span style="font-family: 'Fira Sans', Arial, sans-serif; font-weight: 600;">View logs</span>

Manage models

View logs


**ComfyUI:** [http://localhost:8188](http://localhost:8188)

**File Browser:** [http://localhost:8080](http://localhost:8080)


## Models

SpriteForge expects models in:

/workspace/models/checkpoints
/workspace/models/loras
/workspace/models/vae
/workspace/models/controlnet
/workspace/models/unet


### Recommended Models

- AnimateDiff: `v3_sd15_mm.ckpt`
- IP‑Adapter: `ip-adapter-faceid-plusv2_sd15.bin`
- ControlNet: openpose, depth, normalbae, canny
- Checkpoints: SDXL‑Turbo, SDXL‑Lightning, SDXL 1.0


## Development

**GUI Backend:**
Located in `/workspace/pipeline/gui/app.py` (runs automatically via supervisord)

**Custom Nodes:**
Installed via `/workspace/pipeline/scripts/install_custom_nodes.sh`

**HY‑Motion:**
Located in `/workspace/hy-motion`


## Roadmap

- Sprite sheet assembler
- Batch animation presets
- Character identity library
- Style presets
- Web‑based model downloader
- Full React/Vue frontend


## License
MIT License (or your preferred license)


## Contributing
Pull requests are welcome.
Please open an issue first to discuss major changes.


## Credits
- HY‑Motion by Tencent Hunyuan
- ComfyUI by comfyanonymous
- Custom nodes by their respective authors
- SpriteForge architecture by Morgen

---
