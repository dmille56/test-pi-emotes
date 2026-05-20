# pi-emote: cyber-greymane

This repo generates and maintains a **pi-emote** sprite set for a character (“cyber chaos scientist”) using the required `emotes/<set-name>/` layout.

It includes:
- A scripted **frame generator** (`scripts/generate_emotes.py`) using the OpenAI Images API (`images.edit`) starting from a single `master_img.png`.
- A **Nix flake** with a `generate-emotes` command for `nix develop` / `nix shell` workflows.
- Tests that validate the required filenames and `talk.weights` mapping.

## Repo layout

- `emotes/` – emote sets (currently `emotes/cyber-greymane/`)
- `master_img.png` – the shoulder-up master reference image used for edit-based generation
- `scripts/generate_emotes.py` – generator + local post-processing (background removal)
- `PROMPT_GENERATION_PLAN.md` – the generation/invariants plan
- `tests/` – checks required files and `talk.weights` consistency

## Required pi-emote files (validated by tests)

The set at `emotes/cyber-greymane/` must contain at least:
- `idle/idle.png`
- `idle/idle_blink.png`
- `think/think.png`
- `think/think_hard.png`
- `talk/` directory with one or more `*.png` files including **at least one** whose filename contains `"close"` (e.g. `talk/talk_close.png`)
- Folders `hi/`, `read/`, `write/`, `tool/`, `success/`, `failure/` each containing ≥1 PNG

Additionally, `emotes/cyber-greymane/emotes.json` must have:
- `talk.weights` keys that match `talk/*.png` **exactly**.

## Generate / update frames

### Prerequisites
- A working OpenAI API key in your environment:
  ```bash
  export OPENAI_API_KEY=...
  ```
- `nix` available.

### Generate into the repo’s emote set directory

```bash
nix shell --command generate-emotes \
  --output emotes/cyber-greymane \
  --overwrite \
  --size 128x128 \
  --background opaque \
  --remove-bg
```

Notes:
- `--background transparent` may not be supported for all models; if so, use `opaque` + `--remove-bg`.
- `--size 128x128` matches the small/sprite-friendly dimensions used by upstream defaults.

### Re-run ONLY background removal on existing PNGs

If you already generated PNGs but want consistent transparent backgrounds:

```bash
nix shell --command generate-emotes \
  --output ~/.pi/agent/extensions/pi-emote/emotes/cyber-greymane \
  --remove-bg-only \
  --bg-fuzz 25% \
  --alpha-cutoff 30
```

Then reload pi:

```text
/reload
```

- `--bg-fuzz` controls how aggressively pixels are classified as background.
- `--alpha-cutoff` forces very-low-alpha pixels to fully transparent to remove grey/black fringe artifacts.

## Install into pi’s global extension directory (Linux)

After generating into `emotes/cyber-greymane/`, copy it into your pi install:

```bash
cp -r emotes/cyber-greymane ~/.pi/agent/extensions/pi-emote/emotes/
```

Then in pi:

```text
/reload
```

## Tests

Run:

```bash
python -m unittest discover -s tests -v
```

## How it works (high level)

`scripts/generate_emotes.py` generates each target PNG using `images.edit` with the master image as reference, so identity/crop invariants remain consistent across frames.

Local post-processing can then enforce transparent backgrounds so pi-emote doesn’t show “black squares” or inconsistent grey/black halos.
