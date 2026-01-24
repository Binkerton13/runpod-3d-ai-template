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
BLENDER_PYTHON=""

# Try common Blender installation base directories
POSSIBLE_BASES=(
    "/opt/blender-4.0.2-linux-x64"
    "/opt/blender-4.0-linux-x64"
    "/opt/blender"
    "/opt/blender-4.0"
    "/usr/local/blender"
)

echo "Searching for Blender Python interpreter..."

for base in "${POSSIBLE_BASES[@]}"; do
    if [ -d "$base" ]; then
        echo "Checking: $base"
        # Look for python3.* in the bin directory
        FOUND=$(find "$base" -path "*/python/bin/python3.*" -type f 2>/dev/null | grep -v "python3.*-config" | head -n1)
        if [ -n "$FOUND" ]; then
            BLENDER_PYTHON="$FOUND"
            echo "Found Python at: $BLENDER_PYTHON"
            break
        fi
    fi
done

# If not found in common paths, search using which blender
if [ -z "$BLENDER_PYTHON" ]; then
    echo "Not found in common paths, searching via blender binary..."
    
    # Try to find Blender
    BLENDER_PATH=$(which blender 2>/dev/null || echo "")
    if [ -z "$BLENDER_PATH" ]; then
        echo -e "${RED}ERROR: Blender not found. Please install Blender first.${NC}"
        exit 1
    fi
    
    echo "Blender binary at: $BLENDER_PATH"
    
    # Get Blender's Python path - follow symlink to real installation
    BLENDER_REAL=$(readlink -f "$BLENDER_PATH")
    BLENDER_DIR=$(dirname $(dirname "$BLENDER_REAL"))
    
    echo "Blender real path: $BLENDER_REAL"
    echo "Searching in: $BLENDER_DIR"
    
    BLENDER_PYTHON=$(find "$BLENDER_DIR" -path "*/python/bin/python3.*" -type f 2>/dev/null | grep -v "python3.*-config" | head -n1)
    
    if [ -z "$BLENDER_PYTHON" ]; then
        echo -e "${RED}ERROR: Could not locate Blender's Python interpreter${NC}"
        echo ""
        echo "Debug information:"
        echo "  Blender binary: $BLENDER_PATH"
        echo "  Real path: $BLENDER_REAL"
        echo "  Search directory: $BLENDER_DIR"
        echo ""
        echo "Directory contents:"
        ls -la "$BLENDER_DIR" 2>/dev/null || echo "  Cannot list directory"
        echo ""
        echo "Please report this issue with the above information."
        exit 1
    fi
fi

echo "Found Blender Python: $BLENDER_PYTHON"

# Install Pillow, PyYAML, and tqdm for Blender's Python
echo "Installing Pillow, PyYAML, and tqdm..."
$BLENDER_PYTHON -m pip install --upgrade pip
$BLENDER_PYTHON -m pip install Pillow pyyaml tqdm python-box scipy trimesh fast_simplification

# Verify installations
echo "Verifying Pillow installation..."
$BLENDER_PYTHON -c "from PIL import Image; print(f'Pillow {Image.__version__} installed successfully')"
echo "Verifying PyYAML installation..."
$BLENDER_PYTHON -c "import yaml; print(f'PyYAML {yaml.__version__} installed successfully')"
echo "Verifying tqdm installation..."
$BLENDER_PYTHON -c "import tqdm; print(f'tqdm {tqdm.__version__} installed successfully')"
echo "Verifying python-box installation..."
$BLENDER_PYTHON -c "import python_box; print(f'python-box {python_box.__version__} installed successfully')"
echo "Verifying scipy installation..."
$BLENDER_PYTHON -c "import scipy; print(f'scipy {scipy.__version__} installed successfully')"
echo "Verifying trimesh installation..."
$BLENDER_PYTHON -c "import trimesh; print(f'trimesh {trimesh.__version__} installed successfully')"
echo "Verifying fast_simplification installation..."
$BLENDER_PYTHON -c "import fast_simplification; print(f'fast_simplification {fast_simplification.__version__} installed successfully')"

echo -e "${GREEN}✓ Pillow, PyYAML, python-box, tqdm, scipy, trimesh, and fast_simplification installed successfully${NC}"
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
    # Use --user with --ignore-installed to bypass precedence check
    pip install --user --ignore-installed --upgrade -r requirements.txt
else
    # Use system Python
    python3 -m pip install --user --upgrade -r requirements.txt
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

# Install correct Transformers version into user site-packages
pip install --user "transformers==4.41.2"

# Ensure our custom sitecustomize.py is always loaded
export PYTHONPATH="/workspace/pipeline/env_patches:$PYTHONPATH"

# Persist for future shells
echo 'export PYTHONPATH="/workspace/pipeline/env_patches:$PYTHONPATH"' >> ~/.bashrc

# ================================================================================
# 3. Install HY-Motion
# ================================================================================

echo -e "${YELLOW}[3/3] Installing HY-Motion...${NC}"
echo ""

HYMOTION_PATH="/workspace/HY-Motion"

if [ -d "$HYMOTION_PATH" ]; then
    echo "HY-Motion directory already exists. Updating..."
    cd "$HYMOTION_PATH"
    git pull
else
    echo "Cloning HY-Motion repository..."
    git clone https://github.com/Tencent-Hunyuan/HY-Motion-1.0.git "$HYMOTION_PATH"
    cd "$HYMOTION_PATH"
fi

# Create lowercase symlink for compatibility
if [ ! -L "/workspace/hy-motion" ]; then
    echo "Creating lowercase symlink..."
    ln -s "$HYMOTION_PATH" /workspace/hy-motion
fi

# Install dependencies
if [ -f "requirements.txt" ]; then
    echo "Installing HY-Motion dependencies..."
    if [ -n "$VIRTUAL_ENV" ]; then
        # Use --user with --ignore-installed to bypass precedence check
        pip install --user --ignore-installed --upgrade -r requirements.txt
    else
        python3 -m pip install --user --upgrade -r requirements.txt
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
