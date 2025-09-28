#====================== BEGIN GPL LICENSE BLOCK ======================
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
#======================= END GPL LICENSE BLOCK ========================
#
# Updated to work with Blender 4.3+
# UI has collapsible sections and material reset functionality
# Popup panel with shortcut options
# Update options for Official and Unofficial githubs
# Reflections/reflective materials can now be set
# Holdouts for reflections
# Added Feather/Dilate controls for reflectors from Compify node tree
# Added Mesh Tools section with normals recalculation for footage geo
#
#
bl_info = {
    "name": "Compify",
    "version": (0, 2, 1),
    "author": "Nathan Vegdahl, Ian Hubert, mr. robot",
    "blender": (4, 0, 0),
    "description": "Do compositing in 3D space with selective reflections.",
    "location": "Scene properties",
    # "doc_url": "",
    "category": "Compositing",
}

import re
import math

import bpy

from .names import \
    compify_mat_name, \
    compify_baked_texture_name, \
    MAIN_NODE_NAME, \
    BAKE_IMAGE_NODE_NAME, \
    UV_LAYER_NAME
from .node_groups import \
    ensure_footage_group, \
    ensure_camera_project_group, \
    ensure_feathered_square_group
from .uv_utils import leftmost_u
from .camera_align import camera_align_register, camera_align_unregister
from .preferences import register_preferences, unregister_preferences


class BakerWithReflections:
    """Modified Baker that handles reflector materials and preserves holdouts"""
    def __init__(self):
        self.is_baking = False
        self.is_done = False
        self.proxy_objects = []
        self.reflector_objects = []
        self.holdout_objects = []  # Track holdout objects
        self.hide_render_list = {}
        self.main_nodes = {}  # Store multiple main nodes for different materials
        self.reflector_materials = {}  # Track reflector materials
        self.holdout_materials = {}  # Track holdout materials to preserve them

    def post(self, scene, context=None):
        self.is_baking = False
        self.is_done = True

    def cancelled(self, scene, context=None):
        self.is_baking = False
        self.is_done = True

    def execute(self, context):
        # Misc setup and checks.
        if context.scene.compify_config.geo_collection == None:
            return {'CANCELLED'}

        self.proxy_objects = list(context.scene.compify_config.geo_collection.objects)

        # Get reflector objects separately
        if context.scene.compify_config.reflectors_collection != None:
            self.reflector_objects = [obj for obj in context.scene.compify_config.reflectors_collection.objects
                                     if obj.type == 'MESH']

        # Get holdout objects separately - DON'T BAKE THEM
        if context.scene.compify_config.holdout_collection != None:
            self.holdout_objects = [obj for obj in context.scene.compify_config.holdout_collection.objects
                                   if obj.type == 'MESH']
            # Store their materials to preserve them
            for obj in self.holdout_objects:
                if obj.data.materials:
                    for mat in obj.data.materials:
                        if mat and "Compify_Reflection_Holdout" in mat.name:
                            self.holdout_materials[obj.name] = mat

        proxy_lights = []
        if context.scene.compify_config.lights_collection != None:
            proxy_lights = context.scene.compify_config.lights_collection.objects

        # Get the base material
        base_material = bpy.data.materials[compify_mat_name(context)]
        self.main_nodes[base_material.name] = base_material.node_tree.nodes[MAIN_NODE_NAME]

        # Handle reflector materials
        for obj in self.reflector_objects:
            if obj.data.materials:
                for mat in obj.data.materials:
                    if mat and "_Reflector_" in mat.name and MAIN_NODE_NAME in mat.node_tree.nodes:
                        self.reflector_materials[mat.name] = mat
                        self.main_nodes[mat.name] = mat.node_tree.nodes[MAIN_NODE_NAME]
                        print(f"Found reflector material {mat.name} for baking")

        # Set up bake image for base material
        delight_image_node = base_material.node_tree.nodes[BAKE_IMAGE_NODE_NAME]

        if len(self.proxy_objects) == 0:
            return {'CANCELLED'}

        # Ensure we have an image of the right resolution to bake to.
        bake_image_name = compify_baked_texture_name(context)
        bake_res = context.scene.compify_config.bake_image_res
        if bake_image_name in bpy.data.images \
        and bpy.data.images[bake_image_name].resolution[0] != bake_res:
            bpy.data.images.remove(bpy.data.images[bake_image_name])

        bake_image = None
        if bake_image_name in bpy.data.images:
            bake_image = bpy.data.images[bake_image_name]
        else:
            bake_image = bpy.data.images.new(
                bake_image_name,
                bake_res, bake_res,
                alpha=False,
                float_buffer=True,
                stereo3d=False,
                is_data=False,
                tiled=False,
            )
        delight_image_node.image = bake_image

        # Also set bake image for reflector materials
        for mat in self.reflector_materials.values():
            if BAKE_IMAGE_NODE_NAME in mat.node_tree.nodes:
                mat.node_tree.nodes[BAKE_IMAGE_NODE_NAME].image = bake_image
                print(f"Set bake image for reflector material {mat.name}")

        # Configure ALL materials for baking mode
        for mat_name, main_node in self.main_nodes.items():
            main_node.inputs["Do Bake"].default_value = 1.0
            main_node.inputs["Debug"].default_value = 0.0
            print(f"Set bake mode for material {mat_name}")

        # Set the base material's bake image node as active
        delight_image_node.select = True
        base_material.node_tree.nodes.active = delight_image_node

        # Deselect everything.
        for obj in context.scene.objects:
            obj.select_set(False)

        # Build a dictionary of the visibility of non-proxy objects so that
        # we can restore it afterwards. EXCLUDE holdouts from baking
        all_bake_objects = self.proxy_objects + self.reflector_objects  # NOT holdouts
        for obj in context.scene.objects:
            if obj not in all_bake_objects and obj.name not in proxy_lights:
                self.hide_render_list[obj.name] = obj.hide_render

        # Make all non-proxy objects invisible (INCLUDING holdouts during baking)
        for obj_name in self.hide_render_list:
            bpy.data.objects[obj_name].hide_render = True

        # Set up the baking job event handlers.
        bpy.app.handlers.object_bake_complete.append(self.post)
        bpy.app.handlers.object_bake_cancel.append(self.cancelled)

        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type == 'TIMER':
            if not self.is_baking and not self.is_done:
                self.is_baking = True

                # Select objects for baking (NOT including holdouts!)
                all_bake_objects = self.proxy_objects + self.reflector_objects
                for obj in all_bake_objects:
                    if obj.type == 'MESH':
                        obj.select_set(True)

                if len(all_bake_objects) > 0:
                    context.view_layer.objects.active = all_bake_objects[0]

                    # Do the bake.
                    bpy.ops.object.bake(
                        "INVOKE_DEFAULT",
                        type='DIFFUSE',
                        pass_filter={'DIRECT', 'INDIRECT', 'COLOR'},
                        margin=context.scene.compify_config.bake_uv_margin,
                        margin_type='EXTEND',
                        use_selected_to_active=False,
                        max_ray_distance=0.0,
                        cage_extrusion=0.0,
                        cage_object='',
                        normal_space='TANGENT',
                        normal_r='POS_X',
                        normal_g='POS_Y',
                        normal_b='POS_Z',
                        target='IMAGE_TEXTURES',
                        save_mode='INTERNAL',
                        use_clear=True,
                        use_cage=False,
                        use_split_materials=False,
                        use_automatic_name=False,
                        uv_layer='',
                    )
            elif self.is_done:
                # Clean up the handlers and timer.
                bpy.app.handlers.object_bake_complete.remove(self.post)
                bpy.app.handlers.object_bake_cancel.remove(self.cancelled)
                self._timer = None

                # Restore visibility of non-proxy objects.
                for obj_name in self.hide_render_list:
                    bpy.data.objects[obj_name].hide_render = self.hide_render_list[obj_name]
                self.hide_render_list = {}

                # Set ALL materials back to non-bake mode
                for mat_name, main_node in self.main_nodes.items():
                    main_node.inputs["Do Bake"].default_value = 0.0
                    print(f"Disabled bake mode for material {mat_name}")

                self.main_nodes = {}
                self.reflector_materials = {}
                self.holdout_materials = {}

                # Reset other self properties.
                self.is_baking = False
                self.is_done = False
                self.proxy_objects = []
                self.reflector_objects = []
                self.holdout_objects = []

                return {'FINISHED'}

        return {'PASS_THROUGH'}

    def reset(self):
        self.is_baking = False
        self.is_done = False


def update_reflection_holdout(self, context):
    obj = self.id_data
    if not obj:
        return

    if obj.compify_reflection.reflection_holdout:
        obj.visible_glossy = True
        if obj.type == 'LIGHT' and hasattr(obj.data, 'visible_glossy'):
            obj.data.visible_glossy = True

        if obj.type == 'MESH':
            apply_reflection_holdout_material(obj, context)
    else:
        if obj.type == 'MESH':
            remove_reflection_holdout_material(obj, context)


def update_reflector_material_properties(self, context):
    obj = self.id_data

    if not obj or obj.type != 'MESH' or not hasattr(obj, 'compify_reflection'):
        return

    compify_material = get_compify_material(context)
    if not compify_material:
        return

    reflector_material_name = f"{compify_material.name}_Reflector_{obj.name}"

    if reflector_material_name in bpy.data.materials:
        reflector_material = bpy.data.materials[reflector_material_name]

        blend_mode = context.scene.compify_config.reflection_blend_mode

        modify_compify_material_for_reflection(
            reflector_material,
            obj.compify_reflection.reflection_metallic,
            obj.compify_reflection.reflection_roughness,
            obj.compify_reflection.reflection_strength,
            blend_mode,
            obj
        )

        print(f"Auto-updated reflector material for {obj.name} (not active object)")


def update_reflection_visibility(self, context):
    obj = self.id_data
    if not obj:
        return

    if obj.type == 'MESH':
        obj.visible_glossy = obj.compify_reflection.visible_in_reflections
        print(f"Updated mesh {obj.name}: visible_glossy = {obj.compify_reflection.visible_in_reflections}")
    elif obj.type == 'LIGHT':
        obj.visible_glossy = obj.compify_reflection.visible_in_reflections
        if hasattr(obj.data, 'visible_glossy'):
            obj.data.visible_glossy = obj.compify_reflection.visible_in_reflections
        print(f"Updated light {obj.name}: visible_glossy = {obj.compify_reflection.visible_in_reflections}")
    elif obj.type in ['CURVE', 'SURFACE', 'META', 'FONT']:
        obj.visible_glossy = obj.compify_reflection.visible_in_reflections
        print(f"Updated {obj.type.lower()} {obj.name}: visible_glossy = {obj.compify_reflection.visible_in_reflections}")


def update_feather_dilate(self, context):
    """Update feather and dilate values for the selected reflector"""
    obj = self.id_data
    if not obj or obj.type != 'MESH':
        return

    # Find the reflector material
    reflector_material = None
    for mat in obj.data.materials:
        if mat and "_Reflector_" in mat.name:
            reflector_material = mat
            break

    if not reflector_material or not reflector_material.node_tree:
        return

    # Find the Feathered Square node
    for node in reflector_material.node_tree.nodes:
        if node.name == "Feathered Square" and node.type == 'GROUP':
            # Update the feather and dilate values
            if "Feather" in node.inputs:
                node.inputs["Feather"].default_value = obj.compify_reflection.feather
            if "Dilate" in node.inputs:
                node.inputs["Dilate"].default_value = obj.compify_reflection.dilate
            print(f"Updated Feather/Dilate for {obj.name}: F={obj.compify_reflection.feather}, D={obj.compify_reflection.dilate}")
            break


def change_footage_material_clip(config, context):
    if config.footage == None:
        return
    mat = get_compify_material(context)
    if mat != None:
        footage_node = mat.node_tree.nodes["Input Footage"]
        footage_node.image = config.footage
        footage_node.image_user.frame_duration = config.footage.frame_duration


def change_footage_camera(config, context):
    if config.camera == None or config.camera.type != 'CAMERA':
        return
    mat = get_compify_material(context)
    if mat != None:
        group = ensure_camera_project_group(config.camera)
        mat.node_tree.nodes["Camera Project"].node_tree = group


def get_footage_geo_objects_enum(self, context):
    """Generate enum items for objects in footage geo, reflective, and holdout collections"""
    items = [('NONE', "Select Object...", "Choose an object to edit", 'OBJECT_DATA', 0)]

    if not hasattr(context.scene, 'compify_config'):
        return items

    config = context.scene.compify_config

    # Collect all unique mesh objects from all three collections
    all_objects = {}  # Use dict to avoid duplicates

    # Add objects from Footage Geo collection
    if config.geo_collection:
        for obj in config.geo_collection.objects:
            if obj.type == 'MESH' and obj.name not in all_objects:
                all_objects[obj.name] = ('OUTLINER_OB_MESH', "Footage Geo")

    # Add objects from Reflective Geo collection
    if config.reflectors_collection:
        for obj in config.reflectors_collection.objects:
            if obj.type == 'MESH' and obj.name not in all_objects:
                all_objects[obj.name] = ('SHADING_RENDERED', "Reflective Geo")

    # Add objects from Holdout Geo collection
    if config.holdout_collection:
        for obj in config.holdout_collection.objects:
            if obj.type == 'MESH' and obj.name not in all_objects:
                all_objects[obj.name] = ('HOLDOUT_ON', "Holdout Geo")

    # Create enum items with collection indicators
    for i, (obj_name, (icon, collection_name)) in enumerate(sorted(all_objects.items())):
        description = f"Edit {obj_name} (from {collection_name})"
        items.append((obj_name, obj_name, description, icon, i + 1))

    return items



def apply_reflection_holdout_material(obj, context):
    """Apply a material that is COMPLETELY INVISIBLE to camera but occludes in reflections"""

    # Create holdout material name
    holdout_mat_name = f"Compify_Reflection_Holdout_{obj.name}"

    # Check if material already exists
    if holdout_mat_name in bpy.data.materials:
        holdout_mat = bpy.data.materials[holdout_mat_name]
        # Clear it to rebuild
        for node in holdout_mat.node_tree.nodes:
            holdout_mat.node_tree.nodes.remove(node)
    else:
        # Create new holdout material
        holdout_mat = bpy.data.materials.new(name=holdout_mat_name)
        holdout_mat.use_nodes = True

        # Clear default nodes
        for node in holdout_mat.node_tree.nodes:
            holdout_mat.node_tree.nodes.remove(node)

    # Create nodes for COMPLETE invisibility except in reflections
    output_node = holdout_mat.node_tree.nodes.new(type='ShaderNodeOutputMaterial')
    light_path = holdout_mat.node_tree.nodes.new(type='ShaderNodeLightPath')

    # FULLY TRANSPARENT for everything except reflections
    transparent_shader = holdout_mat.node_tree.nodes.new(type='ShaderNodeBsdfTransparent')
    transparent_shader.inputs['Color'].default_value = (1.0, 1.0, 1.0, 1.0)

    # BLACK shader for reflections only (occludes)
    black_shader = holdout_mat.node_tree.nodes.new(type='ShaderNodeBsdfDiffuse')
    black_shader.inputs['Color'].default_value = (0.0, 0.0, 0.0, 1.0)  # Pure black
    black_shader.inputs['Roughness'].default_value = 1.0  # No glossiness

    # Mix shader - switches based on ray type
    mix_shader = holdout_mat.node_tree.nodes.new(type='ShaderNodeMixShader')

    # Position nodes
    output_node.location = (600, 0)
    mix_shader.location = (400, 0)
    light_path.location = (0, 100)
    transparent_shader.location = (200, -100)
    black_shader.location = (200, 0)

    # Connect nodes
    # When Is Glossy Ray = 0 (not a reflection), use transparent (input 1)
    # When Is Glossy Ray = 1 (is a reflection), use black (input 2)
    holdout_mat.node_tree.links.new(light_path.outputs['Is Glossy Ray'], mix_shader.inputs['Fac'])
    holdout_mat.node_tree.links.new(transparent_shader.outputs['BSDF'], mix_shader.inputs[1])
    holdout_mat.node_tree.links.new(black_shader.outputs['BSDF'], mix_shader.inputs[2])
    holdout_mat.node_tree.links.new(mix_shader.outputs['Shader'], output_node.inputs['Surface'])

    # Set material blend mode for transparency (compatible with Blender 4.3-5.0)
    try:
        # Try Blender 4.x method first
        if hasattr(holdout_mat, 'blend_method'):
            holdout_mat.blend_method = 'BLEND'
        # Try Blender 5.x method
        elif hasattr(holdout_mat, 'surface'):
            if hasattr(holdout_mat.surface, 'render_method'):
                holdout_mat.surface.render_method = 'BLENDED'
    except AttributeError:
        pass

    # Set shadow mode (compatible with different Blender versions)
    try:
        if hasattr(holdout_mat, 'shadow_method'):
            holdout_mat.shadow_method = 'NONE'
        elif hasattr(holdout_mat, 'shadow_mode'):
            holdout_mat.shadow_mode = 'NONE'
    except AttributeError:
        pass

    # Handle backface culling settings
    try:
        if hasattr(holdout_mat, 'show_transparent_back'):
            holdout_mat.show_transparent_back = False
        if hasattr(holdout_mat, 'use_backface_culling'):
            holdout_mat.use_backface_culling = False
        elif hasattr(holdout_mat, 'backface_culling'):
            holdout_mat.backface_culling = 'OFF'
    except AttributeError:
        pass

    # Set Cycles-specific settings if available (with proper error handling)
    if hasattr(holdout_mat, 'cycles'):
        cycles_settings = holdout_mat.cycles
        # Only set attributes that actually exist
        if hasattr(cycles_settings, 'use_transparent_shadow'):
            cycles_settings.use_transparent_shadow = True
        # In Blender 5.0, transparent shadows might be handled differently
        # Check for other possible attributes
        if hasattr(cycles_settings, 'transparent_shadow'):
            cycles_settings.transparent_shadow = True

    # Apply the material to the object
    obj.data.materials.clear()
    obj.data.materials.append(holdout_mat)

    # Set object visibility properties
    obj.visible_camera = True  # Must be visible to camera (but shader makes it transparent)
    obj.visible_diffuse = True  # Visible to diffuse
    obj.visible_glossy = True  # MUST be visible to glossy to occlude reflections
    obj.visible_transmission = True  # Visible to transmission
    obj.visible_volume_scatter = False  # Not visible to volume
    obj.visible_shadow = False  # DON'T cast shadows

    # IMPORTANT: Make sure object is NOT a holdout at object level
    obj.is_holdout = False

    # If using Cycles, ensure proper ray visibility (with error handling)
    if hasattr(obj, 'cycles_visibility'):
        try:
            obj.cycles_visibility.camera = True  # Visible to camera (shader handles transparency)
            obj.cycles_visibility.diffuse = True
            obj.cycles_visibility.glossy = True  # Must be true to occlude
            obj.cycles_visibility.transmission = True
            obj.cycles_visibility.scatter = False
            obj.cycles_visibility.shadow = False  # No shadows from holdout
        except AttributeError as e:
            # Some attributes might not exist in newer versions
            print(f"Warning: Could not set some Cycles visibility settings: {e}")

    print(f"Applied invisible holdout material to {obj.name} - invisible to camera, occludes in reflections")


def setup_holdout_for_scene(context):
    """Ensure scene settings are correct for holdout materials to work"""
    scene = context.scene

    # Ensure Cycles is using proper transparency settings
    if scene.render.engine == 'CYCLES':
        # Enable transparency in film settings (with version compatibility)
        try:
            if hasattr(scene.cycles, 'film_transparent'):
                scene.cycles.film_transparent = True
            elif hasattr(scene.cycles, 'transparent'):
                scene.cycles.transparent = True
        except AttributeError:
            pass

        # Set proper transparency bounces (if the attribute exists)
        try:
            if hasattr(scene.cycles, 'transparent_max_bounces'):
                scene.cycles.transparent_max_bounces = max(scene.cycles.transparent_max_bounces, 8)
            elif hasattr(scene.cycles, 'max_transparent_bounces'):
                scene.cycles.max_transparent_bounces = max(scene.cycles.max_transparent_bounces, 8)
        except AttributeError:
            pass

    print("Scene configured for holdout transparency")


def remove_reflection_holdout_material(obj, context):
    """Remove holdout material from object"""

    holdout_mat_name = f"Compify_Reflection_Holdout_{obj.name}"

    # Check if object has the holdout material
    if obj.data.materials:
        for i, mat in enumerate(obj.data.materials):
            if mat and mat.name == holdout_mat_name:
                # Remove from object
                obj.data.materials.clear()

                # Delete the material if no other users
                if mat.users == 0:
                    bpy.data.materials.remove(mat)

                print(f"Removed reflection holdout material from {obj.name}")
                break


def get_compify_material(context):
    """Fetches the current scene's compify material if it exists."""
    name = compify_mat_name(context)
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    else:
        return None


def ensure_compify_material(context):
    """Ensures that the Compify Footage material exists for this scene."""
    mat = get_compify_material(context)
    if mat != None:
        return mat
    else:
        return create_compify_material(
            compify_mat_name(context),
            context.scene.compify_config.camera,
            context.scene.compify_config.footage,
        )


def create_compify_material(name, camera, footage):
    """Creates a Compify Footage material."""
    # Create a new completely empty node-based material.
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True

    # In Blender 4.3, 'shadow_method' and 'blend_method' attributes have changed
    try:
        mat.blend_method = 'HASHED'
    except (AttributeError, TypeError):
        # For Blender 4.3+
        if hasattr(mat, 'blend_mode'):
            mat.blend_mode = 'HASHED'

    try:
        mat.shadow_method = 'HASHED'
    except (AttributeError, TypeError):
        # For Blender 4.3+
        if hasattr(mat, 'shadow_mode'):
            mat.shadow_mode = 'HASHED'

    # Clear all existing nodes
    for node in mat.node_tree.nodes:
        mat.node_tree.nodes.remove(node)

    # Create the nodes.
    output = mat.node_tree.nodes.new(type='ShaderNodeOutputMaterial')
    camera_project = mat.node_tree.nodes.new(type='ShaderNodeGroup')
    baking_uv_map = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
    input_footage = mat.node_tree.nodes.new(type='ShaderNodeTexImage')
    feathered_square = mat.node_tree.nodes.new(type='ShaderNodeGroup')
    baked_lighting = mat.node_tree.nodes.new(type='ShaderNodeTexImage')
    compify_footage = mat.node_tree.nodes.new(type='ShaderNodeGroup')

    # Label and name the nodes.
    camera_project.label = "Camera Project"
    baking_uv_map.label = "Baking UV Map"
    input_footage.label = "Input Footage"
    feathered_square.label = "Feathered Square"
    baked_lighting.label = BAKE_IMAGE_NODE_NAME
    compify_footage.label = MAIN_NODE_NAME

    camera_project.name = "Camera Project"
    baking_uv_map.label = "Baking UV Map"
    input_footage.name = "Input Footage"
    feathered_square.name = "Feathered Square"
    baked_lighting.name = BAKE_IMAGE_NODE_NAME
    compify_footage.name = MAIN_NODE_NAME

    # Position the nodes.
    hs = 400.0
    x = 0.0

    camera_project.location = (x, 0.0)
    baking_uv_map.location = (x, -200.0)
    x += hs
    input_footage.location = (x, 400.0)
    feathered_square.location = (x, 0.0)
    baked_lighting.location = (x, -200.0)
    x += hs
    compify_footage.location = (x, 0.0)
    compify_footage.width = 200.0
    x += hs
    output.location = (x, 0.0)

    # Configure the nodes.
    camera_project.node_tree = ensure_camera_project_group(camera)
    if footage and hasattr(footage, 'size') and footage.size[0] > 0 and footage.size[1] > 0:
        camera_project.inputs['Aspect Ratio'].default_value = footage.size[0] / footage.size[1]
    else:
        # Default to the output render aspect ratio if we're on a bogus footage frame.
        render_x = bpy.context.scene.render.resolution_x * bpy.context.scene.render.pixel_aspect_x
        render_y = bpy.context.scene.render.resolution_y * bpy.context.scene.render.pixel_aspect_y
        camera_project.inputs['Aspect Ratio'].default_value = render_x / render_y

    baking_uv_map.uv_map = UV_LAYER_NAME

    input_footage.image = footage
    if hasattr(input_footage, 'interpolation'):
        input_footage.interpolation = 'Closest'
    else:
        try:
            input_footage.interpolation_type = 'Closest'
        except AttributeError:
            pass

    input_footage.projection = 'FLAT'
    input_footage.extension = 'EXTEND'

    if hasattr(input_footage, 'image_user') and footage:
        if hasattr(footage, 'frame_duration'):
            input_footage.image_user.frame_duration = footage.frame_duration
        input_footage.image_user.use_auto_refresh = True

    feathered_square.node_tree = ensure_feathered_square_group()
    feathered_square.inputs['Feather'].default_value = 0.05
    feathered_square.inputs['Dilate'].default_value = 0.0

    compify_footage.node_tree = ensure_footage_group()

    # Hook up the nodes.
    mat.node_tree.links.new(camera_project.outputs['Vector'], input_footage.inputs['Vector'])
    mat.node_tree.links.new(camera_project.outputs['Vector'], feathered_square.inputs['Vector'])
    mat.node_tree.links.new(baking_uv_map.outputs['UV'], baked_lighting.inputs['Vector'])
    mat.node_tree.links.new(input_footage.outputs['Color'], compify_footage.inputs['Footage'])
    mat.node_tree.links.new(feathered_square.outputs['Value'], compify_footage.inputs['Footage Alpha'])
    mat.node_tree.links.new(baked_lighting.outputs['Color'], compify_footage.inputs['Baked Lighting'])
    mat.node_tree.links.new(compify_footage.outputs['Shader'], output.inputs['Surface'])

    return mat


def setup_reflection_visibility(context):
    """ONLY objects in reflectees collection are visible in reflections + preserve holdouts"""
    scene = context.scene
    reflectees_collection = scene.compify_config.reflectees_collection
    holdout_collection = scene.compify_config.holdout_collection

    print("Setting up reflection visibility - ONLY selected objects reflect")

    # IMPORTANT: Hide world/environment from ALL reflections
    if scene.world:
        if hasattr(scene.world, 'cycles_visibility'):
            scene.world.cycles_visibility.glossy = False
            scene.world.cycles_visibility.transmission = False
            print("World/environment hidden from ALL reflections")

    # Set ALL objects to NOT be visible in reflections by default
    for obj in scene.objects:
        obj.visible_glossy = False
        if obj.type == 'LIGHT' and hasattr(obj.data, 'visible_glossy'):
            obj.data.visible_glossy = False
        print(f"Set {obj.name} to NOT reflect")

    # ONLY objects in reflectees collection are visible in reflections
    if reflectees_collection:
        print(f"Making ONLY these objects visible in reflections:")
        # Use .objects[:] to get a proper list instead of the collection view
        reflectee_objects = list(reflectees_collection.objects)
        for obj in reflectee_objects:
            try:
                obj.visible_glossy = True
                if obj.type == 'LIGHT' and hasattr(obj.data, 'visible_glossy'):
                    obj.data.visible_glossy = True
                print(f"  - {obj.name} WILL reflect")
            except Exception as e:
                print(f"Warning: Could not set reflection visibility for {obj.name}: {e}")

    # Re-enable glossy visibility for holdouts (they need to block reflections)
    if holdout_collection:
        print(f"Ensuring holdouts block reflections:")
        # Use .objects[:] to get a proper list instead of the collection view
        holdout_objects = list(holdout_collection.objects)
        for obj in holdout_objects:
            try:
                obj.visible_glossy = True  # Must be true to block reflections
                print(f"  - {obj.name} will BLOCK reflections (holdout)")
            except Exception as e:
                print(f"Warning: Could not set holdout visibility for {obj.name}: {e}")

    print("Reflection visibility setup complete!")


def modify_compify_material_for_reflection(material, reflection_metallic=0.0, reflection_roughness=0.0,
                                           reflection_strength=0.5, blend_mode='ADD', obj=None):
    """Add reflections to existing Compify material with enhanced roughness support"""
    if not material or not material.node_tree:
        return

    # Find required nodes
    compify_node = None
    output_node = None
    for node in material.node_tree.nodes:
        if node.name == MAIN_NODE_NAME:
            compify_node = node
        elif node.type == 'OUTPUT_MATERIAL':
            output_node = node

    if not compify_node or not output_node:
        return

    # Get roughness source from object if available
    roughness_source = 'VALUE'  # Default
    roughness_texture = None
    if obj and hasattr(obj, 'compify_reflection'):
        roughness_source = obj.compify_reflection.roughness_source
        roughness_texture = obj.compify_reflection.roughness_texture

    # Check if reflection nodes already exist and just update them
    has_valid_setup = True
    required_nodes = ["Compify_Reflection_Glossy", "Compify_Reflection_Strength",
                      "Compify_Reflection_Mix", "Compify_Blend_Reflections"]

    for node_name in required_nodes:
        if node_name not in material.node_tree.nodes:
            has_valid_setup = False
            break

    if has_valid_setup:
        # Just update the existing values
        print(f"Updating existing reflection nodes for {material.name}")

        glossy_bsdf = material.node_tree.nodes["Compify_Reflection_Glossy"]

        # Handle roughness based on source
        if roughness_source == 'VALUE':
            # Disconnect any roughness texture connections and use direct value
            for link in list(material.node_tree.links):
                if link.to_socket == glossy_bsdf.inputs['Roughness']:
                    material.node_tree.links.remove(link)
            glossy_bsdf.inputs['Roughness'].default_value = reflection_roughness
            # Don't remove texture nodes - user might switch back and want to keep their ColorRamp settings
        elif roughness_source == 'TEXTURE' and roughness_texture:
            setup_texture_roughness(material, glossy_bsdf, roughness_texture)
        elif roughness_source == 'COMPIFY':
            setup_compify_roughness(material, glossy_bsdf, compify_node)
        else:
            # Fallback to value
            for link in list(material.node_tree.links):
                if link.to_socket == glossy_bsdf.inputs['Roughness']:
                    material.node_tree.links.remove(link)
            glossy_bsdf.inputs['Roughness'].default_value = reflection_roughness

        # Update other settings
        if "Compify_Reflection_Metallic" in material.node_tree.nodes:
            metallic_node = material.node_tree.nodes["Compify_Reflection_Metallic"]
            metallic_node.inputs['Metallic'].default_value = reflection_metallic

        # Update strength via ColorRamp
        strength_node = material.node_tree.nodes["Compify_Reflection_Strength"]
        strength_node.color_ramp.elements[1].color = (reflection_strength, reflection_strength, reflection_strength, 1.0)

        # Update Mix RGB Fac to ensure it's always at 1.0
        mix_rgb = material.node_tree.nodes["Compify_Reflection_Mix"]
        mix_rgb.inputs['Fac'].default_value = 1.0

        print(f"Successfully updated reflection settings for {material.name}")
        return

    # If we get here, we need to create the reflection setup from scratch
    print(f"Creating new reflection setup for {material.name}")

    # Clean up any partial/broken reflection nodes first
    cleanup_reflection_nodes(material)

    # Create fresh reflection nodes
    create_reflection_nodes(material, compify_node, output_node, reflection_metallic,
                           reflection_roughness, reflection_strength, blend_mode,
                           roughness_source, roughness_texture, obj)

def setup_texture_roughness(material, glossy_bsdf, roughness_texture):
    """Set up texture-based roughness with ColorRamp remapping - PRESERVES existing ColorRamp"""

    # Check if texture and remap nodes already exist
    texture_node = None
    remap_node = None

    if "Compify_Texture_Roughness" in material.node_tree.nodes:
        texture_node = material.node_tree.nodes["Compify_Texture_Roughness"]

    if "Compify_Texture_Roughness_Remap" in material.node_tree.nodes:
        remap_node = material.node_tree.nodes["Compify_Texture_Roughness_Remap"]

    # Create texture node if it doesn't exist
    if not texture_node:
        texture_node = material.node_tree.nodes.new(type='ShaderNodeTexImage')
        texture_node.name = "Compify_Texture_Roughness"
        texture_node.location = (glossy_bsdf.location[0] - 600, glossy_bsdf.location[1] - 200)

    # Always update the texture reference
    texture_node.image = roughness_texture

    # Create ColorRamp node if it doesn't exist (PRESERVE if it does!)
    if not remap_node:
        remap_node = material.node_tree.nodes.new(type='ShaderNodeValToRGB')
        remap_node.name = "Compify_Texture_Roughness_Remap"
        remap_node.location = (glossy_bsdf.location[0] - 300, glossy_bsdf.location[1] - 200)

        # Set up default linear remap ONLY for new nodes
        remap_node.color_ramp.elements[0].position = 0.0
        remap_node.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
        remap_node.color_ramp.elements[1].position = 1.0
        remap_node.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)
        print(f"Created new texture roughness ColorRamp for {material.name}")
    else:
        print(f"Preserved existing texture roughness ColorRamp for {material.name}")

    # Ensure proper connections (may have been broken)
    # Remove any existing connections to the glossy roughness input first
    for link in list(material.node_tree.links):
        if link.to_socket == glossy_bsdf.inputs['Roughness']:
            material.node_tree.links.remove(link)

    # Connect: Texture -> ColorRamp -> Glossy Roughness
    material.node_tree.links.new(texture_node.outputs['Color'], remap_node.inputs['Fac'])
    material.node_tree.links.new(remap_node.outputs['Color'], glossy_bsdf.inputs['Roughness'])

def setup_compify_roughness(material, glossy_bsdf, compify_node):
    """Set up Compify footage-based roughness with ColorRamp remapping - PRESERVES existing ColorRamp"""

    # Check if remap node already exists
    remap_node = None
    if "Compify_Roughness_Remap" in material.node_tree.nodes:
        remap_node = material.node_tree.nodes["Compify_Roughness_Remap"]

    # Create ColorRamp node if it doesn't exist (PRESERVE if it does!)
    if not remap_node:
        remap_node = material.node_tree.nodes.new(type='ShaderNodeValToRGB')
        remap_node.name = "Compify_Roughness_Remap"
        remap_node.location = (glossy_bsdf.location[0] - 300, glossy_bsdf.location[1] - 200)

        # Set up default linear remap ONLY for new nodes
        remap_node.color_ramp.elements[0].position = 0.0
        remap_node.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
        remap_node.color_ramp.elements[1].position = 1.0
        remap_node.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)
        print(f"Created new Compify roughness ColorRamp for {material.name}")
    else:
        print(f"Preserved existing Compify roughness ColorRamp for {material.name}")

    # Find the footage input from the compify material
    footage_input = None
    for node in material.node_tree.nodes:
        if node.name == "Input Footage" and node.type == 'TEX_IMAGE':
            footage_input = node
            break

    if footage_input:
        # Remove any existing connections to the glossy roughness input first
        for link in list(material.node_tree.links):
            if link.to_socket == glossy_bsdf.inputs['Roughness']:
                material.node_tree.links.remove(link)

        # Connect: Compify Footage -> ColorRamp -> Glossy Roughness
        material.node_tree.links.new(footage_input.outputs['Color'], remap_node.inputs['Fac'])
        material.node_tree.links.new(remap_node.outputs['Color'], glossy_bsdf.inputs['Roughness'])
        print(f"Connected Compify footage roughness with preserved ColorRamp for {material.name}")
    else:
        print(f"Warning: Could not find footage input for Compify roughness in {material.name}")


def remove_roughness_texture_nodes(material):
    """Remove texture roughness nodes"""
    nodes_to_remove = ["Compify_Texture_Roughness", "Compify_Texture_Roughness_Remap"]
    for node_name in nodes_to_remove:
        if node_name in material.node_tree.nodes:
            material.node_tree.nodes.remove(material.node_tree.nodes[node_name])


def remove_compify_roughness_nodes(material):
    """Remove Compify roughness nodes"""
    nodes_to_remove = ["Compify_Roughness_Remap"]
    for node_name in nodes_to_remove:
        if node_name in material.node_tree.nodes:
            material.node_tree.nodes.remove(material.node_tree.nodes[node_name])


def cleanup_reflection_nodes(material):
    """Clean up any partial/broken reflection nodes"""
    reflection_node_names = ["Compify_Reflection_Glossy", "Compify_Reflection_Metallic",
                             "Compify_Reflection_Strength", "Compify_Reflection_Mix",
                             "Compify_Blend_Reflections", "Compify_Mix_Metallic",
                             "Compify_Add_Reflections", "Compify_Reflection_Strength_Mixer",
                             "Compify_Reflection_Transparent", "Compify_Reflection_Alpha_Mult",
                             "Compify_Texture_Roughness", "Compify_Texture_Roughness_Remap",
                             "Compify_Roughness_Remap"]

    for node_name in reflection_node_names:
        if node_name in material.node_tree.nodes:
            material.node_tree.nodes.remove(material.node_tree.nodes[node_name])
            print(f"Removed incomplete node: {node_name}")


def create_reflection_nodes(material, compify_node, output_node, reflection_metallic,
                           reflection_roughness, reflection_strength, blend_mode,
                           roughness_source='VALUE', roughness_texture=None, obj=None):
    """Create the reflection node setup with proper roughness handling"""

    # Create Glossy BSDF for reflections
    glossy_bsdf = material.node_tree.nodes.new(type='ShaderNodeBsdfGlossy')
    glossy_bsdf.name = "Compify_Reflection_Glossy"
    glossy_bsdf.inputs['Color'].default_value = (1.0, 1.0, 1.0, 1.0)
    glossy_bsdf.inputs['Roughness'].default_value = reflection_roughness

    # Create Principled BSDF for metallic reflections (optional)
    metallic_bsdf = None
    if reflection_metallic > 0:
        metallic_bsdf = material.node_tree.nodes.new(type='ShaderNodeBsdfPrincipled')
        metallic_bsdf.name = "Compify_Reflection_Metallic"
        metallic_bsdf.inputs['Base Color'].default_value = (1.0, 1.0, 1.0, 1.0)
        metallic_bsdf.inputs['Metallic'].default_value = reflection_metallic
        metallic_bsdf.inputs['Roughness'].default_value = reflection_roughness
        metallic_bsdf.inputs['IOR'].default_value = 1.45

    # Create ColorRamp to control reflection strength
    strength_ramp = material.node_tree.nodes.new(type='ShaderNodeValToRGB')
    strength_ramp.name = "Compify_Reflection_Strength"
    strength_ramp.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    strength_ramp.color_ramp.elements[1].color = (reflection_strength, reflection_strength, reflection_strength, 1.0)

    # Create Mix RGB to apply strength
    mix_rgb = material.node_tree.nodes.new(type='ShaderNodeMixRGB')
    mix_rgb.name = "Compify_Reflection_Mix"
    mix_rgb.blend_type = 'MULTIPLY'
    mix_rgb.inputs['Color1'].default_value = (1.0, 1.0, 1.0, 1.0)

    # Choose blend node based on mode
    if blend_mode == 'ADD':
        blend_shader = material.node_tree.nodes.new(type='ShaderNodeAddShader')
        blend_shader.name = "Compify_Blend_Reflections"
    else:  # MIX mode
        blend_shader = material.node_tree.nodes.new(type='ShaderNodeMixShader')
        blend_shader.name = "Compify_Blend_Reflections"
        blend_shader.inputs[0].default_value = reflection_strength

    # Position nodes
    output_x, output_y = output_node.location
    blend_shader.location = (output_x - 200, output_y)

    if metallic_bsdf:
        # Mix between glossy and metallic
        mix_shader = material.node_tree.nodes.new(type='ShaderNodeMixShader')
        mix_shader.name = "Compify_Mix_Metallic"
        mix_shader.location = (output_x - 400, output_y - 100)
        mix_shader.inputs[0].default_value = reflection_metallic

        glossy_bsdf.location = (output_x - 600, output_y - 50)
        metallic_bsdf.location = (output_x - 600, output_y - 150)
        mix_rgb.location = (output_x - 800, output_y - 100)
        strength_ramp.location = (output_x - 1000, output_y - 100)
    else:
        glossy_bsdf.location = (output_x - 400, output_y - 100)
        mix_rgb.location = (output_x - 600, output_y - 100)
        strength_ramp.location = (output_x - 800, output_y - 100)

    # Set up roughness based on source AFTER positioning
    if roughness_source == 'TEXTURE' and roughness_texture:
        setup_texture_roughness(material, glossy_bsdf, roughness_texture)
    elif roughness_source == 'COMPIFY':
        setup_compify_roughness(material, glossy_bsdf, compify_node)
    # else: default value-based roughness is already set

    # Disconnect existing connection
    for link in material.node_tree.links:
        if link.to_node == output_node and link.to_socket.name == 'Surface':
            material.node_tree.links.remove(link)
            break

    # Connect the nodes
    material.node_tree.links.new(strength_ramp.outputs['Color'], mix_rgb.inputs['Color2'])
    material.node_tree.links.new(mix_rgb.outputs['Color'], glossy_bsdf.inputs['Color'])

    if metallic_bsdf:
        # Mix glossy and metallic based on metallic value
        material.node_tree.links.new(glossy_bsdf.outputs['BSDF'], mix_shader.inputs[1])
        material.node_tree.links.new(metallic_bsdf.outputs['BSDF'], mix_shader.inputs[2])
        # Connect to blend shader
        material.node_tree.links.new(compify_node.outputs['Shader'], blend_shader.inputs[0])
        material.node_tree.links.new(mix_shader.outputs['Shader'], blend_shader.inputs[1])
    else:
        # Direct connection for glossy only
        material.node_tree.links.new(compify_node.outputs['Shader'], blend_shader.inputs[0])
        material.node_tree.links.new(glossy_bsdf.outputs['BSDF'], blend_shader.inputs[1])

    material.node_tree.links.new(blend_shader.outputs['Shader'], output_node.inputs['Surface'])

    print(f"Reflections added with {blend_mode} blending and {roughness_source} roughness")

def setup_reflector_materials(context):
    """Setup materials for reflector objects - PRESERVE HOLDOUTS"""
    scene = context.scene

    reflectors_collection = scene.compify_config.reflectors_collection
    holdout_collection = scene.compify_config.holdout_collection

    if not reflectors_collection:
        print("No reflectors collection found")
        return

    # Convert collection.objects to proper lists to avoid the bpy_prop_collection issue
    reflector_objects = list(reflectors_collection.objects)
    holdout_objects = list(holdout_collection.objects) if holdout_collection else []

    print(f"Setting up reflector materials for {len(reflector_objects)} objects")

    # Get the main compify material
    compify_material = get_compify_material(context)
    if not compify_material:
        print("No Compify material found - run Prep Scene first")
        return

    # Get global reflection settings
    global_roughness = scene.compify_config.reflection_roughness
    global_strength = scene.compify_config.reflection_strength
    global_blend_mode = scene.compify_config.reflection_blend_mode

    for obj in reflector_objects:
        if obj.type == 'MESH':
            print(f"Processing reflector object: {obj.name}")

            # SKIP if object is a holdout (using safer comparison)
            is_holdout = False
            for holdout_obj in holdout_objects:
                if obj.name == holdout_obj.name:
                    is_holdout = True
                    break

            if is_holdout:
                print(f"Skipping {obj.name} - it's a holdout")
                continue

            # Check if object has holdout material - if so, skip it
            has_holdout_mat = False
            if obj.data.materials:
                for mat in obj.data.materials:
                    if mat and "Compify_Reflection_Holdout" in mat.name:
                        has_holdout_mat = True
                        break

            if has_holdout_mat:
                print(f"Skipping {obj.name} - has holdout material")
                continue

            # Ensure the object has reflection properties
            if not hasattr(obj, 'compify_reflection'):
                print(f"Object {obj.name} missing reflection properties - skipping")
                continue

            # Set this object as a reflector
            obj.compify_reflection.is_reflector = True

            # Create a unique reflector material for this object
            reflector_material_name = f"{compify_material.name}_Reflector_{obj.name}"

            # Check if material already exists and is properly assigned
            reflector_material = None
            if reflector_material_name in bpy.data.materials:
                reflector_material = bpy.data.materials[reflector_material_name]
                print(f"Found existing reflector material: {reflector_material_name}")

                # Check if it's already assigned to the object
                material_assigned = False
                if obj.data.materials:
                    for mat in obj.data.materials:
                        if mat and mat.name == reflector_material_name:
                            material_assigned = True
                            break

                if not material_assigned:
                    # Material exists but not assigned - assign it
                    obj.data.materials.clear()
                    obj.data.materials.append(reflector_material)
                    print(f"Re-assigned existing reflector material to {obj.name}")
            else:
                print(f"Creating new reflector material: {reflector_material_name}")
                # Create a copy of the compify material
                reflector_material = compify_material.copy()
                reflector_material.name = reflector_material_name

                # Assign the new material
                obj.data.materials.clear()
                obj.data.materials.append(reflector_material)
                print(f"Assigned new reflector material to {obj.name}")

            # Use individual object settings if available, otherwise use global settings
            obj_roughness = obj.compify_reflection.reflection_roughness if obj.compify_reflection.reflection_roughness > 0 else global_roughness
            obj_strength = obj.compify_reflection.reflection_strength if obj.compify_reflection.reflection_strength > 0 else global_strength

            # Modify the material to add/update reflection capability
            print(f"Updating reflection nodes for {reflector_material.name}")
            modify_compify_material_for_reflection(
                reflector_material,
                obj.compify_reflection.reflection_metallic,
                obj_roughness,
                obj_strength,
                global_blend_mode
            )

            # Make sure the reflector is visible to everything
            obj.visible_camera = True
            obj.visible_diffuse = True
            obj.visible_glossy = True

            print(f"Successfully setup reflector: {obj.name}")


def safe_check_object_in_collection(obj, collection):
    """Safely check if an object is in a collection"""
    if not obj or not collection:
        return False

    try:
        # Convert to list first to avoid bpy_prop_collection issues
        collection_objects = list(collection.objects)
        for coll_obj in collection_objects:
            if obj.name == coll_obj.name:
                return True
        return False
    except Exception as e:
        print(f"Warning: Error checking collection membership for {obj.name if obj else 'None'}: {e}")
        return False


def get_reflector_objects_enum(self, context):
    """Generate enum items for reflector objects"""
    items = [('NONE', "Select Reflector Object...", "Choose an object to edit its reflection properties", 'OBJECT_DATA', 0)]

    if not hasattr(context.scene, 'compify_config'):
        return items

    config = context.scene.compify_config
    if not config.reflectors_collection:
        return items

    # Get all mesh objects from the reflectors collection
    reflector_objects = [obj for obj in config.reflectors_collection.objects if obj.type == 'MESH']

    for i, obj in enumerate(reflector_objects):
        # Check if object has reflector material
        has_reflector_mat = False
        if obj.data.materials:
            for mat in obj.data.materials:
                if mat and "_Reflector_" in mat.name:
                    has_reflector_mat = True
                    break

        icon = 'SHADING_RENDERED' if has_reflector_mat else 'MESH_DATA'
        description = f"Edit reflection properties for {obj.name}"
        if has_reflector_mat:
            description += " (Has reflector material)"
        else:
            description += " (Needs reflector material)"

        items.append((obj.name, obj.name, description, icon, i + 1))

    return items


class CompifyReflectionProperties(bpy.types.PropertyGroup):
    """Properties for controlling reflections on individual objects"""

    is_reflector: bpy.props.BoolProperty(
        name="Act as Reflector",
        description="This object will act as a reflective surface",
        default=False,
        update=update_reflector_material_properties
    )

    reflection_strength: bpy.props.FloatProperty(
        name="Reflection Strength",
        description="Strength of reflections on this surface",
        default=0.0,
        min=0.0,
        max=1.0,
        update=update_reflector_material_properties
    )

    reflection_roughness: bpy.props.FloatProperty(
        name="Reflection Roughness",
        description="Roughness of the reflective surface (0=mirror, 1=blurry)",
        default=0.0,
        min=0.0,
        max=1.0,
        update=update_reflector_material_properties
    )

    reflection_metallic: bpy.props.FloatProperty(
        name="Metallic",
        description="Metallic property of the reflective surface",
        default=0.0,
        min=0.0,
        max=1.0,
        update=update_reflector_material_properties
    )

    roughness_source: bpy.props.EnumProperty(
        name="Roughness Source",
        description="Source for roughness values",
        items=[
            ('VALUE', "Value", "Use the roughness slider value"),
            ('TEXTURE', "Texture", "Use a custom texture for roughness"),
            ('COMPIFY', "Compify Footage", "Use the Compify footage as roughness map")
        ],
        default='VALUE',
        update=update_reflector_material_properties
    )

    roughness_texture: bpy.props.PointerProperty(
        type=bpy.types.Image,
        name="Roughness Texture",
        description="Texture to use for roughness mapping",
        update=update_reflector_material_properties
    )

    roughness_remap_invert: bpy.props.BoolProperty(
        name="Invert Roughness",
        description="Invert the roughness values (dark=rough becomes dark=smooth)",
        default=False,
        update=update_reflector_material_properties
    )

    roughness_remap_contrast: bpy.props.FloatProperty(
        name="Roughness Contrast",
        description="Adjust contrast of the roughness map",
        default=1.0,
        min=0.0,
        max=5.0,
        update=update_reflector_material_properties
    )

    show_edge_controls: bpy.props.BoolProperty(
        name="Show Edge Controls",
        description="Toggle visibility of edge control settings",
        default=False
    )
    feather: bpy.props.FloatProperty(
        name="Feather",
        description="Feather amount for the footage edge",
        default=0.05,
        min=0.0,
        max=1.0,
        update=update_feather_dilate
    )

    dilate: bpy.props.FloatProperty(
        name="Dilate",
        description="Dilate/erode the footage edge",
        default=0.0,
        min=-0.1,
        max=0.1,
        update=update_feather_dilate
    )

    show_roughness_remap: bpy.props.BoolProperty(
        name="Show Roughness Remap",
        description="Show/hide roughness remapping controls",
        default=False
    )

    show_texture_roughness_remap: bpy.props.BoolProperty(
        name="Show Texture Roughness Remap",
        description="Show/hide texture roughness remapping controls",
        default=False
    )
    show_object_settings: bpy.props.BoolProperty(
        name="Show Object Settings",
        description="Toggle visibility of object reflection settings",
        default=True,
    )

    visible_in_reflections: bpy.props.BoolProperty(
        name="Visible in Reflections",
        description="This object will be visible in reflections",
        default=False,
        update=update_reflection_visibility
    )

    reflection_holdout: bpy.props.BoolProperty(
        name="Reflection Holdout",
        description="Object blocks reflections but doesn't appear in them (occlusion only)",
        default=False,
        update=update_reflection_holdout
    )


class CompifyFootageConfig(bpy.types.PropertyGroup):
    footage: bpy.props.PointerProperty(
        type=bpy.types.Image,
        name="Footage Texture",
        update=change_footage_material_clip,
    )
    camera: bpy.props.PointerProperty(
        type=bpy.types.Object,
        name="Footage Camera",
        poll=lambda scene, obj : obj.type == 'CAMERA',
        update=change_footage_camera,
    )
    geo_collection: bpy.props.PointerProperty(
        type=bpy.types.Collection,
        name="Footage Geo Collection",
    )
    lights_collection: bpy.props.PointerProperty(
        type=bpy.types.Collection,
        name="Footage Lights Collection",
    )
    reflectors_collection: bpy.props.PointerProperty(
        type=bpy.types.Collection,
        name="Reflective Geo Collection",
        description="Collection containing objects that act as reflective surfaces"
    )
    reflectees_collection: bpy.props.PointerProperty(
        type=bpy.types.Collection,
        name="Reflected Geo Collection",
        description="Collection containing objects that should be visible in reflections"
    )
    holdout_collection: bpy.props.PointerProperty(
        type=bpy.types.Collection,
        name="Holdout Geo Collection",
        description="Collection containing objects that block reflections but don't appear in them"
    )

    # Global reflection quality settings
    reflection_roughness: bpy.props.FloatProperty(
        name="Reflection Roughness",
        description="Global roughness for all reflections (0=mirror, 1=very blurry)",
        default=0.1,
        min=0.0,
        max=1.0
    )
    reflection_strength: bpy.props.FloatProperty(
        name="Reflection Strength",
        description="Global strength for all reflections",
        default=0.3,
        min=0.0,
        max=1.0
    )
    reflection_blend_mode: bpy.props.EnumProperty(
        name="Blend Mode",
        description="How reflections are blended with the base material",
        items=[
            ('ADD', "Add", "Add reflections on top (brighter)"),
            ('MIX', "Mix", "Mix reflections with base (more realistic)")
        ],
        default='ADD'
    )
    selected_reflector_object: bpy.props.PointerProperty(
        type=bpy.types.Object,
        name="Selected Reflector",
        description="Select a reflector object to edit its individual properties",
        poll=lambda self, obj: (
            obj.type == 'MESH' and
            hasattr(bpy.context.scene, 'compify_config') and
            bpy.context.scene.compify_config.reflectors_collection and
            obj in bpy.context.scene.compify_config.reflectors_collection.objects[:]
        )
    )

    selected_reflector_object_enum: bpy.props.EnumProperty(
        name="Select Reflector Object",
        description="Choose a reflector object to edit its properties",
        items=get_reflector_objects_enum,
        update=lambda self, context: update_selected_reflector(self, context)
    )

    # Mesh Tools properties
    selected_mesh_object_enum: bpy.props.EnumProperty(
        name="Select Mesh Object",
        description="Choose a mesh object from Footage Geo collection to edit",
        items=get_footage_geo_objects_enum
    )

    bake_uv_margin: bpy.props.IntProperty(
        name="Bake UV Margin",
        subtype='PIXEL',
        options=set(), # Not animatable.
        default=4,
        min=0,
        max=2**16,
        soft_max=32,
    )
    bake_image_res: bpy.props.IntProperty(
        name="Bake Resolution",
        subtype='PIXEL',
        options=set(), # Not animatable.
        default=1024,
        min=64,
        max=2**16,
        soft_max=8192,
    )

    # UI Collapse states
    show_footage_section: bpy.props.BoolProperty(
        name="Show Footage Section",
        default=True,
        description="Toggle footage section visibility"
    )
    show_collections_section: bpy.props.BoolProperty(
        name="Show Collections Section",
        default=True,
        description="Toggle collections section visibility"
    )
    show_reflections_section: bpy.props.BoolProperty(
        name="Show Reflections Section",
        default=False,
        description="Toggle reflections section visibility"
    )
    show_baking_section: bpy.props.BoolProperty(
        name="Show Baking Section",
        default=False,
        description="Toggle baking settings section visibility"
    )
    show_mesh_tools_section: bpy.props.BoolProperty(
        name="Show Mesh Tools Section",
        default=False,
        description="Toggle mesh tools section visibility"
    )

def update_selected_reflector(self, context):
    """Update the selected reflector object when enum changes"""
    if self.selected_reflector_object_enum == 'NONE':
        return

    # Find the object by name
    if self.selected_reflector_object_enum in bpy.data.objects:
        obj = bpy.data.objects[self.selected_reflector_object_enum]
        # Set it as the active object for easier editing
        context.view_layer.objects.active = obj
        # Also select it
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)


class CompifyMakeReflectiveAndSelect(bpy.types.Operator):
    """Make object reflective and automatically select it in the dropdown"""
    bl_idname = "scene.compify_make_reflective_and_select"
    bl_label = "Make Object Reflective and Select"
    bl_options = {'UNDO'}

    object_name: bpy.props.StringProperty()

    def execute(self, context):
        if self.object_name not in bpy.data.objects:
            self.report({'ERROR'}, f"Object {self.object_name} not found")
            return {'CANCELLED'}

        obj = bpy.data.objects[self.object_name]
        scene = context.scene
        config = scene.compify_config

        # Step 1: MOVE object to Reflective Geo collection (remove from others first)
        for coll in obj.users_collection:
            coll.objects.unlink(obj)

        # Create Reflective Geo collection if it doesn't exist
        if not config.reflectors_collection:
            collection = bpy.data.collections.new("Reflective Geo")

            # Add to the footage geo collection as a child if it exists
            geo_collection = config.geo_collection
            if geo_collection:
                geo_collection.children.link(collection)
            else:
                # If no footage geo collection, add to scene root
                context.scene.collection.children.link(collection)

            config.reflectors_collection = collection

        # Add to Reflective Geo collection
        config.reflectors_collection.objects.link(obj)

        # Step 2: Get or create base material
        base_material = ensure_compify_material(context)

        # Step 3: Create and apply reflector material
        reflector_material_name = f"{base_material.name}_Reflector_{obj.name}"

        # Remove old if exists
        if reflector_material_name in bpy.data.materials:
            old_mat = bpy.data.materials[reflector_material_name]
            bpy.data.materials.remove(old_mat)

        # Create new
        reflector_material = base_material.copy()
        reflector_material.name = reflector_material_name

        # Apply to object
        obj.data.materials.clear()
        obj.data.materials.append(reflector_material)

        # Step 4: Apply reflection with default settings
        modify_compify_material_for_reflection(
            reflector_material,
            0.0,  # metallic
            0.1,  # default roughness
            0.5,  # default strength
            'ADD'
        )

        # Step 5: Make visible
        obj.visible_camera = True
        obj.visible_diffuse = True
        obj.visible_glossy = True

        # Step 6: AUTOMATICALLY SELECT THE OBJECT IN THE DROPDOWN
        config.selected_reflector_object_enum = obj.name

        # Step 7: Also set it as active object for immediate editing
        context.view_layer.objects.active = obj
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)

        self.report({'INFO'}, f"{obj.name} made reflective and selected for editing")
        return {'FINISHED'}


class CompifyRecalculateNormals(bpy.types.Operator):
    """Recalculate normals for selected mesh object"""
    bl_idname = "scene.compify_recalculate_normals"
    bl_label = "Recalculate Normals"
    bl_options = {'UNDO'}

    inside: bpy.props.BoolProperty(
        name="Inside",
        description="Calculate normals pointing inward",
        default=False
    )

    object_name: bpy.props.StringProperty(
        name="Object Name",
        description="Name of the object to recalculate normals for",
        default=""
    )

    @classmethod
    def poll(cls, context):
        # Basic poll to ensure we're in object mode
        return context.mode == 'OBJECT'

    def execute(self, context):
        if not self.object_name:
            self.report({'ERROR'}, "No object name specified")
            return {'CANCELLED'}

        if self.object_name not in bpy.data.objects:
            self.report({'ERROR'}, f"Object '{self.object_name}' not found")
            return {'CANCELLED'}

        obj = bpy.data.objects[self.object_name]

        if obj.type != 'MESH':
            self.report({'ERROR'}, f"Object '{self.object_name}' is not a mesh")
            return {'CANCELLED'}

        # Store current state
        prev_active = context.view_layer.objects.active
        prev_selected = [o for o in context.selected_objects]
        prev_mode = context.mode

        try:
            # Clear selection and make target object active
            bpy.ops.object.select_all(action='DESELECT')
            context.view_layer.objects.active = obj
            obj.select_set(True)

            # Switch to edit mode
            bpy.ops.object.mode_set(mode='EDIT')

            # Select all geometry
            bpy.ops.mesh.select_all(action='SELECT')

            # Recalculate normals
            bpy.ops.mesh.normals_make_consistent(inside=self.inside)

            # Return to object mode
            bpy.ops.object.mode_set(mode='OBJECT')

        except Exception as e:
            self.report({'ERROR'}, f"Failed to recalculate normals: {str(e)}")
            # Try to return to object mode if we're stuck in edit mode
            try:
                bpy.ops.object.mode_set(mode='OBJECT')
            except:
                pass
            return {'CANCELLED'}

        finally:
            # Restore previous selection state
            bpy.ops.object.select_all(action='DESELECT')
            for o in prev_selected:
                if o.name in bpy.data.objects:
                    bpy.data.objects[o.name].select_set(True)
            if prev_active and prev_active.name in bpy.data.objects:
                context.view_layer.objects.active = prev_active

        direction = "inward" if self.inside else "outward"
        self.report({'INFO'}, f"Recalculated normals {direction} for {obj.name}")
        return {'FINISHED'}


class CompifyCameraPanel(bpy.types.Panel):
    """Configure cameras for 3D compositing."""
    bl_label = "Compify"
    bl_idname = "DATA_PT_compify_camera"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "data"

    @classmethod
    def poll(cls, context):
        return context.active_object.type == 'CAMERA'

    def draw(self, context):
        wm = context.window_manager
        layout = self.layout

        col = layout.column()
        col.operator("material.compify_camera_project_new")


class CompifyResetFeatherDilate(bpy.types.Operator):
    """Reset feather and dilate to default values"""
    bl_idname = "scene.compify_reset_feather_dilate"
    bl_label = "Reset Feather/Dilate"
    bl_options = {'UNDO'}

    object_name: bpy.props.StringProperty()

    def execute(self, context):
        if self.object_name not in bpy.data.objects:
            self.report({'ERROR'}, f"Object {self.object_name} not found")
            return {'CANCELLED'}

        obj = bpy.data.objects[self.object_name]

        # Reset to defaults
        obj.compify_reflection.reflection_feather = 0.05
        obj.compify_reflection.reflection_dilate = 0.0

        self.report({'INFO'}, f"Reset feather/dilate for {obj.name}")
        return {'FINISHED'}


class CompifyResetMaterial(bpy.types.Operator):
    """Reset the Compify material on the selected object"""
    bl_idname = "material.compify_reset_material"
    bl_label = "Reset Material"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        if not context.active_object or context.active_object.type != 'MESH':
            return False

        # Check if object has a compify-related material (including holdout materials)
        if context.active_object.data.materials:
            for mat in context.active_object.data.materials:
                if mat and (mat.name == compify_mat_name(context) or
                          "_Reflector_" in mat.name or
                          "Compify_Reflection_Holdout" in mat.name):  # Added holdout check
                    return True
        return False

    def invoke(self, context, event):
        # Show confirmation dialog
        return context.window_manager.invoke_confirm(self, event)

    def draw(self, context):
        layout = self.layout
        obj = context.active_object

        col = layout.column()
        col.label(text=f"Are you sure you want to reset the material on '{obj.name}'?", icon='ERROR')
        col.label(text="This will remove all Compify materials from this object.")
        col.separator()
        col.label(text="This action cannot be undone.", icon='INFO')

    def execute(self, context):
        obj = context.active_object

        materials_to_remove = []

        if obj.data.materials:
            for mat in obj.data.materials:
                if mat:
                    # Include holdout materials in the removal
                    if ("_Reflector_" in mat.name or
                        mat.name == compify_mat_name(context) or
                        "Compify_Reflection_Holdout" in mat.name):
                        materials_to_remove.append(mat)

        # Clear all materials from the object
        obj.data.materials.clear()

        # Delete the material data blocks if no other users
        for mat in materials_to_remove:
            if mat.users == 0:
                mat_name = mat.name
                bpy.data.materials.remove(mat)
                print(f"Deleted material: {mat_name}")

        # Reset holdout properties if they exist
        if hasattr(obj, 'compify_reflection'):
            obj.compify_reflection.reflection_holdout = False

        # Reset visibility settings that might have been modified for holdouts
        obj.visible_camera = True
        obj.visible_diffuse = True
        obj.visible_glossy = True
        obj.visible_transmission = True
        obj.visible_volume_scatter = True
        obj.visible_shadow = True
        obj.is_holdout = False

        self.report({'INFO'}, f"Cleared all Compify materials from {obj.name}")

        return {'FINISHED'}


class CompifyPrepScene(bpy.types.Operator):
    """Prepares the scene for compification"""
    bl_idname = "material.compify_prep_scene"
    bl_label = "Prep Scene"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' \
            and context.scene.compify_config.footage != None \
            and context.scene.compify_config.camera != None \
            and context.scene.compify_config.geo_collection != None \
            and len(context.scene.compify_config.geo_collection.all_objects) > 0

    def execute(self, context):
        proxy_collection = context.scene.compify_config.geo_collection
        lights_collection = context.scene.compify_config.lights_collection
        reflectors_collection = context.scene.compify_config.reflectors_collection
        holdout_collection = context.scene.compify_config.holdout_collection

        try:
            material = ensure_compify_material(context)
        except Exception as e:
            self.report({'ERROR'}, f"Failed to create material: {str(e)}")
            return {'CANCELLED'}

        # Process ONLY proxy objects for base material application
        proxy_objects = list(proxy_collection.all_objects)

        # Process reflectors separately - they need special handling
        reflector_objects = []
        if reflectors_collection:
            reflector_objects = [obj for obj in reflectors_collection.all_objects if obj.type == 'MESH']

        # Track holdout objects separately - DON'T apply base material to them
        holdout_objects = []
        holdout_materials_to_preserve = {}
        if holdout_collection:
            holdout_objects = [obj for obj in holdout_collection.all_objects if obj.type == 'MESH']
            # Store their holdout materials to preserve them
            for obj in holdout_objects:
                if obj.data.materials:
                    for mat in obj.data.materials:
                        if mat and "Compify_Reflection_Holdout" in mat.name:
                            holdout_materials_to_preserve[obj.name] = mat

        # Combine for UV processing but keep track of which is which
        all_geo_objects = proxy_objects + reflector_objects + holdout_objects

        if len(all_geo_objects) == 0:
            self.report({'ERROR'}, "No geometry objects found for processing")
            return {'CANCELLED'}

        # Deselect all objects.
        for obj in context.scene.objects:
            obj.select_set(False)

        # Apply scale to all geometry objects
        for obj in all_geo_objects:
            if obj.type == 'MESH':
                obj.select_set(True)
                context.view_layer.objects.active = obj
                bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
                obj.select_set(False)

        # Set up proxy objects with base Compify material (but NOT reflectors or holdouts!)
        for obj in proxy_objects:
            if obj.type == 'MESH' and obj not in reflector_objects and obj not in holdout_objects:
                obj.select_set(True)
                context.view_layer.objects.active = obj

                # Ensure it has a compify UV layer
                if UV_LAYER_NAME not in obj.data.uv_layers:
                    obj.data.uv_layers.new(name=UV_LAYER_NAME)
                obj.data.uv_layers.active = obj.data.uv_layers[UV_LAYER_NAME]

                # Check if this object already has a reflector or holdout material
                has_special_material = False
                if obj.data.materials:
                    for mat in obj.data.materials:
                        if mat and ("_Reflector_" in mat.name or "Compify_Reflection_Holdout" in mat.name):
                            has_special_material = True
                            break

                # Only apply base material if it doesn't have a special material
                if not has_special_material:
                    obj.data.materials.clear()
                    obj.data.materials.append(material)
                    print(f"Applied base material to {obj.name}")
                else:
                    print(f"Preserved special material on {obj.name}")

        # Set up reflector objects with UV layers but preserve their materials
        for obj in reflector_objects:
            if obj not in holdout_objects:  # Don't process if it's also a holdout
                obj.select_set(True)
                context.view_layer.objects.active = obj

                # Ensure it has a compify UV layer
                if UV_LAYER_NAME not in obj.data.uv_layers:
                    obj.data.uv_layers.new(name=UV_LAYER_NAME)
                obj.data.uv_layers.active = obj.data.uv_layers[UV_LAYER_NAME]

                # DON'T touch materials on reflectors - they'll be handled by setup_reflector_materials
                print(f"Preserved materials on reflector {obj.name}")

        # Set up holdout objects with UV layers and PRESERVE their holdout materials
        for obj in holdout_objects:
            obj.select_set(True)
            context.view_layer.objects.active = obj

            # Ensure it has a compify UV layer
            if UV_LAYER_NAME not in obj.data.uv_layers:
                obj.data.uv_layers.new(name=UV_LAYER_NAME)
            obj.data.uv_layers.active = obj.data.uv_layers[UV_LAYER_NAME]

            # Preserve holdout material if it had one
            if obj.name in holdout_materials_to_preserve:
                obj.data.materials.clear()
                obj.data.materials.append(holdout_materials_to_preserve[obj.name])
                print(f"Preserved holdout material on {obj.name}")

        # UV unwrap all geometry objects
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(
            angle_limit=(math.pi/180)*60,
            island_margin=0.001,
            area_weight=0.0,
            correct_aspect=False,
            scale_to_bounds=False,
        )
        bpy.ops.object.mode_set(mode='OBJECT')

        # UV island margin adjustment
        try:
            actual_margin = leftmost_u(context.selected_objects, UV_LAYER_NAME)
            actual_margin_pixels = actual_margin * context.scene.compify_config.bake_image_res
            target_margin_with_buffer = context.scene.compify_config.bake_uv_margin * (5.0 / 4.0)
            correction_factor = target_margin_with_buffer / actual_margin_pixels
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.uv.select_all(action='SELECT')

            try:
                bpy.ops.uv.pack_islands(rotate=False, margin=0.001 * correction_factor)
            except TypeError:
                try:
                    bpy.ops.uv.pack_islands(margin=0.001 * correction_factor)
                except:
                    self.report({'WARNING'}, "Could not properly set UV island margins")

            bpy.ops.object.mode_set(mode='OBJECT')
        except Exception as e:
            self.report({'WARNING'}, f"UV adjustment error: {str(e)}")
            bpy.ops.object.mode_set(mode='OBJECT')

        # NOW set up reflections - this creates special materials for reflectors
        try:
            setup_reflection_visibility(context)
            setup_reflector_materials(context)  # This creates and assigns reflector materials

            # Re-apply holdout materials after reflection setup
            for obj_name, mat in holdout_materials_to_preserve.items():
                if obj_name in bpy.data.objects:
                    obj = bpy.data.objects[obj_name]
                    obj.data.materials.clear()
                    obj.data.materials.append(mat)
                    # Ensure holdout visibility settings
                    obj.visible_glossy = True  # Must be true to block reflections
                    print(f"Re-applied holdout material to {obj_name}")

            self.report({'INFO'}, "Scene preparation completed")
        except Exception as e:
            self.report({'WARNING'}, f"Reflection setup warning: {str(e)}")

        return {'FINISHED'}


class CompifyBake(bpy.types.Operator):
    """Does the Compify lighting baking for proxy geometry"""
    bl_idname = "material.compify_bake"
    bl_label = "Bake Footage Lighting"
    bl_options = {'UNDO'}

    _timer = None
    baker = None

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' \
            and context.scene.compify_config.footage != None \
            and context.scene.compify_config.camera != None \
            and context.scene.compify_config.geo_collection != None \
            and len(context.scene.compify_config.geo_collection.all_objects) > 0 \
            and compify_mat_name(context) in bpy.data.materials

    def post(self, scene, context=None):
        if hasattr(self, 'baker') and self.baker:
            self.baker.post(scene, context)

    def cancelled(self, scene, context=None):
        if hasattr(self, 'baker') and self.baker:
            self.baker.cancelled(scene, context)

    def execute(self, context):
        self.baker = BakerWithReflections()  # Use modified baker
        self._timer = context.window_manager.event_timer_add(0.05, window=context.window)
        context.window_manager.modal_handler_add(self)
        return self.baker.execute(context)

    def modal(self, context, event):
        result = self.baker.modal(context, event)
        if result == {'FINISHED'} or result == {'CANCELLED'}:
            context.window_manager.event_timer_remove(self._timer)
        return result


class CompifyRender(bpy.types.Operator):
    """Render, but with Compify baking before rendering each frame"""
    bl_idname = "render.compify_render"
    bl_label = "Render Animation with Compify Integration"

    _timer = None
    render_started = False
    render_done = False
    frame_range = None
    stage = ""
    baker = None

    is_finished = False
    is_cancelled = False

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' \
            and context.scene.compify_config.footage != None \
            and context.scene.compify_config.camera != None \
            and context.scene.compify_config.geo_collection != None \
            and len(context.scene.compify_config.geo_collection.all_objects) > 0 \
            and compify_mat_name(context) in bpy.data.materials

    def invoke(self, context, event):
        """Show confirmation dialog before starting render"""
        return context.window_manager.invoke_props_dialog(self, width=400)

    def draw(self, context):
        """Draw the confirmation dialog"""
        layout = self.layout

        # Title
        col = layout.column()
        col.label(text="Render Settings Check", icon='RENDER_ANIMATION')
        col.separator()

        # Current settings display
        settings_box = col.box()
        settings_col = settings_box.column(align=True)
        settings_col.label(text="Current Output Settings:", icon='SETTINGS')
        settings_col.separator(factor=0.5)

        # Show current output path
        output_row = settings_col.row()
        output_row.label(text="Output:", icon='FILE_FOLDER')
        output_path = context.scene.render.filepath
        if output_path:
            output_row.label(text=output_path)
        else:
            output_row.label(text="Not Set!", icon='ERROR')

        # Show format
        format_row = settings_col.row()
        format_row.label(text="Format:", icon='IMAGE_DATA')
        format_row.label(text=context.scene.render.image_settings.file_format)

        # Show resolution
        res_row = settings_col.row()
        res_row.label(text="Resolution:", icon='FULLSCREEN_ENTER')
        res_row.label(text=f"{context.scene.render.resolution_x} x {context.scene.render.resolution_y}")

        # Show frame range
        frame_row = settings_col.row()
        frame_row.label(text="Frames:", icon='TIME')
        frame_row.label(text=f"{context.scene.frame_start} - {context.scene.frame_end}")

        col.separator()

        # Warning if no output path
        if not output_path:
            warning_box = col.box()
            warning_box.alert = True
            warning_col = warning_box.column()
            warning_col.label(text="âš ï¸ No output path set!", icon='ERROR')
            warning_col.label(text="Your renders won't be saved!")

        # Confirmation question
        col.separator()
        question_box = col.box()
        question_col = question_box.column()
        question_col.label(text="Have you configured your output settings?", icon='QUESTION')
        question_col.label(text="Click OK to start rendering, or Cancel to adjust settings.", icon='INFO')

    def render_post_callback(self, scene, context=None):
        self.render_done = True

    def cancelled_callback(self, scene, context=None):
        self.is_cancelled = True

    def execute(self, context):
        """Start the actual rendering process"""
        self.render_started = False
        self.render_done = False
        self.frame_range = (context.scene.frame_start, context.scene.frame_end)
        self.stage = "bake"
        self.baker = BakerWithReflections()

        self.is_finished = False
        self.is_cancelled = False

        bpy.app.handlers.render_post.append(self.render_post_callback)
        bpy.app.handlers.render_cancel.append(self.cancelled_callback)
        bpy.app.handlers.object_bake_cancel.append(self.cancelled_callback)

        self._timer = context.window_manager.event_timer_add(0.05, window=context.window)
        context.window_manager.modal_handler_add(self)

        context.scene.frame_set(self.frame_range[0])

        # Report that rendering has started
        self.report({'INFO'}, f"Starting Compify render: frames {self.frame_range[0]} to {self.frame_range[1]}")

        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if self.is_cancelled or self.is_finished:
            bpy.app.handlers.render_post.remove(self.render_post_callback)
            bpy.app.handlers.render_cancel.remove(self.cancelled_callback)
            bpy.app.handlers.object_bake_cancel.remove(self.cancelled_callback)

        if self.is_cancelled:
            return {'CANCELLED'}

        if self.is_finished:
            return {'FINISHED'}

        if event.type == 'TIMER':
            # Bake stage.
            if self.stage == "bake":
                if not self.baker.is_baking and not self.baker.is_done:
                    self.baker.execute(context)
                result = self.baker.modal(context, event)
                if result == {'FINISHED'}:
                    self.baker.reset()
                    self.stage = "render"
                else:
                    if result == {'CANCELLED'}:
                        self.is_cancelled = True
                    return result
            # Render stage.
            elif self.stage == "render":
                if not self.render_started:
                    self.render_started = True
                    bpy.ops.render.render("INVOKE_DEFAULT", animation=False)
                elif self.render_done:
                    image_path_start = bpy.path.abspath(context.scene.render.filepath)
                    image_ext = context.scene.render.file_extension
                    image_path = "{}{:04}{}".format(image_path_start, context.scene.frame_current, image_ext)
                    print("Saving image \"{}\"".format(image_path))
                    bpy.data.images['Render Result'].save_render(filepath=image_path)

                    if context.scene.frame_current >= self.frame_range[1]:
                        self.is_finished = True
                        self.report({'INFO'}, "Compify render completed successfully!")
                    else:
                        context.scene.frame_set(context.scene.frame_current + 1)
                        self.render_started = False
                        self.render_done = False
                        self.stage = "bake"

        return {'PASS_THROUGH'}

class CompifyAddFootageGeoCollection(bpy.types.Operator):
    """Creates and assigns a new empty collection for footage geometry"""
    bl_idname = "scene.compify_add_footage_geo_collection"
    bl_label = "Add Footage Geo Collection"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.scene.compify_config.geo_collection == None

    def execute(self, context):
        collection = bpy.data.collections.new("Footage Geo")
        context.scene.collection.children.link(collection)
        context.scene.compify_config.geo_collection = collection
        return {'FINISHED'}


class CompifyAddFootageLightsCollection(bpy.types.Operator):
    """Creates and assigns a new empty collection for footage lights"""
    bl_idname = "scene.compify_add_footage_lights_collection"
    bl_label = "Add Footage Lights Collection"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.scene.compify_config.lights_collection == None

    def execute(self, context):
        collection = bpy.data.collections.new("Footage Lights")
        context.scene.collection.children.link(collection)
        context.scene.compify_config.lights_collection = collection
        return {'FINISHED'}


class CompifyUpdateReflections(bpy.types.Operator):
    """Update reflection settings for all objects in the scene"""
    bl_idname = "scene.compify_update_reflections"
    bl_label = "Update Reflections"
    bl_options = {'UNDO'}

    def execute(self, context):
        setup_reflection_visibility(context)
        setup_reflector_materials(context)
        self.report({'INFO'}, "Reflections updated successfully")
        return {'FINISHED'}


class CompifyAddReflectorsCollection(bpy.types.Operator):
    """Creates and assigns a new empty collection for reflective geometry"""
    bl_idname = "scene.compify_add_reflectors_collection"
    bl_label = "Add Reflective Geo Collection"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.scene.compify_config.reflectors_collection == None

    def execute(self, context):
        collection = bpy.data.collections.new("Reflective Geo")

        # Add to the footage geo collection as a child if it exists
        geo_collection = context.scene.compify_config.geo_collection
        if geo_collection:
            geo_collection.children.link(collection)
            self.report({'INFO'}, "Created Reflective Geo collection inside Footage Geo collection")
        else:
            # If no footage geo collection, add to scene root
            context.scene.collection.children.link(collection)
            self.report({'WARNING'}, "Created Reflective Geo collection in scene root - create Footage Geo collection first")

        context.scene.compify_config.reflectors_collection = collection
        return {'FINISHED'}


class CompifyAddReflecteesCollection(bpy.types.Operator):
    """Creates and assigns a new empty collection for reflected geometry"""
    bl_idname = "scene.compify_add_reflectees_collection"
    bl_label = "Add Reflected Geo Collection"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.scene.compify_config.reflectees_collection == None

    def execute(self, context):
        collection = bpy.data.collections.new("Reflected Geo")
        context.scene.collection.children.link(collection)
        context.scene.compify_config.reflectees_collection = collection
        return {'FINISHED'}


class CompifyAddHoldoutCollection(bpy.types.Operator):
    """Creates and assigns a new collection for holdout geometry"""
    bl_idname = "scene.compify_add_holdout_collection"
    bl_label = "Add Holdout Geo Collection"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.scene.compify_config.holdout_collection == None

    def execute(self, context):
        collection = bpy.data.collections.new("Holdout Geo")
        context.scene.collection.children.link(collection)
        context.scene.compify_config.holdout_collection = collection
        return {'FINISHED'}


class CompifyCameraProjectGroupNew(bpy.types.Operator):
    """Creates a new camera projection node group from the current selected camera"""
    bl_idname = "material.compify_camera_project_new"
    bl_label = "New Camera Project Node Group"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object != None and context.active_object.type == 'CAMERA'

    def execute(self, context):
        x_res = context.scene.render.resolution_x
        y_res = context.scene.render.resolution_y
        x_asp = context.scene.render.pixel_aspect_x
        y_asp = context.scene.render.pixel_aspect_y

        ensure_camera_project_group(context.active_object, (x_res * x_asp) / (y_res * y_asp))
        return {'FINISHED'}


# Reflection-specific operators

class CompifyMakeReflective(bpy.types.Operator):
    """Make selected object reflective with current global settings"""
    bl_idname = "scene.compify_make_reflective"
    bl_label = "Make Object Reflective"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'MESH' \
            and context.scene.compify_config.reflectors_collection != None

    def execute(self, context):
        obj = context.active_object
        scene = context.scene
        config = scene.compify_config

        # Step 1: MOVE object to Reflective Geo collection (remove from others first)
        for coll in obj.users_collection:
            coll.objects.unlink(obj)

        # Add to Reflective Geo collection
        config.reflectors_collection.objects.link(obj)

        # Step 2: Get or create base material
        base_material = ensure_compify_material(context)

        # Step 3: Create and apply reflector material
        reflector_material_name = f"{base_material.name}_Reflector_{obj.name}"

        # Remove old if exists
        if reflector_material_name in bpy.data.materials:
            old_mat = bpy.data.materials[reflector_material_name]
            bpy.data.materials.remove(old_mat)

        # Create new
        reflector_material = base_material.copy()
        reflector_material.name = reflector_material_name

        # Apply to object
        obj.data.materials.clear()
        obj.data.materials.append(reflector_material)

        # Step 4: Apply reflection with default settings
        modify_compify_material_for_reflection(
            reflector_material,
            0.0,  # metallic
            0.1,  # default roughness
            0.5,  # default strength
            'ADD'
        )

        # Step 5: Make visible
        obj.visible_camera = True
        obj.visible_diffuse = True
        obj.visible_glossy = True

        self.report({'INFO'}, f"{obj.name} moved to Reflective Geo collection and made reflective")
        return {'FINISHED'}


class CompifyMakeObjectReflect(bpy.types.Operator):
    """Add selected object to the Objects to Reflect collection"""
    bl_idname = "scene.compify_make_object_reflect"
    bl_label = "Make Object Reflect"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object \
            and context.scene.compify_config.reflectees_collection != None

    def execute(self, context):
        obj = context.active_object
        config = context.scene.compify_config

        # Check if already in reflectees collection
        if obj in config.reflectees_collection.objects[:]:
            self.report({'INFO'}, f"{obj.name} already in Reflected Geo collection")
            return {'FINISHED'}

        for coll in obj.users_collection:
            coll.objects.unlink(obj)

        config.reflectees_collection.objects.link(obj)

        obj.visible_glossy = True
        if obj.type == 'LIGHT' and hasattr(obj.data, 'visible_glossy'):
            obj.data.visible_glossy = True

        self.report({'INFO'}, f"{obj.name} moved to Reflected Geo collection")
        return {'FINISHED'}


class CompifyMakeHoldout(bpy.types.Operator):
    bl_idname = "scene.compify_make_holdout"
    bl_label = "Make Reflection Holdout"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'MESH'

    def execute(self, context):
        original_obj = context.active_object

        obj = original_obj.copy()
        obj.data = original_obj.data.copy()  #copy the mesh

        if "holdout" not in obj.name.lower():
            obj.name = f"{original_obj.name}_holdout"

        context.collection.objects.link(obj)

        obj.compify_reflection.reflection_holdout = True

        apply_reflection_holdout_material(obj, context)

        setup_holdout_for_scene(context)

        if not context.scene.compify_config.holdout_collection:
            collection = bpy.data.collections.new("Holdout Geo")
            context.scene.collection.children.link(collection)
            context.scene.compify_config.holdout_collection = collection
            self.report({'INFO'}, "Created Holdout Geo collection")

        context.collection.objects.unlink(obj)

        context.scene.compify_config.holdout_collection.objects.link(obj)

        if context.scene.compify_config.reflectees_collection:
            if obj in context.scene.compify_config.reflectees_collection.objects[:]:
                context.scene.compify_config.reflectees_collection.objects.unlink(obj)

        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        context.view_layer.objects.active = obj

        self.report({'INFO'}, f"Created holdout duplicate: {obj.name}")
        return {'FINISHED'}


class CompifyRemoveHoldout(bpy.types.Operator):
    bl_idname = "scene.compify_remove_holdout"
    bl_label = "Remove Holdout"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'MESH' \
            and hasattr(context.active_object, 'compify_reflection') \
            and context.active_object.compify_reflection.reflection_holdout

    def execute(self, context):
        obj = context.active_object

        obj_name = obj.name

        remove_reflection_holdout_material(obj, context)

        if context.scene.compify_config.holdout_collection:
            if obj in context.scene.compify_config.holdout_collection.objects[:]:
                context.scene.compify_config.holdout_collection.objects.unlink(obj)

        mesh_data = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)

        if mesh_data.users == 0:
            bpy.data.meshes.remove(mesh_data)

        self.report({'INFO'}, f"Removed holdout object: {obj_name}")
        return {'FINISHED'}


class CompifyMakeReflectiveSpecific(bpy.types.Operator):
    bl_idname = "scene.compify_make_reflective_specific"
    bl_label = "Make Object Reflective"
    bl_options = {'UNDO'}

    object_name: bpy.props.StringProperty()

    def execute(self, context):
        if self.object_name not in bpy.data.objects:
            self.report({'ERROR'}, f"Object {self.object_name} not found")
            return {'CANCELLED'}

        obj = bpy.data.objects[self.object_name]

        scene = context.scene
        config = scene.compify_config

        base_material = ensure_compify_material(context)

        reflector_material_name = f"{base_material.name}_Reflector_{obj.name}"

        if reflector_material_name in bpy.data.materials:
            old_mat = bpy.data.materials[reflector_material_name]
            bpy.data.materials.remove(old_mat)

        reflector_material = base_material.copy()
        reflector_material.name = reflector_material_name

        obj.data.materials.clear()
        obj.data.materials.append(reflector_material)

        # Apply reflection with default settings
        modify_compify_material_for_reflection(
            reflector_material,
            0.0,  # metallic
            0.1,  # default roughness
            0.5,  # default strength
            'ADD'
        )

        # Make visible
        obj.visible_camera = True
        obj.visible_diffuse = True
        obj.visible_glossy = True

        self.report({'INFO'}, f"{obj.name} made reflective")
        return {'FINISHED'}


class CompifyForceUpdateReflectorSpecific(bpy.types.Operator):
    bl_idname = "scene.compify_force_update_reflector_specific"
    bl_label = "Force Update Reflector"
    bl_options = {'UNDO'}

    object_name: bpy.props.StringProperty()

    def execute(self, context):
        if self.object_name not in bpy.data.objects:
            self.report({'ERROR'}, f"Object {self.object_name} not found")
            return {'CANCELLED'}

        obj = bpy.data.objects[self.object_name]

        reflector_material = None
        for mat in obj.data.materials:
            if mat and "_Reflector_" in mat.name:
                reflector_material = mat
                break

        if not reflector_material:
            self.report({'ERROR'}, "No reflector material found")
            return {'CANCELLED'}

        obj_strength = obj.compify_reflection.reflection_strength
        obj_metallic = obj.compify_reflection.reflection_metallic
        obj_roughness = obj.compify_reflection.reflection_roughness

        modify_compify_material_for_reflection(
            reflector_material,
            obj_metallic,
            obj_roughness,
            obj_strength,
            'ADD',
            obj
        )

        self.report({'INFO'}, f"Updated {obj.name} reflection settings")
        return {'FINISHED'}

class CompifyRemoveReflectorMaterial(bpy.types.Operator):
    """Remove reflector material from specific object"""
    bl_idname = "scene.compify_remove_reflector_material"
    bl_label = "Remove Reflector Material"
    bl_options = {'UNDO'}

    object_name: bpy.props.StringProperty()

    def execute(self, context):
        if self.object_name not in bpy.data.objects:
            self.report({'ERROR'}, f"Object {self.object_name} not found")
            return {'CANCELLED'}

        obj = bpy.data.objects[self.object_name]

        # Track which materials to remove
        materials_to_remove = []

        # Check current materials
        if obj.data.materials:
            for mat in obj.data.materials:
                if mat and "_Reflector_" in mat.name:
                    materials_to_remove.append(mat)

        # Clear materials from object
        obj.data.materials.clear()

        # Delete the actual material data blocks
        for mat in materials_to_remove:
            if mat.users == 0:
                mat_name = mat.name
                bpy.data.materials.remove(mat)
                print(f"Deleted material: {mat_name}")

        self.report({'INFO'}, f"Removed reflector material from {obj.name}")
        return {'FINISHED'}

class CompifyForceUpdateReflector(bpy.types.Operator):
    """Force update reflector material with current settings"""
    bl_idname = "scene.compify_force_update_reflector"
    bl_label = "Force Update Reflector"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        if not context.active_object or context.active_object.type != 'MESH':
            return False

        # Check if has reflector material
        obj = context.active_object
        if obj.data.materials:
            for mat in obj.data.materials:
                if mat and "_Reflector_" in mat.name:
                    return True
        return False

    def execute(self, context):
        obj = context.active_object
        scene = context.scene

        # Find the reflector material
        reflector_material = None
        for mat in obj.data.materials:
            if mat and "_Reflector_" in mat.name:
                reflector_material = mat
                break

        if not reflector_material:
            self.report({'ERROR'}, "No reflector material found")
            return {'CANCELLED'}

        # Get settings from the OBJECT'S properties
        obj_strength = obj.compify_reflection.reflection_strength
        obj_metallic = obj.compify_reflection.reflection_metallic
        obj_roughness = obj.compify_reflection.reflection_roughness

        # Pass the object reference so the function can access roughness source settings
        modify_compify_material_for_reflection(
            reflector_material,
            obj_metallic,
            obj_roughness,
            obj_strength,
            'ADD',
            obj  # Pass the object so we can access its roughness settings
        )

        self.report({'INFO'}, f"Updated {obj.name} reflection settings")
        return {'FINISHED'}


class CompifyRoughnessRemapPreset(bpy.types.Operator):
    """Apply a preset to the roughness remap"""
    bl_idname = "scene.compify_roughness_remap_preset"
    bl_label = "Roughness Remap Preset"
    bl_options = {'UNDO'}

    preset: bpy.props.StringProperty()
    object_name: bpy.props.StringProperty()  # Add this property

    def execute(self, context):
        # Use object_name if provided, otherwise fall back to active object
        if self.object_name and self.object_name in bpy.data.objects:
            obj = bpy.data.objects[self.object_name]
        else:
            obj = context.active_object

        if not obj:
            self.report({'ERROR'}, "No object specified or active")
            return {'CANCELLED'}

        # Find the reflector material and ramp node
        reflector_mat = None
        if obj.data.materials:
            for mat in obj.data.materials:
                if mat and "_Reflector_" in mat.name:
                    reflector_mat = mat
                    break

        if not reflector_mat or not reflector_mat.node_tree:
            # Material doesn't exist yet - create it automatically
            self.report({'INFO'}, f"Creating reflector material for {obj.name}")

            # Get or create base material
            base_material = ensure_compify_material(context)

            # Create reflector material
            reflector_material_name = f"{base_material.name}_Reflector_{obj.name}"
            if reflector_material_name in bpy.data.materials:
                bpy.data.materials.remove(bpy.data.materials[reflector_material_name])

            reflector_mat = base_material.copy()
            reflector_mat.name = reflector_material_name
            obj.data.materials.clear()
            obj.data.materials.append(reflector_mat)

            # Apply basic reflection setup
            modify_compify_material_for_reflection(
                reflector_mat,
                0.0,  # metallic
                obj.compify_reflection.reflection_roughness,
                obj.compify_reflection.reflection_strength,
                'ADD',
                obj
            )

        # Now find the ramp node (should exist after material creation)
        ramp_node = None
        for node in reflector_mat.node_tree.nodes:
            if node.name == "Compify_Roughness_Remap" and node.type == 'VALTORGB':
                ramp_node = node
                break

        if not ramp_node:
            self.report({'ERROR'}, "No remap node found - material setup may have failed")
            return {'CANCELLED'}

        # Apply preset
        if self.preset == 'LINEAR':
            ramp_node.color_ramp.elements[0].position = 0.0
            ramp_node.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
            ramp_node.color_ramp.elements[1].position = 1.0
            ramp_node.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)
        elif self.preset == 'INVERT':
            ramp_node.color_ramp.elements[0].position = 0.0
            ramp_node.color_ramp.elements[0].color = (1.0, 1.0, 1.0, 1.0)
            ramp_node.color_ramp.elements[1].position = 1.0
            ramp_node.color_ramp.elements[1].color = (0.0, 0.0, 0.0, 1.0)
        elif self.preset == 'CONTRAST':
            ramp_node.color_ramp.elements[0].position = 0.25
            ramp_node.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
            ramp_node.color_ramp.elements[1].position = 0.75
            ramp_node.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)

        return {'FINISHED'}


class CompifyTextureRoughnessRemapPreset(bpy.types.Operator):
    """Apply a preset to the texture roughness remap"""
    bl_idname = "scene.compify_texture_roughness_remap_preset"
    bl_label = "Texture Roughness Remap Preset"
    bl_options = {'UNDO'}

    preset: bpy.props.StringProperty()
    object_name: bpy.props.StringProperty()  # Add this property

    def execute(self, context):
        # Use object_name if provided, otherwise fall back to active object
        if self.object_name and self.object_name in bpy.data.objects:
            obj = bpy.data.objects[self.object_name]
        else:
            obj = context.active_object

        if not obj:
            self.report({'ERROR'}, "No object specified or active")
            return {'CANCELLED'}

        # Find the reflector material and ramp node
        reflector_mat = None
        if obj.data.materials:
            for mat in obj.data.materials:
                if mat and "_Reflector_" in mat.name:
                    reflector_mat = mat
                    break

        if not reflector_mat or not reflector_mat.node_tree:
            # Material doesn't exist yet - create it automatically
            self.report({'INFO'}, f"Creating reflector material for {obj.name}")

            # Get or create base material
            base_material = ensure_compify_material(context)

            # Create reflector material
            reflector_material_name = f"{base_material.name}_Reflector_{obj.name}"
            if reflector_material_name in bpy.data.materials:
                bpy.data.materials.remove(bpy.data.materials[reflector_material_name])

            reflector_mat = base_material.copy()
            reflector_mat.name = reflector_material_name
            obj.data.materials.clear()
            obj.data.materials.append(reflector_mat)

            # Apply basic reflection setup
            modify_compify_material_for_reflection(
                reflector_mat,
                0.0,  # metallic
                obj.compify_reflection.reflection_roughness,
                obj.compify_reflection.reflection_strength,
                'ADD',
                obj
            )

        # Now find the texture remap node (should exist after material creation)
        ramp_node = None
        for node in reflector_mat.node_tree.nodes:
            if node.name == "Compify_Texture_Roughness_Remap" and node.type == 'VALTORGB':
                ramp_node = node
                break

        if not ramp_node:
            self.report({'ERROR'}, "No texture remap node found - material setup may have failed")
            return {'CANCELLED'}

        # Apply preset
        if self.preset == 'LINEAR':
            ramp_node.color_ramp.elements[0].position = 0.0
            ramp_node.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
            ramp_node.color_ramp.elements[1].position = 1.0
            ramp_node.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)
        elif self.preset == 'INVERT':
            ramp_node.color_ramp.elements[0].position = 0.0
            ramp_node.color_ramp.elements[0].color = (1.0, 1.0, 1.0, 1.0)
            ramp_node.color_ramp.elements[1].position = 1.0
            ramp_node.color_ramp.elements[1].color = (0.0, 0.0, 0.0, 1.0)
        elif self.preset == 'CONTRAST':
            ramp_node.color_ramp.elements[0].position = 0.25
            ramp_node.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
            ramp_node.color_ramp.elements[1].position = 0.75
            ramp_node.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)

        return {'FINISHED'}


class CompifyPanel(bpy.types.Panel):
    """Composite in 3D space."""
    bl_label = "Compify"
    bl_idname = "DATA_PT_compify"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"

    @classmethod
    def poll(cls, context):
        # Check if user wants the panel in Scene Properties
        try:
            from .preferences import get_compify_preferences
            prefs = get_compify_preferences()
            return prefs.panel_location in ['SCENE_PROPERTIES', 'BOTH']
        except:
            # Fallback to True if preferences can't be accessed
            return True

    def draw(self, context):
        wm = context.window_manager
        layout = self.layout

        # Safety check for compify_config
        if not hasattr(context.scene, 'compify_config'):
            layout.label(text="Compify not properly initialized. Please restart Blender.")
            return

        config = context.scene.compify_config

        box = layout.box()
        row = box.row()
        row.prop(config, "show_footage_section",
                icon='TRIA_DOWN' if config.show_footage_section else 'TRIA_RIGHT',
                icon_only=True, emboss=False)
        row.label(text="Footage", icon='IMAGE_DATA')

        if config.show_footage_section:
            col = box.column()
            col.template_ID(config, "footage", open="image.open")
            col.use_property_split = True
            if config.footage != None:
                col.prop(config.footage, "source")
                col.prop(config.footage.colorspace_settings, "name", text="Color Space")

            # Camera selection
            col.prop(config, "camera", text="Camera")

        box = layout.box()
        row = box.row()
        row.prop(config, "show_collections_section",
                icon='TRIA_DOWN' if config.show_collections_section else 'TRIA_RIGHT',
                icon_only=True, emboss=False)
        row.label(text="Collections", icon='OUTLINER_COLLECTION')

        # Check if active object has a compify material and show reset button if so
        if context.active_object and context.active_object.type == 'MESH':
            has_compify_mat = False
            if context.active_object.data.materials:
                for mat in context.active_object.data.materials:
                    if mat and (mat.name == compify_mat_name(context) or "_Reflector_" in mat.name):
                        has_compify_mat = True
                        break

            if has_compify_mat:
                row.operator("material.compify_reset_material", text="", icon='FILE_REFRESH')

        if config.show_collections_section:
            col = box.column()
            col.use_property_split = True

            # Footage Geo Collection
            row1 = col.row()
            row1.prop(config, "geo_collection", text="Footage Geo")
            row1.operator("scene.compify_add_footage_geo_collection", text="", icon='ADD')

            # Footage Lights Collection
            row2 = col.row()
            row2.prop(config, "lights_collection", text="Footage Lights")
            row2.operator("scene.compify_add_footage_lights_collection", text="", icon='ADD')

            # Mesh Tools subsection
            col.separator()
            mesh_tools_box = col.box()
            mesh_tools_row = mesh_tools_box.row()
            mesh_tools_row.prop(config, "show_mesh_tools_section",
                    icon='TRIA_DOWN' if config.show_mesh_tools_section else 'TRIA_RIGHT',
                    icon_only=True, emboss=False)
            mesh_tools_row.label(text="Mesh Tools", icon='MESH_DATA')

            # Only show if at least one collection exists
            has_collections = (config.geo_collection or
                             config.reflectors_collection or
                             config.holdout_collection)

            if config.show_mesh_tools_section and has_collections:
                mesh_tools_col = mesh_tools_box.column()

                # Object selector dropdown
                mesh_tools_col.prop(config, "selected_mesh_object_enum", text="Object")

                if config.selected_mesh_object_enum != 'NONE':
                    if config.selected_mesh_object_enum in bpy.data.objects:
                        selected_obj = bpy.data.objects[config.selected_mesh_object_enum]

                        # Determine which collection the object is from
                        collection_name = "Unknown"
                        collection_icon = 'OBJECT_DATA'

                        if config.geo_collection and selected_obj in config.geo_collection.objects[:]:
                            collection_name = "Footage Geo"
                            collection_icon = 'OUTLINER_OB_MESH'
                        elif config.reflectors_collection and selected_obj in config.reflectors_collection.objects[:]:
                            collection_name = "Reflective Geo"
                            collection_icon = 'SHADING_RENDERED'
                        elif config.holdout_collection and selected_obj in config.holdout_collection.objects[:]:
                            collection_name = "Holdout Geo"
                            collection_icon = 'HOLDOUT_ON'

                        tools_box = mesh_tools_col.box()
                        header_row = tools_box.row()
                        header_row.label(text=f"Tools for: {selected_obj.name}", icon='OBJECT_DATA')
                        header_row.label(text=f"({collection_name})", icon=collection_icon)

                        # Normals section
                        normals_row = tools_box.row()
                        normals_row.label(text="Normals:", icon='NORMALS_FACE')

                        normals_buttons = tools_box.row(align=True)

                        # Check if operator exists before trying to use it
                        if hasattr(bpy.ops.scene, 'compify_recalculate_normals'):
                            # Recalculate Outside button
                            op_out = normals_buttons.operator("scene.compify_recalculate_normals",
                                                             text="Recalculate Outside")
                            if op_out is not None:
                                op_out.object_name = selected_obj.name
                                op_out.inside = False

                            # Recalculate Inside button
                            op_in = normals_buttons.operator("scene.compify_recalculate_normals",
                                                            text="Recalculate Inside")
                            if op_in is not None:
                                op_in.object_name = selected_obj.name
                                op_in.inside = True
                        else:
                            # Fallback if operator isn't registered
                            normals_buttons.label(text="Normals operator not available", icon='ERROR')
            elif config.show_mesh_tools_section:
                mesh_tools_col = mesh_tools_box.column()
                mesh_tools_col.label(text="No collections available", icon='ERROR')
                mesh_tools_col.label(text="Create Footage, Reflective, or Holdout Geo collections", icon='INFO')


        box = layout.box()
        row = box.row()
        row.prop(config, "show_reflections_section",
                icon='TRIA_DOWN' if config.show_reflections_section else 'TRIA_RIGHT',
                icon_only=True, emboss=False)
        row.label(text="Reflections", icon='SHADING_RENDERED')

        if config.show_reflections_section:
            col = box.column()
            col.use_property_split = True

            # Reflective Geo Collection - Always show this first
            row3 = col.row()
            row3.prop(config, "reflectors_collection", text="Reflective Geo")
            row3.operator("scene.compify_add_reflectors_collection", text="", icon='ADD')

            # Reflected Geo Collection
            row4 = col.row()
            row4.prop(config, "reflectees_collection", text="Reflected Geo")
            row4.operator("scene.compify_add_reflectees_collection", text="", icon='ADD')

            # Holdout Geo Collection
            row5 = col.row()
            row5.prop(config, "holdout_collection", text="Holdout Geo")
            row5.operator("scene.compify_add_holdout_collection", text="", icon='ADD')

            # Only show reflector settings if Reflective Geo collection exists
            if config.reflectors_collection:
                col.separator()
                reflector_select_box = col.box()
                reflector_select_box.label(text="Individual Reflector Settings", icon='SETTINGS')

                # Object selector dropdown
                selector_row = reflector_select_box.row()
                selector_row.prop(config, "selected_reflector_object_enum", text="Object")

                # Show settings for selected reflector object OR add new reflector button
                if config.selected_reflector_object_enum != 'NONE':
                    selected_obj_name = config.selected_reflector_object_enum
                    if selected_obj_name in bpy.data.objects:
                        selected_obj = bpy.data.objects[selected_obj_name]  # GET OBJECT FROM DROPDOWN, NOT ACTIVE OBJECT

                        # Ensure the object has reflection properties
                        if hasattr(selected_obj, 'compify_reflection'):
                            settings_box = reflector_select_box.box()

                            # Collapsible header for settings
                            header_row = settings_box.row()
                            header_row.prop(selected_obj.compify_reflection, "show_object_settings",
                                           icon='TRIA_DOWN' if selected_obj.compify_reflection.show_object_settings else 'TRIA_RIGHT',
                                           icon_only=True, emboss=False)
                            header_row.label(text=f"Settings for: {selected_obj.name}", icon='OBJECT_DATA')

                            # Only show settings if expanded
                            if selected_obj.compify_reflection.show_object_settings:
                                # Check if object has reflector material
                                has_reflector_mat = False
                                reflector_mat = None
                                if selected_obj.data.materials:
                                    for mat in selected_obj.data.materials:
                                        if mat and "_Reflector_" in mat.name:
                                            has_reflector_mat = True
                                            reflector_mat = mat
                                            break

                                if not has_reflector_mat:
                                    # No reflector material - show button to create one
                                    warning_box = settings_box.box()
                                    warning_box.alert = True
                                    warning_box.label(text="âš ï¸ Object needs reflector material", icon='ERROR')

                                    make_reflective_row = settings_box.row()
                                    make_reflective_row.scale_y = 1.3
                                    make_reflective_op = make_reflective_row.operator("scene.compify_make_reflective_specific",
                                                                                    text="Make This Object Reflective",
                                                                                    icon='SHADING_RENDERED')
                                    make_reflective_op.object_name = selected_obj.name
                                else:
                                    # HAS reflector material - show comprehensive settings
                                    settings_box.label(text="âœ… Object is Reflective", icon='CHECKMARK')
                                    settings_box.separator()

                                    # Main reflection properties
                                    settings_box.prop(selected_obj.compify_reflection, "reflection_strength", text="Strength", slider=True)

                                    # Roughness source selector
                                    settings_box.prop(selected_obj.compify_reflection, "roughness_source", text="Roughness")

                                    # Show appropriate roughness control based on source
                                    if selected_obj.compify_reflection.roughness_source == 'VALUE':
                                        settings_box.prop(selected_obj.compify_reflection, "reflection_roughness", text="Roughness Value", slider=True)

                                    elif selected_obj.compify_reflection.roughness_source == 'TEXTURE':
                                        settings_box.template_ID(selected_obj.compify_reflection, "roughness_texture", open="image.open")

                                        # Add ColorRamp section for texture roughness
                                        if selected_obj.compify_reflection.roughness_texture:
                                            remap_box = settings_box.box()
                                            remap_row = remap_box.row()
                                            remap_row.prop(selected_obj.compify_reflection, "show_texture_roughness_remap",
                                                          icon='TRIA_DOWN' if selected_obj.compify_reflection.show_texture_roughness_remap else 'TRIA_RIGHT',
                                                          icon_only=True, emboss=False)
                                            remap_row.label(text="Texture Roughness Remap", icon='FCURVE')

                                            if selected_obj.compify_reflection.show_texture_roughness_remap:
                                                # Find the ColorRamp node if it exists
                                                ramp_node = None
                                                if reflector_mat and reflector_mat.node_tree:
                                                    for node in reflector_mat.node_tree.nodes:
                                                        if node.name == "Compify_Texture_Roughness_Remap" and node.type == 'VALTORGB':
                                                            ramp_node = node
                                                            break

                                                if ramp_node:
                                                    # Show the actual ColorRamp widget
                                                    remap_box.template_color_ramp(ramp_node, "color_ramp", expand=True)
                                                else:
                                                    remap_box.label(text="Apply changes to create remap", icon='INFO')

                                                # Quick presets
                                                remap_box.separator()
                                                preset_row = remap_box.row(align=True)
                                                preset_row.label(text="Presets:")
                                                preset_op1 = preset_row.operator("scene.compify_texture_roughness_remap_preset", text="Linear")
                                                preset_op1.preset = 'LINEAR'
                                                preset_op1.object_name = selected_obj.name
                                                preset_op2 = preset_row.operator("scene.compify_texture_roughness_remap_preset", text="Invert")
                                                preset_op2.preset = 'INVERT'
                                                preset_op2.object_name = selected_obj.name
                                                preset_op3 = preset_row.operator("scene.compify_texture_roughness_remap_preset", text="Contrast")
                                                preset_op3.preset = 'CONTRAST'
                                                preset_op3.object_name = selected_obj.name

                                    elif selected_obj.compify_reflection.roughness_source == 'COMPIFY':
                                        # Using Compify footage - show collapsible ColorRamp section
                                        remap_box = settings_box.box()
                                        remap_row = remap_box.row()
                                        remap_row.prop(selected_obj.compify_reflection, "show_roughness_remap",
                                                      icon='TRIA_DOWN' if selected_obj.compify_reflection.show_roughness_remap else 'TRIA_RIGHT',
                                                      icon_only=True, emboss=False)
                                        remap_row.label(text="Roughness Remap", icon='FCURVE')

                                        if selected_obj.compify_reflection.show_roughness_remap:
                                            # Find the ColorRamp node if it exists
                                            ramp_node = None
                                            if reflector_mat and reflector_mat.node_tree:
                                                for node in reflector_mat.node_tree.nodes:
                                                    if node.name == "Compify_Roughness_Remap" and node.type == 'VALTORGB':
                                                        ramp_node = node
                                                        break

                                            if ramp_node:
                                                # Show the actual ColorRamp widget
                                                remap_box.template_color_ramp(ramp_node, "color_ramp", expand=True)
                                            else:
                                                remap_box.label(text="Apply changes to create remap", icon='INFO')

                                            # Quick presets
                                            remap_box.separator()
                                            preset_row = remap_box.row(align=True)
                                            preset_row.label(text="Presets:")
                                            preset_op1 = preset_row.operator("scene.compify_roughness_remap_preset", text="Linear")
                                            preset_op1.preset = 'LINEAR'
                                            preset_op1.object_name = selected_obj.name
                                            preset_op2 = preset_row.operator("scene.compify_roughness_remap_preset", text="Invert")
                                            preset_op2.preset = 'INVERT'
                                            preset_op2.object_name = selected_obj.name
                                            preset_op3 = preset_row.operator("scene.compify_roughness_remap_preset", text="Contrast")
                                            preset_op3.preset = 'CONTRAST'
                                            preset_op3.object_name = selected_obj.name

                                    settings_box.separator()
                                    edge_control_box = settings_box.box()

                                    # Collapsible header for edge controls
                                    edge_header_row = edge_control_box.row()
                                    edge_header_row.prop(selected_obj.compify_reflection, "show_edge_controls",
                                                        icon='TRIA_DOWN' if selected_obj.compify_reflection.show_edge_controls else 'TRIA_RIGHT',
                                                        icon_only=True, emboss=False)
                                    edge_header_row.label(text="Edge Controls", icon='MOD_SMOOTH')

                                    # Only show controls if expanded
                                    if selected_obj.compify_reflection.show_edge_controls:
                                        edge_control_col = edge_control_box.column()
                                        edge_control_col.prop(selected_obj.compify_reflection, "feather", text="Feather", slider=True)
                                        edge_control_col.prop(selected_obj.compify_reflection, "dilate", text="Dilate", slider=True)

                                    # Apply changes button
                                    settings_box.separator()
                                    apply_row = settings_box.row()
                                    apply_row.scale_y = 1.2
                                    apply_op = apply_row.operator("scene.compify_force_update_reflector_specific",
                                                                text="Apply Changes",
                                                                icon='FILE_REFRESH')
                                    apply_op.object_name = selected_obj.name

                                    # Remove reflector material button
                                    settings_box.separator()
                                    remove_row = settings_box.row()
                                    remove_op = remove_row.operator("scene.compify_remove_reflector_material",
                                                                  text="Remove Reflector Material",
                                                                  icon='X')
                                    remove_op.object_name = selected_obj.name
                        else:
                            error_box = reflector_select_box.box()
                            error_box.alert = True
                            error_box.label(text="Selected object missing reflection properties", icon='ERROR')
                else:
                    # No object selected - show add current object button or help text
                    if context.active_object and context.active_object.type == 'MESH':
                        # Show button to make the active object reflective
                        add_box = reflector_select_box.box()
                        add_box.label(text=f"Active Object: {context.active_object.name}", icon='OBJECT_DATA')

                        # Check if already in reflectors collection
                        is_already_reflector = False
                        if config.reflectors_collection:
                            is_already_reflector = context.active_object in config.reflectors_collection.objects[:]

                        if is_already_reflector:
                            add_box.label(text="âœ… Already in Reflective Geo collection", icon='CHECKMARK')
                            help_row = add_box.row()
                            help_row.label(text="Use dropdown above to edit settings", icon='INFO')
                        else:
                            make_reflector_row = add_box.row()
                            make_reflector_row.scale_y = 1.3
                            make_reflector_op = make_reflector_row.operator("scene.compify_make_reflective_and_select",
                                                                          text="Make Active Object Reflective",
                                                                          icon='SHADING_RENDERED')
                            make_reflector_op.object_name = context.active_object.name
                    else:
                        # No object selected or not a mesh
                        help_box = reflector_select_box.box()
                        if context.active_object:
                            help_box.label(text=f"Active object '{context.active_object.name}' is not a mesh", icon='INFO')
                        else:
                            help_box.label(text="Select a mesh object to make it reflective", icon='INFO')

            # Quick Actions section - only show if we have an active object
            if context.active_object:
                obj = context.active_object

                # Determine what actions are available based on collections
                show_quick_actions = False
                can_make_visible = config.reflectees_collection is not None
                can_make_holdout = config.holdout_collection is not None and obj.type == 'MESH'

                # Check if object is already in one of the collections
                is_in_reflectees = False
                if config.reflectees_collection:
                    is_in_reflectees = obj in config.reflectees_collection.objects[:]

                is_holdout = hasattr(obj, 'compify_reflection') and obj.compify_reflection.reflection_holdout

                # Only show quick actions if there's something to show
                if can_make_visible or can_make_holdout or is_in_reflectees or is_holdout:
                    show_quick_actions = True

                if show_quick_actions:
                    col.separator()
                    quick_actions_box = col.box()
                    quick_actions_box.label(text=f"Quick Actions: {obj.name}", icon='OBJECT_DATA')

                    # Check if object is holdout
                    if is_holdout:
                        quick_actions_box.label(text="âœ… Object is a Reflection Holdout", icon='HOLDOUT_ON')
                        quick_actions_box.label(text="(Blocks reflections but invisible)", icon='INFO')

                        # Option to remove holdout
                        row = quick_actions_box.row()
                        row.operator("scene.compify_remove_holdout",
                                    text="Remove Holdout",
                                    icon='X')
                    elif is_in_reflectees:
                        quick_actions_box.label(text="âœ… Object is in Reflected Geo collection", icon='CHECKMARK')
                    else:
                        # Show available actions based on what collections exist
                        if can_make_visible or can_make_holdout:
                            col_options = quick_actions_box.column(align=True)

                            if can_make_visible:
                                col_options.operator("scene.compify_make_object_reflect",
                                                    text="Make Object Visible in Reflections",
                                                    icon='HIDE_OFF')

                            if can_make_holdout:
                                col_options.operator("scene.compify_make_holdout",
                                                    text="Make Reflection Holdout",
                                                    icon='HOLDOUT_OFF')
                        else:
                            # No collections created yet
                            info_box = quick_actions_box.box()
                            info_box.label(text="Create collections above to enable quick actions", icon='INFO')

            # If no reflectors collection exists, show helpful message
            if not config.reflectors_collection:
                col.separator()
                help_box = col.box()
                help_box.label(text="Create 'Reflective Geo' collection to enable reflection features", icon='INFO')

        box = layout.box()
        row = box.row()
        row.prop(config, "show_baking_section",
                icon='TRIA_DOWN' if config.show_baking_section else 'TRIA_RIGHT',
                icon_only=True, emboss=False)
        row.label(text="Baking Settings", icon='RENDER_STILL')

        if config.show_baking_section:
            col = box.column()
            col.use_property_split = True
            col.prop(config, "bake_uv_margin")
            col.prop(config, "bake_image_res")

        layout.separator(factor=1.0)

        main_row = layout.row(align=True)
        main_row.scale_y = 1.3
        
        main_row.operator("material.compify_prep_scene", text="Prep", icon='SCENE_DATA')
        main_row.operator("material.compify_bake", text="Bake", icon='RENDER_STILL')
        main_row.operator("render.compify_render", text="Render", icon='RENDER_ANIMATION')
        
        main_row.operator("preferences.addon_show", text="", icon='PREFERENCES').module = __package__


def register():
    bpy.utils.register_class(CompifyReflectionProperties)
    bpy.utils.register_class(CompifyFootageConfig)
    bpy.utils.register_class(CompifyAddFootageGeoCollection)
    bpy.utils.register_class(CompifyAddFootageLightsCollection)
    bpy.utils.register_class(CompifyAddReflectorsCollection)
    bpy.utils.register_class(CompifyAddReflecteesCollection)
    bpy.utils.register_class(CompifyAddHoldoutCollection)
    bpy.utils.register_class(CompifyRecalculateNormals)
    bpy.utils.register_class(CompifyResetMaterial)
    bpy.utils.register_class(CompifyPrepScene)
    bpy.utils.register_class(CompifyBake)
    bpy.utils.register_class(CompifyRender)
    bpy.utils.register_class(CompifyCameraProjectGroupNew)
    bpy.utils.register_class(CompifyMakeReflective)
    bpy.utils.register_class(CompifyMakeReflectiveSpecific)
    bpy.utils.register_class(CompifyMakeReflectiveAndSelect)
    bpy.utils.register_class(CompifyMakeObjectReflect)
    bpy.utils.register_class(CompifyMakeHoldout)
    bpy.utils.register_class(CompifyRemoveHoldout)
    bpy.utils.register_class(CompifyForceUpdateReflector)
    bpy.utils.register_class(CompifyForceUpdateReflectorSpecific)
    bpy.utils.register_class(CompifyUpdateReflections)
    bpy.utils.register_class(CompifyRemoveReflectorMaterial)
    bpy.utils.register_class(CompifyRoughnessRemapPreset)
    bpy.utils.register_class(CompifyTextureRoughnessRemapPreset)
    bpy.utils.register_class(CompifyPanel)
    bpy.utils.register_class(CompifyCameraPanel)
    bpy.types.Scene.compify_config = bpy.props.PointerProperty(type=CompifyFootageConfig)
    bpy.types.Object.compify_reflection = bpy.props.PointerProperty(type=CompifyReflectionProperties)
    camera_align_register()
    register_preferences()

    print("Compify addon registered successfully")


def unregister():
    if hasattr(bpy.types.Scene, 'compify_config'):
        del bpy.types.Scene.compify_config
    if hasattr(bpy.types.Object, 'compify_reflection'):
        del bpy.types.Object.compify_reflection
    unregister_preferences()
    camera_align_unregister()
    bpy.utils.unregister_class(CompifyCameraPanel)
    bpy.utils.unregister_class(CompifyPanel)
    bpy.utils.unregister_class(CompifyTextureRoughnessRemapPreset)
    bpy.utils.unregister_class(CompifyRoughnessRemapPreset)
    bpy.utils.unregister_class(CompifyRemoveReflectorMaterial)
    bpy.utils.unregister_class(CompifyUpdateReflections)
    bpy.utils.unregister_class(CompifyForceUpdateReflectorSpecific)
    bpy.utils.unregister_class(CompifyForceUpdateReflector)
    bpy.utils.unregister_class(CompifyRemoveHoldout)
    bpy.utils.unregister_class(CompifyMakeHoldout)
    bpy.utils.unregister_class(CompifyMakeObjectReflect)
    bpy.utils.unregister_class(CompifyMakeReflectiveAndSelect)
    bpy.utils.unregister_class(CompifyMakeReflectiveSpecific)
    bpy.utils.unregister_class(CompifyMakeReflective)
    bpy.utils.unregister_class(CompifyCameraProjectGroupNew)
    bpy.utils.unregister_class(CompifyRender)
    bpy.utils.unregister_class(CompifyBake)
    bpy.utils.unregister_class(CompifyPrepScene)
    bpy.utils.unregister_class(CompifyResetMaterial)
    bpy.utils.unregister_class(CompifyRecalculateNormals)
    bpy.utils.unregister_class(CompifyAddHoldoutCollection)
    bpy.utils.unregister_class(CompifyAddReflecteesCollection)
    bpy.utils.unregister_class(CompifyAddReflectorsCollection)
    bpy.utils.unregister_class(CompifyAddFootageLightsCollection)
    bpy.utils.unregister_class(CompifyAddFootageGeoCollection)
    bpy.utils.unregister_class(CompifyFootageConfig)
    bpy.utils.unregister_class(CompifyReflectionProperties)

    print("Compify addon unregistered successfully")


# Main entry point
if __name__ == "__main__":
    register()


#wuttup scrubs <3
#fsociety
