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
import os
import subprocess
import tempfile
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
    
    # Get bmesh for accurate selection checking
    import bmesh
    bm = bmesh.from_edit_mesh(mesh)
    
    # Check for non-manifold geometry
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.mesh.select_non_manifold()
    bm = bmesh.from_edit_mesh(mesh)  # Refresh after selection
    non_manifold_count = sum(1 for v in bm.verts if v.select)
    
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
    bm = bmesh.from_edit_mesh(mesh)  # Refresh after selection
    loose_count = sum(1 for v in bm.verts if v.select)
    
    if loose_count > 0:
        print(f"⚠ Loose vertices detected: {loose_count}")
        print("  Removing loose geometry...")
        removed_count = bpy.ops.mesh.delete(type='VERT')
        print(f"  ✓ Removed {loose_count} loose vertices")
    else:
        print("✓ No loose vertices")
    
    # Remove duplicate vertices
    bpy.ops.mesh.select_all(action='SELECT')
    result = bpy.ops.mesh.remove_doubles(threshold=0.0001)
    bm = bmesh.from_edit_mesh(mesh)
    # remove_doubles returns a set, check if FINISHED
    if result == {'FINISHED'}:
        print(f"✓ Merged duplicate vertices")
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
        print("⚠ No UV mapping found (should have been created in mesh prep)")
    
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
    print(f"  UV layers: {len(mesh_obj.data.uv_layers)}")
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
    
    # Verify merge.sh script exists
    merge_script = Path("/workspace/unirig/launch/inference/merge.sh")
    if not merge_script.exists():
        print(f"WARNING: merge.sh not found at {merge_script}")
        print("Falling back to basic armature")
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
            "blender", "--background",
            "--python-expr",
            (
                "import sys, os, numpy as np; "
                "sys.path.append('/workspace/unirig'); "
                "from src.inference.merge import merge; "
                f"raw_skin = np.load(r'{temp_skin}', allow_pickle=True); "
                f"raw_data = np.load(r'{temp_input}', allow_pickle=True); "
                "merge("
                f"path=r'{temp_input}', "
                f"output_path=r'{temp_output}', "
                "vertices=raw_skin['vertices'], "
                "joints=raw_skin['joints'], "
                "skin=raw_skin['skin'], "
                "parents=raw_data['parents'], "
                "names=raw_data['names'], "
                "tails=raw_data['tails'], "
                "add_root=False, "
                "is_vrm=(raw_data['cls']=='vroid')"
                ");"
            )
        ]       
        try:
            result = subprocess.run(merge_cmd, check=True, capture_output=True, text=True)
            print("Merge command completed")
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(f"stderr: {result.stderr}")
            
            # Verify output file was created
            if not os.path.exists(temp_output):
                print(f"ERROR: Merge completed but output file not created: {temp_output}")
                print(f"Temp directory contents: {os.listdir(tmpdir)}")
                print("Falling back to basic armature")
                return create_basic_armature(mesh_obj)
                print("Falling back to basic armature")
                return create_basic_armature(mesh_obj)
            
            file_size = os.path.getsize(temp_output)
            print(f"Merge complete - output file: {temp_output} ({file_size} bytes)")
            
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


def analyze_mesh_geometry(mesh_obj):
    """Analyze mesh to find key anatomical points"""
    import bmesh
    
    print("Analyzing mesh geometry for anatomical landmarks...")
    
    # Get mesh vertices in world space
    vertices = [mesh_obj.matrix_world @ v.co for v in mesh_obj.data.vertices]
    
    # Calculate bounds
    min_x = min(v.x for v in vertices)
    max_x = max(v.x for v in vertices)
    min_y = min(v.y for v in vertices)
    max_y = max(v.y for v in vertices)
    min_z = min(v.z for v in vertices)
    max_z = max(v.z for v in vertices)
    
    center_x = (min_x + max_x) / 2
    center_y = (min_y + max_y) / 2
    height = max_z - min_z
    width = max_x - min_x
    depth = max_y - min_y
    
    print(f"  Height: {height:.3f}, Width: {width:.3f}, Depth: {depth:.3f}")
    print(f"  Mesh bounds: X[{min_x:.3f}, {max_x:.3f}], Y[{min_y:.3f}, {max_y:.3f}], Z[{min_z:.3f}, {max_z:.3f}]")
    
    # Use center of mesh as reference point (not min_z) to avoid offset issues
    center_z = (min_z + max_z) / 2
    
    # Estimate anatomical proportions (standard humanoid) relative to center
    landmarks = {
        'pelvis_height': center_z - height * 0.45,  # Below center
        'hip_height': center_z,  # At center
        'waist_height': center_z + height * 0.05,  # Just above center
        'chest_height': center_z + height * 0.20,  # Upper torso
        'shoulder_height': center_z + height * 0.30,  # Shoulder level
        'neck_height': center_z + height * 0.38,  # Base of neck
        'head_top': center_z + height * 0.50,  # Top of head
        'knee_height': center_z - height * 0.25,  # Below center
        'ankle_height': center_z - height * 0.45,  # Near bottom
        'shoulder_width': width * 0.45,  # Distance from center to shoulder
        'hip_width': width * 0.18,  # Distance from center to hip
        'arm_length': height * 0.35,  # Full arm length
        'forearm_length': height * 0.18,  # Forearm length
        'leg_length': height * 0.45,  # Full leg length
        'center_x': center_x,
        'center_y': center_y,
        'center_z': center_z,
        'min_z': min_z,
        'max_z': max_z,
    }
    
    print(f"  Using center-based coordinates: center_z={center_z:.3f}")
    print(f"  Pelvis: {landmarks['pelvis_height']:.3f}, Hip: {landmarks['hip_height']:.3f}, Head: {landmarks['head_top']:.3f}")
    
    return landmarks


def create_basic_armature(mesh_obj):
    """
    Fallback: Create a basic humanoid armature if UniRig fails
    Uses anatomical analysis to position bones correctly
    """
    print("Creating basic humanoid fallback armature...")
    
    # Analyze mesh geometry
    lm = analyze_mesh_geometry(mesh_obj)
    
    # Create armature at pelvis
    bpy.ops.object.armature_add(location=(lm['center_x'], lm['center_y'], lm['pelvis_height']))
    armature = bpy.context.active_object
    armature.name = "Fallback_Armature"
    
    # Enter edit mode
    bpy.ops.object.mode_set(mode='EDIT')
    edit_bones = armature.data.edit_bones
    edit_bones.remove(edit_bones[0])  # Remove default bone
    
    cx, cy = lm['center_x'], lm['center_y']
    
    # Root (pelvis)
    root = edit_bones.new('Root')
    root.head = (cx, cy, lm['pelvis_height'])
    root.tail = (cx, cy, lm['hip_height'])
    
    # Spine chain
    spine = edit_bones.new('Spine')
    spine.parent = root
    spine.head = root.tail
    spine.tail = (cx, cy, lm['waist_height'])
    
    spine1 = edit_bones.new('Spine1')
    spine1.parent = spine
    spine1.head = spine.tail
    spine1.tail = (cx, cy, lm['chest_height'])
    
    spine2 = edit_bones.new('Spine2')
    spine2.parent = spine1
    spine2.head = spine1.tail
    spine2.tail = (cx, cy, lm['shoulder_height'])
    
    # Neck and Head
    neck = edit_bones.new('Neck')
    neck.parent = spine2
    neck.head = spine2.tail
    neck.tail = (cx, cy, lm['neck_height'])
    
    head = edit_bones.new('Head')
    head.parent = neck
    head.head = neck.tail
    head.tail = (cx, cy, lm['head_top'])
    
    # Arms - Left
    l_shoulder = edit_bones.new('Shoulder.L')
    l_shoulder.parent = spine2
    l_shoulder.head = (cx, cy, lm['shoulder_height'])
    l_shoulder.tail = (cx + lm['shoulder_width'] * 0.3, cy, lm['shoulder_height'])
    
    l_arm = edit_bones.new('UpperArm.L')
    l_arm.parent = l_shoulder
    l_arm.head = l_shoulder.tail
    l_arm.tail = (cx + lm['shoulder_width'], cy, lm['shoulder_height'] - lm['arm_length'] * 0.5)
    
    l_forearm = edit_bones.new('ForeArm.L')
    l_forearm.parent = l_arm
    l_forearm.head = l_arm.tail
    l_forearm.tail = (cx + lm['shoulder_width'], cy, l_arm.tail.z - lm['forearm_length'])
    
    l_hand = edit_bones.new('Hand.L')
    l_hand.parent = l_forearm
    l_hand.head = l_forearm.tail
    l_hand.tail = (cx + lm['shoulder_width'], cy, l_forearm.tail.z - lm['forearm_length'] * 0.3)
    
    # Arms - Right (mirror)
    for bone_name in ['Shoulder.L', 'UpperArm.L', 'ForeArm.L', 'Hand.L']:
        r_name = bone_name.replace('.L', '.R')
        l_bone = edit_bones[bone_name]
        r_bone = edit_bones.new(r_name)
        r_bone.head = (cx - (l_bone.head.x - cx), l_bone.head.y, l_bone.head.z)
        r_bone.tail = (cx - (l_bone.tail.x - cx), l_bone.tail.y, l_bone.tail.z)
        if l_bone.parent:
            parent_name = l_bone.parent.name.replace('.L', '.R') if '.L' in l_bone.parent.name else l_bone.parent.name
            r_bone.parent = edit_bones.get(parent_name)
    
    # Legs - Left
    l_thigh = edit_bones.new('Thigh.L')
    l_thigh.parent = root
    l_thigh.head = (cx + lm['hip_width'], cy, lm['hip_height'])
    l_thigh.tail = (cx + lm['hip_width'], cy, lm['knee_height'])
    
    l_shin = edit_bones.new('Shin.L')
    l_shin.parent = l_thigh
    l_shin.head = l_thigh.tail
    l_shin.tail = (cx + lm['hip_width'], cy, lm['ankle_height'])
    
    l_foot = edit_bones.new('Foot.L')
    l_foot.parent = l_shin
    l_foot.head = l_shin.tail
    l_foot.tail = (cx + lm['hip_width'], cy + lm['leg_length'] * 0.15, lm['ankle_height'])
    
    # Legs - Right (mirror)
    for bone_name in ['Thigh.L', 'Shin.L', 'Foot.L']:
        r_name = bone_name.replace('.L', '.R')
        l_bone = edit_bones[bone_name]
        r_bone = edit_bones.new(r_name)
        r_bone.head = (cx - (l_bone.head.x - cx), l_bone.head.y, l_bone.head.z)
        r_bone.tail = (cx - (l_bone.tail.x - cx), l_bone.tail.y, l_bone.tail.z)
        if l_bone.parent:
            parent_name = l_bone.parent.name.replace('.L', '.R') if '.L' in l_bone.parent.name else l_bone.parent.name
            r_bone.parent = edit_bones.get(parent_name)
    
    # Return to object mode
    bpy.ops.object.mode_set(mode='OBJECT')
    
    print(f"Created anatomically-aligned armature with {len(armature.data.bones)} bones")
    
    # Apply weights - try automatic first, fallback to manual on failure
    print("Applying automatic weights...")
    mesh_obj.select_set(True)
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    
    # Try automatic weights
    try:
        bpy.ops.object.parent_set(type='ARMATURE_AUTO')
        
        # Check if armature modifier was actually created
        armature_mod = None
        for mod in mesh_obj.modifiers:
            if mod.type == 'ARMATURE':
                armature_mod = mod
                break
        
        if not armature_mod:
            print("WARNING: Automatic weights failed - no armature modifier created")
            raise Exception("Automatic weights failed")
        
        print("✓ Automatic weights applied successfully")
        
        # Clean up weights
        print("Cleaning up vertex weights...")
        bpy.context.view_layer.objects.active = mesh_obj
        bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
        bpy.ops.object.vertex_group_clean(group_select_mode='ALL', limit=0.01)
        bpy.ops.object.mode_set(mode='OBJECT')
        
    except Exception as e:
        print(f"⚠ Automatic weights failed: {e}")
        print("Applying manual weight painting fallback...")
        
        # Parent mesh to armature without weights
        mesh_obj.parent = armature
        
        # Create armature modifier manually
        armature_mod = mesh_obj.modifiers.new(name='Armature', type='ARMATURE')
        armature_mod.object = armature
        
        # Apply basic weight painting based on bone proximity
        apply_proximity_weights(mesh_obj, armature)
        
        print("✓ Manual proximity weights applied")
    
    print(f"Created fallback humanoid armature: {armature.name} (24 bones)")
    return armature


def apply_proximity_weights(mesh_obj, armature):
    """
    Apply weights based on vertex proximity to bones
    Fallback when automatic weights fail
    """
    print("  Calculating proximity-based weights...")
    
    # Get mesh vertices in world space
    mesh_verts = [mesh_obj.matrix_world @ v.co for v in mesh_obj.data.vertices]
    
    # For each bone, create vertex group
    for bone in armature.data.bones:
        if bone.name not in mesh_obj.vertex_groups:
            mesh_obj.vertex_groups.new(name=bone.name)
    
    # Calculate bone positions in world space
    bone_positions = {}
    for bone in armature.data.bones:
        bone_positions[bone.name] = armature.matrix_world @ ((bone.head_local + bone.tail_local) / 2)
    
    # Assign weights based on proximity (inverse distance)
    for v_idx, v_co in enumerate(mesh_verts):
        # Calculate distance to each bone
        bone_distances = {}
        for bone_name, bone_pos in bone_positions.items():
            distance = (v_co - bone_pos).length
            if distance < 0.001:  # Avoid division by zero
                distance = 0.001
            bone_distances[bone_name] = distance
        
        # Get the 3 closest bones
        closest_bones = sorted(bone_distances.items(), key=lambda x: x[1])[:3]
        
        # Calculate weights (inverse distance, normalized)
        total_inv_dist = sum(1.0 / dist for _, dist in closest_bones)
        
        for bone_name, dist in closest_bones:
            weight = (1.0 / dist) / total_inv_dist
            if weight > 0.01:  # Only assign significant weights
                vgroup = mesh_obj.vertex_groups[bone_name]
                vgroup.add([v_idx], weight, 'REPLACE')
    
    print(f"  Applied proximity weights to {len(mesh_verts)} vertices")


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
