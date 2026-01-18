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
    
    def __init__(self, project_path):
        self.project_path = Path(project_path)
        self.config_path = self.project_path / "pipeline" / "config.json"
        self.log_path = self.project_path / "pipeline" / "pipeline_log.txt"
        
        # Load configuration
        with open(self.config_path, 'r') as f:
            self.config = json.load(f)
        
        self.mesh_type = self.config.get('mesh_type', 'skeletal')
        
        # Define pipeline stages
        self.stages = {
            'textures': {
                'name': 'Texture Generation',
                'required_for': ['skeletal', 'static'],
                'script': 'tools/generate_textures.py',
                'input_dir': '0_input',
                'output_dir': '1_textures'
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
            'export': {
                'name': 'Export',
                'required_for': ['skeletal', 'static'],
                'script': 'tools/export_package.py',
                'input_dir': '3_animation',  # or 1_textures for static
                'output_dir': '4_export'
            },
            'sprites': {
                'name': 'Sprite Generation',
                'required_for': ['skeletal'],
                'script': 'tools/generate_sprites.py',
                'input_dir': '3_animation',
                'output_dir': '4_export/sprites',
                'optional': True  # Only runs if enabled in config
            }
        }
    
    def log(self, message):
        """Write log message to both console and log file"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        print(log_message)
        
        with open(self.log_path, 'a') as f:
            f.write(log_message + '\n')
    
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
        
        return True
    
    def run_stage(self, stage_name):
        """Execute a pipeline stage"""
        stage = self.stages[stage_name]
        
        if not self.should_run_stage(stage_name):
            return True
        
        self.log(f"Starting stage: {stage['name']}")
        self.log(f"  Script: {stage['script']}")
        
        # Prepare stage directories
        output_dir = self.project_path / stage['output_dir']
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Build command based on stage
        script_path = Path(__file__).parent / stage['script']
        
        if stage_name in ['rigging', 'animation', 'sprites']:
            # Blender scripts
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
            result = subprocess.run(
                cmd,
                cwd=script_path.parent,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )
            
            if result.returncode == 0:
                self.log(f"  ✓ {stage['name']} completed successfully")
                
                # Log output if verbose
                if result.stdout:
                    self.log(f"  Output: {result.stdout[:500]}")
                
                return True
            else:
                self.log(f"  ✗ {stage['name']} failed with code {result.returncode}")
                self.log(f"  Error: {result.stderr}")
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
        
        # Check for mesh file
        mesh_files = list(input_dir.glob("*.obj")) + list(input_dir.glob("*.fbx"))
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
            stages_to_run = ['textures', 'export']
        else:  # skeletal
            stages_to_run = ['textures', 'rigging', 'animation', 'export', 'sprites']
        
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
    if len(sys.argv) < 2:
        print("Usage: python run_pipeline.py <project_path>")
        print("  project_path: Path to project directory")
        sys.exit(1)
    
    project_path = sys.argv[1]
    
    orchestrator = PipelineOrchestrator(project_path)
    success = orchestrator.run_pipeline()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
