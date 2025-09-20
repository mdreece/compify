# Compify v0.1.5 – Blender Addon

**A Blender addon for easier/better compositing in 3D space.**  
This addon was originally created by **Nathan Vegdahl** and **Ian Hubert**. Without their work, this unofficial version would not exist. **All credit to them.**

---

<p align="center">
  <img width="383" height="213" src="https://github.com/user-attachments/assets/8fb013da-f923-4d66-9a96-b6798e73da52" alt="Main UI Preview" />
</p>

---

## 🙌 Support Ian Hubert

Want this addon to have *official support and updates*?  
🎉 **Subscribe to Ian’s Patreon:**  
👉 [https://www.patreon.com/IanHubert](https://www.patreon.com/IanHubert)

> *(I am doing this purely as a user and make no income from these changes/updates.)*

<p align="center">
  <img width="409" height="513" src="https://github.com/user-attachments/assets/eec98d54-c287-4f73-8473-025e0852036e" alt="Support Ian Screenshot" />
</p>

---

## 📦 Original Addon Description

> This addon is currently beta quality. There may still be major bugs and rough edges, but in general it should basically work.  
> Due to limitations in Blender's Python APIs, there are also some rough edges that are unfortunately impossible to fix at the moment.

---

## 🧪 How to Use

The moderate expectation is that you have recreated your scene in some way for the Compify process to work with.  
This is a shot I took and recreated by tracking and then extruding with the wonderful default cube (lol).

### Wireframe
<p align="center">
  <img width="796" height="454" src="https://github.com/user-attachments/assets/b2f9fd4b-1042-461c-b4bb-158d7ed1c02e" alt="Wireframe View" />
</p>

### Solid View
<p align="center">
  <img width="798" height="451" src="https://github.com/user-attachments/assets/54186a4e-e5cf-4476-882a-57edfdb82a3d" alt="Solid View" />
</p>

---

### 1. Open Compify Panel

Access the Compify menu in the **Scene Properties** (or set a popup panel shortcut in preferences).

<p align="center">
  <img width="482" height="269" src="https://github.com/user-attachments/assets/546e58e4-c5e5-4229-8e0c-5c3c326cfe2f" alt="Compify Panel UI" />
</p>

---

### 2. Footage Settings

<p align="center">
  <img width="436" height="131" src="https://github.com/user-attachments/assets/05ebcd71-82bf-42aa-9069-0308ca8a198a" alt="Footage Settings" />
</p>

- Select your **footage**
- Choose **color space**
- Set your **scene camera**

---

### 3. Collections Setup

<p align="center">
  <img width="436" height="131" src="https://github.com/user-attachments/assets/2a7b4302-78d6-4991-9ed1-809f0b780bf7" alt="Collections UI" />
</p>

- Use the `+` next to **Footage Geo** to create the collection.
  - Add objects/geometry that the footage will be projected onto.
- Use the `+` next to **Footage Lights** to create the collection.
  - Add recreated lights here (HDRI/World is handled separately).
- Click **Prep Scene** → then **Bake Footage Lighting**

<p align="center">
  <img width="438" height="87" src="https://github.com/user-attachments/assets/4e40f38d-01ff-4788-80e6-a41dbb9e2ca8" alt="Bake Lighting UI" />
</p>

---

### 4. Rendered Result

<p align="center">
  <img width="799" height="453" src="https://github.com/user-attachments/assets/d169156c-756b-42de-ab5f-f18b13a82507" alt="Rendered View" />
</p>

> *If your scene has reflections, hold on—those are handled below!*

---

## ✨ Features Added in This Fork

This fork expands the original Compify with **quality-of-life improvements** and **new compositing tools**.

---

### 🔧 Preferences & Shortcuts

- Customizable keyboard shortcut to open the Compify panel
- Auto-update support:
  - Switch between the **official GitHub release** or this **forked build**
  - Installing the official version will automatically **remove this fork**

---

### 🪞 Reflections System

Tools for compositing **reflections** directly into your scenes.

- **Reflective Geo**  
  Loads into `Footage Geo` collection.  
  → Add objects that *should be reflected* in the scene.

- **Reflected Geo**  
  Loads as its own collection.  
  → Add objects that *reflect* the ones above.

- **Holdout Geo**  
  Blocks unwanted reflections inside `Reflected Geo` objects.  
  → Perfect for occlusion and cleanup.

Each has dedicated **UI buttons**.

Reflection controls include:
- Noise
- Texture maps
- Compify materials
- Color ramp adjustments
- Presets for fast setup

---

## 🧰 Requirements

- **Blender 4.0.0 or later**  
  (Tested with Blender **v5.0.0**)

---

## 📄 License

Licensed under the **GNU General Public License v2.0**  
See [LICENSE.md](./LICENSE.md) for full details.

---

## 🤝 Contributing

Although **Nathan** and **Ian** are not accepting contributions to the official version,  
I'm very open to feedback and collaboration on this fork!

> I love this tool and keep thinking of new features almost weekly.  
> Feel free to [open issues](../../issues) or contact me!

---

