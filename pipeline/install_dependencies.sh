#!/bin/bash
set -e

###############################################################################
# RunPod 3D Pipeline – Dependency Installer (Idempotent, Logged, Versioned)
###############################################################################

START_TIME=$(date +%s)
LOG_FILE="/workspace/pipeline/install.log"

echo "==============================================================================" | tee -a "$LOG_FILE"
echo "RunPod 3D Pipeline – Dependency Installation" | tee -a "$LOG_FILE"
echo "Timestamp: $(date)" | tee -a "$LOG_FILE"
echo "==============================================================================" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

###############################################################################
# Helper: Check marker file to skip reinstall
###############################################################################

MARKER="/workspace/pipeline/.deps_installed"

if [ -f "$MARKER" ]; then
    echo -e "${GREEN}✓ Dependencies already installed. Skipping.${NC}" | tee -a "$LOG_FILE"
    echo "To force reinstall, delete: $MARKER" | tee -a "$LOG_FILE"
    exit 0
fi

###############################################################################
# Helper: Log + Timer wrapper
###############################################################################

run_step() {
    local label="$1"
    shift
    echo -e "${YELLOW}→ $label...${NC}" | tee -a "$LOG_FILE"
    local t0=$(date +%s)
    "$@" 2>&1 | tee -a "$LOG_FILE"
    local t1=$(date +%s)
    echo -e "${GREEN}✓ Completed: $label in $((t1 - t0))s${NC}" | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"
}

###############################################################################
# 1. Install Blender Python dependencies
###############################################################################

install_blender_deps() {
    echo "Locating Blender Python..." | tee -a "$LOG_FILE"

    BLENDER_PYTHON=$(find /opt -path "*/python/bin/python3.*" -type f 2>/dev/null | head -n1)

    if [ -z "$BLENDER_PYTHON" ]; then
        echo -e "${RED}ERROR: Blender Python not found.${NC}" | tee -a "$LOG_FILE"
        return 1
    fi

    echo "Using Blender Python: $BLENDER_PYTHON" | tee -a "$LOG_FILE"

    $BLENDER_PYTHON -m pip install --upgrade pip
    $BLENDER_PYTHON -m pip install Pillow pyyaml tqdm python-box scipy trimesh fast_simplification
}

run_step "Installing Blender Python dependencies" install_blender_deps

###############################################################################
# 2. Install UniRig (idempotent)
###############################################################################

install_unirig() {
    local repo="/workspace/unirig"

    if [ -d "$repo" ]; then
        echo "Updating UniRig..." | tee -a "$LOG_FILE"
        git -C "$repo" pull
    else
        echo "Cloning UniRig..." | tee -a "$LOG_FILE"
        git clone https://github.com/VAST-AI-Research/UniRig.git "$repo"
    fi

    cp "$repo/requirements.txt" "$repo/requirements.txt.backup" || true
    sed -i '/bpy/d' "$repo/requirements.txt"
    sed -i '/flash_attn/d' "$repo/requirements.txt"

    pip install --user --ignore-installed --upgrade -r "$repo/requirements.txt"
}

run_step "Installing UniRig" install_unirig

###############################################################################
# 3. Install HY-Motion (idempotent)
###############################################################################

install_hymotion() {
    local repo="/workspace/HY-Motion"

    if [ -d "$repo" ]; then
        echo "Updating HY-Motion..." | tee -a "$LOG_FILE"
        git -C "$repo" pull
    else
        echo "Cloning HY-Motion..." | tee -a "$LOG_FILE"
        git clone https://github.com/Tencent-Hunyuan/HY-Motion-1.0.git "$repo"
    fi

    ln -sf "$repo" /workspace/hy-motion

    if [ -f "$repo/requirements.txt" ]; then
        pip install --user --ignore-installed --upgrade -r "$repo/requirements.txt"
    fi
}

run_step "Installing HY-Motion" install_hymotion

###############################################################################
# 4. Install Custom ComfyUI Nodes (idempotent)
###############################################################################

run_step "Installing ComfyUI custom nodes" bash /workspace/pipeline/scripts/install_custom_nodes.sh


###############################################################################
# 5. Transformers Version Enforcement (critical for UniRig)
###############################################################################

install_transformers_fix() {
    REQUIRED_VERSION="4.41.2"

    CURRENT_VERSION=$(python3 - <<EOF
import transformers
print(transformers.__version__)
EOF
)

    echo "Transformers installed: $CURRENT_VERSION" | tee -a "$LOG_FILE"

    if [ "$CURRENT_VERSION" = "$REQUIRED_VERSION" ]; then
        echo "Correct Transformers version already installed." | tee -a "$LOG_FILE"
        return 0
    fi

    echo "Installing Transformers $REQUIRED_VERSION..." | tee -a "$LOG_FILE"
    pip install --user --upgrade "transformers==$REQUIRED_VERSION"
}

run_step "Enforcing Transformers version" install_transformers_fix

###############################################################################
# 6. Activate sitecustomize override
###############################################################################

activate_sitecustomize() {
    PATCH_DIR="/workspace/pipeline/env_patches"

    mkdir -p "$PATCH_DIR"

    cat > "$PATCH_DIR/sitecustomize.py" << 'EOF'
import sys, os
USER_SITE = os.path.expanduser("~/.local/lib/python3.11/site-packages")
if USER_SITE not in sys.path:
    sys.path.insert(0, USER_SITE)
EOF

    echo "export PYTHONPATH=\"$PATCH_DIR:\$PYTHONPATH\"" >> ~/.bashrc
    export PYTHONPATH="$PATCH_DIR:$PYTHONPATH"
}

run_step "Activating sitecustomize override" activate_sitecustomize

###############################################################################
# Mark installation complete
###############################################################################

touch "$MARKER"

END_TIME=$(date +%s)
echo "==============================================================================" | tee -a "$LOG_FILE"
echo "Installation complete in $((END_TIME - START_TIME)) seconds." | tee -a "$LOG_FILE"
echo "==============================================================================" | tee -a "$LOG_FILE"