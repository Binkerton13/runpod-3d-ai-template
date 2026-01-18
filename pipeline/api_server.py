#!/usr/bin/env python3
"""
api_server.py
-------------
Simple REST API server for pod-based project management.

Provides endpoints for:
- Creating new projects
- Listing existing projects
- Running pipeline operations

Usage:
    python pipeline/api_server.py
    
    # Or specify port
    python pipeline/api_server.py --port 8080
"""

import argparse
import json
import os
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory, send_file
from werkzeug.utils import secure_filename
from project_init import (
    init_project_with_name,
    rename_existing_project,
    validate_project_name
)
from model_manager import ModelManager, get_default_comfyui_path

app = Flask(__name__, static_folder=None, static_url_path=None)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size

# Configuration
WORKSPACE_ROOT = Path("/workspace")  # Default for pod
if not WORKSPACE_ROOT.exists():
    WORKSPACE_ROOT = Path.cwd().parent  # Fallback for local testing

WEB_UI_DIR = Path(__file__).parent / "web_ui"
UPLOAD_FOLDER = WEB_UI_DIR / "uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)

# Initialize Model Manager
COMFYUI_ROOT = get_default_comfyui_path()
model_manager = ModelManager(COMFYUI_ROOT)

ALLOWED_MESH_EXTENSIONS = {'.fbx', '.obj', '.glb', '.gltf'}
ALLOWED_IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.tiff', '.exr'}


def allowed_file(filename, allowed_extensions):
    return Path(filename).suffix.lower() in allowed_extensions


# ---------------------------------------------------------
# Web UI Routes
# ---------------------------------------------------------

@app.route("/")
def index():
    """Serve the main web UI"""
    return send_file(WEB_UI_DIR / "index.html")


@app.route("/static/<path:filename>")
def serve_static(filename):
    """Serve static files (CSS, JS)"""
    static_dir = str(WEB_UI_DIR / "static")
    print(f"Serving static file: {filename} from {static_dir}")
    return send_from_directory(static_dir, filename)


@app.route("/pipeline/hy_motion_prompts/<path:filename>")
def serve_pipeline_resources(filename):
    """Serve pipeline resource files (prompt library, etc.)"""
    pipeline_dir = str(Path(__file__).parent / "hy_motion_prompts")
    return send_from_directory(pipeline_dir, filename)


# ---------------------------------------------------------
# File Upload Routes
# ---------------------------------------------------------

@app.route("/api/upload", methods=["POST"])
def upload_file():
    """Upload files (mesh, UDIM tiles, references)"""
    try:
        if 'file' not in request.files:
            return jsonify({
                "status": "error",
                "message": "No file provided"
            }), 400
        
        file = request.files['file']
        file_type = request.form.get('type', 'unknown')
        project_name = request.form.get('project')
        
        if not project_name:
            return jsonify({
                "status": "error",
                "message": "Project name is required"
            }), 400
        
        project_path = WORKSPACE_ROOT / project_name
        if not project_path.exists():
            return jsonify({
                "status": "error",
                "message": f"Project '{project_name}' does not exist"
            }), 404
        
        if file.filename == '':
            return jsonify({
                "status": "error",
                "message": "No file selected"
            }), 400
        
        filename = secure_filename(file.filename)
        
        # Determine destination based on file type
        if file_type == 'mesh':
            if not allowed_file(filename, ALLOWED_MESH_EXTENSIONS):
                return jsonify({
                    "status": "error",
                    "message": "Invalid mesh file format"
                }), 400
            dest_folder = project_path / "0_input/meshes"
        elif file_type == 'udim':
            if not allowed_file(filename, ALLOWED_IMAGE_EXTENSIONS):
                return jsonify({
                    "status": "error",
                    "message": "Invalid image file format"
                }), 400
            dest_folder = project_path / "0_input/uv_layouts"
        elif file_type == 'style_reference':
            if not allowed_file(filename, ALLOWED_IMAGE_EXTENSIONS):
                return jsonify({
                    "status": "error",
                    "message": "Invalid image file format"
                }), 400
            dest_folder = project_path / "0_input/reference/style_images"
        elif file_type == 'pose_reference':
            if not allowed_file(filename, ALLOWED_IMAGE_EXTENSIONS):
                return jsonify({
                    "status": "error",
                    "message": "Invalid image file format"
                }), 400
            dest_folder = project_path / "0_input/reference/motion_reference"
        elif file_type == 'reference':
            # Fallback for legacy reference uploads
            if not allowed_file(filename, ALLOWED_IMAGE_EXTENSIONS):
                return jsonify({
                    "status": "error",
                    "message": "Invalid image file format"
                }), 400
            dest_folder = project_path / "0_input/reference"
        else:
            return jsonify({
                "status": "error",
                "message": "Invalid file type"
            }), 400
        
        dest_folder.mkdir(parents=True, exist_ok=True)
        dest_path = dest_folder / filename
        
        file.save(str(dest_path))
        
        return jsonify({
            "status": "success",
            "message": f"File uploaded: {filename}",
            "path": str(dest_path),
            "size": dest_path.stat().st_size
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route("/api/files/<project_name>/<file_type>", methods=["GET"])
def list_files(project_name, file_type):
    """List uploaded files for a project"""
    try:
        project_path = WORKSPACE_ROOT / project_name
        
        if file_type == 'mesh':
            folder = project_path / "0_input/meshes"
        elif file_type == 'udim':
            folder = project_path / "0_input/uv_layouts"
        elif file_type == 'style_reference':
            folder = project_path / "0_input/reference/style_images"
        elif file_type == 'pose_reference':
            folder = project_path / "0_input/reference/motion_reference"
        elif file_type == 'reference':
            folder = project_path / "0_input/reference"
        else:
            return jsonify({
                "status": "error",
                "message": "Invalid file type"
            }), 400
        
        if not folder.exists():
            return jsonify({
                "status": "success",
                "files": []
            })
        
        files = []
        for file_path in folder.iterdir():
            if file_path.is_file():
                files.append({
                    "name": file_path.name,
                    "size": file_path.stat().st_size,
                    "path": str(file_path)
                })
        
        return jsonify({
            "status": "success",
            "files": files
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


# ---------------------------------------------------------
# Pipeline Execution Routes
# ---------------------------------------------------------
# Moved to end of file before main()


# ---------------------------------------------------------
# API Endpoints (existing)
# ---------------------------------------------------------

@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "workspace": str(WORKSPACE_ROOT)
    })


@app.route("/api/projects", methods=["GET"])
def list_projects():
    """List all projects in workspace"""
    try:
        projects = []
        for item in WORKSPACE_ROOT.iterdir():
            if item.is_dir() and (item / "pipeline").exists():
                # Check if it's a valid project (has pipeline folder)
                projects.append({
                    "name": item.name,
                    "path": str(item),
                    "has_config": (item / "pipeline/config.json").exists()
                })
        
        return jsonify({
            "status": "success",
            "projects": projects,
            "count": len(projects)
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route("/api/projects/create", methods=["POST"])
def create_project():
    """Create a new project"""
    try:
        data = request.json
        project_name = data.get("project_name")
        
        if not project_name:
            return jsonify({
                "status": "error",
                "message": "project_name is required"
            }), 400
        
        # Validate project name
        is_valid, error_msg = validate_project_name(project_name)
        if not is_valid:
            return jsonify({
                "status": "error",
                "message": error_msg
            }), 400
        
        # Check if already exists
        project_path = WORKSPACE_ROOT / project_name
        if project_path.exists():
            return jsonify({
                "status": "error",
                "message": f"Project '{project_name}' already exists"
            }), 409
        
        # Create project
        project_root = init_project_with_name(WORKSPACE_ROOT, project_name)
        
        if project_root:
            return jsonify({
                "status": "success",
                "project_name": project_name,
                "project_path": str(project_root),
                "message": f"Project '{project_name}' created successfully"
            }), 201
        else:
            return jsonify({
                "status": "error",
                "message": "Failed to create project"
            }), 500
            
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route("/api/projects/<project_name>/rename", methods=["POST"])
def rename_project(project_name):
    """Rename an existing project"""
    try:
        data = request.json
        new_name = data.get("new_name")
        
        if not new_name:
            return jsonify({
                "status": "error",
                "message": "new_name is required"
            }), 400
        
        # Rename project
        new_path = rename_existing_project(WORKSPACE_ROOT, project_name, new_name)
        
        if new_path:
            return jsonify({
                "status": "success",
                "old_name": project_name,
                "new_name": new_name,
                "project_path": str(new_path),
                "message": f"Project renamed from '{project_name}' to '{new_name}'"
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Failed to rename project"
            }), 400
            
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route("/api/projects/<project_name>", methods=["GET"])
def get_project_info(project_name):
    """Get information about a specific project"""
    try:
        project_path = WORKSPACE_ROOT / project_name
        
        if not project_path.exists():
            return jsonify({
                "status": "error",
                "message": f"Project '{project_name}' not found"
            }), 404
        
        # Read config if available
        config_path = project_path / "pipeline/config.json"
        config = None
        if config_path.exists():
            config = json.loads(config_path.read_text())
        
        # Get folder structure info
        folders = {
            "input": (project_path / "0_input").exists(),
            "textures": (project_path / "1_textures").exists(),
            "rig": (project_path / "2_rig").exists(),
            "animation": (project_path / "3_animation").exists(),
            "export": (project_path / "4_export").exists(),
        }
        
        return jsonify({
            "status": "success",
            "project_name": project_name,
            "project_path": str(project_path),
            "config": config,
            "folders": folders
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route("/api/projects/<project_name>/config", methods=["GET", "PUT"])
def project_config(project_name):
    """Get or update project configuration"""
    try:
        config_path = WORKSPACE_ROOT / project_name / "pipeline/config.json"
        
        if not config_path.exists():
            return jsonify({
                "status": "error",
                "message": f"Config for project '{project_name}' not found"
            }), 404
        
        if request.method == "GET":
            config = json.loads(config_path.read_text())
            return jsonify({
                "status": "success",
                "config": config
            })
        
        elif request.method == "PUT":
            new_config = request.json
            config_path.write_text(json.dumps(new_config, indent=2))
            return jsonify({
                "status": "success",
                "message": "Configuration updated"
            })
            
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route("/api/projects/<project_name>/textures", methods=["GET"])
def get_project_textures(project_name):
    """Get generated texture file paths for a project"""
    try:
        project_path = WORKSPACE_ROOT / project_name
        if not project_path.exists():
            return jsonify({
                "status": "error",
                "message": f"Project '{project_name}' not found"
            }), 404
        
        textures_path = project_path / "1_textures"
        if not textures_path.exists():
            return jsonify({
                "status": "success",
                "textures": {}
            })
        
        # Look for common texture types
        texture_types = ['albedo', 'normal', 'roughness', 'metallic', 'ao']
        textures = {}
        
        for tex_type in texture_types:
            tex_folder = textures_path / tex_type
            if tex_folder.exists():
                # Get first image file in folder
                for ext in ['.png', '.jpg', '.jpeg', '.tif', '.tiff']:
                    files = list(tex_folder.glob(f'*{ext}'))
                    if files:
                        # Return relative path for web access
                        textures[tex_type] = f"/api/projects/{project_name}/texture-files/{tex_type}/{files[0].name}"
                        break
        
        return jsonify({
            "status": "success",
            "textures": textures
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route("/api/projects/<project_name>/texture-list", methods=["GET"])
def get_texture_file_list(project_name):
    """Get list of all generated texture files for viewing"""
    try:
        project_path = WORKSPACE_ROOT / project_name
        if not project_path.exists():
            return jsonify({
                "status": "error",
                "message": f"Project '{project_name}' not found"
            }), 404
        
        textures_path = project_path / "1_textures"
        if not textures_path.exists():
            return jsonify({
                "status": "success",
                "files": []
            })
        
        files = []
        texture_types = ['albedo', 'normal', 'roughness', 'metallic', 'ao']
        
        for tex_type in texture_types:
            tex_folder = textures_path / tex_type
            if tex_folder.exists():
                for ext in ['.png', '.jpg', '.jpeg', '.tif', '.tiff']:
                    for file in tex_folder.glob(f'*{ext}'):
                        files.append({
                            "name": f"{tex_type}/{file.name}",
                            "path": f"/api/projects/{project_name}/texture-files/{tex_type}/{file.name}",
                            "type": tex_type
                        })
        
        return jsonify({
            "status": "success",
            "files": files
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route("/api/projects/<project_name>/texture-files/<tex_type>/<filename>")
def serve_texture_file(project_name, tex_type, filename):
    """Serve generated texture files"""
    try:
        project_path = WORKSPACE_ROOT / project_name
        tex_folder = project_path / "1_textures" / tex_type
        return send_from_directory(str(tex_folder), filename)
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 404


# ---------------------------------------------------------
# Pipeline Execution Routes
# ---------------------------------------------------------

@app.route('/api/pipeline/run', methods=['POST'])
def run_pipeline():
    """Execute the pipeline for a project"""
    data = request.get_json()
    project_name = data.get('project_name')
    
    if not project_name:
        return jsonify({'error': 'Project name is required'}), 400
    
    project_path = WORKSPACE_ROOT / project_name
    if not project_path.exists():
        return jsonify({'error': 'Project not found'}), 404
    
    # Import and run pipeline orchestrator
    import subprocess
    import sys
    
    pipeline_script = Path(__file__).parent / "run_pipeline.py"
    
    try:
        # Run pipeline in background
        process = subprocess.Popen(
            [sys.executable, str(pipeline_script), str(project_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        return jsonify({
            'status': 'started',
            'project': project_name,
            'pid': process.pid,
            'message': 'Pipeline execution started'
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/pipeline/status/<project_name>', methods=['GET'])
def get_pipeline_status(project_name):
    """Get pipeline status for a project"""
    project_path = WORKSPACE_ROOT / project_name
    if not project_path.exists():
        return jsonify({'error': 'Project not found'}), 404
    
    # Import pipeline orchestrator
    from run_pipeline import PipelineOrchestrator
    
    try:
        orchestrator = PipelineOrchestrator(project_path)
        status = orchestrator.get_pipeline_status()
        
        return jsonify(status)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/pipeline/log/<project_name>', methods=['GET'])
def get_pipeline_log(project_name):
    """Get pipeline log for a project"""
    project_path = WORKSPACE_ROOT / project_name
    log_path = project_path / "pipeline" / "pipeline_log.txt"
    
    if not log_path.exists():
        return jsonify({'log': ''})
    
    try:
        with open(log_path, 'r') as f:
            log_content = f.read()
        
        # Get last N lines if requested
        lines = request.args.get('lines', type=int)
        if lines:
            log_lines = log_content.split('\n')
            log_content = '\n'.join(log_lines[-lines:])
        
        return jsonify({'log': log_content})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ---------------------------------------------------------
# Model Management Routes
# ---------------------------------------------------------

@app.route('/api/models/list', methods=['GET'])
def list_models():
    """List all available ComfyUI models"""
    try:
        model_type = request.args.get('type')
        
        if model_type:
            # List specific type
            models = model_manager.list_models(model_type)
            return jsonify({
                'type': model_type,
                'models': models,
                'count': len(models)
            })
        else:
            # List all types
            all_models = model_manager.list_all_models()
            total = sum(len(models) for models in all_models.values())
            
            return jsonify({
                'models': all_models,
                'total_count': total
            })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/models/upload', methods=['POST'])
def upload_model():
    """Upload a ComfyUI model file"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        model_type = request.form.get('type')
        
        if not model_type:
            return jsonify({'error': 'Model type is required'}), 400
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        filename = secure_filename(file.filename)
        
        # Validate file extension
        if not model_manager.validate_model_file(filename, model_type):
            valid_exts = model_manager.MODEL_EXTENSIONS.get(model_type, [])
            return jsonify({
                'error': f'Invalid file type for {model_type}. Expected: {", ".join(valid_exts)}'
            }), 400
        
        # Save file
        save_path = model_manager.get_model_save_path(filename, model_type)
        file.save(save_path)
        
        # Get file info
        model_info = model_manager.get_model_info(model_type, filename)
        
        return jsonify({
            'status': 'success',
            'message': f'Model uploaded: {filename}',
            'model': model_info
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/models/delete', methods=['POST'])
def delete_model():
    """Delete a ComfyUI model file"""
    try:
        data = request.get_json()
        model_type = data.get('type')
        filename = data.get('filename')
        
        if not model_type or not filename:
            return jsonify({'error': 'Model type and filename required'}), 400
        
        success = model_manager.delete_model(model_type, filename)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': f'Model deleted: {filename}'
            })
        else:
            return jsonify({'error': 'Model not found'}), 404
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/models/validate/<workflow_name>', methods=['GET'])
def validate_workflow_models(workflow_name):
    """Validate that all required models exist for a workflow"""
    try:
        validation = model_manager.validate_workflow_models(workflow_name)
        return jsonify(validation)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/models/selected/<workflow_name>', methods=['GET'])
def get_selected_models(workflow_name):
    """Get currently selected models for a workflow"""
    try:
        selected = model_manager.get_selected_models(workflow_name)
        
        # If no selections, try auto-select
        if not selected:
            selected = model_manager.auto_select_models(workflow_name)
        
        return jsonify({
            'workflow': workflow_name,
            'selected': selected
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/models/selected/<workflow_name>', methods=['POST'])
def set_selected_models(workflow_name):
    """Save model selections for a workflow"""
    try:
        data = request.get_json()
        model_selections = data.get('selections', {})
        
        model_manager.set_selected_models(workflow_name, model_selections)
        
        return jsonify({
            'status': 'success',
            'message': 'Model selections saved',
            'workflow': workflow_name,
            'selected': model_selections
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/models/auto-select/<workflow_name>', methods=['GET'])
def auto_select_models(workflow_name):
    """Auto-select models for a workflow"""
    try:
        selections = model_manager.auto_select_models(workflow_name)
        
        return jsonify({
            'workflow': workflow_name,
            'selected': selections
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/models/download/<model_type>/<filename>', methods=['GET'])
def download_model(model_type, filename):
    """Download a model file"""
    try:
        model_dir = model_manager.get_model_path(model_type)
        file_path = model_dir / filename
        
        if not file_path.exists():
            return jsonify({'error': 'Model not found'}), 404
        
        return send_file(file_path, as_attachment=True)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="3D Pipeline API Server")
    parser.add_argument(
        "--port",
        "-p",
        type=int,
        default=int(os.environ.get('PIPELINE_GUI_PORT', 7860)),
        help="Port to run server on (default: 7860, or PIPELINE_GUI_PORT env var)"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        default=None,
        help="Workspace root directory"
    )
    
    args = parser.parse_args()
    
    global WORKSPACE_ROOT
    if args.workspace:
        WORKSPACE_ROOT = args.workspace.resolve()
    
    print(f"\n=== 3D PIPELINE API SERVER ===")
    print(f"Workspace: {WORKSPACE_ROOT}")
    print(f"Starting server on {args.host}:{args.port}...\n")
    
    app.run(host=args.host, port=args.port, debug=False)


if __name__ == "__main__":
    main()

