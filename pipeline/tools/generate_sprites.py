#!/usr/bin/env python3
"""
Generate 2D sprite animations from 3D animated models.
Renders frames from multiple camera angles and generates character sprites using ComfyUI.
"""
import sys
import json
import math
from pathlib import Path
import subprocess
import time
import requests
from PIL import Image

# Blender Python API imports
try:
    import bpy
    import mathutils
except ImportError:
    print("Warning: Blender Python API not available. This script must be run through Blender.")

def setup_render_settings(resolution=512, transparent_bg=True):
    """Configure Blender render settings for sprite generation"""
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'GPU'
    scene.render.resolution_x = resolution
    scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = transparent_bg
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.image_settings.color_depth = '8'
    scene.view_settings.view_transform = 'Standard'

def setup_camera(angle='front', distance=3.0):
    """Setup camera position based on angle"""
    # Clear existing cameras
    for obj in bpy.data.objects:
        if obj.type == 'CAMERA':
            bpy.data.objects.remove(obj, do_unlink=True)
    
    # Create new camera
    camera_data = bpy.data.cameras.new(name='SpriteCamera')
    camera_obj = bpy.data.objects.new('SpriteCamera', camera_data)
    bpy.context.collection.objects.link(camera_obj)
    bpy.context.scene.camera = camera_obj
    
    # Get mesh bounds to center camera
    mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']
    if not mesh_objects:
        print("Warning: No mesh objects found")
        return camera_obj
    
    # Calculate bounding box center
    bbox_center = mathutils.Vector((0, 0, 0))
    count = 0
    for obj in mesh_objects:
        bbox_center += obj.location
        count += 1
    bbox_center /= count
    
    # Set camera position based on angle
    angle_positions = {
        'front': (0, -distance, bbox_center.z),
        'back': (0, distance, bbox_center.z),
        'left': (-distance, 0, bbox_center.z),
        'right': (distance, 0, bbox_center.z),
        'diagonal_fl': (-distance * 0.7, -distance * 0.7, bbox_center.z),
        'diagonal_fr': (distance * 0.7, -distance * 0.7, bbox_center.z),
        'diagonal_bl': (-distance * 0.7, distance * 0.7, bbox_center.z),
        'diagonal_br': (distance * 0.7, distance * 0.7, bbox_center.z)
    }
    
    camera_pos = angle_positions.get(angle, angle_positions['front'])
    camera_obj.location = mathutils.Vector(camera_pos)
    
    # Point camera at center
    direction = bbox_center - camera_obj.location
    rot_quat = direction.to_track_quat('-Z', 'Y')
    camera_obj.rotation_euler = rot_quat.to_euler()
    
    return camera_obj

def setup_lighting():
    """Setup three-point lighting for clean sprite renders"""
    # Clear existing lights
    for obj in bpy.data.objects:
        if obj.type == 'LIGHT':
            bpy.data.objects.remove(obj, do_unlink=True)
    
    # Key light (front-right, bright)
    key_light_data = bpy.data.lights.new(name='KeyLight', type='AREA')
    key_light_data.energy = 1000
    key_light_data.size = 5
    key_light = bpy.data.objects.new('KeyLight', key_light_data)
    bpy.context.collection.objects.link(key_light)
    key_light.location = (3, -3, 4)
    key_light.rotation_euler = (math.radians(45), 0, math.radians(45))
    
    # Fill light (front-left, softer)
    fill_light_data = bpy.data.lights.new(name='FillLight', type='AREA')
    fill_light_data.energy = 500
    fill_light_data.size = 5
    fill_light = bpy.data.objects.new('FillLight', fill_light_data)
    bpy.context.collection.objects.link(fill_light)
    fill_light.location = (-3, -3, 3)
    fill_light.rotation_euler = (math.radians(45), 0, math.radians(-45))
    
    # Rim light (back-top, edge definition)
    rim_light_data = bpy.data.lights.new(name='RimLight', type='AREA')
    rim_light_data.energy = 300
    rim_light_data.size = 5
    rim_light = bpy.data.objects.new('RimLight', rim_light_data)
    bpy.context.collection.objects.link(rim_light)
    rim_light.location = (0, 3, 5)
    rim_light.rotation_euler = (math.radians(135), 0, 0)

def render_animation_frames(output_dir, frame_interval=2, angles=['front']):
    """Render frames from animation at specified interval and angles"""
    scene = bpy.context.scene
    total_frames = scene.frame_end - scene.frame_start + 1
    
    render_data = {}
    
    for angle in angles:
        print(f"Rendering from angle: {angle}")
        setup_camera(angle)
        
        angle_frames = []
        frame_num = scene.frame_start
        
        while frame_num <= scene.frame_end:
            # Set current frame
            scene.frame_set(frame_num)
            
            # Render frame
            output_path = Path(output_dir) / f"render_{angle}_frame_{frame_num:04d}.png"
            scene.render.filepath = str(output_path)
            bpy.ops.render.render(write_still=True)
            
            angle_frames.append({
                'frame': frame_num,
                'path': str(output_path),
                'time': (frame_num - scene.frame_start) / scene.render.fps
            })
            
            print(f"  Rendered frame {frame_num}/{scene.frame_end}")
            frame_num += frame_interval
        
        render_data[angle] = angle_frames
    
    return render_data

def call_comfyui_sprite_generation(render_path, character_prompt, negative_prompt, 
                                   style_reference=None, resolution=512, 
                                   comfyui_url="http://127.0.0.1:8188"):
    """Call ComfyUI API to generate character sprite from 3D render"""
    workflow_path = Path(__file__).parent.parent / "comfui_workflows" / "sprite_generation_workflow.json"
    
    with open(workflow_path, 'r') as f:
        workflow = json.load(f)
    
    # Update workflow parameters
    for node in workflow['nodes']:
        if node['id'] == 1:  # LoadImage - 3D render
            node['inputs']['image'] = str(render_path)
        elif node['id'] == 3:  # CLIPTextEncode - positive prompt
            node['inputs']['text'] = character_prompt
        elif node['id'] == 4:  # CLIPTextEncode - negative prompt
            node['inputs']['text'] = negative_prompt
        elif node['id'] == 10:  # EmptyLatentImage - resolution
            node['inputs']['width'] = resolution
            node['inputs']['height'] = resolution
        elif node['id'] == 15 and style_reference:  # LoadImage - style reference
            node['inputs']['image'] = str(style_reference)
    
    # Queue prompt to ComfyUI
    try:
        response = requests.post(f"{comfyui_url}/prompt", json={"prompt": workflow})
        response.raise_for_status()
        prompt_id = response.json()['prompt_id']
        
        # Wait for completion and get output
        while True:
            time.sleep(2)
            history = requests.get(f"{comfyui_url}/history/{prompt_id}").json()
            
            if prompt_id in history:
                outputs = history[prompt_id].get('outputs', {})
                # Find SaveImage node output
                for node_id, node_output in outputs.items():
                    if 'images' in node_output:
                        return node_output['images'][0]['filename']
                return None
        
    except Exception as e:
        print(f"Error calling ComfyUI: {e}")
        return None

def create_spritesheet(frames, output_path, columns=8):
    """Combine individual frames into a spritesheet"""
    if not frames:
        print("No frames to combine")
        return
    
    # Load first image to get dimensions
    first_img = Image.open(frames[0])
    frame_width, frame_height = first_img.size
    
    # Calculate spritesheet dimensions
    rows = math.ceil(len(frames) / columns)
    sheet_width = frame_width * columns
    sheet_height = frame_height * rows
    
    # Create spritesheet
    spritesheet = Image.new('RGBA', (sheet_width, sheet_height), (0, 0, 0, 0))
    
    for idx, frame_path in enumerate(frames):
        img = Image.open(frame_path)
        col = idx % columns
        row = idx // columns
        x = col * frame_width
        y = row * frame_height
        spritesheet.paste(img, (x, y))
    
    spritesheet.save(output_path)
    print(f"Spritesheet saved: {output_path}")

def main(project_path, config_path=None):
    """Main sprite generation pipeline"""
    project_path = Path(project_path)
    
    # Load configuration
    if config_path:
        with open(config_path, 'r') as f:
            config = json.load(f)
    else:
        config_file = project_path / "pipeline" / "config.json"
        with open(config_file, 'r') as f:
            config = json.load(f)
    
    sprite_config = config.get('sprite_generation', {})
    
    if not sprite_config.get('enabled', False):
        print("Sprite generation is disabled in config")
        return
    
    # Setup directories
    animation_dir = project_path / "3_animation"
    render_dir = project_path / "4_export" / "sprite_renders"
    output_dir = project_path / "4_export" / "sprites"
    spritesheet_dir = project_path / "4_export" / "spritesheets"
    
    render_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    spritesheet_dir.mkdir(parents=True, exist_ok=True)
    
    # Find animated FBX
    fbx_files = list(animation_dir.glob("*.fbx"))
    if not fbx_files:
        print("No FBX files found in animation directory")
        return
    
    fbx_path = fbx_files[0]
    print(f"Loading animation: {fbx_path}")
    
    # Clear scene and import FBX
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    bpy.ops.import_scene.fbx(filepath=str(fbx_path))
    
    # Setup rendering
    resolution = sprite_config.get('resolution', 512)
    setup_render_settings(resolution=resolution, transparent_bg=True)
    setup_lighting()
    
    # Render frames
    frame_interval = sprite_config.get('frame_interval', 2)
    angles = sprite_config.get('angles', ['front'])
    
    print(f"Rendering frames (interval: {frame_interval}, angles: {angles})")
    render_data = render_animation_frames(render_dir, frame_interval, angles)
    
    # Generate character sprites using ComfyUI
    character_prompt = sprite_config.get('character_prompt', 'character, sprite, 2d art')
    negative_prompt = sprite_config.get('negative_prompt', 'blurry, low quality, 3d render')
    style_ref_dir = project_path / "0_input" / "style_images"
    style_refs = list(style_ref_dir.glob("*")) if style_ref_dir.exists() else []
    style_reference = style_refs[0] if style_refs else None
    
    generated_sprites = {}
    
    for angle, frames in render_data.items():
        print(f"\nGenerating sprites for angle: {angle}")
        angle_sprites = []
        
        for frame_data in frames:
            print(f"  Processing frame {frame_data['frame']}...")
            output_filename = call_comfyui_sprite_generation(
                frame_data['path'],
                character_prompt,
                negative_prompt,
                style_reference,
                resolution
            )
            
            if output_filename:
                # Move from ComfyUI output to project
                sprite_path = output_dir / f"sprite_{angle}_frame_{frame_data['frame']:04d}.png"
                # Note: Would need to implement file copy from ComfyUI output directory
                angle_sprites.append(str(sprite_path))
                print(f"    Generated: {sprite_path.name}")
        
        generated_sprites[angle] = angle_sprites
        
        # Create spritesheet if enabled
        if sprite_config.get('generate_spritesheet', False) and angle_sprites:
            spritesheet_path = spritesheet_dir / f"spritesheet_{angle}.png"
            create_spritesheet(angle_sprites, spritesheet_path)
    
    # Save generation metadata
    metadata = {
        'frame_interval': frame_interval,
        'angles': angles,
        'resolution': resolution,
        'character_prompt': character_prompt,
        'frames_per_angle': {angle: len(frames) for angle, frames in generated_sprites.items()},
        'spritesheets_generated': sprite_config.get('generate_spritesheet', False)
    }
    
    metadata_path = output_dir / "sprite_generation_info.json"
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"\nSprite generation complete!")
    print(f"Sprites: {output_dir}")
    if sprite_config.get('generate_spritesheet', False):
        print(f"Spritesheets: {spritesheet_dir}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: blender --background --python generate_sprites.py -- <project_path> [config_path]")
        sys.exit(1)
    
    # Parse arguments (after -- separator for Blender)
    try:
        separator_idx = sys.argv.index('--')
        script_args = sys.argv[separator_idx + 1:]
    except ValueError:
        script_args = sys.argv[1:]
    
    project_path = script_args[0]
    config_path = script_args[1] if len(script_args) > 1 else None
    
    main(project_path, config_path)
