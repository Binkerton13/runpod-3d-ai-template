"""
export_package.py
-----------------
Final packaging script for the Exhibition pipeline.

This script collects:
- The rigged mesh (FBX)
- The animations (FBX files)
- The textures (PBR maps)
- Sprites (if generated)
- Metadata (project.json)

Usage:
python3 export_package.py <project_path> <config_path>
"""

import json
import shutil
import sys
from pathlib import Path


def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def copy_if_exists(src: Path, dst: Path):
    if src.exists():
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dst)
        print(f"[✔] Copied: {src.name}")
        return True
    else:
        print(f"[SKIP] Not found: {src}")
        return False


def build_metadata(project_name: str, output_dir: Path, config: dict):
    """Build comprehensive metadata for the export package"""
    
    mesh_type = config.get('mesh_type', 'skeletal')
    
    metadata = {
        "project": project_name,
        "mesh_type": mesh_type,
        "description": "Final packaged output from the 3D AI Pipeline",
        "pipeline_version": "1.0",
        "contents": {}
    }
    
    # Check what was actually exported
    if (output_dir / "rig.fbx").exists():
        metadata["contents"]["rig"] = "rig.fbx"
    
    animations = list((output_dir / "animations").glob("*.fbx")) if (output_dir / "animations").exists() else []
    if animations:
        metadata["contents"]["animations"] = {
            "directory": "animations/",
            "count": len(animations),
            "files": [a.name for a in animations]
        }
    
    if (output_dir / "textures").exists():
        metadata["contents"]["textures"] = "textures/"
    
    sprites = list((output_dir / "sprites").glob("*.png")) if (output_dir / "sprites").exists() else []
    if sprites:
        metadata["contents"]["sprites"] = {
            "directory": "sprites/",
            "count": len(sprites),
            "frames": len(sprites)
        }
    
    metadata_path = output_dir / "project.json"
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=4)
    
    print(f"[✔] Metadata written: {metadata_path.name}")


def package_export(project_path: Path, config: dict):
    """Package all pipeline outputs into final export directory"""
    
    project_path = Path(project_path)
    project_name = project_path.name
    
    # Setup export directory
    export_root = project_path / "4_export" / "package"
    ensure_dir(export_root)
    
    print("\n" + "="*80)
    print(f"PACKAGING EXPORT: {project_name}")
    print("="*80)
    print(f"Output directory: {export_root}")
    
    # ---------------------------------------------------------
    # 1. Copy rigged mesh
    # ---------------------------------------------------------
    print("\n--- Rigged Mesh ---")
    rig_dir = project_path / "2_rig"
    if rig_dir.exists():
        rigged_files = list(rig_dir.glob("*_rigged.fbx"))
        if rigged_files:
            rig_dst = export_root / "rig.fbx"
            copy_if_exists(rigged_files[0], rig_dst)
    
    # ---------------------------------------------------------
    # 2. Copy animations
    # ---------------------------------------------------------
    print("\n--- Animations ---")
    anim_dir = project_path / "3_animation"
    if anim_dir.exists():
        anim_files = list(anim_dir.glob("*.fbx"))
        if anim_files:
            anim_export_dir = export_root / "animations"
            ensure_dir(anim_export_dir)
            for anim_file in anim_files:
                copy_if_exists(anim_file, anim_export_dir / anim_file.name)
    
    # ---------------------------------------------------------
    # 3. Copy textures
    # ---------------------------------------------------------
    print("\n--- Textures ---")
    texture_dir = project_path / "1_textures"
    if texture_dir.exists():
        texture_export_dir = export_root / "textures"
        copy_if_exists(texture_dir, texture_export_dir)
    
    # ---------------------------------------------------------
    # 4. Copy sprites (if generated)
    # ---------------------------------------------------------
    print("\n--- Sprites ---")
    sprite_dir = project_path / "4_export" / "sprites"
    if sprite_dir.exists():
        sprite_export_dir = export_root / "sprites"
        copy_if_exists(sprite_dir, sprite_export_dir)
    
    spritesheet_dir = project_path / "4_export" / "spritesheets"
    if spritesheet_dir.exists():
        spritesheet_export_dir = export_root / "spritesheets"
        copy_if_exists(spritesheet_dir, spritesheet_export_dir)
    
    # ---------------------------------------------------------
    # 5. Write metadata
    # ---------------------------------------------------------
    print("\n--- Metadata ---")
    build_metadata(project_name, export_root, config)
    
    print("\n" + "="*80)
    print(f"[✔] Export package complete: {export_root}")
    print("="*80)


def main():
    """Main entry point for export packaging"""
    
    # Check if called with pipeline arguments or legacy arguments
    if "--input" in sys.argv:
        # Legacy mode for backwards compatibility
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--input", required=True, help="Retargeted animation FBX")
        parser.add_argument("--project", required=True, help="Project name for export folder")
        args = parser.parse_args()
        
        print("WARNING: Using legacy argument format")
        print("Please update to: python export_package.py <project_path> <config_path>")
        sys.exit(1)
    else:
        # Pipeline mode: project_path and config_path
        if len(sys.argv) < 3:
            print("ERROR: Missing required arguments")
            print("Usage: python export_package.py <project_path> <config_path>")
            sys.exit(1)
        
        project_path = sys.argv[1]
        config_path = sys.argv[2]
        
        # Load configuration
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        package_export(project_path, config)


if __name__ == "__main__":
    main()
