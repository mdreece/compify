import bpy
from bpy.types import AddonPreferences
from bpy.props import BoolProperty, StringProperty


class CompifyPopupPanel(bpy.types.Panel):
    bl_label = "Compify"
    bl_idname = "VIEW3D_PT_compify_popup"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Compify"

    def draw(self, context):
        from . import CompifyPanel

        layout = self.layout
        header_box = layout.box()
        header_row = header_box.row()
        header_row.alignment = 'CENTER'
        header_row.scale_y = 1.1
        header_row.label(text="COMPIFY", icon='SEQ_CHROMA_SCOPE')

        layout.separator(factor=0.5)

        CompifyPanel.draw(self, context)


class CompifyOpenPopupOperator(bpy.types.Operator):
    bl_idname = "compify.open_popup_panel"
    bl_label = "Open Compify Panel"
    bl_description = "Open the Compify panel as a popup in the 3D viewport"
    bl_options = {'REGISTER'}

    def execute(self, context):
        prefs = get_compify_preferences()
        if not prefs.enable_popup_panel:
            self.report({'WARNING'}, "Popup panel is disabled in addon preferences")
            return {'CANCELLED'}

        return context.window_manager.invoke_popup(self, width=400)

    def draw(self, context):
        CompifyPopupPanel.draw(self, context)


class CompifyCheckUpdatesOperator(bpy.types.Operator):
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
    bl_description = "Click then set. Use CTRL, ALT, SHIFT, etc.."

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

    enable_popup_panel: BoolProperty(
        name="Enable Popup Panel",
        description="Enable the ability to open Compify panel as popup in 3D viewport",
        default=True,
    )

    shortcut_recording: BoolProperty(
        name="Recording Shortcut",
        description="Currently recording a new shortcut",
        default=False,
    )

    shortcut_key_internal: StringProperty(
        name="Internal Shortcut Key",
        description="Internal storage for shortcut key",
        default="none"
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

    show_updates_info_section: BoolProperty(
        name="Show Updates and Information Section",
        description="Toggle updates and information section visibility",
        default=True,
    )

    update_channel: bpy.props.EnumProperty(
        name="Update Channel",
        description="Choose which repository to check for updates",
        items=[
            ('UNOFFICIAL', "Unofficial (mdreece)", "Check the unofficial repository with latest features"),
            ('OFFICIAL', "Original (EatTheFuture)", "Check the original official repository"),
        ],
        default='UNOFFICIAL',
    )

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

    show_popup_panel_section: BoolProperty(
        name="Show Popup Panel Section",
        description="Toggle popup panel section visibility",
        default=True,
    )

    def draw(self, context):
        layout = self.layout

        box = layout.box()
        row = box.row()
        row.prop(self, "show_updates_info_section",
                icon='TRIA_DOWN' if self.show_updates_info_section else 'TRIA_RIGHT',
                icon_only=True, emboss=False)
        row.label(text="Updates & Information", icon='INFO')

        if self.show_updates_info_section:
            col = box.column()

            channel_box = col.box()
            channel_box.label(text="Version Channel", icon='PREFERENCES')

            channel_row = channel_box.row()
            channel_row.prop(self, "update_channel", text="")

            info_box = col.box()

            header_row = info_box.row()
            header_row.alignment = 'CENTER'
            if self.update_channel == 'UNOFFICIAL':
                header_row.label(text="Unofficial Version - Latest Features", icon='EXPERIMENTAL')
            else:
                header_row.label(text="Official Version - Stable Release", icon='BOOKMARKS')

            info_box.separator()

            # Ian's Patreon! SUPPORT !!! lol
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


            links_col = info_box.column(align=True)

            if self.update_channel == 'UNOFFICIAL':
                unofficial_row = links_col.row(align=True)
                unofficial_row.scale_y = 1.0
                unofficial_btn = unofficial_row.operator("wm.url_open", text="🔗  Unofficial Repository & Docs", icon='URL')
                unofficial_btn.url = "https://github.com/mdreece/compify"

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
                official_row = links_col.row(align=True)
                official_row.scale_y = 1.0
                official_btn = official_row.operator("wm.url_open", text="📚  Official Repository & Documentation", icon='HELP')
                official_btn.url = "https://github.com/EatTheFuture/compify"

                info_box.separator(factor=0.3)
                desc_col = info_box.column()
                desc_col.scale_y = 0.7
                desc_col.alignment = 'CENTER'

                desc_row1 = desc_col.row()
                desc_row1.alignment = 'CENTER'
                desc_row1.label(text="📚 Official stable version with original feature set")

                warning_box = info_box.box()
                warning_box.alert = True
                warning_box.label(text="⚠️ Note: Official version lacks unofficial enhancements", icon='ERROR')
                missing_col = warning_box.column()
                missing_col.scale_y = 0.8
                missing_col.label(text="• No enhanced reflection system", icon='BLANK1')
                missing_col.label(text="• Basic material handling only", icon='BLANK1')
                missing_col.label(text="• Limited UI improvements", icon='BLANK1')

                install_box = info_box.box()
                install_box.label(text="Switch to Official Version:", icon='IMPORT')
                install_row = install_box.row()
                install_row.scale_y = 1.2
                install_op = install_row.operator("compify.install_update", text="Install Official Version", icon='PACKAGE')
                install_op.url = "https://github.com/EatTheFuture/compify/archive/refs/heads/master.zip"
                install_op.is_official = True

            info_box.separator(factor=0.3)
            version_row = info_box.row()
            version_row.alignment = 'CENTER'
            version_row.scale_y = 0.8
            if self.update_channel == 'UNOFFICIAL':
                version_row.label(text="Compify v0.1.5 - Unofficial Enhanced Edition", icon='EXPERIMENTAL')
            else:
                version_row.label(text="Compify - Official Stable Version", icon='CHECKMARK')

            col.separator()
            update_box = col.box()
            update_box.label(text="Update Checking", icon='FILE_REFRESH')

            check_row = update_box.row()
            check_row.scale_y = 1.2
            if self.update_channel == 'UNOFFICIAL':
                check_row.operator("compify.check_updates", text="Check for Unofficial Updates", icon='EXPERIMENTAL')
            else:
                check_row.operator("compify.check_updates", text="Check for Official Updates", icon='FILE_REFRESH')

            if self.update_status:
                status_box = update_box.box()

                if self.update_available:
                    status_box.alert = False
                    status_row = status_box.row()
                    status_row.label(text=f"✅ Update Available: {self.latest_version}", icon='CHECKMARK')

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

                shortcut_box = col.box()

                current_shortcut = self.get_current_shortcut_display()

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
        if self.update_channel == 'OFFICIAL':
            return "https://github.com/EatTheFuture/compify/archive/refs/heads/master.zip"
        else:
            return "https://github.com/mdreece/compify/archive/refs/heads/master.zip"


def get_compify_preferences():
    return bpy.context.preferences.addons[__package__].preferences


def add_compify_keymap_from_prefs(prefs):
    if not prefs.shortcut_key_internal:
        return False

    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name='3D View', space_type='VIEW_3D')

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
    if hasattr(bpy.types.Scene, 'compify_keymap_items'):
        for km, kmi in bpy.types.Scene.compify_keymap_items:
            try:
                km.keymap_items.remove(kmi)
            except:
                pass
        bpy.types.Scene.compify_keymap_items.clear()


def get_keymap_info():
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
    bpy.utils.register_class(CompifyPopupPanel)
    bpy.utils.register_class(CompifyOpenPopupOperator)
    bpy.utils.register_class(CompifyCheckUpdatesOperator)
    bpy.utils.register_class(CompifyInstallUpdateOperator)
    bpy.utils.register_class(CompifyRecordShortcutOperator)
    bpy.utils.register_class(CompifyClearShortcutOperator)
    bpy.utils.register_class(CompifyUpdateKeymapOperator)
    bpy.utils.register_class(CompifyRemoveKeymapOperator)
    bpy.utils.register_class(CompifyAddonPreferences)

    try:
        prefs = get_compify_preferences()
        if prefs.enable_popup_panel and prefs.shortcut_key_internal:
            add_compify_keymap_from_prefs(prefs)
    except:
        pass


def unregister_preferences():
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

    if hasattr(bpy.types.Scene, 'compify_keymap_items'):
        del bpy.types.Scene.compify_keymap_items
