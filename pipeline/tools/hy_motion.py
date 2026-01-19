# Exhibition/pipeline/tools/hy_motion.py

import sys
import json
import subprocess
from pathlib import Path


def generate_animation(project_path: Path, config: dict):
    """
    Generates animations using HY-Motion via subprocess calls.
    """
    project_path = Path(project_path)
    
    # Setup directories
    rig_dir = project_path / "2_rig"
    anim_dir = project_path / "3_animation"
    anim_dir.mkdir(parents=True, exist_ok=True)
    
    # Find rigged mesh
    rigged_files = list(rig_dir.glob("*_rigged.fbx"))
    if not rigged_files:
        print("ERROR: No rigged mesh found in 2_rig/")
        sys.exit(1)
    
    rigged_mesh = rigged_files[0]
    print(f"Using rigged mesh: {rigged_mesh.name}")
    
    # Get animation configuration
    anim_config = config.get('animation', {})
    selected_animations = anim_config.get('selected_animations', [])
    
    if not selected_animations:
        print("WARNING: No animations selected in config")
        print("Using default animation: idle")
        selected_animations = ['idle']
    
    # Generate each selected animation
    for anim_name in selected_animations:
        print(f"\n[HY-MOTION] Generating animation: {anim_name}")
        
        # Prepare prompt for this animation
        # Load from animation library if available, otherwise use animation name
        prompt_lib_path = Path(__file__).parent.parent / "hy_motion_prompts" / "prompt_library.json"
        
        if prompt_lib_path.exists():
            with open(prompt_lib_path, 'r') as f:
                prompt_lib = json.load(f)
                animation_data = prompt_lib.get('animations', {}).get(anim_name, {})
                prompt_text = animation_data.get('motion', f"A person performs {anim_name} animation")
        else:
            prompt_text = f"A person performs {anim_name} animation"
        
        print(f"Prompt: {prompt_text}")
        
        # Output path for this animation
        output_path = anim_dir / f"{rigged_mesh.stem}_{anim_name}.fbx"
        
        # Call HY-Motion local_infer.py
        # Model paths: /workspace/hy-motion/ckpts/tencent/HY-Motion-1.0 or HY-Motion-1.0-Lite
        cmd = [
            "python3",
            "/workspace/hy-motion/local_infer.py",
            "--model_path", "/workspace/hy-motion/ckpts/tencent/HY-Motion-1.0-Lite",
            "--input_text", prompt_text,
            "--output_dir", str(anim_dir),
            "--disable_duration_est",  # Disable LLM duration estimation to save VRAM
            "--disable_rewrite"  # Disable LLM prompt rewriting to save VRAM
        ]
        
        try:
            print(f"Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            if result.stdout:
                print(result.stdout)
            
            # Find the generated file (HY-Motion names it automatically)
            # Typically: output/local_infer/<timestamp>_<prompt_hash>.fbx
            generated_files = list(anim_dir.glob("*.fbx"))
            if generated_files:
                latest_file = max(generated_files, key=lambda p: p.stat().st_mtime)
                # Rename to our naming convention
                latest_file.rename(output_path)
                print(f"[✔] Animation saved: {output_path.name}")
            else:
                print(f"WARNING: No FBX file generated for {anim_name}")
                
        except subprocess.CalledProcessError as e:
            print(f"ERROR: HY-Motion generation failed for {anim_name}")
            print(f"stdout: {e.stdout}")
            print(f"stderr: {e.stderr}")
            continue
    
    print(f"\n[✔] Animation generation complete")
    return selected_animations


if __name__ == "__main__":
    # Check if called with pipeline arguments or legacy arguments
    if "--prompt" in sys.argv:
        # Legacy mode: direct prompt/output arguments
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--prompt", required=True)
        parser.add_argument("--output", required=True)
        args = parser.parse_args()
        
        prompt_text = Path(args.prompt).read_text()
        print("\n[HY-MOTION] Loading pipeline...")
        pipe = HunyuanMotionPipeline.from_pretrained(
            "/workspace/hy-motion",
            torch_dtype="float16",
            device="cuda"
        )
        print("[HY-MOTION] Generating animation...")
        result = pipe(prompt=prompt_text, output_path=args.output)
        print(f"[✔] HY-Motion animation saved to: {args.output}")
    else:
        # Pipeline mode: project_path and config_path arguments
        if len(sys.argv) < 3:
            print("ERROR: Missing required arguments")
            print("Usage: python hy_motion.py <project_path> <config_path>")
            sys.exit(1)
        
        project_path = sys.argv[1]
        config_path = sys.argv[2]
        
        # Load configuration
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        generate_animation(project_path, config)

