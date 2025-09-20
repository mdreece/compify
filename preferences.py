import bpy
from bpy.types import AddonPreferences
from bpy.props import BoolProperty, StringProperty


class CompifyPopupPanel(bpy.types.Panel):
    """Popup version of the main Compify panel for 3D viewport"""
    bl_label = "Compify"
    bl_idname = "VIEW3D_PT_compify_popup"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Compify"

    def draw(self, context):
        layout = self.layout

        # Add a header tab at the top
        header_box = layout.box()
        header_row = header_box.row()
        header_row.alignment = 'CENTER'
        header_row.scale_y = 1.2
        header_row.label(text="COMPIFY", icon='SCENE_DATA')

        # Add a subtle separator
        layout.separator(factor=0.5)

        # Safety check for compify_config
        if not hasattr(context.scene, 'compify_config'):
            error_box = layout.box()
            error_box.alert = True
            error_box.label(text="Compify not properly initialized.", icon='ERROR')
            error_box.label(text="Please restart Blender.")
            return

        config = context.scene.compify_config

        #-------- FOOTAGE SECTION (Collapsible) --------
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

        #-------- COLLECTIONS SECTION (Collapsible) --------
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
                    if mat and (mat.name.startswith("Compify Footage") or "_Reflector_" in mat.name):
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

        #-------- REFLECTIONS SECTION (Collapsible) --------
        box = layout.box()
        row = box.row()
        row.prop(config, "show_reflections_section",
                icon='TRIA_DOWN' if config.show_reflections_section else 'TRIA_RIGHT',
                icon_only=True, emboss=False)
        row.label(text="Reflections", icon='SHADING_RENDERED')

        if config.show_reflections_section:
            col = box.column()
            col.use_property_split = True

            # Reflective Geo Collection
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

            # Per-Object Settings (if object selected) - Condensed for popup
            if context.active_object:
                obj = context.active_object
                col.separator()
                col.label(text=f"Selected: {obj.name}", icon='OBJECT_DATA')

                # Reflector settings for mesh objects
                if obj.type == 'MESH':
                    sub_box = col.box()

                    # Check if object has reflector material
                    has_reflector_mat = False
                    for mat in obj.data.materials if obj.data.materials else []:
                        if mat and "_Reflector_" in mat.name:
                            has_reflector_mat = True
                            break

                    if not has_reflector_mat:
                        sub_box.operator("scene.compify_make_reflective",
                                       text="Make Reflective", icon='SHADING_RENDERED')
                    else:
                        sub_box.label(text="✓ Reflective", icon='CHECKMARK')
                        # Quick controls for popup
                        sub_box.prop(obj.compify_reflection, "reflection_strength", text="Strength", slider=True)
                        sub_box.prop(obj.compify_reflection, "reflection_roughness", text="Roughness", slider=True)
                        sub_box.operator("scene.compify_force_update_reflector", text="Apply", icon='FILE_REFRESH')

                # Reflection visibility controls
                col.separator()
                reflect_box = col.box()

                if hasattr(obj, 'compify_reflection') and obj.compify_reflection.reflection_holdout:
                    reflect_box.label(text="✓ Holdout", icon='HOLDOUT_ON')
                    reflect_box.operator("scene.compify_remove_holdout", text="Remove Holdout", icon='X')
                else:
                    col_options = reflect_box.column(align=True)
                    col_options.operator("scene.compify_make_object_reflect",
                                        text="Make Visible in Reflections", icon='HIDE_OFF')
                    if obj.type == 'MESH':
                        col_options.operator("scene.compify_make_holdout",
                                            text="Make Holdout", icon='HOLDOUT_OFF')

        #-------- BAKING SETTINGS SECTION (Collapsible) --------
        box = layout.box()
        row = box.row()
        row.prop(config, "show_baking_section",
                icon='TRIA_DOWN' if config.show_baking_section else 'TRIA_RIGHT',
                icon_only=True, emboss=False)
        row.label(text="Baking", icon='RENDER_STILL')

        if config.show_baking_section:
            col = box.column()
            col.use_property_split = True
            col.prop(config, "bake_uv_margin")
            col.prop(config, "bake_image_res")

        #-------- MAIN ACTION BUTTONS (Always visible) --------
        layout.separator(factor=1.0)

        # Action buttons in a nice box
        action_box = layout.box()
        col = action_box.column(align=True)
        col.scale_y = 1.2
        col.operator("material.compify_prep_scene", icon='SCENE_DATA')
        col.operator("material.compify_bake", icon='RENDER_STILL')
        col.operator("render.compify_render", icon='RENDER_ANIMATION')


class CompifyOpenPopupOperator(bpy.types.Operator):
    """Open Compify panel as popup in 3D viewport"""
    bl_idname = "compify.open_popup_panel"
    bl_label = "Open Compify Panel"
    bl_description = "Open the Compify panel as a popup in the 3D viewport"
    bl_options = {'REGISTER'}

    def execute(self, context):
        # Get the preferences to check if popup is enabled
        prefs = get_compify_preferences()
        if not prefs.enable_popup_panel:
            self.report({'WARNING'}, "Popup panel is disabled in addon preferences")
            return {'CANCELLED'}

        return context.window_manager.invoke_popup(self, width=400)

    def draw(self, context):
        # Use the exact same draw method as the popup panel
        CompifyPopupPanel.draw(self, context)


class CompifyCheckUpdatesOperator(bpy.types.Operator):
    """Check for Compify updates from selected repository"""
    bl_idname = "compify.check_updates"
    bl_label = "Check Updates"
    bl_description = "Check for available updates from the selected repository"

    def execute(self, context):
        import urllib.request
        import re

        prefs = get_compify_preferences()

        # Get current version from bl_info
        try:
            from . import bl_info
            current_version = bl_info['version']
        except:
            current_version = (0, 6, 0)  # Fallback

        # Determine which repository to check
        if prefs.update_channel == 'OFFICIAL':
            url = "https://raw.githubusercontent.com/EatTheFuture/compify/master/__init__.py"
        else:
            url = "https://raw.githubusercontent.com/mdreece/compify/master/__init__.py"

        try:
            # Download and parse __init__.py
            with urllib.request.urlopen(url, timeout=10) as response:
                content = response.read().decode('utf-8')

            # Extract version from bl_info
            version_match = re.search(r'"version":\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)', content)

            if version_match:
                remote_version = (int(version_match.group(1)), int(version_match.group(2)), int(version_match.group(3)))
                version_str = f"{remote_version[0]}.{remote_version[1]}.{remote_version[2]}"

                # Compare versions
                if remote_version > current_version:
                    prefs.update_available = True
                    prefs.latest_version = version_str
                    prefs.update_status = "AVAILABLE"
                    self.report({'INFO'}, f"Update available: {version_str}")
                else:
                    prefs.update_available = False
                    prefs.latest_version = version_str
                    prefs.update_status = "UP_TO_DATE"
                    self.report({'INFO'}, "You have the latest version!")
            else:
                prefs.update_status = "ERROR"
                self.report({'ERROR'}, "Could not parse version information")

        except Exception as e:
            prefs.update_status = "ERROR"
            self.report({'ERROR'}, f"Failed to check for updates: {str(e)}")

        return {'FINISHED'}


class CompifyInstallUpdateOperator(bpy.types.Operator):
    """Install Compify update from selected repository"""
    bl_idname = "compify.install_update"
    bl_label = "Are You Sure?"
    bl_description = "Download and install the update"

    url: bpy.props.StringProperty()
    is_official: BoolProperty(default=False)

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def draw(self, context):
        layout = self.layout
        col = layout.column()

        if self.is_official:
            col.label(text="⚠️ Installing Official Version", icon='ERROR')
            col.separator()
            col.label(text="This will REMOVE unofficial features:")
            col.label(text="• Enhanced reflection system", icon='X')
            col.label(text="• Improved material handling", icon='X')
            col.label(text="• UI improvements and ColorRamp preservation", icon='X')
            col.label(text="• Blender 4.3-5.0 compatibility enhancements", icon='X')
            col.separator()
            col.label(text="You will get the original stable version with")
            col.label(text="basic features only.")
            col.separator()
            col.label(text="⚠️ This action cannot be undone!")
            col.label(text="Blender restart will be required.")
        else:
            col.label(text="Installing Unofficial Update", icon='CHECKMARK')
            col.separator()
            col.label(text="This will:")
            col.label(text="• Update to latest unofficial version", icon='CHECKMARK')
            col.label(text="• Keep all enhanced features", icon='CHECKMARK')
            col.label(text="• Require Blender restart", icon='INFO')

        col.separator()
        col.label(text="Continue with installation?")

    def execute(self, context):
        import urllib.request
        import zipfile
        import os
        import shutil
        import tempfile

        try:
            # Get addon directory
            addon_dir = os.path.dirname(os.path.realpath(__file__))
            parent_dir = os.path.dirname(addon_dir)

            # Create temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                # Download zip file
                zip_path = os.path.join(temp_dir, "compify.zip")

                self.report({'INFO'}, "Downloading update...")
                urllib.request.urlretrieve(self.url, zip_path)

                # Extract zip
                extract_path = os.path.join(temp_dir, "extracted")
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_path)

                # Find the compify folder in extracted files
                compify_folder = None
                for item in os.listdir(extract_path):
                    item_path = os.path.join(extract_path, item)
                    if os.path.isdir(item_path) and 'compify' in item.lower():
                        compify_folder = item_path
                        break

                if not compify_folder:
                    self.report({'ERROR'}, "Could not find compify folder in download")
                    return {'CANCELLED'}

                # Remove old addon directory
                if os.path.exists(addon_dir):
                    shutil.rmtree(addon_dir)

                # Copy new files
                shutil.copytree(compify_folder, addon_dir)

                self.report({'INFO'}, "Update installed successfully!")
                self.report({'WARNING'}, "Please restart Blender to complete the update")

        except Exception as e:
            self.report({'ERROR'}, f"Installation failed: {str(e)}")
            return {'CANCELLED'}

        return {'FINISHED'}


class CompifyRecordShortcutOperator(bpy.types.Operator):
    """Record a keyboard shortcut by pressing keys"""
    bl_idname = "compify.record_shortcut"
    bl_label = "Record Shortcut"
    bl_description = "Click and then press any key combination to set as shortcut"

    deferred: BoolProperty(default=True)

    def modal(self, context, event):
        prefs = get_compify_preferences()

        # Cancel recording on escape
        if event.type == 'ESC':
            prefs.shortcut_recording = False
            self.report({'INFO'}, "Shortcut recording cancelled")
            return {'CANCELLED'}

        # Only capture key press events
        if event.value == 'PRESS' and event.type not in {'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE', 'TIMER', 'WINDOW_DEACTIVATE'}:
            # Skip modifier-only presses
            if event.type in {'LEFT_CTRL', 'RIGHT_CTRL', 'LEFT_ALT', 'RIGHT_ALT',
                             'LEFT_SHIFT', 'RIGHT_SHIFT', 'OSKEY'}:
                return {'RUNNING_MODAL'}

            # Record the shortcut
            prefs.shortcut_key_internal = event.type
            prefs.shortcut_ctrl_internal = event.ctrl
            prefs.shortcut_alt_internal = event.alt
            prefs.shortcut_shift_internal = event.shift
            prefs.shortcut_oskey_internal = event.oskey
            prefs.shortcut_recording = False

            # Show what was recorded
            shortcut_display = prefs.get_current_shortcut_display()
            self.report({'INFO'}, f"Recorded shortcut: {shortcut_display}")

            return {'FINISHED'}

        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        prefs = get_compify_preferences()

        if self.deferred:
            # Start recording
            prefs.shortcut_recording = True
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        else:
            # Stop recording
            prefs.shortcut_recording = False
            return {'FINISHED'}


class CompifyClearShortcutOperator(bpy.types.Operator):
    """Clear the current shortcut"""
    bl_idname = "compify.clear_shortcut"
    bl_label = "Clear Shortcut"
    bl_description = "Remove the current keyboard shortcut"

    def execute(self, context):
        prefs = get_compify_preferences()
        prefs.shortcut_key_internal = ""
        prefs.shortcut_ctrl_internal = False
        prefs.shortcut_alt_internal = False
        prefs.shortcut_shift_internal = False
        prefs.shortcut_oskey_internal = False
        prefs.shortcut_recording = False

        # Remove from keymap too
        remove_compify_keymap()

        self.report({'INFO'}, "Shortcut cleared")
        return {'FINISHED'}


class CompifyUpdateKeymapOperator(bpy.types.Operator):
    """Update the keymap for Compify popup panel"""
    bl_idname = "compify.update_keymap"
    bl_label = "Update Keymap"
    bl_description = "Apply the keyboard shortcut for opening the popup panel"

    def execute(self, context):
        prefs = get_compify_preferences()

        if not prefs.shortcut_key_internal:
            self.report({'ERROR'}, "No shortcut set")
            return {'CANCELLED'}

        # Remove existing keymap first
        remove_compify_keymap()

        # Add new keymap
        if prefs.enable_popup_panel:
            success = add_compify_keymap_from_prefs(prefs)
            if success:
                shortcut_text = prefs.get_current_shortcut_display()
                self.report({'INFO'}, f"Shortcut applied: {shortcut_text}")
            else:
                self.report({'ERROR'}, f"Failed to create keymap")
                return {'CANCELLED'}

        return {'FINISHED'}


class CompifyRemoveKeymapOperator(bpy.types.Operator):
    """Remove the keymap for Compify popup panel"""
    bl_idname = "compify.remove_keymap"
    bl_label = "Remove Keymap"
    bl_description = "Remove the keyboard shortcut for opening the popup panel"

    def execute(self, context):
        remove_compify_keymap()
        self.report({'INFO'}, "Shortcut removed from keymap")
        return {'FINISHED'}


class CompifyAddonPreferences(AddonPreferences):
    """Compify addon preferences"""
    bl_idname = __package__

    # Popup Panel Settings
    enable_popup_panel: BoolProperty(
        name="Enable Popup Panel",
        description="Enable the ability to open Compify panel as popup in 3D viewport",
        default=True,
    )

    # Simple shortcut recording system
    shortcut_recording: BoolProperty(
        name="Recording Shortcut",
        description="Currently recording a new shortcut",
        default=False,
    )

    # Store the actual shortcut components (no underscore prefixes!)
    shortcut_key_internal: StringProperty(
        name="Internal Shortcut Key",
        description="Internal storage for shortcut key",
        default="C"
    )

    shortcut_ctrl_internal: BoolProperty(
        name="Internal Ctrl",
        description="Internal storage for ctrl modifier",
        default=False
    )

    shortcut_alt_internal: BoolProperty(
        name="Internal Alt",
        description="Internal storage for alt modifier",
        default=False
    )

    shortcut_shift_internal: BoolProperty(
        name="Internal Shift",
        description="Internal storage for shift modifier",
        default=False
    )

    shortcut_oskey_internal: BoolProperty(
        name="Internal OS Key",
        description="Internal storage for OS key modifier",
        default=False
    )

    # UI collapse state for combined updates and information section
    show_updates_info_section: BoolProperty(
        name="Show Updates and Information Section",
        description="Toggle updates and information section visibility",
        default=True,
    )

    # Update checking options
    update_channel: bpy.props.EnumProperty(
        name="Update Channel",
        description="Choose which repository to check for updates",
        items=[
            ('UNOFFICIAL', "Unofficial (mdreece)", "Check the unofficial repository with latest features"),
            ('OFFICIAL', "Original (EatTheFuture)", "Check the original official repository"),
        ],
        default='UNOFFICIAL',
    )

    # Update status tracking
    update_status: bpy.props.StringProperty(
        name="Update Status",
        description="Current update check status",
        default="",
    )

    update_available: BoolProperty(
        name="Update Available",
        description="Whether an update is available",
        default=False,
    )

    latest_version: bpy.props.StringProperty(
        name="Latest Version",
        description="Latest version found",
        default="",
    )

    # UI collapse state for popup panel section
    show_popup_panel_section: BoolProperty(
        name="Show Popup Panel Section",
        description="Toggle popup panel section visibility",
        default=True,
    )

    def draw(self, context):
        layout = self.layout

        # Combined Updates and Information Section (Collapsible)
        box = layout.box()
        row = box.row()
        row.prop(self, "show_updates_info_section",
                icon='TRIA_DOWN' if self.show_updates_info_section else 'TRIA_RIGHT',
                icon_only=True, emboss=False)
        row.label(text="Updates & Information", icon='INFO')

        if self.show_updates_info_section:
            col = box.column()

            # Update channel selection at the top
            channel_box = col.box()
            channel_box.label(text="Version Channel", icon='PREFERENCES')

            channel_row = channel_box.row()
            channel_row.prop(self, "update_channel", text="")

            # Dynamic Information section based on selected channel
            info_box = col.box()

            # Header changes based on channel
            header_row = info_box.row()
            header_row.alignment = 'CENTER'
            if self.update_channel == 'UNOFFICIAL':
                header_row.label(text="Unofficial Version - Latest Features", icon='EXPERIMENTAL')
            else:
                header_row.label(text="Official Version - Stable Release", icon='BOOKMARKS')

            info_box.separator()

            # Ian Hubert's Patreon (always shown)
            patreon_box = info_box.box()
            patreon_header = patreon_box.row()
            patreon_header.scale_y = 1.1
            patreon_btn = patreon_header.operator("wm.url_open", text="❤️  Support Ian Hubert on Patreon", icon='FUND')
            patreon_btn.url = "https://www.patreon.com/IanHubert"

            patreon_desc = patreon_box.row()
            patreon_desc.alignment = 'CENTER'
            patreon_desc.scale_y = 0.8
            patreon_desc.label(text="Thank you for funding Compify's development!", icon='NONE')

            info_box.separator(factor=0.5)

            # Dynamic links based on selected channel
            links_col = info_box.column(align=True)

            if self.update_channel == 'UNOFFICIAL':
                # Unofficial version links
                unofficial_row = links_col.row(align=True)
                unofficial_row.scale_y = 1.0
                unofficial_btn = unofficial_row.operator("wm.url_open", text="🔗  Unofficial Repository & Docs", icon='URL')
                unofficial_btn.url = "https://github.com/mdreece/compify"

                # Feature description
                info_box.separator(factor=0.3)
                desc_col = info_box.column()
                desc_col.scale_y = 0.7
                desc_col.alignment = 'CENTER'

                desc_row1 = desc_col.row()
                desc_row1.alignment = 'CENTER'
                desc_row1.label(text="🔗 Enhanced features & latest fixes from unofficial repository")

                # Features list
                features_box = info_box.box()
                features_box.label(text="Unofficial Enhancements:", icon='PLUS')
                feature_col = features_box.column()
                feature_col.scale_y = 0.8
                feature_col.label(text="• Enhanced reflection system with selective control", icon='BLANK1')
                feature_col.label(text="• Improved material handling and ColorRamp preservation", icon='BLANK1')
                feature_col.label(text="• Better UI and user experience improvements", icon='BLANK1')
                feature_col.label(text="• Blender 4.3-5.0 compatibility updates", icon='BLANK1')

            else:
                # Official version links
                official_row = links_col.row(align=True)
                official_row.scale_y = 1.0
                official_btn = official_row.operator("wm.url_open", text="📚  Official Repository & Documentation", icon='HELP')
                official_btn.url = "https://github.com/EatTheFuture/compify"

                # Feature description
                info_box.separator(factor=0.3)
                desc_col = info_box.column()
                desc_col.scale_y = 0.7
                desc_col.alignment = 'CENTER'

                desc_row1 = desc_col.row()
                desc_row1.alignment = 'CENTER'
                desc_row1.label(text="📚 Official stable version with original feature set")

                # Warning about missing features
                warning_box = info_box.box()
                warning_box.alert = True
                warning_box.label(text="⚠️ Note: Official version lacks unofficial enhancements", icon='ERROR')
                missing_col = warning_box.column()
                missing_col.scale_y = 0.8
                missing_col.label(text="• No enhanced reflection system", icon='BLANK1')
                missing_col.label(text="• Basic material handling only", icon='BLANK1')
                missing_col.label(text="• Limited UI improvements", icon='BLANK1')

                # Install official version option
                install_box = info_box.box()
                install_box.label(text="Switch to Official Version:", icon='IMPORT')
                install_row = install_box.row()
                install_row.scale_y = 1.2
                install_op = install_row.operator("compify.install_update", text="Install Official Version", icon='PACKAGE')
                install_op.url = "https://github.com/EatTheFuture/compify/archive/refs/heads/master.zip"
                install_op.is_official = True

            # Version info
            info_box.separator(factor=0.3)
            version_row = info_box.row()
            version_row.alignment = 'CENTER'
            version_row.scale_y = 0.8
            if self.update_channel == 'UNOFFICIAL':
                version_row.label(text="Compify v0.1.5 - Unofficial Enhanced Edition", icon='EXPERIMENTAL')
            else:
                version_row.label(text="Compify - Official Stable Version", icon='CHECKMARK')

            # Update checking section
            col.separator()
            update_box = col.box()
            update_box.label(text="Update Checking", icon='FILE_REFRESH')

            # Check for updates button
            check_row = update_box.row()
            check_row.scale_y = 1.2
            if self.update_channel == 'UNOFFICIAL':
                check_row.operator("compify.check_updates", text="Check for Unofficial Updates", icon='EXPERIMENTAL')
            else:
                check_row.operator("compify.check_updates", text="Check for Official Updates", icon='FILE_REFRESH')

            # Update status display
            if self.update_status:
                status_box = update_box.box()

                if self.update_available:
                    status_box.alert = False
                    status_row = status_box.row()
                    status_row.label(text=f"✅ Update Available: {self.latest_version}", icon='CHECKMARK')

                    # Warning about version differences when switching to official
                    if self.update_channel == 'OFFICIAL':
                        warning_box = status_box.box()
                        warning_box.alert = True
                        warning_box.label(text="⚠️ Warning: Switching to Official Version", icon='ERROR')
                        warning_box.label(text="This will remove unofficial features you currently have!", icon='BLANK1')

                    # Install button
                    install_row = status_box.row()
                    install_row.scale_y = 1.3
                    install_op = install_row.operator("compify.install_update", text="Install Update", icon='IMPORT')
                    install_op.url = self.get_download_url()
                    install_op.is_official = (self.update_channel == 'OFFICIAL')

                else:
                    status_box.label(text="✅ You have the latest version!", icon='CHECKMARK')

            elif self.update_status == "ERROR":
                error_box = update_box.box()
                error_box.alert = True
                error_box.label(text="❌ Failed to check for updates", icon='ERROR')
                error_box.label(text="Check your internet connection", icon='BLANK1')

        # Popup Panel Settings (Collapsible)
        box = layout.box()
        row = box.row()
        row.prop(self, "show_popup_panel_section",
                icon='TRIA_DOWN' if self.show_popup_panel_section else 'TRIA_RIGHT',
                icon_only=True, emboss=False)
        row.label(text="Popup Panel Settings", icon='WINDOW')

        if self.show_popup_panel_section:
            col = box.column()
            col.prop(self, "enable_popup_panel")

            if self.enable_popup_panel:
                col.separator()

                # Simple shortcut display and recording
                shortcut_box = col.box()

                # Current shortcut display
                current_shortcut = self.get_current_shortcut_display()

                # Main shortcut row
                main_row = shortcut_box.row(align=True)
                main_row.scale_y = 1.3

                # Shortcut display button
                if self.shortcut_recording:
                    shortcut_btn = main_row.operator("compify.record_shortcut",
                                                   text="Press keys now...",
                                                   icon='REC')
                    shortcut_btn.deferred = False  # Stop recording
                else:
                    shortcut_btn = main_row.operator("compify.record_shortcut",
                                                   text=current_shortcut,
                                                   icon='KEYINGSET')
                    shortcut_btn.deferred = True  # Start recording

                # Clear button
                clear_btn = main_row.operator("compify.clear_shortcut", text="", icon='X')

                # Recording instructions
                if self.shortcut_recording:
                    info_row = shortcut_box.row()
                    info_row.alert = True
                    info_row.label(text="Press any key combination (Escape to cancel)", icon='INFO')
                else:
                    # Show helpful info
                    info_row = shortcut_box.row()
                    info_row.label(text="Click the shortcut button above to set a new key combination")

                # Conflict warnings
                if not self.shortcut_recording:
                    conflicts = self.check_shortcut_conflicts()
                    if conflicts:
                        conflict_box = shortcut_box.box()
                        conflict_box.alert = True
                        conflict_box.label(text="⚠ Potential Conflicts:", icon='ERROR')
                        for conflict in conflicts[:2]:  # Limit to 2 for cleaner UI
                            conflict_box.label(text=f"• {conflict}")

                # Apply/Status section
                shortcut_box.separator()
                status_row = shortcut_box.row()

                # Check if keymap is active
                keymap_info = get_keymap_info()
                if keymap_info:
                    active_shortcut = f"{'+'.join(keymap_info['modifiers'] + [keymap_info['key']])}"
                    if active_shortcut == current_shortcut.replace(" ", ""):
                        status_row.label(text="✓ Shortcut Active", icon='CHECKMARK')
                    else:
                        status_row.label(text="⚠ Shortcut Changed - Click Apply", icon='ERROR')
                        apply_row = shortcut_box.row()
                        apply_row.scale_y = 1.2
                        apply_row.operator("compify.update_keymap", text="Apply New Shortcut", icon='CHECKMARK')
                else:
                    if current_shortcut != "None":
                        apply_row = status_row.row()
                        apply_row.scale_y = 1.2
                        apply_row.operator("compify.update_keymap", text="Apply Shortcut", icon='CHECKMARK')
                    else:
                        status_row.label(text="No shortcut set", icon='RADIOBUT_OFF')

    def get_current_shortcut_display(self):
        """Get a clean display string for the current shortcut"""
        if not self.shortcut_key_internal:
            return "None"

        modifiers = []
        if self.shortcut_ctrl_internal:
            modifiers.append("Ctrl")
        if self.shortcut_alt_internal:
            modifiers.append("Alt")
        if self.shortcut_shift_internal:
            modifiers.append("Shift")
        if self.shortcut_oskey_internal:
            modifiers.append("Cmd" if bpy.app.platform == 'DARWIN' else "Win")

        # Clean up key display
        key_display = self.shortcut_key_internal
        key_map = {
            'SPACE': 'Space',
            'RET': 'Enter',
            'TAB': 'Tab',
            'ESC': 'Escape',
            'DEL': 'Delete',
            'BACK_SPACE': 'Backspace',
            'LEFTMOUSE': 'LMB',
            'RIGHTMOUSE': 'RMB',
            'MIDDLEMOUSE': 'MMB'
        }

        if key_display in key_map:
            key_display = key_map[key_display]
        elif key_display.startswith('NUMPAD_'):
            key_display = f"Num {key_display.replace('NUMPAD_', '')}"

        if modifiers:
            return f"{' + '.join(modifiers)} + {key_display}"
        else:
            return key_display

    def check_shortcut_conflicts(self):
        """Simplified conflict checking"""
        if not self.shortcut_key_internal:
            return []

        conflicts = []
        key = self.shortcut_key_internal
        has_modifiers = self.shortcut_ctrl_internal or self.shortcut_alt_internal or self.shortcut_shift_internal or self.shortcut_oskey_internal

        # Only warn about major conflicts
        if not has_modifiers:
            major_conflicts = {
                'G': "Move tool",
                'R': "Rotate tool",
                'S': "Scale tool",
                'X': "Delete menu",
                'TAB': "Edit mode toggle",
                'SPACE': "Search menu",
            }
            if key in major_conflicts:
                conflicts.append(f"Conflicts with {major_conflicts[key]}")

        # Check common Ctrl shortcuts
        if self.shortcut_ctrl_internal and not (self.shortcut_alt_internal or self.shortcut_shift_internal):
            ctrl_conflicts = {
                'C': "Copy",
                'V': "Paste",
                'Z': "Undo",
                'S': "Save",
                'O': "Open"
            }
            if key in ctrl_conflicts:
                conflicts.append(f"Conflicts with Ctrl+{key} ({ctrl_conflicts[key]})")

        return conflicts

    def get_download_url(self):
        """Get the appropriate download URL based on update channel"""
        if self.update_channel == 'OFFICIAL':
            return "https://github.com/EatTheFuture/compify/archive/refs/heads/master.zip"
        else:
            return "https://github.com/mdreece/compify/archive/refs/heads/master.zip"


# Keymap management functions
def get_compify_preferences():
    """Get the Compify addon preferences"""
    return bpy.context.preferences.addons[__package__].preferences


def add_compify_keymap_from_prefs(prefs):
    """Add keymap for Compify popup panel using preferences"""
    if not prefs.shortcut_key_internal:
        return False

    # Get the keymap
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name='3D View', space_type='VIEW_3D')

        # Create the keymap item
        kmi = km.keymap_items.new(
            "compify.open_popup_panel",
            type=prefs.shortcut_key_internal,
            value='PRESS',
            ctrl=prefs.shortcut_ctrl_internal,
            alt=prefs.shortcut_alt_internal,
            shift=prefs.shortcut_shift_internal,
            oskey=prefs.shortcut_oskey_internal
        )

        # Store reference for later removal
        if not hasattr(bpy.types.Scene, 'compify_keymap_items'):
            bpy.types.Scene.compify_keymap_items = []
        bpy.types.Scene.compify_keymap_items.append((km, kmi))

        return True

    return False


def remove_compify_keymap():
    """Remove Compify keymap"""
    if hasattr(bpy.types.Scene, 'compify_keymap_items'):
        for km, kmi in bpy.types.Scene.compify_keymap_items:
            try:
                km.keymap_items.remove(kmi)
            except:
                pass  # Keymap item might already be removed
        bpy.types.Scene.compify_keymap_items.clear()


def get_keymap_info():
    """Get information about current keymap"""
    if hasattr(bpy.types.Scene, 'compify_keymap_items') and bpy.types.Scene.compify_keymap_items:
        try:
            km, kmi = bpy.types.Scene.compify_keymap_items[0]
            modifiers = []
            if kmi.ctrl:
                modifiers.append('CTRL')
            if kmi.alt:
                modifiers.append('ALT')
            if kmi.shift:
                modifiers.append('SHIFT')
            if kmi.oskey:
                modifiers.append('OSKEY')

            return {
                'key': kmi.type,
                'modifiers': modifiers
            }
        except:
            pass
    return None


# Registration functions
def register_preferences():
    """Register preferences classes and setup keymap"""
    bpy.utils.register_class(CompifyPopupPanel)
    bpy.utils.register_class(CompifyOpenPopupOperator)
    bpy.utils.register_class(CompifyCheckUpdatesOperator)
    bpy.utils.register_class(CompifyInstallUpdateOperator)
    bpy.utils.register_class(CompifyRecordShortcutOperator)
    bpy.utils.register_class(CompifyClearShortcutOperator)
    bpy.utils.register_class(CompifyUpdateKeymapOperator)
    bpy.utils.register_class(CompifyRemoveKeymapOperator)
    bpy.utils.register_class(CompifyAddonPreferences)

    # Initialize keymap if preferences exist
    try:
        prefs = get_compify_preferences()
        if prefs.enable_popup_panel and prefs.shortcut_key_internal:
            add_compify_keymap_from_prefs(prefs)
    except:
        pass  # Preferences might not be available yet


def unregister_preferences():
    """Unregister preferences classes and remove keymap"""
    remove_compify_keymap()

    bpy.utils.unregister_class(CompifyAddonPreferences)
    bpy.utils.unregister_class(CompifyRemoveKeymapOperator)
    bpy.utils.unregister_class(CompifyUpdateKeymapOperator)
    bpy.utils.unregister_class(CompifyClearShortcutOperator)
    bpy.utils.unregister_class(CompifyRecordShortcutOperator)
    bpy.utils.unregister_class(CompifyInstallUpdateOperator)
    bpy.utils.unregister_class(CompifyCheckUpdatesOperator)
    bpy.utils.unregister_class(CompifyOpenPopupOperator)
    bpy.utils.unregister_class(CompifyPopupPanel)

    # Clean up keymap references
    if hasattr(bpy.types.Scene, 'compify_keymap_items'):
        del bpy.types.Scene.compify_keymap_items
