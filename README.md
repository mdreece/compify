# Compify v0.1.5: Blender Addon
A Blender addon for easier/better compositing in 3D space.
This addon was created by Nathan Vegdahl and Ian Hubert. Without it's original basis, this unofficial version would be NOTHING. All credit to them.

<img width="383" height="213" alt="Screenshot_20250920_155311" src="https://github.com/user-attachments/assets/8fb013da-f923-4d66-9a96-b6798e73da52" />

Patreon: https://www.patreon.com/IanHubert
Sub to Ians Patreon so it may get official supports and updates.
(I am purely doing this as a user and am making no income from these changes/updates)

<img width="409" height="513" alt="Screenshot_20250920_160241" src="https://github.com/user-attachments/assets/eec98d54-c287-4f73-8473-025e0852036e" />

The original description for this addon still applies:
  This addon is currently beta quality. There may still be major bugs and rough edges, but in general it should basically work. Due to limitations in Blender's Python APIs there are also some rough edges that are unforunately impossible to fix at the moment.

I have mainly added the following options:
 - Preferences options for keyboard shortcuts so the main panel can be brought up without having to navigate/change around the UI.
 - Preferences options for Updates. This is both for the official Github and my forked build here. The official version installation will wipe this instance from your machine entirely.
 - Reflections
     : Reflective Geo: Loads in the 'Footage Geo' collection. Add objects/geo that should be reflected in the environment
     : Reflected Geo: Loads as its own collection. Add objects/geo that should be reflecting in the above objects/geo
     : Holdout Geo: If the reflections should be blocked in the reflection geo itself, use this
 - The above reflection/holdout options all have buttons in the UI
 - Reflections can be adjusted using either noise, a texture OR the Compify material itself. There is a color ramp for adjustments and some presets.

This addon requires Blender 4.0.0 or later (Has been tested up to v5.0.0)


# License

The code in this addon is licensed under the GNU General Public License, version 2.  Please see LICENSE.md for details.


# Contributing
Although Nathan and Ian are not looking for direct contributions, I am certainly down for anything. I love this tool to much to let it die at any point and I find myself finding new features I'd want almost weekly.
