#!/usr/bin/env python3
"""
Model Manager for ComfyUI Models
Handles listing, validation, and organization of ComfyUI models
"""
import json
from pathlib import Path
from typing import Dict, List, Optional

class ModelManager:
    """Manages ComfyUI model files and configuration"""
    
    # ComfyUI model folder structure
    MODEL_PATHS = {
        'checkpoints': 'models/checkpoints',
        'loras': 'models/loras',
        'controlnet': 'models/controlnet',
        'vae': 'models/vae',
        'ipadapter': 'models/ipadapter',
        'embeddings': 'models/embeddings',
        'upscale_models': 'models/upscale_models',
        'clip_vision': 'models/clip_vision'
    }
    
    # File extensions for each model type
    MODEL_EXTENSIONS = {
        'checkpoints': ['.safetensors', '.ckpt', '.pt'],
        'loras': ['.safetensors', '.ckpt', '.pt'],
        'controlnet': ['.safetensors', '.pth', '.bin'],
        'vae': ['.safetensors', '.pt', '.ckpt'],
        'ipadapter': ['.safetensors', '.bin'],
        'embeddings': ['.safetensors', '.pt', '.bin'],
        'upscale_models': ['.pth', '.safetensors'],
        'clip_vision': ['.safetensors', '.bin']
    }
    
    # Required models for pipeline workflows
    REQUIRED_MODELS = {
        'texture_workflow': {
            'checkpoints': ['sdxl'],  # Any checkpoint with 'sdxl' in name
            'controlnet': [],
            'ipadapter': ['ip-adapter'],
            'vae': []  # Optional, SDXL has built-in VAE
        },
        'sprite_generation_workflow': {
            'checkpoints': ['sdxl'],
            'controlnet': ['openpose', 'depth'],
            'ipadapter': ['ip-adapter'],
            'vae': []
        }
    }
    
    def __init__(self, comfyui_root: Path):
        """
        Initialize ModelManager
        
        Args:
            comfyui_root: Path to ComfyUI installation root
        """
        self.comfyui_root = Path(comfyui_root)
        self.config_path = Path(__file__).parent / "model_config.json"
        self.load_config()
    
    def load_config(self):
        """Load model configuration from JSON"""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
        else:
            self.config = {
                'last_used': {},
                'selected': {}
            }
    
    def save_config(self):
        """Save model configuration to JSON"""
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def get_model_path(self, model_type: str) -> Path:
        """Get full path to model directory"""
        if model_type not in self.MODEL_PATHS:
            raise ValueError(f"Unknown model type: {model_type}")
        
        return self.comfyui_root / self.MODEL_PATHS[model_type]
    
    def list_models(self, model_type: str) -> List[Dict[str, any]]:
        """
        List all models of a specific type
        
        Returns:
            List of dicts with model info (name, path, size, modified)
        """
        model_dir = self.get_model_path(model_type)
        
        if not model_dir.exists():
            return []
        
        extensions = self.MODEL_EXTENSIONS.get(model_type, [])
        models = []
        
        for ext in extensions:
            for model_file in model_dir.glob(f"*{ext}"):
                stat = model_file.stat()
                models.append({
                    'name': model_file.name,
                    'path': str(model_file.relative_to(self.comfyui_root)),
                    'size': stat.st_size,
                    'size_mb': round(stat.st_size / (1024 * 1024), 2),
                    'modified': stat.st_mtime,
                    'type': model_type
                })
        
        # Sort by name
        models.sort(key=lambda x: x['name'].lower())
        
        return models
    
    def list_all_models(self) -> Dict[str, List[Dict]]:
        """List all models organized by type"""
        all_models = {}
        
        for model_type in self.MODEL_PATHS.keys():
            all_models[model_type] = self.list_models(model_type)
        
        return all_models
    
    def validate_model_file(self, filename: str, model_type: str) -> bool:
        """Check if file extension is valid for model type"""
        ext = Path(filename).suffix.lower()
        valid_extensions = self.MODEL_EXTENSIONS.get(model_type, [])
        return ext in valid_extensions
    
    def get_model_save_path(self, filename: str, model_type: str) -> Path:
        """Get full path where model should be saved"""
        model_dir = self.get_model_path(model_type)
        model_dir.mkdir(parents=True, exist_ok=True)
        return model_dir / filename
    
    def validate_workflow_models(self, workflow_name: str) -> Dict[str, any]:
        """
        Check if all required models for a workflow are available
        
        Returns:
            Dict with 'valid' bool and 'missing' list of required models
        """
        if workflow_name not in self.REQUIRED_MODELS:
            return {'valid': True, 'missing': [], 'message': 'No requirements defined'}
        
        requirements = self.REQUIRED_MODELS[workflow_name]
        missing = []
        available_models = self.list_all_models()
        
        for model_type, required_keywords in requirements.items():
            if not required_keywords:
                continue  # Optional
            
            type_models = available_models.get(model_type, [])
            
            for keyword in required_keywords:
                # Check if any model contains the keyword
                found = any(keyword.lower() in model['name'].lower() 
                           for model in type_models)
                
                if not found:
                    missing.append({
                        'type': model_type,
                        'keyword': keyword,
                        'description': f"{model_type} containing '{keyword}'"
                    })
        
        valid = len(missing) == 0
        message = "All required models available" if valid else "Missing required models"
        
        return {
            'valid': valid,
            'missing': missing,
            'message': message
        }
    
    def get_selected_models(self, workflow_name: str) -> Dict[str, str]:
        """Get currently selected models for a workflow"""
        return self.config.get('selected', {}).get(workflow_name, {})
    
    def set_selected_models(self, workflow_name: str, model_selections: Dict[str, str]):
        """
        Save model selections for a workflow
        
        Args:
            workflow_name: Name of workflow
            model_selections: Dict of {model_type: model_filename}
        """
        if 'selected' not in self.config:
            self.config['selected'] = {}
        
        self.config['selected'][workflow_name] = model_selections
        
        # Also update last_used
        if 'last_used' not in self.config:
            self.config['last_used'] = {}
        
        for model_type, model_name in model_selections.items():
            self.config['last_used'][model_type] = model_name
        
        self.save_config()
    
    def get_last_used_model(self, model_type: str) -> Optional[str]:
        """Get the last used model of a specific type"""
        return self.config.get('last_used', {}).get(model_type)
    
    def auto_select_models(self, workflow_name: str) -> Dict[str, str]:
        """
        Auto-select models for a workflow based on:
        1. Last used models
        2. First available model matching requirements
        
        Returns:
            Dict of {model_type: model_filename}
        """
        requirements = self.REQUIRED_MODELS.get(workflow_name, {})
        available_models = self.list_all_models()
        selections = {}
        
        for model_type, required_keywords in requirements.items():
            if not required_keywords:
                continue
            
            # Try last used first
            last_used = self.get_last_used_model(model_type)
            if last_used:
                type_models = available_models.get(model_type, [])
                if any(m['name'] == last_used for m in type_models):
                    selections[model_type] = last_used
                    continue
            
            # Otherwise, find first matching model
            type_models = available_models.get(model_type, [])
            
            for keyword in required_keywords:
                matching = [m for m in type_models 
                           if keyword.lower() in m['name'].lower()]
                if matching:
                    selections[model_type] = matching[0]['name']
                    break
        
        return selections
    
    def delete_model(self, model_type: str, filename: str) -> bool:
        """
        Delete a model file
        
        Returns:
            True if deleted, False if not found
        """
        model_path = self.get_model_path(model_type) / filename
        
        if model_path.exists():
            model_path.unlink()
            return True
        
        return False
    
    def get_model_info(self, model_type: str, filename: str) -> Optional[Dict]:
        """Get detailed info about a specific model"""
        models = self.list_models(model_type)
        
        for model in models:
            if model['name'] == filename:
                return model
        
        return None


def get_default_comfyui_path() -> Path:
    """Get default ComfyUI installation path"""
    # Check common locations
    possible_paths = [
        Path("/workspace/ComfyUI"),
        Path.home() / "ComfyUI",
        Path("/opt/ComfyUI"),
        Path.cwd().parent / "ComfyUI"
    ]
    
    for path in possible_paths:
        if path.exists() and (path / "models").exists():
            return path
    
    # Default to /workspace/ComfyUI
    return Path("/workspace/ComfyUI")
