#!/bin/bash
# Install ComfyUI custom nodes for enhanced sprite generation
# Run this script from the ComfyUI custom_nodes directory

set -e  # Exit on error

COMFYUI_DIR="${COMFYUI_DIR:-/opt/ComfyUI}"
CUSTOM_NODES_DIR="$COMFYUI_DIR/custom_nodes"

echo "=========================================="
echo "Installing ComfyUI Custom Nodes"
echo "=========================================="
echo "ComfyUI Directory: $COMFYUI_DIR"
echo "Custom Nodes Directory: $CUSTOM_NODES_DIR"
echo ""

cd "$CUSTOM_NODES_DIR"

# 1. AnimateDiff-Evolved (temporal consistency)
echo "[1/6] Installing ComfyUI-AnimateDiff-Evolved..."
if [ -d "ComfyUI-AnimateDiff-Evolved" ]; then
    echo "  Already exists, pulling updates..."
    cd ComfyUI-AnimateDiff-Evolved
    git pull
    cd ..
else
    git clone https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved.git
fi
if [ -f "ComfyUI-AnimateDiff-Evolved/requirements.txt" ]; then
    echo "  Installing requirements..."
    cd "$COMFYUI_DIR"
    python -m pip install -r custom_nodes/ComfyUI-AnimateDiff-Evolved/requirements.txt
    cd "$CUSTOM_NODES_DIR"
fi
echo "  ✓ AnimateDiff-Evolved installed"
echo ""

# 2. IP-Adapter Plus (character consistency)
echo "[2/6] Installing ComfyUI_IPAdapter_plus..."
if [ -d "ComfyUI_IPAdapter_plus" ]; then
    echo "  Already exists, pulling updates..."
    cd ComfyUI_IPAdapter_plus
    git pull
    cd ..
else
    git clone https://github.com/cubiq/ComfyUI_IPAdapter_plus.git
fi
if [ -f "ComfyUI_IPAdapter_plus/requirements.txt" ]; then
    echo "  Installing requirements..."
    cd "$COMFYUI_DIR"
    python -m pip install -r custom_nodes/ComfyUI_IPAdapter_plus/requirements.txt
    cd "$CUSTOM_NODES_DIR"
fi
echo "  ✓ IP-Adapter Plus installed"
echo ""

# 3. ControlNet Aux (preprocessors for OpenPose, Depth, Normal, Canny)
echo "[3/6] Installing comfyui_controlnet_aux..."
if [ -d "comfyui_controlnet_aux" ]; then
    echo "  Already exists, pulling updates..."
    cd comfyui_controlnet_aux
    git pull
    cd ..
else
    git clone https://github.com/Fannovel16/comfyui_controlnet_aux.git
fi
if [ -f "comfyui_controlnet_aux/requirements.txt" ]; then
    echo "  Installing requirements..."
    cd "$COMFYUI_DIR"
    python -m pip install -r custom_nodes/comfyui_controlnet_aux/requirements.txt
    cd "$CUSTOM_NODES_DIR"
fi
echo "  ✓ ControlNet Aux installed"
echo ""

# 4. Advanced ControlNet (weight scheduling)
echo "[4/6] Installing ComfyUI-Advanced-ControlNet..."
if [ -d "ComfyUI-Advanced-ControlNet" ]; then
    echo "  Already exists, pulling updates..."
    cd ComfyUI-Advanced-ControlNet
    git pull
    cd ..
else
    git clone https://github.com/Kosinkadink/ComfyUI-Advanced-ControlNet.git
fi
if [ -f "ComfyUI-Advanced-ControlNet/requirements.txt" ]; then
    echo "  Installing requirements..."
    cd "$COMFYUI_DIR"
    python -m pip install -r custom_nodes/ComfyUI-Advanced-ControlNet/requirements.txt
    cd "$CUSTOM_NODES_DIR"
fi
echo "  ✓ Advanced ControlNet installed"
echo ""

# 5. Background Removal (alternative methods)
echo "[5/6] Installing background removal support..."
# Note: The mlinmg/ComfyUI-rembg repo is no longer available
# Using alternative: install rembg directly or use other custom nodes

# Option A: Install rembg package directly (works with standard ComfyUI nodes)
cd "$COMFYUI_DIR"
echo "  Installing rembg package..."
python -m pip install rembg[gpu] 2>/dev/null || python -m pip install rembg
cd "$CUSTOM_NODES_DIR"

# Option B: Use ComfyUI_essentials which includes background removal
echo "  Installing ComfyUI_essentials (includes background removal)..."
if [ -d "ComfyUI_essentials" ]; then
    echo "    Already exists, pulling updates..."
    cd ComfyUI_essentials
    git pull
    cd ..
else
    git clone https://github.com/cubiq/ComfyUI_essentials.git
fi
if [ -f "ComfyUI_essentials/requirements.txt" ]; then
    cd "$COMFYUI_DIR"
    python -m pip install -r custom_nodes/ComfyUI_essentials/requirements.txt
    cd "$CUSTOM_NODES_DIR"
fi
echo "  ✓ Background removal support installed"
echo ""

# 6. Frame Interpolation (optional - for smoother animations)
echo "[6/6] Installing ComfyUI-Frame-Interpolation..."
if [ -d "ComfyUI-Frame-Interpolation" ]; then
    echo "  Already exists, pulling updates..."
    cd ComfyUI-Frame-Interpolation
    git pull
    cd ..
else
    git clone https://github.com/Fannovel16/ComfyUI-Frame-Interpolation.git
fi
if [ -f "ComfyUI-Frame-Interpolation/requirements.txt" ]; then
    echo "  Installing requirements..."
    cd "$COMFYUI_DIR"
    python -m pip install -r custom_nodes/ComfyUI-Frame-Interpolation/requirements.txt
    cd "$CUSTOM_NODES_DIR"
fi
echo "  ✓ Frame Interpolation installed"
echo ""

echo "=========================================="
echo "Installation Complete!"
echo "=========================================="
echo ""
echo "Installed custom nodes:"
echo "  1. ComfyUI-AnimateDiff-Evolved (temporal consistency)"
echo "  2. ComfyUI_IPAdapter_plus (character consistency)"
echo "  3. comfyui_controlnet_aux (ControlNet preprocessors)"
echo "  4. ComfyUI-Advanced-ControlNet (weight scheduling)"
echo "  5. ComfyUI-rembg (background removal)"
echo "  6. ComfyUI-Frame-Interpolation (frame interpolation)"
echo ""
echo "Next steps:"
echo "  1. Restart ComfyUI server"
echo "  2. Download required models (AnimateDiff, IP-Adapter, ControlNet)"
echo "  3. Test sprite generation workflow"
echo ""
echo "Required models:"
echo "  - AnimateDiff: v3_sd15_mm.ckpt"
echo "  - IP-Adapter: ip-adapter-faceid-plusv2_sd15.bin"
echo "  - ControlNet: control_v11p_sd15_openpose, control_v11f1p_sd15_depth,"
echo "                control_v11p_sd15_normalbae, control_v11p_sd15_canny"
echo "  - Checkpoint: SDXL-Turbo, SDXL-Lightning, or SDXL 1.0"
echo ""
