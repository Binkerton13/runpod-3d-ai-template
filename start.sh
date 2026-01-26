
#!/usr/bin/env bash
set -e
set -x

echo "==============================================="
echo " SpriteForge – Startup"
echo "==============================================="

# Activate venv
echo "Activating virtual environment..."
source "${VIRTUAL_ENV}/bin/activate"

# Workspace paths
PIPELINE_SRC="/opt/pipeline"
PIPELINE_DST="/workspace/pipeline"
CUSTOM_NODES="/workspace/custom_nodes"
COMFY_MODELS="/workspace/models"
HY_MOTION="/workspace/hy-motion"

PIPELINE_VERSION_SRC=$(cat "$PIPELINE_SRC/VERSION")
PIPELINE_VERSION_DST=$(cat "$PIPELINE_DST/.version" 2>/dev/null || echo "0.0.0")

if [ "$PIPELINE_VERSION_SRC" != "$PIPELINE_VERSION_DST" ]; then
    echo "Pipeline update detected ($PIPELINE_VERSION_DST → $PIPELINE_VERSION_SRC)"
    echo "Applying non-destructive migration..."

    for item in $(ls "$PIPELINE_SRC"); do
        if [ ! -e "$PIPELINE_DST/$item" ]; then
            echo "Adding new file: $item"
            cp -r "$PIPELINE_SRC/$item" "$PIPELINE_DST/"
        else
            echo "Keeping existing file: $item"
        fi
    done

    echo "$PIPELINE_VERSION_SRC" > "$PIPELINE_DST/.version"
else
    echo "Pipeline is up to date (version $PIPELINE_VERSION_DST)"
fi

# Ensure workspace directories exist
echo "Ensuring workspace directories exist..."
mkdir -p "$PIPELINE_DST" \
         "$CUSTOM_NODES" \
         "$COMFY_MODELS" \
         /workspace/animations \
         /workspace/sprites \
         /workspace/pipeline/logs \

# Copy pipeline to workspace on first run
echo "Checking workspace pipeline..."

if [ ! -f "$PIPELINE_DST/.initialized" ]; then
    echo "Initializing workspace pipeline (first run)..."

    # Copy only if the file does not already exist
    for item in $(ls "$PIPELINE_SRC"); do
        if [ ! -e "$PIPELINE_DST/$item" ]; then
            cp -r "$PIPELINE_SRC/$item" "$PIPELINE_DST/"
        else
            echo "Skipping existing item: $item"
        fi
    done

    # Mark initialization complete
    touch "$PIPELINE_DST/.initialized"
else
    echo "Workspace pipeline already initialized."
fi

# Run dependency installer (idempotent)
echo "HY-Motion already installed in image — skipping runtime installation."

# Symlink ComfyUI models + custom nodes
echo "Linking ComfyUI models and custom nodes..."
rm -rf /opt/comfyui/models
rm -rf /opt/comfyui/custom_nodes

ln -s "$COMFY_MODELS" /opt/comfyui/models
ln -s "$CUSTOM_NODES" /opt/comfyui/custom_nodes

# GPU info
echo "Checking CUDA availability..."
python - <<EOF
import torch
print("CUDA available:", torch.cuda.is_available())
print("Device:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "None")
EOF

echo ""
echo "==============================================="
echo " Starting services:"
echo " - ComfyUI on port ${PORT:-8188}"
echo " - File Browser on port 8080"
echo " - SpriteForge GUI on port 5000"
echo "==============================================="
echo ""

# Ensure pipeline destination is a directory
if [ -f "$PIPELINE_DST" ]; then
    echo "ERROR: $PIPELINE_DST exists as a file. Removing it."
    rm -f "$PIPELINE_DST"
fi

mkdir -p "$PIPELINE_DST"

# Extra safety: ensure all required runtime directories exist before launching supervisord
mkdir -p \
    /workspace/models/checkpoints \
    /workspace/models/loras \
    /workspace/models/vae \
    /workspace/models/controlnet \
    /workspace/models/upscale_models \
    /workspace/models/clip \
    /workspace/models/clip_vision \
    /workspace/models/ipadapter \
    /workspace/models/embeddings \
    /workspace/animations \
    /workspace/sprites \
    /workspace/custom_nodes \
    /workspace/pipeline/logs

# Debug: show directory and permissions before starting supervisord
echo "Listing /workspace/pipeline/logs before starting supervisord:"
ls -l /workspace/pipeline/logs || echo "/workspace/pipeline/logs does not exist!"

# Launch supervisor (runs all services)
exec supervisord -c /etc/supervisord.conf
# Just a push forcing comment #3