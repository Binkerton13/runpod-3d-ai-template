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
        # Try to get detailed error message from response
        try:
            if hasattr(e, 'response') and e.response is not None:
                error_detail = e.response.text
                log(f"ERROR: Server response: {error_detail[:500]}")
        except:
            pass
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

def copy_generated_files(comfyui_output_dir, project_output_dir, filename_prefix):
    """Copy generated files from ComfyUI output folder to project directory"""
    comfyui_dir = Path(comfyui_output_dir)
    project_dir = Path(project_output_dir)
    project_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all files matching the prefix
    if not comfyui_dir.exists():
        log(f"WARNING: ComfyUI output directory not found: {comfyui_dir}")
        return []
    
    pattern = f"{filename_prefix}_*"
    matching_files = list(comfyui_dir.glob(pattern))
    
    copied_files = []
    for src_file in matching_files:
        dst_file = project_dir / src_file.name
        try:
            shutil.copy2(src_file, dst_file)
            log(f"  Copied: {src_file.name} -> {dst_file}")
            copied_files.append(dst_file)
        except Exception as e:
            log(f"  ERROR copying {src_file.name}: {e}")
    
    return copied_files

def load_workflow(workflow_path):
    """Load ComfyUI workflow from JSON file and convert to API format"""
    try:
        with open(workflow_path, 'r') as f:
            workflow = json.load(f)
        
        # Check if it's UI format (has 'nodes' array) and convert to API format
        if "nodes" in workflow and isinstance(workflow["nodes"], list):
            log("  Converting UI workflow format to API format...")
            api_workflow = {}
            for node in workflow["nodes"]:
                node_id = str(node["id"])
                api_workflow[node_id] = {
                    "class_type": node["type"],
                    "inputs": node.get("inputs", {})
                }
            return api_workflow
        
        return workflow
    except Exception as e:
        log(f"ERROR: Failed to load workflow {workflow_path}: {e}")
        return None

def update_workflow_params(workflow, udim_tile, udim_config, checkpoint_name=None, uv_image_path=None):
    """Update workflow parameters with UDIM tile configuration
    
    Node structure from texture_workflow.json (API format):
    - Node 2: CheckpointLoaderSimple (base model)
    - Node 3: CLIPTextEncode (positive prompt)
    - Node 4: CLIPTextEncode (negative prompt)
    - Node 5: KSampler (primary sampler, seed)
    - Node 11: KSampler (refiner sampler, seed)
    - Node 1: LoadImage (UV layout)
    - Node 7: SaveImage (output)
    """
    # Workflow is now in API format: {"1": {"class_type": "...", "inputs": {...}}}
    for node_id, node_data in workflow.items():
        node_type = node_data.get("class_type")
        inputs = node_data.get("inputs", {})
        
        # Node 3: Positive prompt
        if node_id == "3" and node_type == "CLIPTextEncode":
            inputs["text"] = udim_config.get("prompt", "3D game character texture, high quality")
            log(f"  Set positive prompt: {inputs['text'][:50]}...")
        
        # Node 4: Negative prompt
        elif node_id == "4" and node_type == "CLIPTextEncode":
            inputs["text"] = udim_config.get("negative_prompt", "blurry, low quality, distorted")
            log(f"  Set negative prompt: {inputs['text'][:50]}...")
        
        # Node 5 & 11: KSamplers - update seed
        elif node_id in ["5", "11"] and node_type == "KSampler":
            seed = udim_config.get("seed", 42)
            inputs["seed"] = seed
            log(f"  Set KSampler (node {node_id}) seed: {seed}")
        
        # Node 2: Base checkpoint
        elif node_id == "2" and node_type == "CheckpointLoaderSimple":
            if checkpoint_name:
                inputs["ckpt_name"] = checkpoint_name
                log(f"  Set base checkpoint: {checkpoint_name}")
        
        # Node 1: UV layout image
        elif node_id == "1" and node_type == "LoadImage":
            if uv_image_path:
                inputs["image"] = uv_image_path
                log(f"  Set UV image: {uv_image_path}")
        
        # Node 7: SaveImage - set output filename with UDIM tile
        elif node_id == "7" and node_type == "SaveImage":
            inputs["filename_prefix"] = f"texture_{udim_tile}"
            log(f"  Set output filename: texture_{udim_tile}")
    
    return workflow

def update_pbr_workflow_params(workflow, udim_tile, texture_type, albedo_path):
    """Update PBR workflow parameters (AO, normal, metallic, roughness)
    
    PBR workflows are simpler and use the albedo as input:
    - pbr_ao.json: Node 1 (LoadImage), Node 4 (SaveImage)
    - pbr_normal.json: Node 1 (LoadImage), Node 3 (SaveImage)
    - pbr_metallic.json: Node 2 (SaveImage) - no input needed
    - pbr_roughness.json: Node 1 (LoadImage), Node 4 (SaveImage)
    """
    # Workflow is now in API format: {"1": {"class_type": "...", "inputs": {...}}}
    for node_id, node_data in workflow.items():
        node_type = node_data.get("class_type")
        inputs = node_data.get("inputs", {})
        
        # Update LoadImage node with albedo path
        if node_type == "LoadImage" and albedo_path:
            # Extract just the filename without extension for ComfyUI
            from pathlib import Path
            albedo_filename = Path(albedo_path).stem
            inputs["image"] = albedo_filename
            log(f"  Set input image: {albedo_filename}")
        
        # Update SaveImage node with proper filename
        elif node_type == "SaveImage":
            inputs["filename_prefix"] = f"{texture_type}_{udim_tile}"
            log(f"  Set output filename: {texture_type}_{udim_tile}")
    
    return workflow

def generate_pbr_maps(comfyui_url, project_dir, udim_tile, albedo_path):
    """Generate all PBR maps from the albedo texture"""
    workflow_base = Path(__file__).parent.parent / "comfui_workflows"
    texture_dir = project_dir / "1_textures"
    
    pbr_maps = {
        "normal": "pbr_normal.json",
        "ao": "pbr_ao.json", 
        "roughness": "pbr_roughness.json",
        "metallic": "pbr_metallic.json"
    }
    
    success_count = 0
    for map_type, workflow_file in pbr_maps.items():
        workflow_path = workflow_base / workflow_file
        
        if not workflow_path.exists():
            log(f"WARNING: Workflow not found: {workflow_path}")
            continue
        
        log(f"\nGenerating {map_type} map for tile {udim_tile}...")
        if generate_texture_for_tile(comfyui_url, workflow_path, udim_tile, {}, texture_dir, map_type, albedo_path):
            success_count += 1
        else:
            log(f"WARNING: Failed to generate {map_type} map")
    
    return success_count

def generate_texture_for_tile(comfyui_url, workflow_path, udim_tile, udim_config, output_dir, texture_type="diffuse", albedo_path=None):
    """Generate texture for a single UDIM tile
    
    Args:
        albedo_path: For PBR maps (AO, normal, roughness), path to the albedo texture
    """
    log(f"Generating {texture_type} texture for UDIM tile {udim_tile}")
    
    # Load workflow template
    workflow = load_workflow(workflow_path)
    if not workflow:
        return False
    
    # Update workflow based on texture type
    if texture_type == "diffuse":
        workflow = update_workflow_params(workflow, udim_tile, udim_config)
    else:
        # PBR maps need the albedo as input
        workflow = update_pbr_workflow_params(workflow, udim_tile, texture_type, albedo_path)
    
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
    
    # Copy generated files from ComfyUI output to project directory
    comfyui_output = "/opt/comfyui/output"
    filename_prefix = f"texture_{udim_tile}" if texture_type == "diffuse" else f"{texture_type}_{udim_tile}"
    copied_files = copy_generated_files(comfyui_output, output_dir, filename_prefix)
    
    if not copied_files:
        log(f"WARNING: No files found with prefix '{filename_prefix}' in {comfyui_output}")
        log(f"  Generated files may be in ComfyUI output folder but not copied to project")
    
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
        log("WARNING: ComfyUI is not available - running in test/development mode")
        log("Skipping texture generation (requires ComfyUI server)")
        log("\nIn production, ensure ComfyUI is running at http://localhost:8188")
        log("For now, creating placeholder outputs...")
        
        # Create placeholder outputs so pipeline can continue
        for tile_id in udim_tiles.keys():
            placeholder_path = texture_dir / f"texture_{tile_id}_albedo.png"
            placeholder_path.touch()
            log(f"  Created placeholder: {placeholder_path.name}")
        
        log("\n" + "="*80)
        log("TEXTURE GENERATION SKIPPED (ComfyUI not available)")
        log("="*80)
        sys.exit(0)
    
    # Find workflow file
    workflow_path = Path(__file__).parent.parent / "comfui_workflows" / "texture_workflow.json"
    if not workflow_path.exists():
        log(f"ERROR: Workflow file not found: {workflow_path}")
        sys.exit(1)
    
    log(f"Using workflow: {workflow_path}")
    
    # Generate diffuse/albedo textures for each UDIM tile
    success_count = 0
    albedo_paths = {}  # Store albedo paths for PBR map generation
    
    for tile_id, tile_config in udim_tiles.items():
        log(f"\n{'='*80}")
        log(f"Processing UDIM tile {tile_id} - Diffuse/Albedo")
        log(f"{'='*80}")
        log(f"  Prompt: {tile_config.get('prompt', 'N/A')}")
        log(f"  Seed: {tile_config.get('seed', 42)}")
        
        if generate_texture_for_tile(comfyui_url, workflow_path, tile_id, tile_config, texture_dir):
            success_count += 1
            # Save albedo path for PBR generation
            # ComfyUI SaveImage adds frame number to filename_prefix
            albedo_paths[tile_id] = texture_dir / f"texture_{tile_id}_00001_.png"
            log(f"✓ Diffuse texture generated for tile {tile_id}")
        else:
            log(f"✗ Failed to generate diffuse texture for tile {tile_id}")
    
    if success_count == 0:
        log("\nERROR: No diffuse textures were generated successfully")
        sys.exit(1)
    
    # Generate PBR maps (normal, AO, roughness, metallic) from albedo
    log(f"\n{'='*80}")
    log("Generating PBR Maps from Albedo Textures")
    log(f"{'='*80}")
    
    pbr_success_count = 0
    for tile_id, albedo_path in albedo_paths.items():
        if not albedo_path.exists():
            log(f"WARNING: Albedo not found for tile {tile_id}, skipping PBR maps")
            continue
        
        log(f"\nGenerating PBR maps for tile {tile_id}...")
        maps_generated = generate_pbr_maps(comfyui_url, project_dir, tile_id, str(albedo_path))
        pbr_success_count += maps_generated
        log(f"✓ Generated {maps_generated}/4 PBR maps for tile {tile_id}")
    
    # Summary
    log("\n" + "="*80)
    log("TEXTURE GENERATION COMPLETE")
    log("="*80)
    log(f"Diffuse/Albedo: {success_count}/{len(udim_tiles)} tiles successful")
    log(f"PBR Maps: {pbr_success_count} maps generated")
    log(f"Output directory: {texture_dir}")
    log("="*80)
    
    sys.exit(0)

if __name__ == "__main__":
    main()
