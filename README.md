# Compify v0.2.1 – Blender Addon

**A Blender addon for easier/better compositing in 3D space.**  

Demo: https://youtu.be/GIGjy5w5mak

This addon was originally created by **Nathan Vegdahl** and **Ian Hubert**. Without their work, this unofficial version would not exist. **All credit to them.**

**THERE ARE LIMITATIONS WITH THIS ADDON. MAIN KNOWN IS NO OPAQUE REFLECTIONS ATM (wip). THERE ARE OTHERS HERE AND THERE**

---

<img width="383" height="213" src="https://github.com/user-attachments/assets/8fb013da-f923-4d66-9a96-b6798e73da52" alt="Main UI Preview" />



## 🙌 Support Ian Hubert

 **Subscribe to Ian’s Patreon:**  
[https://www.patreon.com/IanHubert](https://www.patreon.com/IanHubert)

 **Ian's Official Github for Compify:** 
 
https://github.com/EatTheFuture/compify

> *(I am doing this purely as a user and make no income from these changes/updates.)*

---

<img width="431" height="622" alt="Screenshot_20250928_001606" src="https://github.com/user-attachments/assets/03fe8079-f2a2-442b-898f-51098e4ccfa1" />


##  Original Addon Description

> This addon is currently beta quality. There may still be major bugs and rough edges, but in general it should basically work.  
> Due to limitations in Blender's Python APIs, there are also some rough edges that are unfortunately impossible to fix at the moment.

---

## Examples 

<img width="960" height="540" alt="hall" src="https://github.com/user-attachments/assets/c11d4716-7084-454e-bb33-de304401a655" />

<img width="960" height="540" alt="pond" src="https://github.com/user-attachments/assets/38e612fd-982e-42f5-98e8-9c5dca0ec232" />

![TankTest4](https://github.com/user-attachments/assets/0b50379e-2d7f-4147-8cdc-de9597af7cb4)


---

##  HOW TO USE

The moderate expectation is that you have recreated your scene in some way for the Compify process to work with.
- Shoot your footage
- Track your footage
- Recreate the geometry of your footage (be sure to recalculate normals in mesh tools if needed)
  
This is a shot I took and recreated by tracking and then extruding with the wonderful default cube (lol).

### Wireframe

<img width="846" height="478" alt="Screenshot_20250928_142005" src="https://github.com/user-attachments/assets/2017b2a4-c9c6-4c0b-9b6a-dbcfccb4838a" />


### Solid View

<img width="848" height="479" alt="Screenshot_20250928_142033" src="https://github.com/user-attachments/assets/aaed7926-5bbd-4e12-b830-8679daeb6220" />

### Rendered View

<img width="847" height="482" alt="Screenshot_20250928_142821" src="https://github.com/user-attachments/assets/10c1e287-4e74-4658-8ea3-6cfc30c46d29" />

---

### 1. Open Compify Panel

Access the Compify menu in the **Scene Properties** (or popup panel/UI location).

<img width="477" height="211" alt="Screenshot_20250928_142150" src="https://github.com/user-attachments/assets/ab829664-866d-484c-8a06-27bc08e267d9" />

---

### 2. Footage Settings

<img width="428" height="133" alt="Screenshot_20250928_142344" src="https://github.com/user-attachments/assets/2a9a11fb-89c6-47a4-ae7a-12b1756c0ebc" />

- Select your **footage** from where it is saved.
- Choose the **color space** for your selected footage.
- Select your **scene camera**

---

### 3. Collections Setup

<img width="424" height="128" alt="Screenshot_20250928_142426" src="https://github.com/user-attachments/assets/8494a130-ad31-4427-a285-949b45111860" />

- Use the `+` next to **Footage Geo** to create the collection.
  - Add objects/geometry that the footage will be projected onto.
- Use the `+` next to **Footage Lights** to create the collection.
  - Add recreated lights here (HDRI/World is handled separately).
    
<img width="174" height="42" alt="Screenshot_20250920_165812" src="https://github.com/user-attachments/assets/bbf9f9ae-8ff5-447f-bbe2-159afcb2212a" />

- Mesh Tools: Recalculate inside/outside normals.

<img width="414" height="153" alt="Screenshot_20250928_145650" src="https://github.com/user-attachments/assets/d1d8f01e-6aec-46c6-b9a0-d810287a8e3c" />

- Material reset: Clear Compify material from selected object.

<img width="422" height="90" alt="Screenshot_20250928_145810" src="https://github.com/user-attachments/assets/9ab73464-ce82-49a0-919f-8907bc0483b3" />

---

- Click **Prep Scene** → then **Bake Footage Lighting**

<img width="389" height="36" alt="Screenshot_20250928_142646" src="https://github.com/user-attachments/assets/30f67531-2fa3-4101-aa0d-09845548e5d7" />


<img width="844" height="479" alt="Screenshot_20250928_142920" src="https://github.com/user-attachments/assets/cac4cde2-5f1b-4512-963d-72c278f7847e" />


---

### If your scene does not have reflective surfaces, you are good to click on 'Render Animation with Compify Integration'. Be sure to set your output settings as you typically would. Otherwise, continue!

### 4. Reflections

<img width="422" height="149" alt="Screenshot_20250928_143001" src="https://github.com/user-attachments/assets/8fe489b4-e079-4e0d-9359-0ee562f1625e" />


### Reflective Geometry

- Use the '+' next to **Reflective Geo** to create the collection (will be in Footage Geo)

<img width="411" height="137" alt="Screenshot_20250928_144358" src="https://github.com/user-attachments/assets/0786d727-685b-4d61-af52-9b752b1b18e6" />

- Select the geometry that will be reflective and click 'Make Active Object Reflective' (or select from Object dropdown if already in reflective geo collection)

<img width="416" height="369" alt="Screenshot_20250928_144723" src="https://github.com/user-attachments/assets/7e40d58f-c720-4a94-a515-93954319caf9" />

- Roughness options: Value, Texture, Compify Footage
- Adjust the Strength/values as needed
- Texture and Compify have color ramps

### Reflected Geometry

- Use the '+' next to **Reflected Geo** to create the collection
- Once the collection is created, select your object that should be reflected and click 'Make Object Visible in Reflections' in Quick Actions.

<img width="411" height="66" alt="Screenshot_20250928_145104" src="https://github.com/user-attachments/assets/fccafee0-038f-4f1d-8d26-f5f45a254186" />

### Holdout Geometry

- Use the '+' next to **Holdout Geo** to create the collection
- Once the collection is created, select your object that should be reflection holdouts and click 'Make Reflection Holdout' in Quick Actions.


<img width="412" height="63" alt="Screenshot_20250928_145353" src="https://github.com/user-attachments/assets/88f04d3f-039b-4ded-be99-1b9918d8b39c" />

---
    
- Click **Prep Scene** → then **Bake Footage Lighting**

<img width="843" height="476" alt="Screenshot_20250928_145539" src="https://github.com/user-attachments/assets/0fdf681c-a4d9-4e78-ab60-63aa0bd18e98" />


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
  Loads as its own collection.  
  → Add objects that *reflect* the ones above.

- **Reflected Geo**  
  Loads into `Footage Geo` collection.  
  → Add objects that *should be reflected* in the scene.

- **Holdout Geo**  
  Blocks unwanted reflections inside `Reflected Geo` objects.  
  → Perfect for occlusion and cleanup.

---

### Process/UI

 - There are UI button options to quickly mark/move objects
 - Scale is auto applied to objects added to Footage Geo collection when 'Prep Scene' is clicked

Reflection controls include:
- Noise
- Texture maps
- Compify materials
- Color ramp adjustments
- Presets for fast setup

---

## 🧰 Requirements

- **Blender Tested 4.0.0, 4.2.0(12), 4.3.2, 4.5.0, 5.0.0**  
  

---

## 📄 License

Licensed under the **GNU General Public License v2.0**  
See [LICENSE.md](./LICENSE.md) for full details.

---

## 🤝 Contributing
  
I'm very open to feedback and collaboration on this fork!

> I love this tool and keep thinking of new features almost weekly.  
> Feel free to [open issues](../../issues) or contact me!
> I commit a ton because I'm dumb.

---

