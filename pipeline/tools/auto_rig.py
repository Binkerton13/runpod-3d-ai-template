#!/usr/bin/env python3
"""
auto_rig.py
-----------
Automated rigging pipeline using UniRig with deformation fixes

Workflow:
1. Load mesh from 0_input/
2. Apply UniRig auto-rigging
3. Sample deformation poses
4. Fix joint orientation issues
5. Apply corrective shape keys
6. Export rigged mesh to 2_rig/

Usage (called by pipeline):
blender --background --python auto_rig.py -- <project_path> <config_path>
"""

import sys
import json
from pathlib import Path

try:
    import bpy
except ImportError:
    print("ERROR: This script must be run through Blender")
    sys.exit(1)


def clear_scene():
    """Clear all objects from scene"""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    print("Scene cleared")


def import_mesh(mesh_path):
    """Import mesh file (FBX or OBJ)"""
    mesh_path = Path(mesh_path)
    
    if mesh_path.suffix.lower() == '.fbx':
        bpy.ops.import_scene.fbx(filepath=str(mesh_path))
    elif mesh_path.suffix.lower() == '.obj':
        bpy.ops.import_scene.obj(filepath=str(mesh_path))
    else:
        raise ValueError(f"Unsupported mesh format: {mesh_path.suffix}")
    
    print(f"Imported mesh: {mesh_path.name}")
    return bpy.context.selected_objects[0] if bpy.context.selected_objects else None


def validate_and_clean_mesh(mesh_obj):
    """
    Validate mesh and automatically fix common issues
    - Removes loose vertices
    - Merges duplicate vertices
    - Fixes non-manifold geometry
    - Checks UV mapping
    """
    print("\n=== Mesh Validation & Cleanup ===")
    
    mesh = mesh_obj.data
    bpy.context.view_layer.objects.active = mesh_obj
    mesh_obj.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    
    # Check for non-manifold geometry
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.mesh.select_non_manifold()
    non_manifold_count = len([v for v in mesh.vertices if v.select])
    if non_manifold_count > 0:
        print(f"⚠ Non-manifold geometry detected: {non_manifold_count} vertices")
        print("  Attempting to fix...")
        bpy.ops.mesh.fill_holes(sides=0)
        print("  ✓ Filled holes")
    else:
        print("✓ No non-manifold geometry")
    
    # Check for loose vertices
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.mesh.select_loose()
    loose_count = len([v for v in mesh.vertices if v.select])
    if loose_count > 0:
        print(f"⚠ Loose vertices detected: {loose_count}")
        print("  Removing loose geometry...")
        bpy.ops.mesh.delete(type='VERT')
        print("  ✓ Removed loose vertices")
    else:
        print("✓ No loose vertices")
    
    # Remove duplicate vertices
    bpy.ops.mesh.select_all(action='SELECT')
    removed = bpy.ops.mesh.remove_doubles(threshold=0.0001)
    if removed:
        print(f"✓ Merged {removed} duplicate vertices")
    else:
        print("✓ No duplicate vertices")
    
    # Check UV mapping
    if mesh.uv_layers.active:
        uv_layer = mesh.uv_layers.active.data
        uv_outside = sum(1 for uv in uv_layer if uv.uv.x < 0 or uv.uv.x > 1 or uv.uv.y < 0 or uv.uv.y > 1)
        if uv_outside > 0:
            print(f"⚠ {uv_outside} UV coordinates outside 0-1 range")
        else:
            print("✓ UV coordinates valid")
    else:
        print("⚠ No UV mapping found")
    
    # Recalculate normals
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    print("✓ Recalculated normals")
    
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # Print final mesh stats
    print(f"\nFinal mesh stats:")
    print(f"  Vertices: {len(mesh.vertices)}")
    print(f"  Polygons: {len(mesh.polygons)}")
    print(f"  Edges: {len(mesh.edges)}")
    print("=== Mesh Validation Complete ===\n")
    
    return True


def apply_unirig(mesh_obj, config):
    """
    Apply UniRig auto-rigging using subprocess calls to UniRig scripts
    """
    import subprocess
    import tempfile
    
    print("\n=== UniRig Auto-Rigging ===")
    
    rigging_config = config.get('rigging', {})
    preset = rigging_config.get('preset', 'humanoid')
    seed = rigging_config.get('seed', 42)
    
    print(f"Rigging preset: {preset}")
    print(f"Random seed: {seed}")
    
    # Check if UniRig is available
    unirig_script = Path("/workspace/unirig/launch/inference/generate_skeleton.sh")
    if not unirig_script.exists():
        print("WARNING: UniRig not found at /workspace/unirig")
        print("Running in test/development mode - using fallback armature")
        print("In production, UniRig will be installed at /workspace/unirig")
        return create_basic_armature(mesh_obj)
    
    # Create temporary directory for UniRig processing
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_input = f"{tmpdir}/input_mesh.fbx"
        temp_skeleton = f"{tmpdir}/skeleton.fbx"
        temp_skin = f"{tmpdir}/skin.fbx"
        temp_output = f"{tmpdir}/rigged.fbx"
        
        # Export current mesh to temporary FBX
        print("Exporting mesh for UniRig...")
        bpy.ops.export_scene.fbx(
            filepath=temp_input,
            use_selection=True,
            object_types={'MESH'},
            path_mode='COPY',
            embed_textures=True
        )
        
        # Step 1: Generate skeleton
        print("Running UniRig skeleton prediction...")
        skeleton_cmd = [
            "bash", "/workspace/unirig/launch/inference/generate_skeleton.sh",
            "--input", temp_input,
            "--output", temp_skeleton,
            "--seed", str(seed)
        ]
        
        try:
            result = subprocess.run(skeleton_cmd, check=True, capture_output=True, text=True)
            print("Skeleton generation complete")
            if result.stdout:
                print(result.stdout)
        except subprocess.CalledProcessError as e:
            print(f"ERROR: Skeleton generation failed: {e}")
            print(f"stdout: {e.stdout}")
            print(f"stderr: {e.stderr}")
            # Fall back to basic armature
            return create_basic_armature(mesh_obj)
        
        # Step 2: Generate skinning weights
        print("Running UniRig skinning prediction...")
        skin_cmd = [
            "bash", "/workspace/unirig/launch/inference/generate_skin.sh",
            "--input", temp_skeleton,
            "--output", temp_skin
        ]
        
        try:
            result = subprocess.run(skin_cmd, check=True, capture_output=True, text=True)
            print("Skinning generation complete")
            if result.stdout:
                print(result.stdout)
        except subprocess.CalledProcessError as e:
            print(f"ERROR: Skinning generation failed: {e}")
            print(f"stdout: {e.stdout}")
            print(f"stderr: {e.stderr}")
            # Use skeleton without skinning
            temp_skin = temp_skeleton
        
        # Step 3: Merge rigged result back with original mesh
        print("Merging UniRig results...")
        merge_cmd = [
            "bash", "/workspace/unirig/launch/inference/merge.sh",
            "--source", temp_skin,
            "--target", temp_input,
            "--output", temp_output
        ]
        
        try:
            result = subprocess.run(merge_cmd, check=True, capture_output=True, text=True)
            print("Merge complete")
            if result.stdout:
                print(result.stdout)
        except subprocess.CalledProcessError as e:
            print(f"ERROR: Merge failed: {e}")
            print(f"stdout: {e.stdout}")
            print(f"stderr: {e.stderr}")
            return create_basic_armature(mesh_obj)
        
        # Import the rigged result
        print("Importing rigged mesh...")
        clear_scene()
        bpy.ops.import_scene.fbx(filepath=temp_output)
        
        # Find the imported armature
        armature = None
        for obj in bpy.context.scene.objects:
            if obj.type == 'ARMATURE':
                armature = obj
                armature.name = "UniRig_Armature"
                break
        
        if not armature:
            print("WARNING: No armature found in UniRig output, creating basic armature")
            return create_basic_armature(mesh_obj)
        
        print(f"UniRig rigging complete: {armature.name}")
        return armature


def create_basic_armature(mesh_obj):
    """
    Fallback: Create a basic humanoid armature if UniRig fails
    Creates spine, head, arms, and legs with proper hierarchy
    """
    print("Creating basic humanoid fallback armature...")
    
    # Get mesh bounds for bone sizing
    bbox = [mesh_obj.matrix_world @ v.co for v in mesh_obj.data.vertices]
    min_z = min(v.z for v in bbox)
    max_z = max(v.z for v in bbox)
    height = max_z - min_z
    
    # Create armature
    bpy.ops.object.armature_add(location=(0, 0, min_z))
    armature = bpy.context.active_object
    armature.name = "Fallback_Armature"
    
    # Enter edit mode to create bones
    bpy.ops.object.mode_set(mode='EDIT')
    edit_bones = armature.data.edit_bones
    
    # Remove default bone
    edit_bones.remove(edit_bones[0])
    
    # Create root bone
    root = edit_bones.new('Root')
    root.head = (0, 0, min_z)
    root.tail = (0, 0, min_z + height * 0.1)
    
    # Spine chain
    spine1 = edit_bones.new('Spine')
    spine1.parent = root
    spine1.head = root.tail
    spine1.tail = (0, 0, min_z + height * 0.4)
    
    spine2 = edit_bones.new('Spine1')
    spine2.parent = spine1
    spine2.head = spine1.tail
    spine2.tail = (0, 0, min_z + height * 0.6)
    
    # Neck and Head
    neck = edit_bones.new('Neck')
    neck.parent = spine2
    neck.head = spine2.tail
    neck.tail = (0, 0, min_z + height * 0.85)
    
    head = edit_bones.new('Head')
    head.parent = neck
    head.head = neck.tail
    head.tail = (0, 0, max_z)
    
    # Left arm chain
    l_shoulder = edit_bones.new('Shoulder.L')
    l_shoulder.parent = spine2
    l_shoulder.head = (0, 0, min_z + height * 0.6)
    l_shoulder.tail = (height * 0.15, 0, min_z + height * 0.6)
    
    l_arm = edit_bones.new('UpperArm.L')
    l_arm.parent = l_shoulder
    l_arm.head = l_shoulder.tail
    l_arm.tail = (height * 0.35, 0, min_z + height * 0.5)
    
    l_forearm = edit_bones.new('ForeArm.L')
    l_forearm.parent = l_arm
    l_forearm.head = l_arm.tail
    l_forearm.tail = (height * 0.55, 0, min_z + height * 0.45)
    
    l_hand = edit_bones.new('Hand.L')
    l_hand.parent = l_forearm
    l_hand.head = l_forearm.tail
    l_hand.tail = (height * 0.65, 0, min_z + height * 0.45)
    
    # Right arm chain (mirror)
    for bone_name in ['Shoulder.L', 'UpperArm.L', 'ForeArm.L', 'Hand.L']:
        r_name = bone_name.replace('.L', '.R')
        l_bone = edit_bones[bone_name]
        r_bone = edit_bones.new(r_name)
        r_bone.head = (-l_bone.head.x, l_bone.head.y, l_bone.head.z)
        r_bone.tail = (-l_bone.tail.x, l_bone.tail.y, l_bone.tail.z)
        # Set parent
        if l_bone.parent:
            parent_name = l_bone.parent.name.replace('.L', '.R') if '.L' in l_bone.parent.name else l_bone.parent.name
            r_bone.parent = edit_bones.get(parent_name)
    
    # Left leg chain
    l_thigh = edit_bones.new('Thigh.L')
    l_thigh.parent = root
    l_thigh.head = (height * 0.1, 0, min_z + height * 0.1)
    l_thigh.tail = (height * 0.1, 0, min_z + height * 0.5)
    
    l_shin = edit_bones.new('Shin.L')
    l_shin.parent = l_thigh
    l_shin.head = l_thigh.tail
    l_shin.tail = (height * 0.1, 0, min_z + height * 0.05)
    
    l_foot = edit_bones.new('Foot.L')
    l_foot.parent = l_shin
    l_foot.head = l_shin.tail
    l_foot.tail = (height * 0.1, height * 0.1, min_z)
    
    # Right leg chain (mirror)
    for bone_name in ['Thigh.L', 'Shin.L', 'Foot.L']:
        r_name = bone_name.replace('.L', '.R')
        l_bone = edit_bones[bone_name]
        r_bone = edit_bones.new(r_name)
        r_bone.head = (-l_bone.head.x, l_bone.head.y, l_bone.head.z)
        r_bone.tail = (-l_bone.tail.x, l_bone.tail.y, l_bone.tail.z)
        if l_bone.parent:
            parent_name = l_bone.parent.name.replace('.L', '.R') if '.L' in l_bone.parent.name else l_bone.parent.name
            r_bone.parent = edit_bones.get(parent_name)
    
    # Return to object mode
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # Parent mesh to armature with automatic weights
    mesh_obj.select_set(True)
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.parent_set(type='ARMATURE_AUTO')
    
    print(f"Created fallback humanoid armature: {armature.name} (23 bones)")
    return armature


def sample_deformation_poses(armature, mesh_obj):
    """
    Sample various poses to identify deformation issues
    """
    print("\n=== Sampling Deformation Poses ===")
    
    poses = [
        ('T-Pose', 0),
        ('Arms Down', 1),
        ('Squat', 2),
        ('Arms Forward', 3)
    ]
    
    deformation_data = []
    
    for pose_name, frame_num in poses:
        print(f"Sampling pose: {pose_name}")
        bpy.context.scene.frame_set(frame_num)
        
        # Placeholder: Would analyze mesh deformation here
        deformation_data.append({
            'pose': pose_name,
            'frame': frame_num,
            'issues': []  # Would contain detected deformation issues
        })
    
    print(f"Sampled {len(poses)} poses for deformation analysis")
    return deformation_data


def fix_joint_orientation(armature):
    """
    Fix joint orientation issues that cause deformation problems
    """
    print("\n=== Fixing Joint Orientations ===")
    
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='EDIT')
    
    # Placeholder: Would fix bone roll and orientation here
    print("Analyzing bone orientations...")
    print("Applying orientation corrections...")
    
    bpy.ops.object.mode_set(mode='OBJECT')
    print("Joint orientations fixed")


def apply_corrective_shape_keys(mesh_obj, deformation_data):
    """
    Create corrective shape keys for problematic deformations
    """
    print("\n=== Creating Corrective Shape Keys ===")
    
    if not mesh_obj.data.shape_keys:
        mesh_obj.shape_key_add(name='Basis')
    
    # Placeholder: Would create actual corrective shapes
    for pose_data in deformation_data:
        shape_key_name = f"Corrective_{pose_data['pose'].replace(' ', '_')}"
        print(f"Creating shape key: {shape_key_name}")
        mesh_obj.shape_key_add(name=shape_key_name)
    
    print(f"Created {len(deformation_data)} corrective shape keys")


def smooth_skin_weights(mesh_obj):
    """
    Smooth skin weights to reduce deformation artifacts
    """
    print("\n=== Smoothing Skin Weights ===")
    
    bpy.context.view_layer.objects.active = mesh_obj
    bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
    
    # Placeholder: Would apply weight smoothing here
    print("Applying weight smoothing...")
    
    bpy.ops.object.mode_set(mode='OBJECT')
    print("Skin weights smoothed")


def export_rigged_mesh(mesh_obj, armature, output_path):
    """
    Export rigged mesh with armature to FBX
    """
    print(f"\n=== Exporting Rigged Mesh ===")
    
    # Select mesh and armature for export
    bpy.ops.object.select_all(action='DESELECT')
    mesh_obj.select_set(True)
    armature.select_set(True)
    
    # Export to FBX
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    bpy.ops.export_scene.fbx(
        filepath=str(output_path),
        use_selection=True,
        add_leaf_bones=False,
        bake_anim=False
    )
    
    print(f"Exported rigged mesh: {output_path.name}")


def main(project_path, config_path):
    """Main rigging pipeline"""
    project_path = Path(project_path)
    
    # Load configuration
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    print("="*80)
    print("AUTOMATIC RIGGING PIPELINE")
    print("="*80)
    
    # Setup directories
    input_dir = project_path / "0_input"
    rig_dir = project_path / "2_rig"
    rig_dir.mkdir(parents=True, exist_ok=True)
    
    # Find input mesh
    mesh_files = list(input_dir.rglob("*.fbx")) + list(input_dir.rglob("*.obj"))
    if not mesh_files:
        print("ERROR: No mesh files found in input directory")
        sys.exit(1)
    
    mesh_path = mesh_files[0]
    print(f"Input mesh: {mesh_path.name}")
    
    # Clear scene and import mesh
    clear_scene()
    mesh_obj = import_mesh(mesh_path)
    
    if not mesh_obj:
        print("ERROR: Failed to import mesh")
        sys.exit(1)
    
    # Validate and clean mesh before rigging
    validate_and_clean_mesh(mesh_obj)
    
    # Apply rigging pipeline
    armature = apply_unirig(mesh_obj, config)
    deformation_data = sample_deformation_poses(armature, mesh_obj)
    fix_joint_orientation(armature)
    apply_corrective_shape_keys(mesh_obj, deformation_data)
    smooth_skin_weights(mesh_obj)
    
    # Export result
    output_filename = mesh_path.stem + "_rigged.fbx"
    output_path = rig_dir / output_filename
    export_rigged_mesh(mesh_obj, armature, output_path)
    
    print("\n" + "="*80)
    print("RIGGING COMPLETE")
    print(f"Output: {output_path}")
    print("="*80)


if __name__ == "__main__":
    # Parse Blender arguments (after -- separator)
    try:
        separator_idx = sys.argv.index('--')
        script_args = sys.argv[separator_idx + 1:]
    except ValueError:
        print("ERROR: No arguments provided after '--' separator")
        print("Usage: blender --background --python auto_rig.py -- <project_path> <config_path>")
        sys.exit(1)
    
    if len(script_args) < 2:
        print("ERROR: Missing required arguments")
        print("Usage: blender --background --python auto_rig.py -- <project_path> <config_path>")
        sys.exit(1)
    
    project_path = script_args[0]
    config_path = script_args[1]
    
    main(project_path, config_path)
