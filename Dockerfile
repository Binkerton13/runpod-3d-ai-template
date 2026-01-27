# ============================================
# BASE — CUDA + system deps (rarely changes)
# ============================================
FROM nvidia/cuda:12.1.1-cudnn8-devel-ubuntu22.04 AS base

ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Etc/UTC \
    WORKSPACE=/workspace

RUN apt-get update && apt-get install -y --no-install-recommends \
    git git-lfs \
    wget curl \
    ca-certificates \
    ffmpeg \
    python3 python3-venv python3-dev python3-pip \
    build-essential \
    unzip \
    libgl1 libglib2.0-0 \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

RUN git lfs install --system || true


# ============================================
# PYTHON — venv + PyTorch (rarely changes)
# ============================================
FROM base AS python

RUN python3 -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip wheel setuptools

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

ARG USE_CUDA=1
RUN if [ "${USE_CUDA}" = "1" ]; then \
        pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121; \
    else \
        pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu; \
    fi


# ============================================
# PYTHON DEPS — requirements.txt
# ============================================
FROM python AS deps

COPY requirements.txt /opt/requirements.txt
RUN pip install --no-cache-dir -r /opt/requirements.txt


# ============================================
# FRONTEND — Node build stage (NEW + REQUIRED)
# ============================================
FROM node:20 AS frontend

WORKDIR /app

# Copy only package files first
COPY package.json package-lock.json ./

# Install dependencies cleanly
RUN npm install

# Now copy the rest of the source
COPY . .

# Build
RUN npm run build


# ============================================
# BUILDER — ComfyUI + HY-Motion
# ============================================
FROM deps AS builder

# --- ComfyUI ---
RUN git clone https://github.com/comfyanonymous/ComfyUI.git /opt/comfyui

RUN mkdir -p /opt/comfyui/custom_nodes && \
    cd /opt/comfyui/custom_nodes && \
    git clone https://github.com/cubiq/ComfyUI_essentials.git && \
    git clone https://github.com/WASasquatch/was-node-suite-comfyui.git

RUN pip install --no-cache-dir -r /opt/comfyui/requirements.txt

# --- HY-Motion ---
RUN git clone https://github.com/Tencent-Hunyuan/HY-Motion-1.0.git /opt/hy-motion
RUN if [ -f "/opt/hy-motion/requirements.txt" ]; then \
        pip install --no-cache-dir -r /opt/hy-motion/requirements.txt; \
    fi


# ============================================
# RUNTIME — minimal + fast
# ============================================
FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04 AS runtime

ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Etc/UTC \
    WORKSPACE=/workspace \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:${PATH}"

RUN apt-get update && apt-get install -y --no-install-recommends \
    git git-lfs \
    ffmpeg \
    libgl1 libglib2.0-0 \
    supervisor \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN git lfs install --system || true

# Copy Python environment
COPY --from=deps /opt/venv /opt/venv

# Copy ComfyUI + HY-Motion
COPY --from=builder /opt/comfyui /opt/comfyui
COPY --from=builder /opt/hy-motion ${WORKSPACE}/hy-motion

# Copy built frontend (NEW)
COPY --from=frontend /opt/pipeline/gui/frontend/dist /opt/pipeline/gui/static

# Persistent workspace folders
RUN mkdir -p \
    ${WORKSPACE}/models \
    ${WORKSPACE}/custom_nodes \
    ${WORKSPACE}/animations \
    ${WORKSPACE}/sprites \
    ${WORKSPACE}/pipeline/logs

# Install ComfyUI Manager persistently
RUN git clone https://github.com/ltdrdata/ComfyUI-Manager.git /workspace/custom_nodes/ComfyUI-Manager

# Copy SpriteForge runtime files
COPY file_browser.py /usr/local/bin/file_browser.py
COPY supervisord.conf /etc/supervisord.conf
COPY pipeline /opt/pipeline
COPY start.sh /usr/local/bin/start.sh

RUN chmod +x /usr/local/bin/start.sh /usr/local/bin/file_browser.py

EXPOSE 8188 8080 5000 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -fsS http://127.0.0.1:${PORT:-8188}/ || exit 1

CMD ["/bin/bash", "/usr/local/bin/start.sh"]
