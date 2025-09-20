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

## How to Use 
The moderate expectation is that you have recreated your scene in some way for the compify process to work with.
This is a shot I took and recreated by tracking and then extruding with the wonderful default cube (lol)

**Wireframe**
<img width="796" height="454" alt="Screenshot_20250920_163603" src="https://github.com/user-attachments/assets/b2f9fd4b-1042-461c-b4bb-158d7ed1c02e" />

**Solid View**
<img width="798" height="451" alt="Screenshot_20250920_163809" src="https://github.com/user-attachments/assets/54186a4e-e5cf-4476-882a-57edfdb82a3d" />


1. Access the Compify menu in the Scene Properties (or set a popup panel shortcut in preferences)
<img width="482" height="269" alt="Screenshot_20250920_162306" src="https://github.com/user-attachments/assets/546e58e4-c5e5-4229-8e0c-5c3c326cfe2f" />

2. In the Footage options:
<img width="436" height="131" alt="Screenshot_20250920_162417" src="https://github.com/user-attachments/assets/05ebcd71-82bf-42aa-9069-0308ca8a198a" />
 - Select your footage
 - Select the color space
 - Select your scene camera

3. In the Collections options:
<img width="436" height="131" alt="Screenshot_20250920_162417" src="https://github.com/user-attachments/assets/2a7b4302-78d6-4991-9ed1-809f0b780bf7" />
 - Use the '+' next to Footage Geo to create the 'Footage Geo' collection.
     - Add any objects/geometry that the footage will be projected onto into this collection.
 - Use the '+' next to Footage Lights to create the 'Footage Lights' collection.
     - Add any lights being recreated to this collection (HDRI/World is accounted for)
 - Click 'Prep Scene' then 'Bake Footage Lighting'
<img width="438" height="87" alt="Screenshot_20250920_163151" src="https://github.com/user-attachments/assets/4e40f38d-01ff-4788-80e6-a41dbb9e2ca8" />

**Rendered View**
<img width="799" height="453" alt="Screenshot_20250920_164054" src="https://github.com/user-attachments/assets/d169156c-756b-42de-ab5f-f18b13a82507" />

4. If you're scene has reflections, one second. I need to see what this looks like so far lol




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
