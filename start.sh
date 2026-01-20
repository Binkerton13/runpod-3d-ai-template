#!/usr/bin/env bash
set -e

# Activate Python virtual environment
source "${VIRTUAL_ENV}/bin/activate"

# Remove old ComfyUI symlink if it exists (from previous version)
if [ -L "/workspace/ComfyUI" ]; then
  echo "Removing old ComfyUI symlink..."
  rm /workspace/ComfyUI
fi

# Setup persistent ComfyUI directories
if [ ! -d "/workspace/ComfyUI/models" ]; then
  echo "Creating persistent ComfyUI models directory structure..."
  mkdir -p /workspace/ComfyUI/models/{checkpoints,loras,vae,controlnet,ipadapter,embeddings,upscale_models,clip_vision}
  chown -R app:app /workspace/ComfyUI || true
fi

# Create custom_nodes directory if it doesn't exist
if [ ! -d "/workspace/custom_nodes" ]; then
  echo "Creating persistent custom_nodes directory..."
  mkdir -p /workspace/custom_nodes
  chown -R app:app /workspace/custom_nodes || true
fi

# Install default custom nodes if directory is empty
if [ -z "$(ls -A /workspace/custom_nodes)" ]; then
  echo "Installing default ComfyUI custom nodes..."
  cd /workspace/custom_nodes
  git clone https://github.com/ltdrdata/ComfyUI-Manager.git || echo "Failed to clone ComfyUI-Manager"
  git clone https://github.com/cubiq/ComfyUI_essentials.git || echo "Failed to clone ComfyUI_essentials"
  git clone https://github.com/WASasquatch/was-node-suite-comfyui.git || echo "Failed to clone was-node-suite-comfyui"
  chown -R app:app /workspace/custom_nodes || true
  echo "Default custom nodes installed"
fi

# Symlink ComfyUI models directory to persistent storage
if [ ! -L "/opt/comfyui/models" ] && [ -d "/opt/comfyui/models" ]; then
  echo "Linking ComfyUI models to persistent storage..."
  # Backup original models directory if it has content
  if [ "$(ls -A /opt/comfyui/models)" ]; then
    mv /opt/comfyui/models /opt/comfyui/models.original
  else
    rm -rf /opt/comfyui/models
  fi
  ln -s /workspace/ComfyUI/models /opt/comfyui/models
fi

# Ensure custom_nodes symlink exists
if [ ! -L "/opt/comfyui/custom_nodes" ]; then
  echo "Linking ComfyUI custom_nodes to persistent storage..."
  if [ -d "/opt/comfyui/custom_nodes" ]; then
    rm -rf /opt/comfyui/custom_nodes
  fi
  ln -s /workspace/custom_nodes /opt/comfyui/custom_nodes
fi

# Copy pipeline files to workspace if not already there
if [ ! -d "/workspace/pipeline" ]; then
  echo "Copying pipeline to /workspace..."
  cp -r /opt/pipeline /workspace/
  cp -r /opt/config /workspace/
  chown -R app:app /workspace/pipeline /workspace/config || true
fi

# Download models if requested
if [ "${MODEL_DOWNLOAD_ON_START:-0}" = "1" ]; then
  echo "MODEL_DOWNLOAD_ON_START=1: downloading configured model URLs"
  if [ -n "${MODEL_URLS}" ]; then
    echo "${MODEL_URLS}" | tr "," '\n' | while read url; do
      url="$(echo "$url" | xargs)"
      if [ -n "$url" ]; then
        fname="$(basename "$url")"
        mkdir -p /workspace/models/3d
        curl -L --retry 3 -o "/workspace/models/3d/$fname" "$url" || echo "download failed: $url"
      fi
    done
  fi
fi

# Run git lfs pull for repos
for repo in comfyui unirig triposr hy-motion; do
  if [ -d "/workspace/$repo/.git" ]; then
    echo "Running git lfs pull in /workspace/$repo"
    git -C "/workspace/$repo" lfs pull || true
  fi
done

# Print CUDA info
python - <<EOF
import torch
print("CUDA available:", torch.cuda.is_available())
print("Device:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "None")
EOF

# Print service info
echo "========================================"
echo "Starting 3D AI Workstation Services:"
echo "  ComfyUI: Port ${PORT:-8188}"
echo "  File Browser: Port ${FILE_BROWSER_PORT:-8080}"
echo "  Pipeline GUI: Port ${PIPELINE_GUI_PORT:-7860}"
echo "========================================"

# Start supervisord from system
exec /usr/bin/supervisord -c /etc/supervisord.conf
