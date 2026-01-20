#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path

# Add pipeline/tools to Python path for imports
sys.path.insert(0, str(Path(__file__).parent / "tools"))

from freeze_rig import main as freeze_rig

CONFIG_PATH = Path("pipeline/config.json")
CONFIG = json.loads(CONFIG_PATH.read_text())

def run(cmd):
    print("\n=== RUNNING:")
    print("   ", cmd)
    print("===")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print("Command failed:", cmd)

# ---------------------------------------------------------
# [1] MODEL PREP
# ---------------------------------------------------------
def prepare_model():
    print("\n[1] Preparing model...")
    clean_fbx = CONFIG["clean_fbx"]
    print(f"Using clean FBX: {clean_fbx}")

# ---------------------------------------------------------
# [2] Mesh VALIDATION
# ---------------------------------------------------------
def mesh_validation():
    print("\n[1.5] Validating mesh...")

    cmd = (
        "blender -b --python pipeline/tools/validate_mesh.py "
        f"-- {CONFIG['clean_fbx']}"
    )

    run(cmd)

# ---------------------------------------------------------
# [3] UDIM TEXTURE GENERATION
# ---------------------------------------------------------
def generate_textures():
    print("\n[2] Generating UDIM textures with ComfyUI...")

    comfy_url = CONFIG["comfyui_url"]
    workflow = CONFIG["texture_workflow"]
    #udim_list = CONFIG["udim_uvs"]
    #udim_prompts = CONFIG["udim_prompts"]
    udim_tiles = CONFIG["udim_tiles"]

    for tile_num, tile in udim_tiles.items():
        uv_png = tile["uv"]
        prompt = tile["prompt"]
        negative = tile["negative"]
        seed = tile["seed"]
        output_name = tile["output"]

        print(f"\n--- Processing UDIM {tile_num}: {uv_png} ---")
        print(f"Prompt: {prompt}")
        print(f"Negative: {negative}")

        payload = (
            f"{{"
            f"\"workflow\": \"{workflow}\", "
            f"\"uv\": \"{uv_png}\", "
            f"\"prompt\": \"{prompt}\", "
            f"\"negative\": \"{negative}\", "
            f"\"seed\": {seed}, "
            f"\"output\": \"{output_name}\""
            f"}}"
        )

        cmd = (
            f"curl -X POST {comfy_url}/prompt "
            f"-H 'Content-Type: application/json' "
            f"-d '{payload}'"
        )

        run(cmd)
        # After generating albedo, generate PBR maps
        generate_pbr_maps(tile_num, output_name)
        
def generate_pbr_maps(tile_num, albedo_path):
    pbr = CONFIG["pbr_outputs"][tile_num]
    comfy_url = CONFIG["comfyui_url"]

    for map_type, output_name in pbr.items():
        payload = (
            f"{{"
            f"\"workflow\": \"pipeline/comfyui_workflows/pbr_{map_type}.json\", "
            f"\"albedo\": \"{albedo_path}\", "
            f"\"output\": \"{output_name}\""
            f"}}"
        )

        cmd = (
            f"curl -X POST {comfy_url}/prompt "
            f"-H 'Content-Type: application/json' "
            f"-d '{payload}'"
        )

        run(cmd)
import os
import shutil

def package_udim_material():
    print("\n[7] Packaging UDIM material set...")

    root = Path(CONFIG["udim_output_root"])
    root.mkdir(exist_ok=True)

    subfolders = ["albedo", "normal", "roughness", "metallic", "ao"]
    for sf in subfolders:
        (root / sf).mkdir(exist_ok=True)

    udim_tiles = CONFIG["udim_tiles"]
    pbr_outputs = CONFIG["pbr_outputs"]

    for tile_num, tile in udim_tiles.items():
        # Move albedo
        albedo_src = Path(tile["output"])
        albedo_dst = root / "albedo" / tile["output"]
        if albedo_src.exists():
            shutil.move(str(albedo_src), str(albedo_dst))

        # Move PBR maps
        for map_type, filename in pbr_outputs[tile_num].items():
            src = Path(filename)
            dst = root / map_type / filename
            if src.exists():
                shutil.move(str(src), str(dst))

    # Write material definition
    material_json = {
        "project": CONFIG["project_name"],
        "udim_tiles": list(udim_tiles.keys()),
        "maps": {
            "albedo": "albedo/albedo_<UDIM>.png",
            "normal": "normal/normal_<UDIM>.png",
            "roughness": "roughness/roughness_<UDIM>.png",
            "metallic": "metallic/metallic_<UDIM>.png",
            "ao": "ao/ao_<UDIM>.png"
        }
    }

    (root / "material.json").write_text(json.dumps(material_json, indent=4))

    print("[✔] UDIM material package assembled.")

# ---------------------------------------------------------
# [4] AUTO-RIGGING
# ---------------------------------------------------------
def auto_rig():
    print("\n[2] Running UniRig auto‑rigging...")

    unirig = CONFIG["unirig"]

    cmd = (
        f"python3 {unirig['executable']} "
        f"--input {unirig['input_mesh']} "
        f"--output {unirig['output_rig']} "
        f"--preset {unirig['preset']} "
        f"--scale {unirig['scale']} "
        f"--root {unirig['root_bone']} "
        f"--orientation {unirig['orientation']}"
    )

    run(cmd)

    print("[✔] UniRig completed.")

def validate_rig():
    print("\n[2.5] Validating rig...")

    cmd = (
        "blender -b --python pipeline/tools/validate_rig.py "
        f"-- {CONFIG['rig_output']['fbx']}"
    )

    run(cmd)

    print("[✔] Rig validation complete.")

def fix_joint_orientation():
    print("\n[3] Fixing joint orientation...")

    cmd = (
        "blender -b --python pipeline/tools/fix_joint_orientation.py "
        f"-- {CONFIG['rig_output']['fbx']}"
    )

    run(cmd)

    print("[✔] Joint orientation cleanup complete.")

def smooth_weights():
    print("\n[3.5] Smoothing skin weights...")

    cmd = (
        "blender -b --python pipeline/tools/smooth_weights.py "
        f"-- {CONFIG['rig_output_clean']}"
    )

    run(cmd)

    print("[✔] Skin weight smoothing complete.")


# ---------------------------------------------------------
# [4] AI DEFORMATION FIX
# ---------------------------------------------------------
def fix_deformations():
    print("\n[4] Fixing deformations with ComfyUI...")

    comfy_url = CONFIG["comfyui_url"]
    workflow = CONFIG["deform_fix_workflow"]
    rigged_fbx = CONFIG["rigged_fbx"]

    payload = (
        f"{{\"workflow\": \"{workflow}\", "
        f"\"rigged\": \"{rigged_fbx}\"}}"
    )

    cmd = (
        f"curl -X POST {comfy_url}/prompt "
        f"-H 'Content-Type: application/json' "
        f"-d '{payload}'"
    )

    run(cmd)

def ai_deformation_correction():
    print("\n[4] Running AI deformation correction...")

    # 1) Sample poses and export deformed meshes
    cmd_sample = (
        "blender -b --python tools/sample_deform_poses.py "
        f"-- {CONFIG['rig_output_smoothed']} {CONFIG['deform_fix']['pose_list']}"
    )
    run(cmd_sample)

    # 2) Run AI correction (ComfyUI) on rendered deformation images / maps
    cmd_ai = (
        f"curl -X POST {CONFIG['comfyui_url']}/prompt "
        f"-H 'Content-Type: application/json' "
        f"-d '{{"
        f"\"workflow\": \"{CONFIG['deform_fix_workflow']}\""
        f"}}'"
    )
    run(cmd_ai)

    # 3) Apply corrective deltas back to the rig
    cmd_apply = (
        "blender -b --python tools/apply_deform_corrections.py "
        f"-- {CONFIG['rig_output_smoothed']} {CONFIG['deform_fix']['corrected_fbx']}"
    )
    run(cmd_apply)

    print("[✔] AI deformation correction complete.")

# ---------------------------------------------------------
# [5] HY-MOTION ANIMATION GENERATION
# ---------------------------------------------------------
def generate_animation():
    print("\n[5] Generating animation with HY-Motion...")

    prompt = CONFIG["hy_motion_prompt"]
    output = CONFIG["hy_motion_raw_anim"]

    cmd = (
        f"python3 tools/hy_motion.py "
        f"--prompt {prompt} "
        f"--output {output}"
    )
    run(cmd)

# ---------------------------------------------------------
# [6] RETARGET ANIMATION
# ---------------------------------------------------------
def retarget_animation():
    print("\n[6] Retargeting animation...")

    rigged_fbx = CONFIG["rigged_fbx"]
    raw_anim = CONFIG["hy_motion_raw_anim"]
    retargeted = CONFIG["retargeted_anim"]

    cmd = (
        f"python3 tools/retarget.py "
        f"--rig {rigged_fbx} "
        f"--anim {raw_anim} "
        f"--output {retargeted}"
    )
    run(cmd)

# ---------------------------------------------------------
# [7] FINAL EXPORT
# ---------------------------------------------------------
def export_package():
    print("\n[7] Packaging final export...")

    retargeted = CONFIG["retargeted_anim"]

    cmd = (
        f"python3 tools/export_package.py "
        f"--input {retargeted} "
        f"--project {CONFIG['project_name']}"
    )
    run(cmd)

# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
def main():
    prepare_model()
    mesh_validation()
    generate_textures()
    auto_rig()
    validate_rig()
    fix_joint_orientation()
    smooth_weights()
    freeze_rig()
    ai_deformation_correction()
    generate_animation()
    retarget_animation()
    export_package()
    package_udim_material()
    print("\n[✔] Full pipeline complete.")

if __name__ == "__main__":
    main()
