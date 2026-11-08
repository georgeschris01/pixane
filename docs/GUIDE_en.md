# Chrypix user guide

Chrypix is a photo editor for Windows that retouches images with an AI running **on your own PC**
(no subscription, no photos sent over the Internet).
This guide explains every tool and every setting. It is updated with each new feature.
(Version française : `docs\GUIDE.md`.)

---

## 1. The window

| Area | Purpose |
|---|---|
| **Top bar** | Open, Save, Undo / Redo, settings of the chosen tool (size, New / Add / Remove…), zoom |
| **Tools (left)** | Hand, Move, selection tools, retouching tools, Crop, Text. A small triangle on a button = several tools: **right-click** (or click and hold) to choose |
| **"Text" panel (left)** | Text settings, shown with the Text tool (see chapter 7) |
| **Photo (centre)** | The photo; the selected area appears in transparent red |
| **"Artificial intelligence" panel (right)** | Erase, Fill, Expand image, Upscale |
| **"Layers" panel (right, below)** | The layers of the image (see chapter 6) |
| **Status bar (bottom)** | AI engine status (coloured dot), photo size |

**Colours**: Chrypix uses the accent colour chosen in Windows (Settings > Personalization > Colors)
and follows the Windows light / dark mode. **View > Theme** menu: *Same as Windows*, *Light* or *Dark*.
The sun / moon button in the top bar also switches between light and dark.

**Language**: Chrypix is available in **French** and **English**. By default it uses the Windows language
(French if Windows is in French, English otherwise). **View > Language** menu: *Same as Windows*, *Français*
or *English*; Chrypix then offers to restart to apply the language (the AI engine restarts too, about
20 seconds). Standard buttons (Yes / No / Cancel, right-click menu) follow the same language.
Layer names that already exist keep their original language.

**AI engine**: when it starts, Chrypix launches the AI (ComfyUI) in the background, without a window. Allow about
20 seconds. The dot at the bottom left turns green when the engine is ready; AI actions are greyed out before that.

---

## 2. Opening and saving

- **File > Open** (Ctrl+O): JPG, PNG, TIFF, WebP, BMP, and the **.chr**, **.ora** and **.psd** (Photoshop)
  layered files.
  The photo is rotated according to the camera orientation.
- **Save** (Ctrl+S), **Save as** (Ctrl+Shift+S):
  - **.chr** (Chrypix project): Chrypix's own format. Keeps **everything**: layers (names, order, visibility,
    opacity, lock) and **editable texts**. Suggested automatically when the image has several layers or a text.
  - **.ora** (OpenRaster): to **share with Krita or GIMP** (open format). Keeps the layers, but texts become
    images.
  - Good to know: a .chr file is built like an .ora file; renamed to .ora, it also opens in Krita or GIMP.
  - **.psd** (Photoshop): to **work with Photoshop**. Keeps the layers (names, order, visibility, opacity, lock);
    texts become images. A photo opened from a PSD is suggested as PSD.
  - **PSD files opened in Chrypix**: RGB or greyscale, 8 or 16-bit, with layers, groups (a hidden group hides its
    layers) and layer masks. Chrypix does not reproduce blend modes other than *Normal*, layer styles (shadow,
    stroke…), adjustment layers or clipping masks: a message says so when opening, as the result may then look
    different from Photoshop. A CMYK PSD opens flattened (a single layer). Large .psb documents are not supported.
  - **JPG** (quality 95), **PNG**, **TIFF**, **WebP**: the **flattened** image (what you see, layers merged).
    A message reminds you of this if the image has several layers.
  Camera information (EXIF) and the colour profile are kept.
- **Undo** (Ctrl+Z) / **Redo** (Ctrl+Y or Ctrl+Shift+Z): every edit and every selection can be undone (30 steps).
- **History panel** (tab next to "Layers"): the list of steps. Click a step to go back to that moment; click a step
  further down to redo the next ones. A new edit discards the steps "ahead".
- **File > Recent files**: the last 10 images opened or saved (*Clear the list* empties it).
- **File > New image…** (Ctrl+N): empty image, any size, white, black or transparent background.
- **File > New image from clipboard** (Ctrl+Alt+V): opens the copied image (screenshot, other program…).
  **Ctrl+V** with no photo open does the same.

---

## 3. Moving around the photo

| Action | How |
|---|---|
| Zoom | Mouse wheel (around the cursor), Ctrl++ / Ctrl+-, magnifier buttons |
| Fit to window | Ctrl+0 |
| Actual size (100%) | Ctrl+1 |
| Move the view | **Hand** tool (H), or hold **Space** and drag, or drag with the **middle button** |
| Move **a layer** | **Move** tool (V): only the selected layer moves (the Hand only moves the view) |

---

## 4. Selecting (telling the AI where to work)

The selected area appears in **transparent red**. You do not need to "outline" an object:
you can simply **paint over it**.

The four selection tools share **one button** in the left bar (small triangle): **right-click** it, or click and
hold, to choose; or press their key directly.

| Tool | Key | Use |
|---|---|---|
| **Rectangle** | M | Rectangular selection |
| **Lasso** | L | Draw an outline freehand, button held down; the shape is closed automatically |
| **Selection brush** | B | Paint the area. Ideal for an object, some text, a wire… |
| **Selection eraser** | E | Remove from the selection by painting |

- **Rectangle and lasso**, as in Photoshop: a new selection **replaces** the old one. Holding **Shift** when you
  start drawing **adds** to the selection, **Alt** **removes**. A single click without drawing **deselects**.
  The **New / Add / Remove** pills in the top bar choose the mode without a key.
- **Selection brush**: it always adds to the selection; **Remove** pill or holding **Alt**: it removes (like the
  selection eraser).
- **Brush size**: "Size" slider in the top bar, or the `[` and `]` keys.
- **Select** menu: *Select all* (Ctrl+A), *Deselect* (Ctrl+D), *Invert* (Ctrl+Shift+I).
- **Select > Modify selection**: *Expand…* or *Shrink…* by a number of pixels, *Soften edges…* (gradual edge,
  useful for image adjustments).
- **Select > Select subject (AI)** (Ctrl+Alt+S): the AI finds the main subject (person, animal, object) and selects
  it. See chapter 5, "Subject and background".

### Cut, copy, paste, delete (Edit menu)
They work on the **layer chosen** in the Layers panel:
- **Copy** (Ctrl+C): copies what is selected (the whole layer if there is no selection). The copy keeps its
  transparency; it can also be pasted into another program.
- **Cut** (Ctrl+X): copies, then erases the selected area (it becomes transparent).
- **Paste** (Ctrl+V): puts the copied image in a **new layer**, at **the same place** if it comes from Chrypix, in the
  centre if it comes from elsewhere (screenshot, another program…). Then move it with the Move tool (V).
- **Delete selection** (Del): erases the selected area of the layer (transparent).

A **locked** layer is protected; a **text** that is cut or deleted becomes an image. Ctrl+Z undoes everything.

The other tools: **Move** (V) moves the content of the **chosen layer** (a moved text stays editable; what goes
outside the image is cut off; refused on a locked layer). The **Layer eraser** (G) **really** erases the pixels of the
chosen layer (see chapter 6); it is grouped with the colour brush and the clone stamp.

**Tip (text, cursive, thin objects)**: cover each letter completely, edges included, with a brush slightly wider
than the stroke; don't forget the shadow or outline if there is one. Chrypix already enlarges the area a little
(about 16 px) to catch blurry edges.

---

## 5. AI actions

Each action offers **several results**: you pick the best one, as in Photoshop.
The result you keep goes onto a **new layer** ("Erase 1", "Fill 2"…): the original photo is never damaged.
The AI always works on the image **as you see it** (all visible layers together).

### Result chooser
- Click a thumbnail to see it full size.
- **Hold to see the original**: while the button is held down, the photo from before is shown.
- **More options**: runs the AI again for new versions (they are added to the previous ones).
- **Keep this result**: applies the chosen version (can be undone with Ctrl+Z). The selection (brush, lasso,
  rectangle) then disappears; Ctrl+Z brings it back with the previous photo.

### While computing
A window shows the current step, a **progress bar**, the elapsed time and the **estimated time left**.
**Cancel** stops the computation.

### Erase (Shift+E)
Removes what is painted in red and rebuilds the background.
- Two combined methods: **LaMa** (fast, erases cleanly), then a finishing pass with **Flux Fill** (more realistic).
- Results offered: 2 Flux versions + the "LaMa only" version.
- Typical time: about 2 minutes (8 GB graphics card).

### Fill (Shift+R)
Redraws the area painted in red.
- **Without text** (recommended): the AI invents something that fits the rest of the photo.
- **With text** ("Optional text" field, preferably in English): describes what you want to see instead.
- 3 options, about 1 minute each.

### Expand image (Shift+A)
Extends the photo beyond its edges: the AI invents the rest of the scene.

Two frames appear on the photo:

| Frame | Look | Purpose |
|---|---|---|
| **Expansion frame** | white dashes, **square handles** in the accent colour | Drag it **outward**: the added area is shown as a grey checkerboard |
| **"Damaged edge" frame** | **red** dashes, round red **handles** | Drag it **inward**: the red hatched strip is a damaged edge (border line, stroke, blur, torn corner…) that will be **discarded, then redrawn** by the AI |

- When both frames are on top of each other (at the start), the **direction of your drag** decides:
  outward = expand, inward = damaged edge.
- **Shift** while dragging: the opposite side moves the same way (expand left and right at once, for example).
- **Automatic detection**: when opened, Chrypix finds the light or dark border lines (1 to 8 px) that many
  images have on their edges, and already places the red frame on them. You can adjust it or set it back to 0.
- **Bar at the top of the photo**:
  - **Expand** row: what is added on each side, as a % of the photo (0 to 200%);
  - **Damaged edge** row: the strip to redo on each side, in pixels;
  - **final size** of the image;
  - **Start** (or Enter) / **Cancel** (or Esc).
  The boxes and the frames follow each other: changing one updates the other.
- **Final size** = original photo + expansion. The damaged edge does not shrink the image: it is replaced.
- The join between the photo and the addition is made by Chrypix: the original photo is kept **pixel for pixel**,
  with a gradual blend and colour matching, so that no line is visible.
- 3 options, about 1 minute each.
- **Layers**: all layers are shifted onto the new canvas; an "Expand 1" layer contains the addition and the
  redone edge (only the new pixels).
- If the photo contains text, the AI sometimes invents meaningless letters in the addition: use "More options".

### Upscale (Shift+U)
Increases the resolution (number of pixels) of the photo.

| Setting | Values | Effect |
|---|---|---|
| **Sharp** | default | RealESRGAN enlarges, then **Flux redraws the details** tile by tile. Slower (about 20 to 30 s per 1024 px tile) but sharp |
| **Fast** | | RealESRGAN only: a few seconds, but may look smoothed ("plastic") |
| **Scale** | ×1.5 to ×4 (×2 by default) | How many times larger |
| **Strength** (Sharp mode) | 0.10 to 0.60 (0.35 by default) | Freedom given to Flux: low = faithful to the original, high = more invented detail |

The window shows the final size before starting; while computing, the progress counts the tiles.

**Layers**: all layers are enlarged (simple smoothing) and the AI result arrives, complete, on an
"Upscale 1" layer on top.

### Subject and background
**BiRefNet** model (MIT, 444 MB, installed with the AI engine; if it is missing, **AI > Install the AI engine…**
adds it). A few seconds.
- **Remove background** (Shift+B, AI panel or AI menu): the background of the **chosen layer** becomes
  transparent, the subject stays. Save as PNG, PSD or .chr to keep the transparency. Ctrl+Z undoes it.
- **Select subject** (Ctrl+Alt+S, Select menu): selects the subject without erasing anything, for example to
  adjust it (Ctrl+U), or *Invert* (Ctrl+Shift+I) to work on the background.

---

## 6. Layers

An image can have several **layers**, stacked like transparent sheets: the top one is in front.
An opened photo has a single layer, "Background".

### The Layers panel
| Element | Purpose |
|---|---|
| **List** | The top layer is at the top. Click a layer to select it (it is highlighted) |
| **Eye** | Show / hide the layer (handy to compare before / after an AI edit) |
| **Thumbnail** | Preview of the layer; the grey checkerboard shows transparent parts |
| **Name** | Double-click to rename |
| **Opacity** | Transparency of the selected layer, from 0% (invisible) to 100%; shown under the name when < 100% |
| **Padlock** (right of the name) | Locks the layer to protect it: it can no longer be erased, deleted or merged, and its opacity is fixed; Flatten is disabled while a layer is locked. AI actions are refused with a message: Erase and Fill if the selected layer is locked, Expand and Upscale if any layer is locked (they change the size of every layer). It can still be hidden, renamed and moved up / down. The open padlock is discreet, the closed padlock clearly visible. The lock is kept in .chr and .ora files |

### The buttons (left to right)
| Button | Action |
|---|---|
| **New layer** | Adds an empty layer above the selected layer |
| **Duplicate** | Copies the selected layer |
| **Move up / down** | Changes the layer's place in the stack |
| **Merge** | Combines the selected layer with the one below (opacity is applied) |
| **Flatten** | Combines all visible layers into a single "Background" |
| **Delete** | Deletes the selected layer (the last layer cannot be deleted) |

### Layer eraser (G)
Erases the pixels of the **selected layer** with the round brush (size: "Size" slider or `[` `]`).
Example: an AI edit that worked except along one edge → select its layer and erase that edge; the original
photo shows through underneath. Erased areas of a single layer appear as a checkerboard.
Not to be confused with the **Selection eraser** (E), which only affects the red of the selection.
On a locked layer, the eraser does nothing and a message at the bottom of the window says so.

All layer actions can be undone with Ctrl+Z (changing the selected layer does not count).

---

## 7. Text

**Text** tool (key **T**, "T" icon in the toolbar). The **Text** panel opens on the left.

### Writing, moving, rotating
- **Click on the photo**: a new text "Text" appears at that spot, on **its own layer**.
  Just type: the suggested word is replaced. The panel's box accepts several lines (Enter).
- **Click on an existing text**: it is selected and its settings are shown; it can be edited at any time,
  even after saving as **.chr** and reopening.
- The text is applied **as you go**: nothing to confirm.
- **Drag the text**: move it (also with the Move tool, V). A dashed frame surrounds the selected text.
- **Round handle** above the frame: rotate the text (**Shift**: in 15° steps), or the *Rotation* box.
- The layer name follows the first line of the text (as long as you have not renamed it yourself).
- With no text selected, the panel settings are used for the **next** text; Chrypix also remembers the last
  style used (font, colour, effects…). The size of a new text is calculated from the photo.

### Panel settings
| Setting | Effect |
|---|---|
| **Font** | All fonts installed in Windows |
| **Size** | Letter height, in pixels of the photo |
| **Colour** (swatch) | Letter colour, with transparency (alpha channel) |
| **B / I / U / S** | Bold, italic, underline, strikethrough |
| **Alignment** | Left, centred, right (for several lines) |
| **Letters** | Space added between letters, as a % of the size (negative = tighter letters) |
| **Lines** | Space between lines, × the letter size |
| **Rotation** | Angle in degrees |
| **Curve** | Text on an arc: positive = arch, negative = dip, 360° = full circle |
| **Outline** | Line around the letters: colour and thickness |
| **Drop shadow** | Colour, distance, direction (0° = to the right, 90° = down) and blur |
| **Background** | Coloured rectangle behind the text: colour, margin and corner rounding |

Effect sizes (thickness, distance, blur, margin, rounding) are a **% of the letter size**:
they stay in proportion when you change the text size.
**Transparency** of the whole text: **Opacity** slider in the Layers panel.

### Good to know
- Every change can be undone with Ctrl+Z; typing several letters is undone in one go.
- **Expand** and **Upscale** keep texts editable: they are shifted or redrawn sharp at the new size.
- The **Layer eraser** on a text turns it into an image (a message says so; Ctrl+Z to go back).
  So do **Merge** and **Flatten**.
- A text on a **locked** layer can be neither moved nor edited.
- To keep texts editable, save as **.chr** (in an .ora file, they become images).

---

## 8. Crop, paint, clone

Three manual editing tools, as in Photoshop. Everything can be undone with **Ctrl+Z**; a **locked** layer is
protected.

### Crop (C)
1. Drag a frame on the photo: the part kept stays bright, the rest is darkened, and a rule-of-thirds grid helps
   place the subject. The size of the result is shown below the frame.
2. Adjust it: the **handles** (corners and middles of the sides) change its size, dragging **inside** the frame
   moves it. The frame never goes beyond the photo (to enlarge, see *Expand image*).
3. **Aspect ratio** (top bar): *Free*, *Same as the photo*, 1:1, 4:3, 3:2, 16:9, and the same in portrait.
4. **Enter**, double-click inside the frame or the **Crop** button: done. **Esc** or **Cancel**: the frame goes
   away without changing anything.

All layers are cropped together; texts stay editable. **Selection > Crop to selection** menu: keeps the smallest
rectangle containing the selection.

### Colour brush (P)
Paints on the **layer chosen** in the Layers panel (tip: an empty layer above the photo lets you correct without
touching the photo).
- **Colour**: swatch in the top bar. **Alt+click** on the photo picks the colour at that spot (eyedropper).
- **Size** (or `[` and `]`), **Opacity** (100% fully covers, less lets what is below show through) and **Hardness**
  (100% sharp edge, 0% very soft edge).
- Going over the same spot during one stroke does not darken the colour; a new stroke does.

### Clone stamp (S)
Copies one part of the photo onto another: to remove a small defect by hand, duplicate a texture…
1. **Alt+click** on the area to copy (a cross marks it).
2. Paint where it should be copied: the cross follows, at the same distance.
3. The next strokes keep the same offset (like Photoshop's "Aligned" option). A new Alt+click chooses another
   area.

The stamp copies the photo **as you see it** (all visible layers) and paints on the chosen layer. Size, opacity
and hardness as for the brush.

A **text** retouched with the brush or the stamp becomes an image (a message reminds you; Ctrl+Z to go back).

---

## 9. Image adjustments

**Image > Image adjustments…** menu (Ctrl+U): correct light, colours and sharpness.

| Setting | From … to | Effect |
|---|---|---|
| **Brightness** | -100 to +100 | Lightens or darkens, keeping black and white |
| **Contrast** | -100 to +100 | Spreads or brings together lights and darks |
| **Saturation** | -100 to +100 | More vivid or duller colours; -100 = black and white |
| **Hue** | -180° to +180° | Rotates all colours (red becomes orange, green…) |
| **Temperature** | -100 to +100 | Warmer (orange) or cooler (blue) |
| **Sharpness** | 0 to 200% | Enhances details |

- The adjustment applies to the **layer chosen** in the Layers panel; if there is a **selection**, only inside it
  (with its soft edges). The window reminds you at the top.
- **Preview on the photo**: you see the result live while moving the sliders (on a large photo it arrives after a
  fraction of a second). Untick to compare with the original.
- **Reset** sets everything back to zero, **Apply** keeps the result, **Cancel** (or Esc) leaves the photo as it
  was. After Apply, Ctrl+Z undoes the adjustment.
- **Auto**: suggests a brightness, contrast and temperature (from the photo, or the selection); the sliders can
  still be adjusted afterwards.
- A **locked** layer is protected; an adjusted **text** becomes an image.

---

## 10. Image menu: size, rotation, transform

- **Image size…** (Ctrl+Alt+I): in pixels or %, proportions kept (tick box), quick buttons (for example 1920 px
  for screen and Internet). No AI: to enlarge with more detail, prefer Upscale.
- **Rotate** 90° right, left or 180°, **Flip** horizontally or vertically: the whole image, all layers, lossless.
  Flipped texts become images; rotated ones stay editable.
- **Straighten…**: rotate by a small angle (-45° to +45°) with a grid to align the horizon or a wall.
  *Crop to remove the empty corners* (ticked by default); unticked, the image grows and the corners are
  transparent.
- **Edit > Transform layer** (Ctrl+T): a frame surrounds the **chosen layer**.
  - **corner**: size, proportions kept (Shift: free); **side**: width or height only;
  - **inside**: move; **outside** (the cursor becomes a round arrow): rotate (Shift: by 15°);
  - the top bar shows width, height and angle; **Enter**, double-click or **Apply** to keep, **Esc** or
    **Cancel** to go back. Changing tool also applies.
  A transformed text becomes an image (to keep a text editable, use the Text tool).

Everything can be undone with Ctrl+Z.

---

## 11. Shortcuts

| Key | Action |
|---|---|
| H, V, M, L, B, E, G, T | Hand, Move, Rectangle, Lasso, Brush, Selection eraser, Layer eraser, Text |
| C, P, S | Crop, Colour brush, Clone stamp |
| Alt+click | (Colour brush) pick a colour; (Clone stamp) area to copy |
| `[` / `]` | Smaller / larger brush |
| Space (held) | Move the view |
| Shift / Alt (when starting a rectangle or a lasso) | Add / Remove |
| Alt (held, selection brush) | Remove for one stroke |
| Shift+E, Shift+R, Shift+A, Shift+U | Erase, Fill, Expand, Upscale |
| Ctrl+Z, Ctrl+Y | Undo, Redo |
| Ctrl+A, Ctrl+D, Ctrl+Shift+I | Select all, Deselect, Invert |
| Ctrl+X, Ctrl+C, Ctrl+V, Del | Cut, Copy, Paste (new layer), Delete selection |
| Ctrl+U | Image adjustments |
| Ctrl+N, Ctrl+Alt+V | New image, New image from clipboard |
| Ctrl+Alt+I | Image size |
| Ctrl+T | Transform layer (Enter apply, Esc cancel) |
| Ctrl+Alt+S, Shift+B | Select subject, Remove background (AI) |
| Right-click on a tool with a small triangle | Choose another tool of the group |
| Ctrl+0, Ctrl+1 | Fit, 100% |
| Enter / Esc | (Expand) Start / Cancel; (Crop) Apply / Cancel |
| Shift (while rotating a text) | Rotate in 15° steps |
| F1 | List of shortcuts |

---

## 12. Hardware and licences

**Installation**: run `Chrypix-Setup-<version>-64bits.exe`.
1. Installation language (it will also be Chrypix's language, which can be changed later in View > Language).
2. Just for me (default, no administrator rights) or for all users.
3. Installation folder.
4. **PC check**: NVIDIA graphics card and its memory (8 GB recommended), free space, AI engine (ComfyUI) found or
   not. If ComfyUI is installed elsewhere, use **Browse…** to select its folder.
   Without ComfyUI, Chrypix opens, edits (layers, text) and saves photos, but the AI actions do not work.
5. **AI engine** (only if ComfyUI is not found): list of what will be downloaded, with size, site and licence
   (19.8 GB to download, about 29 GB on disk); engine folder (default `%LOCALAPPDATA%\Chrypix\moteur`); optional
   **Flux Schnell** box for "Sharp upscale" (11.8 GB more); the **I accept the FLUX.1 [dev] licence** box
   (non-commercial use) is required to install the engine. You can also untick it: Chrypix installs without the
   engine.
6. Options: desktop icon; open .chr files with Chrypix.
7. At the end, the **Install the AI engine** window downloads and installs everything (ComfyUI portable, its
   extensions, the models). It shows progress, speed and time left. You can **Stop** at any time: the download
   resumes later where it stopped (even after a connection loss). Each file is checked (SHA-256 checksum).

The same window opens from **AI > Install the AI engine…** (for example to add Flux Schnell later), and Chrypix
offers it at start-up if it finds no engine. If a ComfyUI installed another way is already there, Chrypix uses it
and installs nothing.

A new version installs over the old one (settings kept). To uninstall: Windows Settings > Apps. The uninstaller
asks two questions (default answer "No"):
- also delete the **AI engine installed by Chrypix** (ComfyUI, extensions, models)? A ComfyUI installed another
  way, such as ComfyUI Desktop, is never touched;
- also delete the **settings** (language, theme, last folder, text style, engine folder) and the logs?


- Chrypix: Chrypix Licence 1.1, © 2026 Georges Christophe (chrypox): free of charge, may be modified and shared,
  author's name required, no sale (of Chrypix or a modified version); file `LICENSE` (French text prevails;
  translation `LICENSE.en.txt`).
  Third-party items: `docs\LICENCES_TIERS.md`.
- Tested on an 8 GB NVIDIA graphics card (RTX 3060 Ti). The times given come from this PC.
- Models used: Flux.1 Fill dev (**non-commercial use**; GGUF Q8 version when installed by Chrypix, same
  quality), Flux.1 Schnell (Apache-2.0), LaMa (Apache-2.0), RealESRGAN x4plus (BSD-3), BiRefNet (MIT).
- Engine: ComfyUI (GPL-3.0) and its extensions Inpaint nodes, Inpaint Crop and Stitch, Ultimate SD Upscale
  (GPL-3.0), ComfyUI-GGUF (Apache-2.0).
