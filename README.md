# Compify v0.1.6 – Blender Addon

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

<img width="417" height="597" alt="Screenshot_20250921_150700" src="https://github.com/user-attachments/assets/21113225-67de-46d8-9248-fa83d7094c35" />


##  Original Addon Description

> This addon is currently beta quality. There may still be major bugs and rough edges, but in general it should basically work.  
> Due to limitations in Blender's Python APIs, there are also some rough edges that are unfortunately impossible to fix at the moment.

---

## Examples 

<img width="960" height="540" alt="hall" src="https://github.com/user-attachments/assets/c11d4716-7084-454e-bb33-de304401a655" />

<img width="960" height="540" alt="pond" src="https://github.com/user-attachments/assets/38e612fd-982e-42f5-98e8-9c5dca0ec232" />

---

##  How to Use

The moderate expectation is that you have recreated your scene in some way for the Compify process to work with.  
This is a shot I took and recreated by tracking and then extruding with the wonderful default cube (lol).

### Wireframe

<img width="796" height="454" src="https://github.com/user-attachments/assets/b2f9fd4b-1042-461c-b4bb-158d7ed1c02e" alt="Wireframe View" />


### Solid View

<img width="798" height="451" src="https://github.com/user-attachments/assets/54186a4e-e5cf-4476-882a-57edfdb82a3d" alt="Solid View" />


---

### 1. Open Compify Panel

Access the Compify menu in the **Scene Properties** (or set a popup panel shortcut in preferences).

<img width="482" height="269" src="https://github.com/user-attachments/assets/546e58e4-c5e5-4229-8e0c-5c3c326cfe2f" alt="Compify Panel UI" />

---

### 2. Footage Settings

<img width="436" height="131" src="https://github.com/user-attachments/assets/05ebcd71-82bf-42aa-9069-0308ca8a198a" alt="Footage Settings" />


- Select your **footage** from where it is saved.
- Choose the **color space** for your selected footage.
- Select your **scene camera**

---

### 3. Collections Setup

<img width="429" height="87" alt="Screenshot_20250920_171315" src="https://github.com/user-attachments/assets/50cb6fbb-3812-484a-a453-262962d416b3" />

- Use the `+` next to **Footage Geo** to create the collection.
  - Add objects/geometry that the footage will be projected onto.
- Use the `+` next to **Footage Lights** to create the collection.
  - Add recreated lights here (HDRI/World is handled separately).
(Reset Material option for if there are issues)

<img width="174" height="42" alt="Screenshot_20250920_165812" src="https://github.com/user-attachments/assets/bbf9f9ae-8ff5-447f-bbe2-159afcb2212a" />

- Click **Prep Scene** → then **Bake Footage Lighting**

<img width="438" height="87" src="https://github.com/user-attachments/assets/4e40f38d-01ff-4788-80e6-a41dbb9e2ca8" alt="Bake Lighting UI" />


<img width="797" height="455" alt="Screenshot_20250920_170604" src="https://github.com/user-attachments/assets/868f2cc2-9082-4ca5-9ebc-6f153fb62066" />

---

### If your scene does not have reflective surfaces, you are good to click on 'Render Animation with Compify Integration'. Be sure to set your output settings as you typically would. Otherwise, continue!

### 4. Reflections

<img width="428" height="228" alt="Screenshot_20250920_165214" src="https://github.com/user-attachments/assets/7095c9e2-143e-4fef-8c15-acb0be35c05a" />

- Use the '+' next to **Reflective Geo** to create the collection (will be in Footage Geo)
  - Add objects/geo that is going to be a reflective surface
  - Select the object/geo for reflection strength options in the panel
- Use the '+' next to **Reflected Geo** to create the collection
  - Add objects/geo that will be reflected on the above surfaces
- Use the '+' next to **Holdout Geo** to create the collection
  - Add objects/geo using the button for blocking reflections
    
- Click **Prep Scene** → then **Bake Footage Lighting**

<img width="796" height="450" alt="Screenshot_20250920_170944" src="https://github.com/user-attachments/assets/239f4ff8-a373-4ccd-b430-027af41b1849" />


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

- **Blender 4.0.0 or later**  
  (Tested from Blender **v4.2.0** to **v5.0.0**)

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
> I commit a ton because I'm dumb.

---

