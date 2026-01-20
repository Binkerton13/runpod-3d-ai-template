#!/bin/bash

# ================================================================================
# RunPod 3D AI Pipeline - Dependency Installation Script
# ================================================================================
# This script installs the missing dependencies for the 3D AI pipeline:
# 1. Pillow (for Blender sprite generation)
# 2. UniRig (automatic rigging)
# 3. HY-Motion (text-to-animation)
#
# IMPORTANT: This script runs AFTER pod deployment to keep the container small.
# Run this inside your RunPod container after it launches.
# ================================================================================

set -e  # Exit on error

echo "=============================================================================="
echo "RunPod 3D AI Pipeline - Dependency Installation"
echo "=============================================================================="
echo ""

# Color codes for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# ================================================================================
# 1. Install Pillow in Blender's Python Environment
# ================================================================================

echo -e "${YELLOW}[1/3] Installing Pillow for Blender...${NC}"
echo ""

# Find Blender's Python
BLENDER_PYTHON="/opt/blender/4.0/python/bin/python3.10"

if [ ! -f "$BLENDER_PYTHON" ]; then
    echo -e "${YELLOW}Blender Python not found at $BLENDER_PYTHON${NC}"
    echo "Searching for Blender installation..."
    
    # Try to find Blender
    BLENDER_PATH=$(which blender 2>/dev/null || echo "")
    if [ -z "$BLENDER_PATH" ]; then
        echo -e "${RED}ERROR: Blender not found. Please install Blender first.${NC}"
        exit 1
    fi
    
    # Get Blender's Python path
    BLENDER_DIR=$(dirname $(dirname $BLENDER_PATH))
    BLENDER_PYTHON=$(find $BLENDER_DIR -name "python3.*" -type f | grep "bin/python" | head -n1)
    
    if [ -z "$BLENDER_PYTHON" ]; then
        echo -e "${RED}ERROR: Could not locate Blender's Python interpreter${NC}"
        exit 1
    fi
fi

echo "Found Blender Python: $BLENDER_PYTHON"

# Install Pillow
echo "Installing Pillow..."
$BLENDER_PYTHON -m pip install --upgrade pip
$BLENDER_PYTHON -m pip install Pillow

# Verify installation
echo "Verifying Pillow installation..."
$BLENDER_PYTHON -c "from PIL import Image; print(f'Pillow {Image.__version__} installed successfully')"

echo -e "${GREEN}✓ Pillow installed successfully${NC}"
echo ""

# ================================================================================
# 2. Install UniRig
# ================================================================================

echo -e "${YELLOW}[2/3] Installing UniRig...${NC}"
echo ""

UNIRIG_PATH="/workspace/unirig"

if [ -d "$UNIRIG_PATH" ]; then
    echo "UniRig directory already exists. Updating..."
    cd "$UNIRIG_PATH"
    git pull
else
    echo "Cloning UniRig repository..."
    git clone https://github.com/VAST-AI-Research/UniRig.git "$UNIRIG_PATH"
    cd "$UNIRIG_PATH"
fi

# Remove problematic dependencies
echo "Preparing requirements.txt..."
cp requirements.txt requirements.txt.backup 2>/dev/null || true

# Remove bpy (conflicts with standalone Blender)
# Remove flash_attn (complex compilation, optional for inference)
sed -i '/bpy/d' requirements.txt
sed -i '/flash_attn/d' requirements.txt

# Install dependencies
echo "Installing UniRig dependencies..."
if [ -n "$VIRTUAL_ENV" ]; then
    # Use virtual environment if available
    pip install -r requirements.txt
else
    # Use system Python
    python3 -m pip install -r requirements.txt
fi

# Download UniRig models if not present
UNIRIG_MODELS_DIR="$UNIRIG_PATH/models"
if [ ! -d "$UNIRIG_MODELS_DIR" ] || [ -z "$(ls -A $UNIRIG_MODELS_DIR 2>/dev/null)" ]; then
    echo ""
    echo -e "${YELLOW}UniRig models not found. You need to download them manually:${NC}"
    echo ""
    echo "1. Visit: https://github.com/VAST-AI-Research/UniRig#download-models"
    echo "2. Download the model checkpoints"
    echo "3. Place them in: $UNIRIG_MODELS_DIR"
    echo ""
    echo "Required models:"
    echo "  - Skeleton generation model"
    echo "  - Skinning weight prediction model"
    echo ""
    echo -e "${YELLOW}⚠ UniRig will NOT work until models are downloaded${NC}"
else
    echo -e "${GREEN}✓ UniRig models found${NC}"
fi

echo -e "${GREEN}✓ UniRig installed successfully${NC}"
echo ""

# ================================================================================
# 3. Install HY-Motion
# ================================================================================

echo -e "${YELLOW}[3/3] Installing HY-Motion...${NC}"
echo ""

HYMOTION_PATH="/workspace/hy-motion"

if [ -d "$HYMOTION_PATH" ]; then
    echo "HY-Motion directory already exists. Updating..."
    cd "$HYMOTION_PATH"
    git pull
else
    echo "Cloning HY-Motion repository..."
    git clone https://github.com/Tencent-Hunyuan/HY-Motion-1.0.git "$HYMOTION_PATH"
    cd "$HYMOTION_PATH"
fi

# Install dependencies
if [ -f "requirements.txt" ]; then
    echo "Installing HY-Motion dependencies..."
    if [ -n "$VIRTUAL_ENV" ]; then
        pip install -r requirements.txt
    else
        python3 -m pip install -r requirements.txt
    fi
else
    echo -e "${YELLOW}No requirements.txt found in HY-Motion repo${NC}"
fi

# Download HY-Motion models if not present
HYMOTION_MODELS_DIR="$HYMOTION_PATH/models"
if [ ! -d "$HYMOTION_MODELS_DIR" ] || [ -z "$(ls -A $HYMOTION_MODELS_DIR 2>/dev/null)" ]; then
    echo ""
    echo -e "${YELLOW}HY-Motion models not found. You need to download them manually:${NC}"
    echo ""
    echo "1. Visit: https://github.com/Tencent-Hunyuan/HY-Motion-1.0#model-download"
    echo "2. Download the model checkpoints"
    echo "3. Place them in: $HYMOTION_MODELS_DIR"
    echo ""
    echo "Required models:"
    echo "  - Text-to-motion model (hunyuan_motion_1.0.safetensors)"
    echo "  - Motion encoder"
    echo "  - Text encoder"
    echo ""
    echo -e "${YELLOW}⚠ HY-Motion will NOT work until models are downloaded${NC}"
else
    echo -e "${GREEN}✓ HY-Motion models found${NC}"
fi

echo -e "${GREEN}✓ HY-Motion installed successfully${NC}"
echo ""

# ================================================================================
# Installation Summary
# ================================================================================

echo "=============================================================================="
echo "Installation Summary"
echo "=============================================================================="
echo ""
echo -e "${GREEN}✓ Pillow:${NC} Installed in Blender Python environment"
echo -e "${GREEN}✓ UniRig:${NC} Repository cloned to $UNIRIG_PATH"
echo -e "${GREEN}✓ HY-Motion:${NC} Repository cloned to $HYMOTION_PATH"
echo ""

# Check if models are missing
MODELS_MISSING=0

if [ ! -d "$UNIRIG_MODELS_DIR" ] || [ -z "$(ls -A $UNIRIG_MODELS_DIR 2>/dev/null)" ]; then
    echo -e "${YELLOW}⚠ UniRig models NOT downloaded${NC}"
    MODELS_MISSING=1
fi

if [ ! -d "$HYMOTION_MODELS_DIR" ] || [ -z "$(ls -A $HYMOTION_MODELS_DIR 2>/dev/null)" ]; then
    echo -e "${YELLOW}⚠ HY-Motion models NOT downloaded${NC}"
    MODELS_MISSING=1
fi

if [ $MODELS_MISSING -eq 1 ]; then
    echo ""
    echo -e "${YELLOW}=============================================================================="
    echo "IMPORTANT: Model Downloads Required"
    echo "==============================================================================${NC}"
    echo ""
    echo "The pipeline will use fallback modes until you download the required models:"
    echo ""
    echo "1. UniRig Models (~2-5 GB):"
    echo "   https://github.com/VAST-AI-Research/UniRig#download-models"
    echo ""
    echo "2. HY-Motion Models (~10-15 GB):"
    echo "   https://github.com/Tencent-Hunyuan/HY-Motion-1.0#model-download"
    echo ""
    echo "Without models:"
    echo "  - UniRig: Uses basic fallback armature (20 bones, automatic weights)"
    echo "  - HY-Motion: Creates placeholder animations (no actual motion)"
    echo ""
fi

echo ""
echo -e "${GREEN}=============================================================================="
echo "Installation Complete!"
echo "==============================================================================${NC}"
echo ""
echo "You can now run the pipeline. It will automatically detect the installed tools."
echo ""
echo "Test the installation:"
echo "  cd /workspace/pipeline"
echo "  python api_server.py"
echo ""
echo "Then access the web UI at: http://localhost:7860"
echo ""
