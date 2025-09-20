# Compify v0.1.5 – Blender Addon

**A Blender addon for easier/better compositing in 3D space.**  
This addon was originally created by **Nathan Vegdahl** and **Ian Hubert**. Without their work, this unofficial version would not exist. **All credit to them.**

---

<img width="383" height="213" alt="Screenshot_20250920_155311" src="https://github.com/user-attachments/assets/8fb013da-f923-4d66-9a96-b6798e73da52" />

---

## Support Ian Hubert  
Want this addon to have *official support and updates*?  
🎉 **Subscribe to Ian’s Patreon:** [https://www.patreon.com/IanHubert](https://www.patreon.com/IanHubert)  
*(I am doing this purely as a user and make no income from these changes/updates.)*

<img width="409" height="513" alt="Screenshot_20250920_160241" src="https://github.com/user-attachments/assets/eec98d54-c287-4f73-8473-025e0852036e" />

---

## Original Addon Description

> This addon is currently beta quality. There may still be major bugs and rough edges, but in general it should basically work. Due to limitations in Blender's Python APIs, there are also some rough edges that are unfortunately impossible to fix at the moment.

---

## Features Added in This Fork

This fork expands the original Compify with additional quality-of-life features and new compositing tools:

### 🔧 Preferences & Shortcuts
- Customizable keyboard shortcuts to open the main panel without navigating the UI.
- Preferences for managing updates:
  - **Official GitHub** or this **forked build**
  - Installing the official version will **remove this fork** from your system

### 🪞 Reflections System
Added tools for compositing reflections directly into your scenes:

- **Reflective Geo**  
  > Loads into the `Footage Geo` collection.  
  Add geometry that *should be reflected* in the environment.

- **Reflected Geo**  
  > Loads as its own collection.  
  Add geometry that *should reflect* the objects from above.

- **Holdout Geo**  
  > Blocks reflections inside the `Reflected Geo` objects.  
  Great for occlusion control.

All of the above have dedicated **UI buttons**.

You can control reflections with:
- Noise
- Texture
- Compify material
- Color ramp adjustments
- Presets for quick setup

---

## Requirements

- **Blender 4.0.0 or later**  
  (Tested up to Blender **v5.0.0**)

---

## License

This addon is licensed under the **GNU General Public License v2.0**.  
See [LICENSE.md](./LICENSE.md) for full details.

---

## Contributing

Although **Nathan** and **Ian** are not looking for direct contributions to the official version, I'm open to collaborating for sure!

I love this tool too much, and I find myself thinking of new features almost weekly. Feel free to reach out or open issues!!!
