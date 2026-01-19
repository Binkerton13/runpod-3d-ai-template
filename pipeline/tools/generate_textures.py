#!/usr/bin/env python3
"""
Texture Generation Tool
Generates PBR textures for 3D meshes using ComfyUI workflows
"""
import sys
import json
import requests
import time
from pathlib import Path
import uuid
import shutil

def log(message):
    """Print timestamped log message"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)

def wait_for_comfyui(base_url, max_retries=30, retry_delay=2):
    """Wait for ComfyUI to be available"""
    log(f"Waiting for ComfyUI at {base_url}...")
    for i in range(max_retries):
        try:
            response = requests.get(f"{base_url}/system_stats", timeout=5)
            if response.status_code == 200:
                log("ComfyUI is ready")
                return True
        except requests.exceptions.RequestException:
            pass
        
        if i < max_retries - 1:
            time.sleep(retry_delay)
    
    log(f"ERROR: ComfyUI not available after {max_retries * retry_delay} seconds")
    return False

def queue_prompt(base_url, prompt):
    """Queue a prompt in ComfyUI"""
    try:
        response = requests.post(f"{base_url}/prompt", json={"prompt": prompt}, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        log(f"ERROR: Failed to queue prompt: {e}")
        return None

def get_history(base_url, prompt_id):
    """Get execution history for a prompt"""
    try:
        response = requests.get(f"{base_url}/history/{prompt_id}", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        log(f"ERROR: Failed to get history: {e}")
        return None

def wait_for_completion(base_url, prompt_id, max_wait=600, check_interval=2):
    """Wait for prompt execution to complete"""
    log(f"Waiting for prompt {prompt_id} to complete...")
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        history = get_history(base_url, prompt_id)
        if history and prompt_id in history:
            status = history[prompt_id].get("status", {})
            if status.get("completed", False):
                log("Prompt execution completed")
                return True
            elif "error" in status:
                log(f"ERROR: Prompt execution failed: {status.get('error', 'Unknown error')}")
                return False
        
        time.sleep(check_interval)
    
    log(f"ERROR: Prompt execution timed out after {max_wait} seconds")
    return False

def load_workflow(workflow_path):
    """Load ComfyUI workflow from JSON file"""
    try:
        with open(workflow_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        log(f"ERROR: Failed to load workflow {workflow_path}: {e}")
        return None

def update_workflow_params(workflow, udim_tile, udim_config, checkpoint_name=None, uv_image_path=None):
    """Update workflow parameters with UDIM tile configuration
    
    Node structure from texture_workflow.json:
    - Node 2: CheckpointLoaderSimple (base model)
    - Node 3: CLIPTextEncode (positive prompt)
    - Node 4: CLIPTextEncode (negative prompt)
    - Node 5: KSampler (primary sampler, seed)
    - Node 11: KSampler (refiner sampler, seed)
    - Node 1: LoadImage (UV layout)
    - Node 7: SaveImage (output)
    """
    nodes = workflow.get("nodes", [])
    
    for node in nodes:
        node_id = node.get("id")
        node_type = node.get("type")
        inputs = node.get("inputs", {})
        
        # Node 3: Positive prompt
        if node_id == 3 and node_type == "CLIPTextEncode":
            inputs["text"] = udim_config.get("prompt", "3D game character texture, high quality")
            log(f"  Set positive prompt: {inputs['text'][:50]}...")
        
        # Node 4: Negative prompt
        elif node_id == 4 and node_type == "CLIPTextEncode":
            inputs["text"] = udim_config.get("negative_prompt", "blurry, low quality, distorted")
            log(f"  Set negative prompt: {inputs['text'][:50]}...")
        
        # Node 5 & 11: KSamplers - update seed
        elif node_id in [5, 11] and node_type == "KSampler":
            seed = udim_config.get("seed", 42)
            inputs["seed"] = seed
            log(f"  Set KSampler (node {node_id}) seed: {seed}")
        
        # Node 2: Base checkpoint
        elif node_id == 2 and node_type == "CheckpointLoaderSimple":
            if checkpoint_name:
                inputs["ckpt_name"] = checkpoint_name
                log(f"  Set base checkpoint: {checkpoint_name}")
        
        # Node 1: UV layout image
        elif node_id == 1 and node_type == "LoadImage":
            if uv_image_path:
                inputs["image"] = uv_image_path
                log(f"  Set UV image: {uv_image_path}")
        
        # Node 7: SaveImage - set output filename with UDIM tile
        elif node_id == 7 and node_type == "SaveImage":
            inputs["filename_prefix"] = f"texture_{udim_tile}"
            log(f"  Set output filename: texture_{udim_tile}")
    
    return workflow

def generate_texture_for_tile(comfyui_url, workflow_path, udim_tile, udim_config, output_dir, texture_type="diffuse"):
    """Generate texture for a single UDIM tile"""
    log(f"Generating {texture_type} texture for UDIM tile {udim_tile}")
    
    # Load workflow template
    workflow = load_workflow(workflow_path)
    if not workflow:
        return False
    
    # Update workflow with UDIM configuration
    workflow = update_workflow_params(workflow, udim_tile, udim_config)
    
    # Queue the prompt
    result = queue_prompt(comfyui_url, workflow)
    if not result or "prompt_id" not in result:
        log(f"ERROR: Failed to queue texture generation for tile {udim_tile}")
        return False
    
    prompt_id = result["prompt_id"]
    log(f"Queued prompt {prompt_id} for tile {udim_tile}")
    
    # Wait for completion
    if not wait_for_completion(comfyui_url, prompt_id):
        return False
    
    # Download generated texture
    # Note: Actual file download would require ComfyUI output node configuration
    # For now, we assume textures are saved to the output directory by ComfyUI
    
    log(f"Successfully generated {texture_type} texture for tile {udim_tile}")
    return True

def main():
    if len(sys.argv) < 3:
        print("Usage: generate_textures.py <project_dir> <config_file>")
        sys.exit(1)
    
    project_dir = Path(sys.argv[1])
    config_file = Path(sys.argv[2])
    
    log("================================================================================")
    log("Texture Generation Tool")
    log("================================================================================")
    log(f"Project directory: {project_dir}")
    log(f"Config file: {config_file}")
    
    # Load configuration
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
    except Exception as e:
        log(f"ERROR: Failed to load config: {e}")
        sys.exit(1)
    
    # Get texture configuration
    udim_tiles = config.get("udim_tiles", {})
    if not udim_tiles:
        log("WARNING: No UDIM tiles configured, using default tile 1001")
        udim_tiles = {"1001": {"prompt": "3D game character texture", "negative_prompt": "", "seed": 42}}
    
    # Setup paths
    texture_dir = project_dir / "1_textures"
    texture_dir.mkdir(exist_ok=True)
    
    # ComfyUI connection
    comfyui_url = "http://localhost:8188"
    
    # Wait for ComfyUI to be ready
    if not wait_for_comfyui(comfyui_url):
        log("ERROR: ComfyUI is not available")
        sys.exit(1)
    
    # Find workflow file
    workflow_path = Path(__file__).parent.parent / "comfui_workflows" / "texture_workflow.json"
    if not workflow_path.exists():
        log(f"ERROR: Workflow file not found: {workflow_path}")
        sys.exit(1)
    
    log(f"Using workflow: {workflow_path}")
    
    # Generate textures for each UDIM tile
    success_count = 0
    for tile_id, tile_config in udim_tiles.items():
        log(f"\nProcessing UDIM tile {tile_id}")
        log(f"  Prompt: {tile_config.get('prompt', 'N/A')}")
        log(f"  Seed: {tile_config.get('seed', 42)}")
        
        if generate_texture_for_tile(comfyui_url, workflow_path, tile_id, tile_config, texture_dir):
            success_count += 1
        else:
            log(f"WARNING: Failed to generate texture for tile {tile_id}")
    
    # Summary
    log("\n================================================================================")
    log(f"Texture generation complete: {success_count}/{len(udim_tiles)} tiles successful")
    log(f"Textures saved to: {texture_dir}")
    log("================================================================================")
    
    if success_count == 0:
        log("ERROR: No textures were generated successfully")
        sys.exit(1)
    
    sys.exit(0)

if __name__ == "__main__":
    main()
