# UniRig & HY-Motion Integration Guide

## Overview

This document describes the integration of **UniRig** (auto-rigging) and **HY-Motion** (animation generation) into the RunPod 3D AI pipeline.

## What Was Integrated

### 1. UniRig - Automatic 3D Rigging
- **Repository**: https://github.com/VAST-AI-Research/UniRig
- **Location**: `/workspace/unirig`
- **Purpose**: Automatically generates skeleton and skinning weights for 3D models
- **Integration**: [pipeline/tools/auto_rig.py](pipeline/tools/auto_rig.py)

### 2. HY-Motion 1.0 - Text-to-3D Animation
- **Repository**: https://github.com/Tencent-Hunyuan/HY-Motion-1.0
- **Location**: `/workspace/hy-motion`
- **Purpose**: Generates 3D character animations from text prompts
- **Integration**: [pipeline/tools/hy_motion.py](pipeline/tools/hy_motion.py)

### 3. Blender 4.0.2
- **Purpose**: Required for running auto_rig.py and sprite generation scripts
- **Location**: `/opt/blender-4.0.2-linux-x64/`
- **Binary**: `/usr/local/bin/blender` (symlink)

---

## Installation in Dockerfile.runpod

### Blender Installation
```dockerfile
ARG BLENDER_VERSION=4.0.2
RUN cd /tmp && \
    wget -q https://download.blender.org/release/Blender${BLENDER_VERSION%.*}/blender-${BLENDER_VERSION}-linux-x64.tar.xz && \
    tar -xf blender-${BLENDER_VERSION}-linux-x64.tar.xz && \
    rm blender-${BLENDER_VERSION}-linux-x64.tar.xz && \
    mv blender-${BLENDER_VERSION}-linux-x64 /opt/ && \
    ln -s /opt/blender-${BLENDER_VERSION}-linux-x64/blender /usr/local/bin/blender
```

### UniRig Installation
```dockerfile
RUN git clone https://github.com/VAST-AI-Research/UniRig.git ${WORKSPACE}/unirig && \
    chown -R app:app ${WORKSPACE}/unirig

# Remove problematic dependencies
RUN sed -i '/bpy/d' ${WORKSPACE}/unirig/requirements.txt && \
    sed -i '/flash_attn/d' ${WORKSPACE}/unirig/requirements.txt

# Install dependencies
RUN ${VIRTUAL_ENV}/bin/pip install --no-cache-dir -r ${WORKSPACE}/unirig/requirements.txt || true
```

**Why remove `bpy` and `flash_attn`?**
- `bpy`: Conflicts with standalone Blender installation
- `flash_attn`: Complex compilation requirements, optional for inference

### HY-Motion Installation
```dockerfile
RUN git clone https://github.com/Tencent-Hunyuan/HY-Motion-1.0.git ${WORKSPACE}/hy-motion && \
    chown -R app:app ${WORKSPACE}/hy-motion

# Install dependencies
RUN if [ -f "${WORKSPACE}/hy-motion/requirements.txt" ]; then \
        ${VIRTUAL_ENV}/bin/pip install --no-cache-dir -r ${WORKSPACE}/hy-motion/requirements.txt || true; \
    fi
```

---

## How UniRig Integration Works

### Workflow in auto_rig.py

The `apply_unirig()` function implements a 3-stage UniRig workflow:

```python
def apply_unirig(mesh_obj, config):
    """
    1. Export mesh to temporary FBX
    2. Generate skeleton using UniRig
    3. Generate skinning weights
    4. Merge rig with original mesh
    5. Import rigged result back into Blender
    """
```

### Stage 1: Skeleton Generation
```bash
bash /workspace/unirig/launch/inference/generate_skeleton.sh \
    --input <mesh.fbx> \
    --output <skeleton.fbx> \
    --seed <random_seed>
```

**Parameters**:
- `--seed`: Controls skeleton variation (default: 42)
- Configurable in pipeline config: `config['rigging']['seed']`

### Stage 2: Skinning Weight Prediction
```bash
bash /workspace/unirig/launch/inference/generate_skin.sh \
    --input <skeleton.fbx> \
    --output <skin.fbx>
```

**Note**: For best results, manually refine skeleton before skinning (optional)

### Stage 3: Merge
```bash
bash /workspace/unirig/launch/inference/merge.sh \
    --source <skin.fbx> \
    --target <original_mesh.fbx> \
    --output <rigged.fbx>
```

### Fallback Behavior

If UniRig fails at any stage, `create_basic_armature()` creates a simple placeholder armature:
```python
def create_basic_armature(mesh_obj):
    """Creates basic armature with auto-parenting as fallback"""
    bpy.ops.object.armature_add(location=(0, 0, 0))
    armature = bpy.context.active_object
    armature.name = "Fallback_Armature"
    # Auto-parent with weights
    bpy.ops.object.parent_set(type='ARMATURE_AUTO')
    return armature
```

---

## Troubleshooting

### Issue: Rig is Too Large and Offset on -Z Axis

**Symptoms:**
- Armature bones are way larger than the mesh
- Bones positioned below the mesh (negative Z offset)
- Logs show "Fallback_Armature" instead of "UniRig_Armature"

**Root Cause:**
You're getting the fallback armature, not UniRig. This happens when:

1. **UniRig Not Installed**: Check if `/workspace/unirig/` exists
   ```bash
   ls -la /workspace/unirig/launch/inference/
   ```

2. **UniRig Scripts Not Executable**: Shell scripts need permissions
   ```bash
   chmod +x /workspace/unirig/launch/inference/*.sh
   ```

3. **UniRig Dependencies Missing**: Python packages not installed
   ```bash
   cd /workspace/unirig
   pip install -r requirements.txt
   ```

4. **GPU Memory Issues**: UniRig needs 8GB+ VRAM
   ```bash
   nvidia-smi  # Check VRAM usage
   ```

**How to Verify Which Rig is Being Used:**

Check the log output for:
```
=== UniRig Auto-Rigging ===          # ✓ Using UniRig
Running UniRig skeleton prediction...
Skeleton generation complete
UniRig rigging complete: UniRig_Armature
```

VS

```
WARNING: UniRig not found at /workspace/unirig     # ✗ Using fallback
Running in test/development mode - using fallback armature
Creating basic humanoid fallback armature...
Created anatomically-aligned armature with 20 bones
```

**Fix for Fallback Armature Z-Offset:**

The fallback previously used `min_z + height * percentage` which caused offset issues when mesh origin isn't at world origin. **Fixed in latest version** to use mesh center as reference:

```python
# Now uses:
center_z = (min_z + max_z) / 2
landmarks = {
    'pelvis_height': center_z - height * 0.45,  # From center
    'hip_height': center_z,
    'head_top': center_z + height * 0.50,
    # ...
}
```

### Issue: UniRig Skeleton Prediction Fails

**Error**: "Skeleton generation failed"

**Common Causes:**

1. **Non-Manifold Geometry**: Mesh has holes or overlapping faces
   - Fix: Run `validate_and_clean_mesh()` before rigging
   - Or manually: Edit Mode → Select All → Mesh → Clean Up → Merge by Distance

2. **Mesh Too Complex**: >100K vertices can cause timeout
   - Fix: Decimate mesh to 50K-80K vertices
   - Blender: Add Decimate Modifier → Ratio: 0.5

3. **Unsupported Mesh Format**: UniRig works best with `.glb`, `.fbx`, `.obj`
   - Fix: Export mesh as FBX with "Apply Modifiers" enabled

4. **Model Checkpoint Not Downloaded**: First run downloads from Hugging Face
   - Fix: Check `/workspace/unirig/checkpoints/` for model files
   - Manually download if network issues:
   ```bash
   cd /workspace/unirig
   python -c "from src.model import load_model; load_model()"
   ```

### Issue: Skinning Weights Incorrect

**Error**: "Skinning generation failed" or mesh deforms strangely

**Cause**: Skeleton doesn't match mesh topology (missing tail, wings, etc.)

**Solution**: Manually edit skeleton before skinning stage

1. After skeleton generation, open `skeleton.fbx` in Blender
2. Add/remove bones as needed (tail, wings, extra limbs)
3. Save and continue to skinning stage
4. UniRig will adapt weights to your edited skeleton

### Issue: HY-Motion Animations are Placeholders

**Symptom**: Animation files are just copies of the rigged mesh

**Cause**: HY-Motion model not installed

**Fix**:
```bash
cd /workspace
git clone https://github.com/Tencent-Hunyuan/HY-Motion-1.0.git hy-motion
cd hy-motion

# Download model checkpoint
mkdir -p ckpts/tencent
cd ckpts/tencent
wget https://huggingface.co/tencent/HY-Motion-1.0-Lite/resolve/main/model.safetensors

# Or for full model:
wget https://huggingface.co/tencent/HY-Motion-1.0/resolve/main/model.safetensors
```

---

## How HY-Motion Integration Works

### Workflow in hy_motion.py

Uses subprocess to call HY-Motion's CLI interface:

```python
cmd = [
    "python3",
    "/workspace/hy-motion/local_infer.py",
    "--model_path", "/workspace/hy-motion/ckpts/tencent/HY-Motion-1.0-Lite",
    "--input_text", prompt_text,
    "--output_dir", str(anim_dir),
    "--disable_duration_est",  # Save VRAM
    "--disable_rewrite"        # Save VRAM
]
subprocess.run(cmd, check=True)
```

### Model Selection

**HY-Motion-1.0-Lite** (default):
- Size: 0.46B parameters, ~24GB disk space
- VRAM: Lower requirements (~8-16GB)
- Use case: Production, faster inference

**HY-Motion-1.0** (alternative):
- Size: 1.0B parameters, ~26GB disk space  
- VRAM: Higher requirements (~16-24GB)
- Use case: Best quality, complex motions

To switch models, change the `--model_path` in [hy_motion.py](pipeline/tools/hy_motion.py#L61).

### VRAM Optimization Flags

```bash
--disable_duration_est  # Disables LLM-based duration estimation
--disable_rewrite       # Disables LLM-based prompt rewriting
```

**Why disable these?**
- Each uses additional VRAM for separate LLM models
- Duration can be specified manually in config
- Prompt rewriting is optional enhancement

### Animation Prompt System

Prompts are loaded from `pipeline/hy_motion_prompts/prompt_library.json`:

```json
{
  "animations": {
    "idle": {
      "motion": "A person stands still with natural breathing motion",
      "style": "natural",
      "duration": 3.0
    },
    "walk": {
      "motion": "A person walks forward with normal gait",
      "style": "natural",
      "duration": 4.0
    }
  }
}
```

If prompt library is missing, fallback prompts are auto-generated:
```python
prompt_text = f"A person performs {anim_name} animation"
```

---

## Pipeline Configuration

### Rigging Configuration (config.json)
```json
{
  "rigging": {
    "preset": "humanoid",
    "seed": 42
  }
}
```

**Options**:
- `preset`: Type of skeleton (humanoid, quadruped, etc.) - currently informational
- `seed`: Random seed for skeleton variation (try different values for alternatives)

### Animation Configuration (config.json)
```json
{
  "animation": {
    "selected_animations": ["idle", "walk", "run", "jump"],
    "duration_override": null
  }
}
```

**Parameters**:
- `selected_animations`: List of animation names from prompt library
- `duration_override`: Optional manual duration (overrides LLM estimation)

---

## Pipeline Execution Flow

### Complete 5-Stage Pipeline

```
1. Texture Generation (generate_textures.py)
   ↓ Input: Mesh + UV + Prompts → ComfyUI
   ↓ Output: 1_textures/*.png

2. Auto Rigging (auto_rig.py) ← UniRig Integration
   ↓ Input: Mesh from 0_input/
   ↓ Process: UniRig skeleton + skinning + merge
   ↓ Output: 2_rig/*_rigged.fbx

3. Animation (hy_motion.py) ← HY-Motion Integration
   ↓ Input: Rigged mesh from 2_rig/
   ↓ Process: Generate animations from prompts
   ↓ Output: 3_animation/*_<anim_name>.fbx

4. Sprite Generation (generate_sprites.py)
   ↓ Input: Animations from 3_animation/
   ↓ Process: Blender rendering + ComfyUI stylization
   ↓ Output: 4_export/sprites/*.png

5. Export Package (export_package.py)
   ↓ Input: All previous outputs
   ↓ Output: 4_export/package/ (organized bundle)
```

### Execution Command

```bash
python pipeline/run_pipeline.py <project_path> <config_path>
```

**Stage Skipping Logic**:
- Static meshes: Skip rigging, animation, sprites (only textures + export)
- Skeletal meshes: Run all 5 stages
- Optional sprites: Can be disabled in config

---

## System Requirements

### GPU Requirements

| Component | Minimum VRAM | Recommended VRAM |
|-----------|--------------|------------------|
| UniRig (skeleton) | 8GB | 12GB |
| UniRig (skinning) | 8GB | 12GB |
| HY-Motion-1.0-Lite | 8GB | 16GB |
| HY-Motion-1.0 | 16GB | 24GB |
| ComfyUI (textures) | 8GB | 12GB |
| ComfyUI (sprites) | 8GB | 12GB |

**Note**: Stages run sequentially, so VRAM is not cumulative. Peak usage is ~16GB with HY-Motion-1.0-Lite.

### Disk Space Requirements

| Component | Size | Notes |
|-----------|------|-------|
| UniRig repo | ~500MB | Code + example data |
| HY-Motion repo | ~200MB | Code only (no models) |
| HY-Motion models | ~24-26GB | Downloaded on first run |
| Blender | ~400MB | Pre-installed |
| ComfyUI models | ~10-15GB | Manual install via ComfyUI Manager |

**Total**: ~35-42GB (with all models)

---

## Model Download Instructions

### HY-Motion Models (Automatic)

Models auto-download on first inference from HuggingFace:
- **HY-Motion-1.0-Lite**: `tencent/HY-Motion-1.0-Lite`
- **HY-Motion-1.0**: `tencent/HY-Motion-1.0`

Located at: `/workspace/hy-motion/ckpts/tencent/`

### UniRig Models (Automatic)

Models auto-download from HuggingFace on first use:
- **Skeleton Model**: `VAST-AI/UniRig` (skeleton prediction)
- **Skinning Model**: `VAST-AI/UniRig` (skinning weights)

Cached in Hugging Face cache: `~/.cache/huggingface/`

### ComfyUI Models (Manual)

Install via ComfyUI Manager UI at `http://pod-ip:8188`:

1. Open ComfyUI Manager
2. Search for required models:
   - **Checkpoint**: sd_xl_base_1.0_0.9vae.safetensors (~8.8GB)
   - **ControlNet**: SDXL-controlnet-openpose-v2 (~2.5GB)
   - **ControlNet**: control-lora-depth-rank256 (~395MB)
   - **IP-Adapter**: ip-adapter_sdxl.safetensors (~851MB)
3. Click Install for each model

---

## Troubleshooting

### UniRig Issues

**Problem**: "Skeleton generation failed"
- **Cause**: Input mesh is too complex or has invalid geometry
- **Solution**: 
  1. Check mesh has proper normals and no holes
  2. Try different `--seed` value in config
  3. Simplify mesh topology if needed
  4. Falls back to basic armature automatically

**Problem**: "Skinning generation failed"
- **Cause**: Skeleton structure incompatible with mesh
- **Solution**: 
  1. Manually refine skeleton in Blender before skinning (optional)
  2. Check bone orientations are reasonable
  3. Script falls back to skeleton-only output

### HY-Motion Issues

**Problem**: "CUDA out of memory"
- **Solution**: 
  1. Use HY-Motion-1.0-Lite instead of HY-Motion-1.0
  2. Ensure `--disable_duration_est` and `--disable_rewrite` are set
  3. Reduce number of simultaneous animations
  4. Use smaller prompt text (<60 words)

**Problem**: "No FBX file generated"
- **Cause**: HY-Motion inference crashed or timed out
- **Solution**:
  1. Check `/workspace/hy-motion/output/` for error logs
  2. Verify model files downloaded correctly
  3. Test with simpler prompt: "A person walks forward"

**Problem**: "ModuleNotFoundError: No module named 'hymotion'"
- **Cause**: HY-Motion dependencies not installed
- **Solution**: Rebuild Docker image (dependencies auto-install)

### Blender Issues

**Problem**: "blender: command not found"
- **Cause**: Blender not installed or symlink broken
- **Solution**: Rebuild Docker image with Blender installation

**Problem**: "This script must be run through Blender"
- **Cause**: Running .py file directly instead of via Blender
- **Solution**: Use proper Blender command:
  ```bash
  blender --background --python auto_rig.py -- <project_path> <config_path>
  ```

---

## Testing the Integration

### Test UniRig

```bash
# In RunPod pod terminal:
cd /workspace

# Test skeleton generation
bash unirig/launch/inference/generate_skeleton.sh \
    --input unirig/examples/giraffe.glb \
    --output test_skeleton.fbx

# Test skinning
bash unirig/launch/inference/generate_skin.sh \
    --input test_skeleton.fbx \
    --output test_skin.fbx

# Test merge
bash unirig/launch/inference/merge.sh \
    --source test_skin.fbx \
    --target unirig/examples/giraffe.glb \
    --output test_rigged.fbx
```

### Test HY-Motion

```bash
# In RunPod pod terminal:
cd /workspace/hy-motion

# Test animation generation
python3 local_infer.py \
    --model_path ckpts/tencent/HY-Motion-1.0-Lite \
    --input_text "A person walks forward with normal gait" \
    --output_dir output/test \
    --disable_duration_est \
    --disable_rewrite
```

### Test Complete Pipeline

```bash
# Create test project
mkdir -p /workspace/TestProject/0_input
cp /workspace/unirig/examples/giraffe.glb /workspace/TestProject/0_input/

# Create config
cat > /workspace/TestProject/config.json << 'EOF'
{
  "project_name": "TestProject",
  "mesh_type": "skeletal",
  "rigging": {
    "preset": "quadruped",
    "seed": 42
  },
  "animation": {
    "selected_animations": ["walk", "idle"]
  }
}
EOF

# Run pipeline
python /opt/pipeline/run_pipeline.py \
    /workspace/TestProject \
    /workspace/TestProject/config.json
```

---

## Advanced Configuration

### Custom UniRig Seeds

Try different skeleton variations by changing seed values:

```json
{
  "rigging": {
    "seed": 12345  // Try: 42, 100, 999, 12345, etc.
  }
}
```

Each seed produces a different (but valid) skeleton topology.

### Custom Animation Prompts

Edit `pipeline/hy_motion_prompts/prompt_library.json`:

```json
{
  "animations": {
    "custom_dance": {
      "motion": "A person performs an energetic dance with arm movements and steps",
      "style": "dynamic",
      "duration": 5.0,
      "constraints": "feet stay on ground"
    }
  }
}
```

Then reference in config:
```json
{
  "animation": {
    "selected_animations": ["custom_dance"]
  }
}
```

### Batch Processing

Generate multiple animation variations:

```python
# In config.json
{
  "animation": {
    "selected_animations": [
      "idle",
      "walk_slow",
      "walk_normal", 
      "walk_fast",
      "run",
      "jump",
      "crouch",
      "wave"
    ]
  }
}
```

All animations will be generated sequentially to `3_animation/` directory.

---

## Performance Optimization Tips

### 1. Use Lite Models
- HY-Motion-1.0-Lite is 2x faster with minimal quality loss
- Saves ~8GB VRAM

### 2. Disable Optional Features
```python
# In hy_motion.py, already disabled:
--disable_duration_est  # Saves ~2GB VRAM
--disable_rewrite       # Saves ~2GB VRAM
```

### 3. Limit Animation Length
- Shorter animations (2-4 seconds) are faster and more reliable
- Set in prompt library or config: `"duration": 3.0`

### 4. Skip Sprite Generation
```json
{
  "sprites": {
    "enabled": false  // Skip optional sprite stage
  }
}
```

### 5. Mesh Simplification
- Reduce polygon count before rigging (UniRig works better with optimized meshes)
- Use Blender's Decimate modifier or similar tools

---

## Integration Timeline

| Date | Change | Commit |
|------|--------|--------|
| 2025-01-19 | Added UniRig to original Dockerfile | Earlier commit |
| 2025-01-19 | Added HY-Motion to original Dockerfile | Earlier commit |
| 2025-01-19 | Removed from Dockerfile.runpod during optimization | 2cc0453 |
| 2025-01-19 | Re-integrated to Dockerfile.runpod with fixes | e9053df |
| 2025-01-19 | Updated auto_rig.py with UniRig workflow | e9053df |
| 2025-01-19 | Updated hy_motion.py with CLI interface | e9053df |

---

## References

- **UniRig Paper**: [One Model to Rig Them All (SIGGRAPH 2025)](https://arxiv.org/abs/2504.12451)
- **UniRig GitHub**: https://github.com/VAST-AI-Research/UniRig
- **HY-Motion Paper**: [HY-Motion 1.0: Scaling Flow Matching Models](https://arxiv.org/pdf/2512.23464)
- **HY-Motion GitHub**: https://github.com/Tencent-Hunyuan/HY-Motion-1.0
- **HY-Motion HuggingFace**: https://huggingface.co/tencent/HY-Motion-1.0
- **UniRig HuggingFace**: https://huggingface.co/VAST-AI/UniRig

---

## Credits

- **UniRig**: Tsinghua University & Tripo AI (VAST-AI-Research)
- **HY-Motion**: Tencent Hunyuan 3D Digital Human Team
- **Blender**: Blender Foundation
- **Integration**: RunPod 3D AI Pipeline Project

---

## License Notes

- **UniRig**: MIT License
- **HY-Motion**: Tencent License (see HY-Motion repo)
- **Blender**: GPL v3
- **Pipeline Code**: Your project license

Ensure compliance with all component licenses when using this integration.
