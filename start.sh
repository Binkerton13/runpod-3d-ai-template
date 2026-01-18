#!/usr/bin/env bash
set -e

# Activate Python virtual environment
source "${VIRTUAL_ENV}/bin/activate"

# Create symlink to ComfyUI if it doesn't exist
if [ ! -e "/workspace/ComfyUI" ]; then
  echo "Creating symlink to ComfyUI..."
  ln -s /opt/comfyui /workspace/ComfyUI
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

# Start supervisord
exec supervisord -c /etc/supervisord.conf
