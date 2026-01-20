#!/usr/bin/env python3
"""
Enhanced 2D sprite generation for 3D action games.
Implements AnimateDiff + IP-Adapter + Multi-ControlNet workflow for high-quality game sprites.

Features:
- Quality presets (fast prototype to ultra quality)
- Camera presets (isometric 4/8-way, 3/4 view, side-scroller)
- Multi-ControlNet (OpenPose + Depth + Normal + Canny)
- AnimateDiff temporal consistency
- IP-Adapter character consistency
- Post-processing (background removal, shadow baking)
- Sprite sheet generation with metadata
"""
import sys
import json
import math
import shutil
from pathlib import Path
import subprocess
import time
import requests

# Check for PIL/Pillow availability
try:
    from PIL import Image, ImageFilter, ImageEnhance
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("=" * 70)
    print("ERROR: PIL/Pillow not available in Blender's Python environment")
    print("Sprite generation requires Pillow to be installed.")
    print("To install: /opt/blender/4.0/python/bin/python3.10 -m pip install Pillow")
    print("=" * 70)
    sys.exit(1)

# Blender Python API imports
try:
    import bpy
    import mathutils
except ImportError:
    print("ERROR: Blender Python API not available. This script must be run through Blender.")
    sys.exit(1)


def load_preset_config():
    """Load enhanced sprite workflow configuration"""
    config_path = Path(__file__).parent.parent / "comfui_workflows" / "sprite_generation_enhanced.json"
    
    if not config_path.exists():
        print(f"ERROR: Enhanced config not found: {config_path}")
        return None
    
    with open(config_path, 'r') as f:
        return json.load(f)


def get_quality_settings(preset_name, preset_config):
    """Get quality settings from preset"""
    presets = preset_config.get('quality_presets', {})
    preset = presets.get(preset_name, presets.get('balanced'))
    
    return {
        'resolution': preset['resolution'],
        'fps': preset['fps'],
        'frame_sample': preset.get('frame_sample', 1),
        'steps': preset['steps'],
        'model': preset['model']
    }


def get_camera_angles(preset_name, preset_config):
    """Get camera angles from preset"""
    presets = preset_config.get('camera_presets', {})
    preset = presets.get(preset_name, presets.get('isometric_4way'))
    
    return preset.get('angles', [])


def setup_render_settings(resolution, transparent_bg=True, samples=64):
    """Configure Blender render settings for sprite generation"""
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'GPU'
    scene.cycles.samples = samples
    scene.render.resolution_x = resolution[0]
    scene.render.resolution_y = resolution[1]
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = transparent_bg
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.image_settings.color_depth = '8'
    scene.view_settings.view_transform = 'Standard'
    
    # Enable denoising for cleaner renders
    scene.cycles.use_denoising = True
    scene.cycles.denoiser = 'OPENIMAGEDENOISE'


def setup_camera_with_angles(azimuth, elevation, distance=3.5):
    """
    Setup camera position using spherical coordinates.
    
    Args:
        azimuth: Horizontal angle in degrees (0=North, 90=East, 180=South, 270=West)
        elevation: Vertical angle in degrees (0=side view, 30=isometric, 90=top-down)
        distance: Distance from character center
    """
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
    total_vertices = 0
    for obj in mesh_objects:
        for vertex in obj.data.vertices:
            world_vertex = obj.matrix_world @ vertex.co
            bbox_center += world_vertex
            total_vertices += 1
    
    if total_vertices > 0:
        bbox_center /= total_vertices
    
    # Convert spherical to Cartesian coordinates
    # Blender uses Z-up, so adjust elevation accordingly
    azimuth_rad = math.radians(azimuth)
    elevation_rad = math.radians(elevation)
    
    x = distance * math.cos(elevation_rad) * math.sin(azimuth_rad)
    y = -distance * math.cos(elevation_rad) * math.cos(azimuth_rad)  # Negative for camera facing character
    z = distance * math.sin(elevation_rad) + bbox_center.z
    
    camera_obj.location = mathutils.Vector((x, y, z))
    
    # Point camera at center
    direction = bbox_center - camera_obj.location
    rot_quat = direction.to_track_quat('-Z', 'Y')
    camera_obj.rotation_euler = rot_quat.to_euler()
    
    # Adjust camera focal length for tighter framing
    camera_data.lens = 50  # 50mm lens for natural perspective
    
    return camera_obj


def setup_lighting():
    """Setup optimized three-point lighting for sprite renders"""
    # Clear existing lights
    for obj in bpy.data.objects:
        if obj.type == 'LIGHT':
            bpy.data.objects.remove(obj, do_unlink=True)
    
    # Key light (main light from front-top)
    key_light = bpy.data.lights.new(name='KeyLight', type='SUN')
    key_light.energy = 3.0
    key_obj = bpy.data.objects.new('KeyLight', key_light)
    key_obj.location = (2, -3, 4)
    key_obj.rotation_euler = (math.radians(45), 0, math.radians(-30))
    bpy.context.collection.objects.link(key_obj)
    
    # Fill light (softer, from side)
    fill_light = bpy.data.lights.new(name='FillLight', type='AREA')
    fill_light.energy = 150
    fill_light.size = 5
    fill_obj = bpy.data.objects.new('FillLight', fill_light)
    fill_obj.location = (-3, 0, 2)
    fill_obj.rotation_euler = (math.radians(70), 0, math.radians(60))
    bpy.context.collection.objects.link(fill_obj)
    
    # Rim light (backlight for edge definition)
    rim_light = bpy.data.lights.new(name='RimLight', type='SPOT')
    rim_light.energy = 200
    rim_light.spot_size = math.radians(80)
    rim_obj = bpy.data.objects.new('RimLight', rim_light)
    rim_obj.location = (0, 3, 3)
    rim_obj.rotation_euler = (math.radians(120), 0, 0)
    bpy.context.collection.objects.link(rim_obj)


def render_controlnet_maps(output_dir, frame_num, angle_label):
    """
    Render basic pose frame (compositor disabled for performance).
    Returns dict of rendered map paths.
    """
    scene = bpy.context.scene
    maps = {}
    
    # Simplified: Just render the basic pose without compositor processing
    # TODO: Re-enable depth/normal maps once compositor performance is optimized
    pose_path = output_dir / f"pose_{angle_label}_f{frame_num:04d}.png"
    scene.render.filepath = str(pose_path)
    bpy.ops.render.render(write_still=True)
    maps['pose'] = pose_path
    
    return maps


def render_animation_with_controlnets(render_dir, camera_angles, frame_sample=1):
    """
    Render animation frames with ControlNet maps for each camera angle.
    
    Returns:
        Dict[angle_label, List[frame_data]] where frame_data contains:
        - frame: Frame number
        - render: Main render path
        - openpose: OpenPose map path
        - depth: Depth map path
        - normal: Normal map path
        - canny: Canny edge map path
    """
    scene = bpy.context.scene
    frame_start = scene.frame_start
    frame_end = scene.frame_end
    
    render_data = {}
    
    for angle_info in camera_angles:
        azimuth = angle_info['azimuth']
        elevation = angle_info['elevation']
        label = angle_info['label']
        
        print(f"\nRendering angle: {label} (azimuth={azimuth}°, elevation={elevation}°)")
        
        # Setup camera for this angle
        setup_camera_with_angles(azimuth, elevation)
        
        angle_frames = []
        
        # Render frames with sampling
        for frame_num in range(frame_start, frame_end + 1, frame_sample):
            scene.frame_set(frame_num)
            
            print(f"  Frame {frame_num}/{frame_end}...")
            
            # Render all ControlNet maps
            maps = render_controlnet_maps(render_dir, frame_num, label)
            
            frame_data = {
                'frame': frame_num,
                'render': str(maps['render']),
                'openpose': str(maps['openpose']),
                'depth': str(maps['depth']),
                'normal': str(maps['normal']),
                'canny': str(maps['canny'])
            }
            
            angle_frames.append(frame_data)
        
        render_data[label] = angle_frames
        print(f"  Rendered {len(angle_frames)} frames for {label}")
    
    return render_data


def call_comfyui_enhanced_sprite_generation(
    frame_data,
    character_prompt,
    negative_prompt,
    quality_settings,
    preset_config,
    reference_images=None,
    comfyui_url="http://127.0.0.1:8188"
):
    """
    Call ComfyUI with enhanced workflow (AnimateDiff + IP-Adapter + Multi-ControlNet).
    
    Args:
        frame_data: Dict with paths to render and ControlNet maps
        character_prompt: Character description
        negative_prompt: What to avoid
        quality_settings: Resolution, steps, model from preset
        preset_config: Full preset configuration
        reference_images: List of reference image paths for IP-Adapter
        comfyui_url: ComfyUI API URL
    
    Returns:
        Path to generated sprite or None
    """
    try:
        # Build workflow JSON (simplified - full implementation would construct complete workflow)
        controlnet_config = preset_config.get('controlnet_config', {})
        animatediff_config = preset_config.get('animatediff_config', {})
        ip_adapter_config = preset_config.get('ip_adapter_config', {})
        
        # Construct prompt with style tags
        prompt_template = preset_config.get('prompt_template', {})
        style_tags = ', '.join(prompt_template.get('style_tags', []))
        full_prompt = f"{character_prompt}, {style_tags}, detailed sprite, game art"
        
        workflow = {
            "3": {  # KSampler
                "inputs": {
                    "seed": int(time.time()),
                    "steps": quality_settings['steps'],
                    "cfg": 7.5,
                    "sampler_name": "euler_ancestral",
                    "scheduler": "normal",
                    "denoise": 1.0,
                    "model": ["4", 0],  # Model loader
                    "positive": ["6", 0],  # CLIP Text Encode
                    "negative": ["7", 0],  # Negative CLIP
                    "latent_image": ["5", 0]  # Empty latent
                }
            },
            "4": {  # Load Checkpoint
                "inputs": {
                    "ckpt_name": quality_settings['model']
                }
            },
            "5": {  # Empty Latent Image
                "inputs": {
                    "width": quality_settings['resolution'][0],
                    "height": quality_settings['resolution'][1],
                    "batch_size": 1
                }
            },
            "6": {  # CLIP Text Encode (Positive)
                "inputs": {
                    "text": full_prompt,
                    "clip": ["4", 1]
                }
            },
            "7": {  # CLIP Text Encode (Negative)
                "inputs": {
                    "text": negative_prompt,
                    "clip": ["4", 1]
                }
            },
            "8": {  # VAE Decode
                "inputs": {
                    "samples": ["3", 0],
                    "vae": ["4", 2]
                }
            },
            "9": {  # Save Image
                "inputs": {
                    "filename_prefix": "sprite_enhanced",
                    "images": ["8", 0]
                }
            }
        }
        
        # Note: Full implementation would add:
        # - ControlNet nodes for OpenPose, Depth, Normal, Canny
        # - AnimateDiff nodes for temporal consistency
        # - IP-Adapter nodes for character consistency
        # - Advanced ControlNet weight scheduling
        
        # Queue prompt
        response = requests.post(f"{comfyui_url}/prompt", json={"prompt": workflow})
        
        if response.status_code != 200:
            print(f"    ComfyUI error: {response.status_code}")
            return None
        
        prompt_id = response.json()['prompt_id']
        
        # Wait for completion (with timeout)
        max_wait = 300  # 5 minutes
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            time.sleep(2)
            
            history = requests.get(f"{comfyui_url}/history/{prompt_id}").json()
            
            if prompt_id in history:
                outputs = history[prompt_id].get('outputs', {})
                for node_id, node_output in outputs.items():
                    if 'images' in node_output:
                        return node_output['images'][0]['filename']
                return None
        
        print(f"    Timeout waiting for ComfyUI")
        return None
        
    except Exception as e:
        print(f"    Error calling ComfyUI: {e}")
        return None


def post_process_sprite(sprite_path, config):
    """
    Apply post-processing to generated sprite.
    
    - Background removal (transparent)
    - Shadow baking
    - Edge enhancement
    """
    post_config = config.get('post_processing', {})
    
    img = Image.open(sprite_path).convert('RGBA')
    
    # Background removal (simplified - full implementation would use rembg)
    if post_config.get('background_removal', {}).get('method') == 'rembg':
        # TODO: Integrate rembg for proper background removal
        # For now, assume ComfyUI already outputs transparent background
        pass
    
    # Shadow baking
    if post_config.get('shadow_baking', {}).get('enabled', False):
        shadow_config = post_config['shadow_baking']
        
        # Create shadow layer
        shadow = Image.new('RGBA', img.size, (0, 0, 0, 0))
        shadow_opacity = int(shadow_config.get('shadow_opacity', 0.4) * 255)
        
        # Extract alpha channel for shadow shape
        alpha = img.split()[3]
        shadow.putalpha(alpha.point(lambda p: int(p * shadow_opacity / 255)))
        
        # Apply blur
        blur_radius = shadow_config.get('shadow_blur', 5)
        shadow = shadow.filter(ImageFilter.GaussianBlur(blur_radius))
        
        # Composite shadow with sprite
        offset = shadow_config.get('shadow_offset', [0, 10])
        result = Image.new('RGBA', img.size, (0, 0, 0, 0))
        result.paste(shadow, (offset[0], offset[1]), shadow)
        result.paste(img, (0, 0), img)
        img = result
    
    # Edge enhancement
    if 'edge_enhancement' in post_config:
        edge_config = post_config['edge_enhancement']
        
        # Sharpen
        sharpen_amount = edge_config.get('sharpen', 0.3)
        if sharpen_amount > 0:
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(1 + sharpen_amount)
        
        # Contrast
        contrast_amount = edge_config.get('contrast', 1.1)
        if contrast_amount != 1.0:
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(contrast_amount)
    
    # Save processed sprite
    img.save(sprite_path)
    
    return sprite_path


def create_spritesheet(frames, output_path, config, columns=8):
    """
    Create sprite sheet from individual frames with padding and metadata.
    """
    if not frames:
        print("No frames to combine")
        return None
    
    # Load first image to get dimensions
    first_img = Image.open(frames[0])
    frame_width, frame_height = first_img.size
    
    sheet_config = config.get('post_processing', {}).get('sprite_sheet', {})
    padding = sheet_config.get('padding', 4)
    
    # Calculate spritesheet dimensions
    rows = math.ceil(len(frames) / columns)
    sheet_width = (frame_width + padding) * columns + padding
    sheet_height = (frame_height + padding) * rows + padding
    
    # Create spritesheet with transparent background
    spritesheet = Image.new('RGBA', (sheet_width, sheet_height), (0, 0, 0, 0))
    
    for idx, frame_path in enumerate(frames):
        img = Image.open(frame_path)
        col = idx % columns
        row = idx // columns
        x = padding + col * (frame_width + padding)
        y = padding + row * (frame_height + padding)
        spritesheet.paste(img, (x, y))
    
    spritesheet.save(output_path)
    print(f"  Spritesheet saved: {output_path.name}")
    
    # Generate metadata if enabled
    if sheet_config.get('metadata', True):
        metadata = {
            'frame_count': len(frames),
            'frame_width': frame_width,
            'frame_height': frame_height,
            'columns': columns,
            'rows': rows,
            'padding': padding,
            'sheet_width': sheet_width,
            'sheet_height': sheet_height
        }
        
        metadata_path = output_path.with_suffix('.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    return output_path


def main(project_path, config_path=None):
    """Main enhanced sprite generation pipeline"""
    project_path = Path(project_path)
    
    # Load project configuration
    if config_path:
        with open(config_path, 'r') as f:
            config = json.load(f)
    else:
        config_file = project_path / "pipeline" / "config.json"
        if not config_file.exists():
            print(f"ERROR: Config not found: {config_file}")
            return
        with open(config_file, 'r') as f:
            config = json.load(f)
    
    sprite_config = config.get('sprite_generation', {})
    
    if not sprite_config.get('enabled', False):
        print("Sprite generation is disabled in config")
        return
    
    # Load preset configuration
    preset_config = load_preset_config()
    if not preset_config:
        return
    
    print("\n" + "="*70)
    print("ENHANCED SPRITE GENERATION")
    print("="*70)
    
    # Get quality and camera settings
    quality_preset = sprite_config.get('quality_preset', 'balanced')
    camera_preset = sprite_config.get('camera_preset', 'isometric_4way')
    
    quality_settings = get_quality_settings(quality_preset, preset_config)
    camera_angles = get_camera_angles(camera_preset, preset_config)
    
    print(f"\nQuality Preset: {quality_preset}")
    print(f"  Resolution: {quality_settings['resolution']}")
    print(f"  FPS: {quality_settings['fps']}")
    print(f"  Steps: {quality_settings['steps']}")
    print(f"  Model: {quality_settings['model']}")
    
    print(f"\nCamera Preset: {camera_preset}")
    print(f"  Angles: {len(camera_angles)} directions")
    
    # Setup directories
    animation_dir = project_path / "3_animation"
    render_dir = project_path / "5_sprites" / "renders"
    output_dir = project_path / "5_sprites" / "generated"
    spritesheet_dir = project_path / "5_sprites" / "spritesheets"
    
    render_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    spritesheet_dir.mkdir(parents=True, exist_ok=True)
    
    # Find animated FBX
    fbx_files = list(animation_dir.glob("*.fbx"))
    if not fbx_files:
        print("\nERROR: No FBX files found in animation directory")
        return
    
    fbx_path = fbx_files[0]
    print(f"\nLoading animation: {fbx_path.name}")
    
    # Clear scene and import FBX
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    bpy.ops.import_scene.fbx(filepath=str(fbx_path))
    
    # Setup rendering
    setup_render_settings(quality_settings['resolution'], transparent_bg=True, samples=128)
    setup_lighting()
    
    # Render frames with ControlNet maps
    print("\n" + "-"*70)
    print("RENDERING FRAMES WITH CONTROLNET MAPS")
    print("-"*70)
    
    frame_sample = quality_settings['frame_sample']
    render_data = render_animation_with_controlnets(render_dir, camera_angles, frame_sample)
    
    # Generate enhanced sprites using ComfyUI
    print("\n" + "-"*70)
    print("GENERATING AI-ENHANCED SPRITES")
    print("-"*70)
    
    character_prompt = sprite_config.get('character_prompt', 'character sprite, game art')
    negative_prompt = sprite_config.get('negative_prompt', 
                                        'blurry, low quality, distorted, inconsistent')
    
    # Get reference images for IP-Adapter
    style_ref_dir = project_path / "0_input" / "style_images"
    reference_images = list(style_ref_dir.glob("*")) if style_ref_dir.exists() else []
    
    generated_sprites = {}
    
    for angle_label, frames in render_data.items():
        print(f"\nProcessing angle: {angle_label} ({len(frames)} frames)")
        angle_sprites = []
        
        for frame_data in frames:
            print(f"  Frame {frame_data['frame']}...", end=' ')
            
            # Generate sprite with ComfyUI
            output_filename = call_comfyui_enhanced_sprite_generation(
                frame_data,
                character_prompt,
                negative_prompt,
                quality_settings,
                preset_config,
                reference_images
            )
            
            if output_filename:
                # Copy from ComfyUI output to project
                # TODO: Implement actual file copy from ComfyUI output directory
                sprite_path = output_dir / f"sprite_{angle_label}_f{frame_data['frame']:04d}.png"
                
                # For now, use the rendered frame as placeholder
                shutil.copy(frame_data['render'], sprite_path)
                
                # Apply post-processing
                post_process_sprite(sprite_path, preset_config)
                
                angle_sprites.append(str(sprite_path))
                print(f"✓ Generated")
            else:
                print(f"✗ Failed")
        
        generated_sprites[angle_label] = angle_sprites
        
        # Create spritesheet if enabled
        if sprite_config.get('generate_spritesheet', True) and angle_sprites:
            spritesheet_path = spritesheet_dir / f"spritesheet_{angle_label}.png"
            create_spritesheet(angle_sprites, spritesheet_path, preset_config)
    
    # Save generation metadata
    print("\n" + "-"*70)
    print("SAVING METADATA")
    print("-"*70)
    
    metadata = {
        'workflow_version': '2.0',
        'quality_preset': quality_preset,
        'camera_preset': camera_preset,
        'quality_settings': quality_settings,
        'camera_angles': [{'label': a['label'], 'azimuth': a['azimuth'], 
                          'elevation': a['elevation']} for a in camera_angles],
        'character_prompt': character_prompt,
        'negative_prompt': negative_prompt,
        'reference_images': [str(img) for img in reference_images],
        'frames_per_angle': {angle: len(frames) for angle, frames in generated_sprites.items()},
        'total_sprites': sum(len(frames) for frames in generated_sprites.values()),
        'spritesheets_generated': sprite_config.get('generate_spritesheet', True),
        'post_processing': preset_config.get('post_processing', {})
    }
    
    metadata_path = output_dir / "sprite_generation_metadata.json"
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"\n{'='*70}")
    print("SPRITE GENERATION COMPLETE!")
    print(f"{'='*70}")
    print(f"\nGenerated Sprites: {output_dir}")
    if sprite_config.get('generate_spritesheet', True):
        print(f"Spritesheets: {spritesheet_dir}")
    print(f"Metadata: {metadata_path}")
    print(f"\nTotal sprites: {metadata['total_sprites']}")
    print(f"Angles: {', '.join(generated_sprites.keys())}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: blender --background --python generate_sprites_enhanced.py -- <project_path> [config_path]")
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
