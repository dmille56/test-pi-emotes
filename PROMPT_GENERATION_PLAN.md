# Prompt generation plan (OpenAI Images API + `gpt-image-2`) for `emotes/cyber-greymane`

## Goal
Generate a consistent set of PNGs for a pi-emote emote set using the required folder/state layout, filenames, and `talk.weights` keys.

Required files (must exist):
- `idle/idle.png`
- `idle/idle_blink.png`
- `think/think.png`
- `think/think_hard.png`
- `talk/*` must include at least one filename containing `"close"`:
  - **`talk/talk_close.png`** (mouth closed; filename includes `close`)

Other folders (need ≥1 `*.png` each):
- `hi/`, `read/`, `write/`, `tool/`, `success/`, `failure/`
- optional: `compact/`

---

## 1) Create a master reference frame (one-time)
### Output
- `emotes/cyber-greymane/master.png` (internal helper file)

### Generation settings
- `model`: `gpt-image-2`
- `size`: `128x128` (square)
- `quality`: start with `"high"` for the master
- `background`: try `"transparent"` if supported for your API/model configuration
  - If transparency fails or looks wrong, generate opaque then remove background locally later.

### Master prompt (paste)
> Create a square shoulder-up sprite frame of an original “cyber chaos scientist” (NOT a parody of any specific existing character): monocle on the right eye, crazy spiky grey hair with a unique silhouette, white lab coat with a distinctive belt/patch layout, one cybernetic arm with hex plates and teal/green glowing cable lines (visible only from upper arm/forearm up), and a small cyber parrot perched on the **left shoulder** at all times.  
> Head-and-upper-shoulders close-up crop (trim the image above the mid-torso; no full body/legs). Front-facing, centered, consistent camera framing for a terminal sprite. Clean readable stylized illustration.  
> **Transparent background**. No text, no logos, no watermark, no extra characters.  
> High legibility at small size; preserve the parrot’s shoulder perch and the scientist’s costume design (within the shoulder-up crop).

### Invariants to keep identical later
- Parrot: always perched on the scientist’s **left** shoulder
- Monocle placement: on the **right eye**
- Hair: same spiky grey silhouette style
- Lab coat: same coat cut + belt/patch layout
- Cyber arm: same hex-plate + teal/green cable glow design
- Pose/framing: same front-facing shoulder-up close-up framing, centered composition

---

## 2) Generate all other frames using **edits** (high consistency)
For every required PNG:
- Use the **master image** as the input to `images.edit`
- Prompt must say: “change ONLY …”
- Explicitly list invariants to preserve:
  - monocle position, hair shape/silhouette, lab coat design, cyber arm design, parrot shoulder perch
  - pose, shoulder-up framing, overall silhouette
- Explicitly say what changes:
  - blink / think expressions
  - mouth opening size for talk frames
  - small facial expression differences for other frames

This edit-based approach is the main reason your character stays consistent across frames.

### Edit prompt template (paste + customize)
> Using the provided input image as the exact character reference, change **ONLY** the following:  
> **[Describe the exact required change for this filename]**  
>  
> Preserve everything else exactly: character identity, monocle position, hair shape, white lab coat (including belt/patch layout), cybernetic arm design (hex plates + teal/green glowing cable style), and a **cyber parrot always perched on the left shoulder**. Preserve pose, shoulder-up framing, and overall silhouette.  
> No extra characters. No text. No logos. No background elements added.  
> Output: square PNG with the same shoulder-up framing crop, **transparent background**.

---

## 3) Frame-by-frame prompt checklist (what to change per file)

### `hi/hi_1.png`, `hi_2.png`, `hi_3.png`
Edits from master; vary greeting expression/posture slightly while keeping shoulder-up silhouette consistent.
- `hi_1`: slight head tilt, eyebrows raised
- `hi_2`: bigger confident grin, subtle shoulder energy
- `hi_3`: surprise/“welcome” eyes, quick blink-friendly expression
Add to edit prompt: “parrot still perched; no new objects; expression only (shoulder-up crop unchanged)”.

---

### `idle/idle.png`
- Neutral idle expression
- Parrot: subtle LED idle shimmer (optional)

### `idle/idle_blink.png`
- Eyes closed blink (monocle still present)
- Mouth neutral
- Parrot: blink/LED pulse (optional) but no reposition

---

### `think/think.png`
- Thinking expression (furrowed brow slightly, mouth pursed)
- Parrot: tiny “thinking tilt” (optional), still perched

### `think/think_hard.png`
- Hard thinking: stronger brow tension, mouth tight or clenched-neutral
- Cyber arm: faint extra glow intensity (optional)
- Parrot: LED pulse once (optional)

---

### `talk/` frames (must match `talk.weights` keys exactly)
Create these filenames exactly:
- `talk/talk_close.png`  ✅ (mouth fully closed; filename contains `close`)
- `talk/talk_small.png`
- `talk/talk_mid.png`
- `talk/talk_wide.png`

Edit differences:
- `talk_close.png`: mouth closed, no open gap
- `talk_small.png`: small mouth opening gap
- `talk_mid.png`: medium mouth opening
- `talk_wide.png`: wide mouth opening, still stylized/readable

**Important constraints**
- Keep all non-mouth parts fixed (monocle/hair/lab coat/arm/parrot perch)
- Mouth opening is the only meaningful change

---

### Cycling folders (one image minimum each; more is fine)
Widget behavior depends on sorted filenames, so use numbered names.

#### `read/read_1..read_5.png`
- Expression: looking down slightly as if “reading”
- Mouth neutral (not talking)
- Parrot remains perched

#### `write/write_1..write_4.png`
- Expression: focused
- Hand/action: “writing on an implied notepad” (keep generic/no logos)
- Parrot remains perched

#### `tool/tool_1..tool_4.png`
- Expression: using an implied tool (generic, no brands)
- Parrot remains perched

#### `success/success_1..success_3.png`
- Expression: pleased/small celebratory grin
- Parrot LED glow warmer (optional)

#### `failure/failure_1..failure_3.png`
- Expression: disappointed/sighing face
- Parrot LED dims (optional)

#### Optional `compact/compact_1..compact_2.png`
- Similar neutral pose with “compact” visual style (optional: slightly simplified shading)
- Parrot still perched

---

## 4) Post-processing / transparency fallback
If `background="transparent"` output is inconsistent:
1. Generate frames with opaque background (easier model output)
2. Run background removal locally (keep edges clean to avoid halos)
3. Export final PNGs into:
   - `emotes/cyber-greymane/<state>/<filename>.png`

---

## 5) `talk.weights` sanity rules
- Keys must match filenames in `talk/` exactly.
- `talk_close.png` filename includes `"close"` and represents “mouth closed”.

Example `emotes.json` fragment:
```json
"talk": {
  "weights": {
    "talk_close.png": 1,
    "talk_small.png": 4,
    "talk_mid.png": 3,
    "talk_wide.png": 2
  }
}
```

---

## 6) Recommended build order (minimize wasted retries)
1. Master image
2. `idle/idle.png` + `idle/idle_blink.png`
3. `think/think.png` + `think/think_hard.png`
4. `talk/talk_close.png` first (critical constraint)
5. Remaining talk variants (`small/mid/wide`)
6. Then `read/write/tool/success/failure`

---

## 7) Implementation helper (scriptable logic)
You can script the pipeline:
- save master
- for each target filename:
  - call `images.edit` with master as input
  - prompt = edit template + filename-specific change description
  - save returned PNG to the correct folder

(If you want, I can generate a ready-to-run Python script that defines filename->edit prompt mappings.)
