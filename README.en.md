# Pixane

[Français](README.md) · **English**

Free photo editor for Windows, with artificial intelligence retouching **that runs entirely on your own PC**. Interface in English and French.

> **No online AI.** Pixane never sends your photos over the Internet: every AI action runs on your computer, with models installed on your disk. No account, no subscription, no limit. The Internet is only used to download the AI engine once; after that, Pixane works even offline.
>
> **Speed depends on your PC**, above all on the **graphics card**: the more powerful it is (and the more memory it has), the faster the AI processing. See [System requirements](#system-requirements).

## What Pixane can do

**AI retouching** (several proposals each time: you pick the best one, as in Photoshop; the result arrives on its own layer, the original photo is never damaged)
- **Erase** an object: paint over it, the AI removes it and rebuilds the background
- **Fill** an area: the AI invents what fits best in that spot (with or without a prompt)
- **Expand the image** beyond its edges (outpaint): the AI extends the scenery; it also redraws damaged edges
- **Upscale**: increase the resolution (×1.5 to ×4), fast or sharper (details redrawn)
- **Remove** (J): one brush stroke on a small defect (wire, spot, dust), it disappears on release
- **Remove background** and **Select subject** in one click
- **Reduce noise** (grain, JPEG artefacts) and **Sharpen** (slight blur)
- **Restore an old photo** (scratches, stains, creases, grain), keeping its colours or **colourising** it

**Selection**
- Rectangle, lasso, selection brush and eraser; add / subtract with Shift / Alt
- AI **object selection** and **quick selection** (SAM 3.1), **magic wand** adjusted by dragging
- **Refine edge** for hair, fur and soft edges; expand, shrink, feather, invert

**Layers, as in Photoshop**
- Visibility, opacity, lock, order (buttons or **drag with the mouse**), merge, flatten
- **17 blend modes**, **layer masks**, **groups**, **adjustment layers** editable at any time
- Non-destructive **layer styles**: drop shadow (including a realistic shadow), perspective ground shadow, inner shadow, glows, multiple outlines, bevel, colour and gradient overlays; 14 ready-made styles, saved styles

**Tools**
- Crop, colour brush, clone stamp, **healing brush**, layer eraser, move
- **Gradient**, **paint bucket**, **shapes** (rectangle, ellipse, line, arrow)
- **Editable text**: font, size, colour, outline, shadow, background, rotation, curved text
- Rulers, guides, grid and snapping

**Adjustments and filters**
- Image adjustments with an **Auto** button (brightness, contrast, saturation, hue, temperature, sharpness)
- **Levels**, **Curves**, **Colour balance**, **Black & white** (with sepia toning), **Vibrance**
- Filters: Gaussian blur, motion blur, noise reduction, sharpen, vignette
- Image size, **canvas size**, rotate, flip, straighten; transform a layer (size, rotation)
- **RGB colour** or **greyscale** mode

**Files**
- **New image** with 34 ready-made formats (CD and vinyl covers, Spotify, books, Amazon KDP, social media, A4, posters…), units (px, cm, mm, inches, points, picas), resolution, **bleed** and **safe area** for print
- **Export for print in CMYK** (TIFF, PDF, JPEG; Windows profiles such as Coated FOGRA39) and **on-screen preview** of the printed colours
- JPG, PNG, TIFF, WebP, BMP; **PSD** (Photoshop) with layers, groups, masks, modes and styles; `.pixane` (Pixane project, everything stays editable) and `.ora` (Krita, GIMP)
- **Several photos open** in tabs, each with its own Undo
- **Autosave** and recovery after a crash
- **Export for web** (JPEG, WebP, PNG; size, quality, file size shown, personal information removed)
- **Batch processing** of a whole folder (resize, auto adjust, AI upscale, background, format)
- Undo / Redo with a History panel; recent files

**Comfort**
- Light or dark theme, Windows accent colour; built-in guide with search (F1)
- Installer that checks the PC and downloads the AI engine itself (ComfyUI and the models), resuming after an interruption

## System requirements

| | Minimum | Recommended |
|---|---|---|
| **System** | Windows 10 or 11, 64-bit | Windows 11, 64-bit |
| **Graphics card** | NVIDIA, **8 GB** of memory (for example RTX 3060 Ti, 3070, 4060) | NVIDIA RTX, **12 GB or more** (for example RTX 3060 12 GB, 4070, 4080, 4090) |
| **RAM** | 16 GB (Flux actions are then slow) | **32 GB** |
| **Disk** | 35 GB free for the AI engine | 60 GB free (with the options), on an SSD |
| **Processor** | recent 4-core | 6 cores or more |

Pixane has been tested on an **RTX 3060 Ti (8 GB) with 32 GB of RAM**; the minimum is an estimate. **Without an NVIDIA card**, Pixane opens and edits normally (layers, text, adjustments, filters, export…), but the AI actions do not work.

**Times measured on this test PC** (a more powerful card is faster):

| Action | Time |
|---|---|
| Object selection, quick selection | about 1 second |
| Remove background, Remove (J), Reduce noise | a few seconds |
| Sharpen (AI) | 15 to 20 seconds |
| Fill, Expand image | about 1 minute per proposal |
| Erase | about 2 minutes |
| Sharp upscale | 20 to 30 seconds per 1024 px tile |
| Restore an old photo | about 2 minutes per proposal |

## Download

**[Pixane for Windows](../../releases/latest)** (64-bit installer, `Pixane-Setup-<version>-64bits.exe`).

The installer checks the graphics card and free space, then offers to download the AI engine from the official sites (GitHub, Hugging Face): **21.5 GB**, about 31 GB on disk. Two optional extras: **Flux Schnell** for "Sharp upscale" (11.8 GB) and **Flux Kontext** for "Restore an old photo" (11.9 GB). The Flux Fill and Flux Kontext models are under the **non-commercial FLUX.1 [dev] licence**: you must accept it to install them.

> **"Windows protected your PC" message:** Pixane is free and not signed, because a code-signing certificate costs money every year. Windows therefore shows this message until the program is well enough known. Click **More info**, then **Run anyway**. Check that the file really comes from this page; its SHA-256 fingerprint is given with each version.

To request a feature or report a problem: open an [Issue](../../issues) on Pixane's GitHub page.

## Where this project comes from (Why and how?)

I used Photoshop and really liked its generative AI: erasing an object, filling an area, expanding an image… It succeeded almost every time. But I no longer wanted to pay for the subscription.

I tried free solutions, such as Krita with its AI extension: the results were very random, the opposite of what I was used to. So I created **Pixane**, at first for my own use: a simple editor, with AI settings chosen and tested to succeed on the first try, running entirely on the PC.

### Full transparency with you:

I want to be 100% honest with everyone: **I know absolutely nothing about programming and I don't speak any language other than French**.

**Pixane** came to life, was entirely coded and translated into English thanks to the help of the artificial intelligence **Claude Code**. The AI guided me step by step to turn my needs into lines of code and to produce the English version of the software so that it is available to as many people as possible.

The program is shared here as it is, wholeheartedly, with the sole aim of being useful. It is entirely free, but as you can read in the Licence section below, it remains protected to make sure it is never sold.

Welcome to all future Pixane users!

## Guide

What follows is the complete guide. It is the same text as the `docs\GUIDE_en.md` file shipped with the program and shown in its **Help > Pixane guide** window (with a search; **F1** opens it at the shortcuts).

<!-- guide -->
## 1. The window

| Area | Purpose |
|---|---|
| **Top bar** | Open, Save, Undo / Redo, settings of the chosen tool (size, New / Add / Remove…), zoom |
| **Tools (left)** | Hand, Move, selection tools, retouching tools, Crop, Text. A small triangle on a button = several tools: **right-click** (or click and hold) to choose |
| **"Text" panel (left)** | Text settings, shown with the Text tool (see chapter 7) |
| **Tabs (above the photo)** | One tab per open photo (as soon as there are two); a "•" marks a modified photo |
| **Rulers** | Above and left of the photo, in pixels (View > Rulers, Ctrl+R) |
| **Photo (centre)** | The photo; the selected area appears in transparent red |
| **"Artificial intelligence" panel (right)** | Erase, Fill, Expand image, Upscale |
| **"Layers" panel (right, below)** | The layers of the image (see chapter 6) |
| **Status bar (bottom)** | AI engine status (coloured dot), photo size |

**Colours**: Pixane uses the accent colour chosen in Windows (Settings > Personalization > Colors)
and follows the Windows light / dark mode. **View > Theme** menu: *Same as Windows*, *Light* or *Dark*.
The sun / moon button in the top bar also switches between light and dark.

**Language**: Pixane is available in **French** and **English**. By default it uses the Windows language
(French if Windows is in French, English otherwise). **View > Language** menu: *Same as Windows*, *Français*
or *English*; Pixane then offers to restart to apply the language (the AI engine restarts too, about
20 seconds). Standard buttons (Yes / No / Cancel, right-click menu) follow the same language.
Layer names that already exist keep their original language.

**AI engine**: when it starts, Pixane launches the AI (ComfyUI) in the background, without a window. Allow about
20 seconds. The dot at the bottom left turns green when the engine is ready; AI actions are greyed out before that.

---

## 2. Opening and saving

- **File > Open** (Ctrl+O): JPG, PNG, TIFF, WebP, BMP, and the **.pixane**, **.ora** and **.psd** (Photoshop)
  layered files.
  The photo is rotated according to the camera orientation.
- **Save** (Ctrl+S), **Save as** (Ctrl+Shift+S):
  - **.pixane** (Pixane project): Pixane's own format. Keeps **everything**: layers (names, order, visibility,
    opacity, lock), **editable texts** and **editable layer styles**. Suggested automatically when the image has several layers or a text.
  - **.ora** (OpenRaster): to **share with Krita or GIMP** (open format). Keeps the layers, but texts become
    images.
  - Good to know: a .pixane file is built like an .ora file; renamed to .ora, it also opens in Krita or GIMP.
  - **.psd** (Photoshop): to **work with Photoshop**. Keeps the layers (names, order, visibility, opacity, lock);
    texts become images. A photo opened from a PSD is suggested as PSD.
  - **PSD files opened in Pixane**: RGB or greyscale, 8 or 16-bit, with layers, **groups**, **layer masks**,
    **blend modes** and **layer styles** (drop and inner shadow, glows, stroke, bevel, colour and gradient overlays),
    which stay editable. Pixane does not reproduce Photoshop adjustment layers, clipping masks or groups in "pass
    through" mode (opened as Normal): a message says so when opening, as the result may then look different. A CMYK
    PSD opens flattened (a single layer). Large .psb documents are not supported.
  - **PSD files saved by Pixane**: layers, groups, masks and blend modes are kept; styles are baked into the
    pixels; an adjustment layer becomes an image layer (the adjusted result).
  - **JPG** (quality 95), **PNG**, **TIFF**, **WebP**: the **flattened** image (what you see, layers merged).
    A message reminds you of this if the image has several layers.
  Camera information (EXIF) and the colour profile are kept.
- **Undo** (Ctrl+Z) / **Redo** (Ctrl+Y or Ctrl+Shift+Z): every edit and every selection can be undone (30 steps).
- **History panel** (tab next to "Layers"): the list of steps. Click a step to go back to that moment; click a step
  further down to redo the next ones. A new edit discards the steps "ahead".
- **File > Recent files**: the last 10 images opened or saved (*Clear the list* empties it).
- **Several photos at once**: *Open* accepts several files at a time (Ctrl+click or Shift+click in the dialog),
  and several files can be dropped on Pixane. Each photo has its own **tab** and its own **Undo** (Ctrl+Z only
  affects the photo shown). Switch photos: click the tab, **Ctrl+Tab** / **Ctrl+Shift+Tab**. **File > Close photo**
  (Ctrl+W, or the tab's cross) asks to save if needed. Opening a photo that is already open just goes to its tab.
- **Autosave**: every 3 minutes, each modified photo is copied (layers, texts, styles and masks included) to
  `%LOCALAPPDATA%\Pixane\recuperation`, without slowing you down. If Pixane closes badly (crash, power cut), it
  offers to **reopen these copies** the next time it starts; they open "to be saved", with the original file name.
  The copies are deleted when the photo is saved or closed, and when Pixane closes normally.
- **If an error occurs**: when a command fails, Pixane shows it and writes it to
  `%LOCALAPPDATA%\Pixane\erreurs.log` (useful to report the problem).
- **File > Export for web…** (Ctrl+Alt+Shift+S): a light copy for the Internet, without touching the photo.
  - **Format**: JPEG (photos), **WebP** (lighter at the same quality, keeps transparency), PNG (lossless).
  - **Shrink: longest side** (for example 2048 px); never enlarged.
  - **Quality** (30 to 100; about 80 is enough for the web).
  - The **file size** is shown live.
  - Camera information (EXIF: model, date, sometimes location) is **removed** by default (box to keep it).
    Suggested name: `<photo>_web.jpg`.
- **File > Batch processing…**: the same work on **a whole folder** of photos.
  - **Photos to process** (source folder, never modified) and **Results in** (another folder).
  - Options: **Shrink** (longest side), **Auto adjust** (brightness, contrast, temperature, like the Auto button),
    **AI upscale ×2** (RealESRGAN), **Remove background** (results as transparent PNG), **Format** (keep, JPEG,
    WebP, PNG) and quality, **Add to name** (e.g. `_web`).
  - A bar shows progress; **Stop** finishes the current photo then stops. A photo that causes a problem is listed
    at the end; the others are done.
  - Safety: if the results would go into the same folder under the same name, Pixane refuses (the originals
    would be replaced).
- **File > New image…** (Ctrl+N): an empty image, as in Photoshop.
  - **Ready-made formats** (on the left): **album covers** (CD, 12-inch and 7-inch vinyl, 3000 × 3000 px for
    Spotify, Deezer, Apple Music), **books** (pocket, novel, Amazon KDP, e-book), **social media** (Instagram, Story,
    Facebook, YouTube, X), **print** (A3, A4, A5, photos, posters, business card, flyer), **screen** (HD, Full HD,
    4K). **Save this format…** keeps your own formats in **My formats**; the last format used is offered next time.
  - **Width, height and unit**: pixels, inches, centimetres, millimetres, points or picas (1 inch = 2.54 cm =
    72 points = 6 picas). Changing the unit does not change the image.
  - **Orientation**: Portrait or Landscape swaps width and height.
  - **Resolution** (dpi, dots per inch): **300** for print, **72** for screen. It is **kept in the file** (.pixane,
    PSD, JPEG, PNG, TIFF): a printer will see the right size.
  - **Mode**: RGB colour or **greyscale** (see *Image > Mode*). Pixane works in **8 bits per channel** (16.7 million
    colours, like JPEG, PNG and the web); 16 and 32 bits are planned for later.
  - **Background**: white, transparent, black or a colour of your choice.
  - **Bleed** (print): band added all around, trimmed off by the printer (usually 3 mm): the background must run to
    the edge of the image. **Safe area**: margin inside the finished size where nothing important goes (text,
    face). **Guides** are placed automatically on these two lines.
  - At the bottom: the size in pixels, the printed size and the memory used.
- **File > Export for print (CMYK)…**: for a printer who asks for CMYK (the four inks). Pixane works in RGB and
  converts when exporting, as printers recommend.
  - **Format**: TIFF (the safest), PDF or JPEG.
  - **CMYK profile**: those installed in Windows, nothing to download. Ask your printer which one they use; in
    Europe it is often **Coated FOGRA39** (coated paper).
  - **Rendering intent**: *Perceptual* for photos, *Relative colorimetric* for logos and flat colours. **Black point
    compensation**: ticked, shadows keep their detail.
  - The **resolution** is written in the file; the photo is not changed (suggested name: `<photo>_cmyk.tif`).
  - Before exporting: **View > Print preview (CMYK)** (Ctrl+Alt+Y) shows on screen the colours as they will come out
    (very bright blues and greens often get duller). Click it again to go back to the normal view; the image is
    never changed.
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

### Rulers, guides and grid (View menu)
- **Rulers** (Ctrl+R): in image pixels, 0 at the top-left corner of the photo; a line follows the mouse.
- **Guides**: drag from a ruler onto the photo to place a blue line (horizontal from the top ruler, vertical from
  the left one). With the **Move** tool (V), grab a guide to move it (the cursor becomes a double arrow
  over it); dragged off the photo, it disappears. *New
  guide…* places one at an exact position, *Clear guides* removes them all, Ctrl+; hides or shows them. They are
  saved in the .pixane file.
- **Grid** (Ctrl+'): regular lines over the photo; *Grid size…* sets the spacing (100 px by default).
- **Snap** (Ctrl+Shift+;, on by default): rectangle selection, gradient and shapes snap to guides, to the photo's
  edges and to the grid (when shown), within 8 screen pixels.

---

## 4. Selecting (telling the AI where to work)

The selected area appears in **transparent red**. You do not need to "outline" an object:
you can simply **paint over it**.

The selection tools share **two buttons** in the left bar (small triangle): the "by hand" tools and the
"automatic" tools. **Right-click** the button, or click and hold, to choose; or press their key directly.

| Tool | Key | Use |
|---|---|---|
| **Rectangle** | M | Rectangular selection |
| **Lasso** | L | Draw an outline freehand, button held down; the shape is closed automatically |
| **Selection brush** | B | Paint the area. Ideal for an object, some text, a wire… |
| **Selection eraser** | E | Remove from the selection by painting |
| **Object selection** (AI) | O | Drag a frame around an object, or click on it: the AI cuts it out |
| **Quick selection** (AI) | Q | Roughly paint over the object: the AI finds its outline |
| **Magic wand** | W | One click on a colour: the whole area of similar colour (no AI) |

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

### Object selection and quick selection (AI)
They use Meta's **SAM 3.1** model (1.6 GB, installed with the AI engine). The AI understands the **whole object**
(a person, a car, a piece of furniture…), even when its colours vary, and follows its real outline. About one second
per request (a few seconds the first time).
- **Object selection (O)**: drag a **frame** around the object, or **click** on it. Like the rectangle: the new
  selection replaces the old one; **Shift** adds, **Alt** removes (or the New / Add / Remove pills).
- **Quick selection (Q)**: roughly **paint** over the object (on it, or along its outline). As in
  Photoshop, each stroke finds **its own** object, which is **added** to the selection: a stroke on a title then a
  stroke around a person give the title + the whole person. Green dots show what the AI must keep. **Alt + paint**
  over a part to leave out (red dots): the AI corrects the objects already found. A selection cleared (Ctrl+D) or
  changed by another tool starts again from scratch; so does **Esc**.
- Ctrl+Z undoes each step. Fine-tune the result afterwards with *Modify selection* (expand, soften…).

### Magic wand (W)
One click on a colour selects the area of similar colour. No AI, instant.
- **Adjust by dragging**: after the click, **keep the button down and drag right** (wider) **or left** (narrower): the
  selection follows live. The tolerance found is kept for the next click.
- **Tolerance** (0 to 255, 32 by default): accepted colour difference. Colours are compared the way the eye sees
  them, and the starting colour is taken over 3 × 3 pixels: photo noise matters less.
- **Contiguous** (ticked): only the area clicked; unticked: all similar colours in the image.
- **Soft edges** (ticked): gradual edge, no jaggies.
- **Fill holes**: adds what is completely surrounded (birds in a sky, reflections on an object…).
- **Visible image** or **Chosen layer**: what the colours are compared on.
- Shift adds, Alt removes, like the rectangle.

### Refine edge (Ctrl+Alt+R, Select menu)
For a rough selection around **hair, fur, foliage or soft edges** (for example after *Select subject* or a quick
lasso): Pixane recomputes the edge from the photo's colours.
- **Radius**: width of the band recomputed around the edge. Increase it until the strands appear; outside this
  band, nothing changes.
- **Smooth**: softens a jagged edge. **Edge contrast**: sharper edge. **Shift edge**: negative pulls it in (removes
  a fringe of the old background), positive pushes it out.
- **View**: the subject **on black**, **on white**, the mask in **black & white**, or the selection in red. Pick a
  background that contrasts with the old one to judge the edges.
- **Output**: a **new selection**, or the **mask of the chosen layer** (the background is then hidden, not erased:
  see *Layer masks*).
One step in Undo. The computation takes one to three seconds on a large photo.

### Cut, copy, paste, delete (Edit menu)
They work on the **layer chosen** in the Layers panel:
- **Copy** (Ctrl+C): copies what is selected (the whole layer if there is no selection). The copy keeps its
  transparency; it can also be pasted into another program.
- **Cut** (Ctrl+X): copies, then erases the selected area (it becomes transparent).
- **Paste** (Ctrl+V): puts the copied image in a **new layer**, at **the same place** if it comes from Pixane, in the
  centre if it comes from elsewhere (screenshot, another program…). Then move it with the Move tool (V). To enlarge
  or shrink it: **Ctrl+T** (see *Transform layer*).
  - **Image larger than the photo**: it arrives **reduced to fit entirely**, with the *Transform* frame already
    open. Adjust its size and position, then press **Enter**. Nothing is cut off before you apply: you can enlarge
    it again without loss.
- **Delete selection** (Del): erases the selected area of the layer (transparent).

A **locked** layer is protected; a **text** that is cut or deleted becomes an image. Ctrl+Z undoes everything.

The other tools: **Move** (V) moves the content of the **chosen layer** (a moved text stays editable; what goes
outside the image is cut off; refused on a locked layer). The **Layer eraser** (G) **really** erases the pixels of the
chosen layer (see chapter 6); it is grouped with the colour brush and the clone stamp.

**Tip (text, cursive, thin objects)**: cover each letter completely, edges included, with a brush slightly wider
than the stroke; don't forget the shadow or outline if there is one. Pixane already enlarges the area a little
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
- Also works on a thin selection (letters picked with the magic wand): every pixel touched by the selection is
  erased, even on a soft edge.
- Typical time: about 2 minutes (8 GB graphics card).

### Fill (Shift+R)
Redraws the area painted in red.
- **Without text** (recommended): the AI invents something that fits the rest of the photo. It starts from the
  background cleaned by LaMa: even next to a title, it does not invent letters again.
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
- **Automatic detection**: when opened, Pixane finds the light or dark border lines (1 to 8 px) that many
  images have on their edges, and already places the red frame on them. You can adjust it or set it back to 0.
- **Bar at the top of the photo**:
  - **Expand** row: what is added on each side, as a % of the photo (0 to 200%);
  - **Damaged edge** row: the strip to redo on each side, in pixels;
  - **final size** of the image;
  - **Start** (or Enter) / **Cancel** (or Esc).
  The boxes and the frames follow each other: changing one updates the other.
- **Final size** = original photo + expansion. The damaged edge does not shrink the image: it is replaced.
- The join between the photo and the addition is made by Pixane: the original photo is kept **pixel for pixel**,
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
  transparent, the subject stays. Save as PNG, PSD or .pixane to keep the transparency. Ctrl+Z undoes it.
- **Select subject** (Ctrl+Alt+S, Select menu): selects the subject without erasing anything, for example to
  adjust it (Ctrl+U), or *Invert* (Ctrl+Shift+I) to work on the background.

### Reduce noise, Sharpen, Restore an old photo (AI menu)
These three actions work on the visible image; if there is a **selection**, only its inside changes. Like the other
AI actions, the result goes on a **new layer** (Ctrl+Z undoes it).
- **Reduce noise (AI)**: removes grain (night or phone photos) and JPEG compression artefacts while keeping detail.
  **SCUNet** model (Apache-2.0, 72 MB). A few seconds.
- **Sharpen (AI)**: makes a slight blur sharper (edges, text, details): the photo is enlarged ×4 by RealESRGAN
  then brought back to its size. It also smooths grain: on a very textured photo, the *Sharpen* filter (Filters
  menu) may be better. 15 to 20 seconds.
- **Restore an old photo…**: the AI **redraws** the whole photo, removing scratches, stains, dust, creases and
  grain, and making contrast and faces sharper. The photo keeps **exactly its size and proportions**.
  - **Restore** keeps the **original colours**: a black & white or sepia photo stays so, a colour photo keeps its
    colours. The AI only provides the light and the details; Pixane then puts back the original's tint.
  - **Restore and colourise** also adds natural colours to a black & white or sepia photo.
  - The result arrives in a **"Restored"** (or **"Restored and colourised"**) layer, and *Save as* as well as *Export
    for web* suggest a name that says so: `photo_restored.jpg`, `photo_restored_colourised.jpg`.
   Two proposals, about **2 minutes each**; *More proposals* asks for others. The AI may change
  small details (facial features, letters): compare carefully with the original (layer eye). **Flux Kontext dev**
  model (11.9 GB, FLUX.1 [dev] licence, **non-commercial** use), optional: *Flux Kontext* box in **AI > Install the
  AI engine…**.

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
| **Name** | Double-click the name to rename; double-click elsewhere on the row: layer style |
| **Opacity** | Transparency of the selected layer, from 0% (invisible) to 100%; shown under the name when < 100% |
| **Padlock** (right of the name) | Locks the layer to protect it: it can no longer be erased, deleted or merged, and its opacity is fixed; Flatten is disabled while a layer is locked. AI actions are refused with a message: Erase and Fill if the selected layer is locked, Expand and Upscale if any layer is locked (they change the size of every layer). It can still be hidden, renamed and moved up / down. The open padlock is discreet, the closed padlock clearly visible. The lock is kept in .pixane and .ora files |
| **Drag a layer** | Change its place in the stack with the mouse: grab the row (on the name) and drag it up or down; an **orange line** shows where it will go. Dropped just below a layer of an open group, it enters the group; a group moves with its layers. A single Undo step |
| **Blend mode** (list at the top of the panel) | How the layer mixes with what is below (see below) |
| **Mask thumbnail** (right of the thumbnail) | The layer's mask, if it has one. Click: you paint the mask (orange frame); click the layer thumbnail: you paint the pixels again. Shift+click: disable / enable the mask (crossed in red) |

### The buttons (left to right)
| Button | Action |
|---|---|
| **New layer** | Adds an empty layer above the selected layer (Ctrl+Shift+N) |
| **New group** | Creates a folder of layers (Ctrl+G puts the selected layer in a group) |
| **Mask** | Adds a mask to the selected layer (from the selection if there is one) |
| **Adjustment** | Menu: new adjustment layer (Levels, Curves, Colour balance, Black & white, Vibrance, Image adjustments) |
| **Duplicate** | Copies the selected layer (Ctrl+J); a group is copied with its layers |
| **fx** | Layer style (see below) |
| **Move up / down** | Changes the layer's place in the stack; enters an open group, leaves it at the edge; a group moves with its layers |
| **Merge** | Combines the selected layer with the one below (opacity, mask and mode applied) |
| **Flatten** | Combines all visible layers into a single "Background" |
| **Delete** | Deletes the selected layer (a group: with its layers) |

### Blend modes
The same as Photoshop, sorted by family: **Normal**; **Darken**, **Multiply**, **Colour burn** (darkening);
**Lighten**, **Screen**, **Colour dodge**, **Linear dodge (Add)** (lightening); **Overlay**, **Soft light**, **Hard
light** (contrast); **Difference**, **Exclusion**; **Hue**, **Saturation**, **Colour**, **Luminosity**. Examples:
*Multiply* for a shadow or dark texture, *Screen* for a glow, *Overlay* for a paper texture, *Colour* to tint. Kept
in .pixane, .ora and .psd files.

### Layer masks
A mask **hides part of a layer without erasing it**: black = hidden, white = visible, grey = half. You can always go
back by painting white.
- **Layer > Layer mask**: *Add: reveal all*, *Add: reveal selection*, *Add: hide selection*; *Paint mask / pixels*
  (Ctrl+\); *Disable mask*; *Invert mask*; *Mask to selection*; *Apply mask* (into the pixels); *Delete mask*.
- **Painting the mask**: select it (click its thumbnail), then use the **colour brush** (black hides, white
  reveals, grey half), the **layer eraser** (hides), the **gradient** (gradual fade, for example to blend two
  photos) or the paint bucket. Adjustments and filters also work on the mask.
- Example: *Remove background* then a mask rather than an eraser: a bit of the subject cut by mistake comes back by
  painting white.
- Masks follow the layer (Ctrl+T, crop, image size, Upscale) and are kept in .pixane, .ora and .psd.

### Groups
A **group** puts several layers in a folder: you can hide, move, duplicate or delete them all at once, and give the
group an opacity, a blend mode and a mask that apply to everything inside.
- **Ctrl+G**: puts the selected layer in a new group; **Ctrl+Shift+G**: ungroups (the layers stay).
- The arrow left of the group **collapses** or **expands** it. Layers inside a group are indented.
- Move up / down takes a layer into an open group, or out of it.

### Adjustment layers
An **adjustment layer** applies an adjustment (Levels, Curves, Colour balance, Black & white, Vibrance,
Image adjustments) to **everything below it**, without touching the pixels: you can edit it (double-click it, or
**Layer > Edit adjustment…**), hide it (eye), lower its opacity or delete it at any time.
- **Layer > New adjustment layer**, or the panel's **Adjustment** button. If there is a selection, it becomes the
  adjustment layer's mask (the adjustment only applies there).
- Inside a group, it only adjusts the group's layers below it.
- Kept as is in .pixane; in .ora and .psd it becomes an image layer (the result).

### Layer style: shadows, outline, glow, bevel… (Ctrl+Alt+F)
**Effects added to the layer**, always editable: the layer's pixels are not touched. To open it: **double-click** a
layer (anywhere but on its name), the **fx** button in the panel, or **Layer > Layer style…**. The photo shows the
result live; **OK** keeps the style (a single step in Undo), **Cancel** puts everything back.

| Effect | What it does |
|---|---|
| **Drop shadow** | Offset shadow under the layer. **Realistic shadow** box: sharp near the object, blurrier further away, like a real shadow |
| **Inner shadow** | Shadow inside the edges (carved look) |
| **Outer / inner glow** | Colour halo around the layer, or from its edges (or centre) inwards |
| **Outline** | Line around the layer: outside, centre or inside, any thickness |
| **Bevel and emboss** | Adds volume: inner bevel, outer bevel or emboss; up or down; light altitude |
| **Colour overlay** | Covers the layer with a colour (Normal, Multiply, Screen, Overlay modes) |
| **Gradient overlay** | Covers the layer with a linear or radial gradient, any angle and scale |
| **Ground shadow** | For a cut-out object: shadow lying on the ground, in perspective, sharp at the base and blurred at the end. **Drag the round dot on the photo** to choose its direction and length |

- **Ready-made styles** (at the top): Soft shadow, Realistic shadow, Ground shadow, Sticker, Black outline, Outline
  only, Neon, Gold, Chrome, Emboss, Engraved, Fire, Candy, Glass. Thumbnails are computed **on your layer**. One
  click tries it, then every effect can still be adjusted.
- **The same effect several times** (two outlines, three shadows…): ⧉ button. The first in the list is in front.
  ▲ / ▼ change the order, ✕ deletes, the tick box turns an effect off without losing it.
- **Fill**: opacity of the content only, effects stay. At 0%: only the outline or shadow remains (outlined text,
  glass…).
- **Same light** (ticked by default): all layers share one light; changing its angle on one layer changes it
  everywhere.
- **Save this style…**: it joins the ready-made styles (right-click it to delete it).
- Effects **follow the layer**: Ctrl+T, Image size and Upscale enlarge or shrink them with it. They also follow an
  edited text or a moved layer.
- **Layer** menu: **Copy style** / **Paste style** (onto another layer), **Remove style**, **Merge style into pixels**
  (to erase or paint the layer with its effects).
- Saving: in **.pixane**, styles stay editable. In **.psd** and **.ora** they are merged into the pixels (visible in
  Photoshop, Krita, GIMP, but no longer editable). Styles of an opened PSD are imported and stay editable (see chapter 2).
- Merge and Flatten also put the effects into the pixels.

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
  even after saving as **.pixane** and reopening.
- The text is applied **as you go**: nothing to confirm.
- **Drag the text**: move it (also with the Move tool, V). A dashed frame surrounds the selected text.
- **Round handle** above the frame: rotate the text (**Shift**: in 15° steps), or the *Rotation* box.
- The layer name follows the first line of the text (as long as you have not renamed it yourself).
- With no text selected, the panel settings are used for the **next** text; Pixane also remembers the last
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
- To keep texts editable, save as **.pixane** (in an .ora file, they become images).

---

## 8. Crop, paint, retouch

The manual editing tools, as in Photoshop. Everything can be undone with **Ctrl+Z**; a **locked** layer is
protected. Tools sharing a button (small triangle) are chosen by **right-clicking** the button.

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

### Remove (J, AI)
Paint over a small flaw (power line, stain, spot, dust): **on release**, it disappears (LaMa). The result goes on a
"Removals" layer, reused for the following strokes. For a large object, use *Erase* (Shift+E), which offers several
results.

### Healing brush (R)
Like the clone stamp, but the copy **takes on the surrounding light and colour**: ideal for a wrinkle, a skin
blemish, a scratch on a graded sky.
1. **Alt+click** a clean area.
2. Paint over the flaw: the raw copy shows while painting; **on release**, it is blended with its surroundings.

### Gradient (D)
Drag from the start to the end of the gradient (**Shift**: horizontal, vertical or 45°). Top bar: **Linear** or
**Radial**, start colour (the brush colour) **to** end colour, or **transparent** (fade to nothing). Inside the
selection if there is one. On a **mask**, it makes a gradual fade (for example to blend two photos).

### Paint bucket (K)
**What it is for**: filling a plain-coloured area in a single click, without painting it by hand. For example:
changing the colour of a plain background or a banner, filling the inside of a letter or a shape, colouring an area
of a line drawing, or filling a selection.

**How**: choose the colour (swatch in the top bar, or **Alt+click** on the photo to pick it), then click inside the
area: it fills until the colour changes, following the visible image.
- **Tolerance** (top bar): at 0, only the exact colour is filled; higher, the fill spreads to nearby shades (useful
  for a slightly graded background or a JPEG photo).
- If there is a **selection**, it stays inside it. It paints on the selected layer (tip: an empty layer above makes
  it easy to go back).

### Shapes (U)
Drag to draw a **rectangle**, **rounded rectangle**, **ellipse**, **line** or **arrow** (**Shift**: square, circle,
straight line). Each shape goes on a **new layer**, in the brush colour. **Filled** (box) or outline only; the
**size** sets the stroke thickness.

A **text** retouched with the brush or the stamp becomes an image (a message reminds you; Ctrl+Z to go back).
Groups and adjustment layers have no pixels: a message asks you to choose an image layer or a mask.

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

### Levels, Curves, Colour balance, Black & white, Vibrance (Image > Adjustments menu)
As in Photoshop, with live preview and histogram. They change the pixels of the **selected layer** (inside the
selection if there is one). To be able to come back to them later, use an **adjustment layer** instead (chapter 6).

| Adjustment | Shortcut | What it does |
|---|---|---|
| **Levels** | Ctrl+L | Input black, grey (gamma) and white points, output black and white; per channel (RGB, red, green, blue). **Auto** sets black and white from the photo |
| **Curves** | Ctrl+M | Tone curve: click to add a point, drag to move it, right-click to remove it; per channel. An S curve adds contrast |
| **Colour balance** | Ctrl+B | Pushes **Shadows**, **Midtones** or **Highlights** towards Cyan–Red, Magenta–Green, Yellow–Blue; *Preserve luminosity* |
| **Black & white** | Ctrl+Alt+Shift+B | Converts to black & white choosing the lightness of each colour (reds, yellows, greens, cyans, blues, magentas); **Tint**: colours the greys (sepia…) |
| **Vibrance** | — | Mostly boosts dull colours, sparing those already vivid (skin); **Saturation**: all colours equally |

### Filters (Filters menu)
**Gaussian blur**, **Motion blur** (angle, distance), **Noise reduction** (strength, keep details, colour noise),
**Sharpen** (amount, radius, threshold: Photoshop's unsharp mask), **Vignette** (darken or lighten the edges:
strength, centre size, softness, round). Same behaviour as adjustments: live preview, selected layer, inside the
selection if there is one, one step in Undo. They also work on a mask.

---

## 10. Image menu: size, rotation, transform

- **Mode**: **RGB colour** or **Greyscale**. In greyscale the image is shown and saved in grey (JPEG, PNG, TIFF in
  true grey); the layers keep their colours, so you can go back to RGB without losing anything.
- **Canvas size…** (Ctrl+Alt+C): enlarges the sheet **without stretching the image** (for example to add a bleed
  or a band for a title), or crops it.
  - New **width** and **height** in pixels, inches, cm, mm, points, picas or **percent**; **Relative**: you type
    what you add (e.g. +200 px).
  - **Anchor**: where the image stays (centre, top left…); the arrows show where the sheet grows.
  - **Added colour** on the bottom layer: white, transparent, black or a colour of your choice.
  - Texts stay editable, guides follow; Ctrl+Z undoes it.
- **Image size…** (Ctrl+Alt+I): in pixels or %, proportions kept (tick box), quick buttons (for example 1920 px
  for screen and Internet). No AI: to enlarge with more detail, prefer Upscale.
- **Rotate** 90° right, left or 180°, **Flip** horizontally or vertically: the whole image, all layers, lossless.
  Flipped texts become images; rotated ones stay editable.
- **Straighten…**: rotate by a small angle (-45° to +45°) with a grid to align the horizon or a wall.
  *Crop to remove the empty corners* (ticked by default); unticked, the image grows and the corners are
  transparent.
- **Edit > Transform layer** (Ctrl+T): a frame surrounds the **chosen layer**. To enlarge, shrink or rotate **a
  single element** of the layer, **select it first** (rectangle, lasso, magic wand…): the frame surrounds only that
  element, the rest of the layer does not move, and its original place becomes transparent.
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
| J, R, D, K, U | Remove (AI), Healing brush, Gradient, Paint bucket, Shapes |
| Alt+click | (Colour brush, Paint bucket) pick a colour; (Clone stamp, Healing brush) area to copy |
| `[` / `]` | Smaller / larger brush |
| Space (held) | Move the view |
| Shift / Alt (when starting a rectangle or a lasso) | Add / Remove |
| Alt (held, selection brush) | Remove for one stroke |
| Shift+E, Shift+R, Shift+A, Shift+U | Erase, Fill, Expand, Upscale |
| Ctrl+Z, Ctrl+Y | Undo, Redo |
| Ctrl+A, Ctrl+D, Ctrl+Shift+I | Select all, Deselect, Invert |
| Ctrl+X, Ctrl+C, Ctrl+V, Del | Cut, Copy, Paste (new layer), Delete selection |
| Ctrl+U | Image adjustments |
| Ctrl+L, Ctrl+M, Ctrl+B, Ctrl+Alt+Shift+B | Levels, Curves, Colour balance, Black & white |
| Ctrl+G, Ctrl+Shift+G | Group, Ungroup |
| Ctrl+\ | Paint the layer's mask / pixels |
| Ctrl+Alt+R | Refine edge |
| Ctrl+R, Ctrl+', Ctrl+;, Ctrl+Shift+; | Rulers, Grid, Guides, Snap |
| Ctrl+W, Ctrl+Tab, Ctrl+Shift+Tab | Close photo, Next photo, Previous photo |
| Ctrl+Alt+Shift+S | Export for web |
| Ctrl+N, Ctrl+Alt+V | New image, New image from clipboard |
| Ctrl+Alt+I, Ctrl+Alt+C | Image size, Canvas size |
| Ctrl+Alt+Y | Print preview (CMYK) |
| Ctrl+T | Transform layer (Enter apply, Esc cancel) |
| Ctrl+Alt+F | Layer style |
| Ctrl+Shift+N, Ctrl+J | New layer, Duplicate layer |
| Ctrl+Alt+S, Shift+B | Select subject, Remove background (AI) |
| O, Q, W | Object selection (AI), Quick selection (AI), Magic wand |
| Drag after a magic wand click | Adjust the tolerance live |
| Right-click on a tool with a small triangle | Choose another tool of the group |
| Ctrl+0, Ctrl+1 | Fit, 100% |
| Enter / Esc | (Expand) Start / Cancel; (Crop) Apply / Cancel |
| Shift (while rotating a text) | Rotate in 15° steps |
| F1 | Guide, opened at the shortcuts (Help > Pixane guide: the whole guide, with a search) |

---

## 12. Hardware and licences

**Installation**: run `Pixane-Setup-<version>-64bits.exe`.
1. Installation language (it will also be Pixane's language, which can be changed later in View > Language).
2. Just for me (default, no administrator rights) or for all users.
3. Installation folder.
4. **PC check**: NVIDIA graphics card and its memory (8 GB recommended), free space, AI engine (ComfyUI) found or
   not. If ComfyUI is installed elsewhere, use **Browse…** to select its folder.
   Without ComfyUI, Pixane opens, edits (layers, text) and saves photos, but the AI actions do not work.
5. **AI engine** (only if ComfyUI is not found): list of what will be downloaded, with size, site and licence
   (21.5 GB to download, about 31 GB on disk); engine folder (default `%LOCALAPPDATA%\Pixane\moteur`); optional
   **Flux Schnell** box for "Sharp upscale" (11.8 GB more); the **I accept the FLUX.1 [dev] licence** box
   (non-commercial use) is required to install the engine. You can also untick it: Pixane installs without the
   engine.
6. Options: desktop icon; open .pixane files with Pixane.
7. At the end, the **Install the AI engine** window downloads and installs everything (ComfyUI portable, its
   extensions, the models). It shows progress, speed and time left. You can **Stop** at any time: the download
   resumes later where it stopped (even after a connection loss). Each file is checked (SHA-256 checksum).

The same window opens from **AI > Install the AI engine…** (for example to add Flux Schnell later, or **Flux
Kontext** — 11.9 GB, optional — for *Restore an old photo*), and Pixane
offers it at start-up if it finds no engine. If a ComfyUI installed another way is already there, Pixane uses it
and installs nothing.

**AI engine updates**: the versions of ComfyUI, the extensions and the models are chosen and tested with each
version of Pixane; nothing changes on its own. When a new version of Pixane needs other versions, Pixane offers
it once at start-up (list and download size), and the **Install the AI engine** window shows the state of each
item (*up to date*, *new version*) with the **Update** button. Only what changed is downloaded. ComfyUI is replaced
while keeping its models, extensions and settings; a replaced old model is deleted. The engine is stopped during the
update and restarted afterwards. A ComfyUI installed another way (for example ComfyUI Desktop) updates itself:
Pixane does not touch it.

A new version installs over the old one (settings kept). To uninstall: Windows Settings > Apps. The uninstaller
asks two questions (default answer "No"):
- also delete the **AI engine installed by Pixane** (ComfyUI, extensions, models)? A ComfyUI installed another
  way, such as ComfyUI Desktop, is never touched;
- also delete the **settings** (language, theme, last folder, text style, engine folder) and the logs?

**Licences and test hardware**:
- Pixane: Pixane Licence 1.1, © 2026 Georges Christophe (chrypox): free of charge, may be modified and shared,
  author's name required, no sale (of Pixane or a modified version); file `LICENSE` (French text prevails;
  translation `LICENSE.en.txt`).
  Third-party items: `docs\LICENCES_TIERS.md`.
- Tested on an 8 GB NVIDIA graphics card (RTX 3060 Ti). The times given come from this PC.
- Models used: Flux.1 Fill dev (**non-commercial use**; GGUF Q8 version when installed by Pixane, same
  quality), Flux.1 Kontext dev (**non-commercial use**, optional), Flux.1 Schnell (Apache-2.0), LaMa (Apache-2.0),
  RealESRGAN x4plus (BSD-3), SCUNet (Apache-2.0), BiRefNet (MIT), SAM 3.1 (Meta SAM License).
- Engine: ComfyUI (GPL-3.0) and its extensions Inpaint nodes, Inpaint Crop and Stitch, Ultimate SD Upscale
  (GPL-3.0), ComfyUI-GGUF (Apache-2.0).
<!-- /guide -->

## Frequently asked questions

### Are my photos sent over the Internet?
No. The AI runs on your PC. The Internet is only used once, to download the AI engine and the models.

### Why is the AI slow?
AI models are large (Flux Fill: 12 GB). On an 8 GB card, count about one minute per proposal. Pixane only processes the area around the selection, not the whole photo, to go faster.

### I have an AMD or Intel card. Does it work?
Pixane opens and edits (layers, text, crop…), but the AI actions need an NVIDIA card.

### I already have ComfyUI. Do I have to download everything again?
No: the installer looks for it, and the **Browse…** button lets you point to its folder. Pixane then uses it as it is.

### How do I change the language?
**View > Language** menu. Pixane restarts to apply it.

### Can I use it at work?
Yes, free of charge, in companies too. It is only forbidden to sell it, rent it or include it in a paid offer. Note: the **Flux Fill** model (Erase, Fill, Expand) is under a non-commercial licence; check that it suits your use.

### How do I uninstall it?
Windows Settings > Apps > Pixane. The uninstaller asks whether to also delete the AI engine and the settings.

## Development

You need Python 3.11 and [uv](https://github.com/astral-sh/uv).

- `uv venv` then `uv pip install -e .`: prepares the environment.
- `Pixane.bat` (or `.venv\Scripts\python -m pixane photo.jpg`): starts Pixane.
- `construire-installateur.bat`: builds the installer (needs [Inno Setup 7](https://jrsoftware.org/isdl.php)).
- `tests\essai_*.py`: automatic tests (they do not touch your settings).
- `outils\readme.py`: copies the guide (`docs\GUIDE.md`, `docs\GUIDE_en.md`) into the READMEs.

| Folder | Purpose |
|---|---|
| `pixane` | The program (PySide6): window, canvas, layers, text, AI recipes, link with ComfyUI |
| `installateur` | Inno Setup installer |
| `docs` | Guides, roadmap, third-party licences |
| `tests` | Automatic tests |

## Licence

Pixane is published under the **Pixane Licence 1.1** — © 2026 Georges Christophe (chrypox). The French text in the [`LICENSE`](LICENSE) file is the only one that is legally binding; [`LICENSE.en.txt`](LICENSE.en.txt) is a courtesy translation. In short:

- **Free**: free use, in companies and internally too; forbidden to sell it, rent it or include it in a paid offer.
- **Sharing**: free copying and sharing, with the licence and the author's name.
- **Modifications allowed**: anyone may modify Pixane, publish their modified version ("fork") or reuse its code, provided they keep the author's name, state that the version is modified, and publish it under the same licence: it therefore stays free and non-commercial.
- **Fixes**: proposed through an Issue (ticket) or a pull request; the author integrates them, crediting their author.
- **Rights of others**: an element that does not respect a licence or your rights? Write to admin@chrypox.be.

The AI engine (ComfyUI) and the AI models are not included in Pixane: they remain under their own licence, and the **Flux.1 Fill [dev]** model is under a non-commercial licence. Full list: [`docs/LICENCES_TIERS.md`](docs/LICENCES_TIERS.md).
