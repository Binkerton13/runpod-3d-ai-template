
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

# Ensure workspace directories exist
echo "Ensuring workspace directories exist..."
mkdir -p "$PIPELINE_DST" \
         "$CUSTOM_NODES" \
         "$COMFY_MODELS" \
         /workspace/animations \
         /workspace/sprites \
         /workspace/pipeline/logs \

# Copy pipeline to workspace on first run
if [ ! -f "$PIPELINE_DST/.initialized" ]; then
    echo "Copying SpriteForge pipeline into workspace..."
    cp -r "$PIPELINE_SRC/"* "$PIPELINE_DST/"
    touch "$PIPELINE_DST/.initialized"
fi

# Run dependency installer (idempotent)
echo "Running dependency installer..."
bash "$PIPELINE_DST/install_dependencies.sh"

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



# Extra safety: ensure log directory exists before launching supervisord
mkdir -p /workspace/pipeline/logs

# Debug: show directory and permissions before starting supervisord
echo "Listing /workspace/pipeline/logs before starting supervisord:"
ls -l /workspace/pipeline/logs || echo "/workspace/pipeline/logs does not exist!"

# Launch supervisor (runs all services)
exec supervisord -c /etc/supervisord.conf
