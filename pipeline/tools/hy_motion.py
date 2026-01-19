# Exhibition/pipeline/tools/hy_motion.py

import sys
import json
from pathlib import Path

# Add HY-Motion repo to Python path
sys.path.append("/workspace/hy-motion")

from inference import HunyuanMotionPipeline


def generate_animation(project_path: Path, config: dict):
    """
    Generates animations using HY-Motion Python API.
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
    
    print(f"\n[HY-MOTION] Loading pipeline...")
    pipe = HunyuanMotionPipeline.from_pretrained(
        "/workspace/hy-motion",
        torch_dtype="float16",
        device="cuda"
    )
    
    # Generate each selected animation
    for anim_name in selected_animations:
        print(f"\n[HY-MOTION] Generating animation: {anim_name}")
        
        # Load prompt for this animation
        prompt_path = Path(__file__).parent.parent / "hy_motion_prompts" / "single_output" / "motion.txt"
        if not prompt_path.exists():
            print(f"WARNING: Prompt file not found: {prompt_path}")
            prompt_text = f"Generate {anim_name} animation"
        else:
            prompt_text = prompt_path.read_text()
        
        # Generate animation
        output_path = anim_dir / f"{rigged_mesh.stem}_{anim_name}.fbx"
        
        result = pipe(
            prompt=prompt_text,
            output_path=str(output_path)
        )
        
        print(f"[✔] Animation saved: {output_path.name}")
    
    print(f"\n[✔] Generated {len(selected_animations)} animations")
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

