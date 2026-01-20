#!/usr/bin/env python3
"""
Main pipeline orchestrator for 3D character processing.
Handles mesh type detection and conditionally executes pipeline stages.
"""
import sys
import json
import subprocess
from pathlib import Path
import time

class PipelineOrchestrator:
    """Orchestrates the complete 3D character pipeline based on mesh type and configuration"""
    
    def __init__(self, project_path, force_rerun=False):
        self.project_path = Path(project_path)
        self.config_path = self.project_path / "pipeline" / "config.json"
        self.log_path = self.project_path / "pipeline" / "pipeline_log.txt"
        self.force_rerun = force_rerun
        
        # Load configuration
        with open(self.config_path, 'r') as f:
            self.config = json.load(f)
        
        self.mesh_type = self.config.get('mesh_type', 'skeletal')
        
        # Define pipeline stages
        # New pipeline: Mesh → UniRig → HY-Motion → AI-Enhanced Sprites
        # Removed: Texture generation (archived)
        self.stages = {
            'prep': {
                'name': 'Mesh Preparation',
                'required_for': ['skeletal', 'static'],
                'script': 'tools/prepare_mesh.py',
                'input_dir': '0_input',
                'output_dir': '0_input'  # Overwrites input with prepared mesh
            },
            'rigging': {
                'name': 'Rigging',
                'required_for': ['skeletal'],
                'script': 'tools/auto_rig.py',
                'input_dir': '0_input',
                'output_dir': '2_rig'
            },
            'animation': {
                'name': 'Animation',
                'required_for': ['skeletal'],
                'script': 'tools/hy_motion.py',
                'input_dir': '2_rig',
                'output_dir': '3_animation'
            },
            'sprites': {
                'name': 'AI-Enhanced Sprite Generation',
                'required_for': ['skeletal'],
                'script': 'tools/generate_sprites_enhanced.py',
                'input_dir': '3_animation',
                'output_dir': '5_sprites'  # Changed from 4_export/sprites
            },
            'export': {
                'name': 'Export',
                'required_for': ['skeletal', 'static'],
                'script': 'tools/export_package.py',
                'input_dir': '5_sprites',  # Package sprites
                'output_dir': '4_export'
            }
        }
    
    def log(self, message):
        """Write log message to both console and log file"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        print(log_message)
        
        with open(self.log_path, 'a') as f:
            f.write(log_message + '\n')
    
    def stage_has_output(self, stage_name):
        """Check if a stage already has output files"""
        stage = self.stages[stage_name]
        output_dir = self.project_path / stage['output_dir']
        
        if not output_dir.exists():
            return False
        
        # Check for relevant output files
        if stage_name == 'prep':
            # Prep stage always runs to ensure UV unwrapping
            return False
        elif stage_name == 'rigging':
            # Look for rigged FBX
            return any(output_dir.glob('*_rigged.fbx'))
        elif stage_name == 'animation':
            # Look for animation FBX files
            return any(output_dir.glob('*.fbx'))
        elif stage_name == 'export':
            # Look for export packages
            return any(output_dir.glob('*.zip')) or any(output_dir.glob('*.glb'))
        elif stage_name == 'sprites':
            # Look for sprite images
            return any(output_dir.glob('*.png'))
        
        # Default: check if directory has any files
        return any(output_dir.iterdir())
    
    def should_run_stage(self, stage_name):
        """Determine if a stage should run based on mesh type and configuration"""
        stage = self.stages[stage_name]
        
        # Check if stage is required for this mesh type
        if self.mesh_type not in stage['required_for']:
            self.log(f"  Skipping {stage['name']} (not required for {self.mesh_type} mesh)")
            return False
        
        # Check optional stages
        if stage.get('optional', False):
            if stage_name == 'sprites':
                sprite_config = self.config.get('sprite_generation', {})
                if not sprite_config.get('enabled', False):
                    self.log(f"  Skipping {stage['name']} (disabled in config)")
                    return False
        
        # Check if input exists
        input_dir = self.project_path / stage['input_dir']
        if not input_dir.exists() or not any(input_dir.iterdir()):
            self.log(f"  Skipping {stage['name']} (no input found in {stage['input_dir']})")
            return False
        
        # Check if stage already completed (unless force_rerun)
        if not self.force_rerun and self.stage_has_output(stage_name):
            self.log(f"  Skipping {stage['name']} (output already exists, use force_rerun to regenerate)")
            return False
        
        return True
    
    def run_stage(self, stage_name):
        """Execute a pipeline stage"""
        stage = self.stages[stage_name]
        
        if not self.should_run_stage(stage_name):
            # Stage was skipped - still return True so pipeline continues
            # but mark in logs that it was skipped, not completed
            return True
        
        self.log(f"Starting stage: {stage['name']}")
        self.log(f"  Script: {stage['script']}")
        
        # Prepare stage directories
        output_dir = self.project_path / stage['output_dir']
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Build command based on stage
        script_path = Path(__file__).parent / stage['script']
        
        # Check if script exists
        if not script_path.exists():
            self.log(f"  ✗ Script not found: {stage['script']}")
            self.log(f"  This stage is not yet implemented")
            return False
        
        if stage_name in ['prep', 'rigging', 'animation', 'sprites']:
            # Blender scripts - need input/output mesh paths
            if stage_name == 'prep':
                # Look for mesh in 0_input/meshes folder
                input_dir = self.project_path / '0_input' / 'meshes'
                if not input_dir.exists():
                    # Fallback to 0_input for backward compatibility
                    input_dir = self.project_path / '0_input'
                
                input_mesh = next(input_dir.glob('*.fbx'), next(input_dir.glob('*.obj'), None))
                if not input_mesh:
                    self.log(f"  ✗ No input mesh found in {input_dir}")
                    return False
                
                # Output to 0_input (root) for other stages to use
                output_mesh = self.project_path / '0_input' / f"{input_mesh.stem}_prepared.fbx"
                
                self.log(f"  Input:  {input_mesh.name}")
                self.log(f"  Output: {output_mesh.name}")
                
                cmd = [
                    'blender',
                    '--background',
                    '--python', str(script_path),
                    '--',
                    str(input_mesh),
                    str(output_mesh)
                ]
            else:
                # Other Blender scripts use project path and config
                cmd = [
                    'blender',
                    '--background',
                    '--python', str(script_path),
                    '--',
                    str(self.project_path),
                    str(self.config_path)
                ]
        else:
            # Python scripts
            cmd = [
                sys.executable,
                str(script_path),
                str(self.project_path),
                str(self.config_path)
            ]
        
        try:
            self.log(f"  Executing: {' '.join(cmd)}")
            
            # Stream output in real-time instead of capturing
            process = subprocess.Popen(
                cmd,
                cwd=script_path.parent,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            # Stream output line by line
            for line in process.stdout:
                line = line.rstrip()
                if line:  # Only log non-empty lines
                    self.log(f"    {line}")
            
            # Wait for completion with timeout
            try:
                returncode = process.wait(timeout=3600)
            except subprocess.TimeoutExpired:
                process.kill()
                raise
            
            if returncode == 0:
                self.log(f"  ✓ {stage['name']} completed successfully")
                return True
            else:
                self.log(f"  ✗ {stage['name']} failed with code {returncode}")
                return False
        
        except subprocess.TimeoutExpired:
            self.log(f"  ✗ {stage['name']} timed out after 1 hour")
            return False
        except Exception as e:
            self.log(f"  ✗ {stage['name']} error: {str(e)}")
            return False
    
    def validate_input(self):
        """Validate that required input files exist"""
        input_dir = self.project_path / "0_input"
        
        if not input_dir.exists():
            self.log("Error: Input directory does not exist")
            return False
        
        # Check for mesh file (search recursively in subdirectories)
        mesh_files = list(input_dir.rglob("*.obj")) + list(input_dir.rglob("*.fbx"))
        if not mesh_files:
            self.log("Error: No mesh files found in input directory")
            return False
        
        self.log(f"Found input mesh: {mesh_files[0].name}")
        self.log(f"Mesh type: {self.mesh_type}")
        
        return True
    
    def run_pipeline(self):
        """Execute the complete pipeline"""
        self.log("="*80)
        self.log(f"Starting pipeline for project: {self.project_path.name}")
        self.log(f"Mesh type: {self.mesh_type}")
        self.log("="*80)
        
        # Validate input
        if not self.validate_input():
            return False
        
        # Define stage execution order
        if self.mesh_type == 'static':
            stages_to_run = ['prep', 'export']
        else:  # skeletal
            stages_to_run = ['prep', 'rigging', 'animation', 'sprites', 'export']
        
        # Execute stages
        for stage_name in stages_to_run:
            success = self.run_stage(stage_name)
            
            if not success and not self.stages[stage_name].get('optional', False):
                self.log(f"Pipeline failed at stage: {stage_name}")
                return False
        
        self.log("="*80)
        self.log("Pipeline completed successfully!")
        self.log("="*80)
        
        return True
    
    def get_pipeline_status(self):
        """Get current pipeline status and completed stages"""
        status = {
            'project': self.project_path.name,
            'mesh_type': self.mesh_type,
            'stages': {}
        }
        
        for stage_name, stage_config in self.stages.items():
            output_dir = self.project_path / stage_config['output_dir']
            
            stage_status = {
                'name': stage_config['name'],
                'required': self.mesh_type in stage_config['required_for'],
                'completed': output_dir.exists() and any(output_dir.iterdir()),
                'output_exists': output_dir.exists()
            }
            
            status['stages'][stage_name] = stage_status
        
        return status

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run 3D character pipeline")
    parser.add_argument("project_path", help="Path to project directory")
    parser.add_argument("--force-rerun", "-f", action="store_true",
                        help="Force re-run all stages even if outputs exist")
    
    args = parser.parse_args()
    
    orchestrator = PipelineOrchestrator(args.project_path, force_rerun=args.force_rerun)
    success = orchestrator.run_pipeline()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
