# ComfyUI workflow graphs (Cuebert)

This directory holds **named ComfyUI workflow JSON graphs** that the
`comfyui-toolkit` MCP tools may load. Each file is one exported graph; the
tool API selects workflows by **filename stem** (for example,
`texture_tileable.json` is referenced as `texture_tileable`).

## Naming and metadata

- Use **lowercase snake_case** stems for stable agent references.
- Optional top-level field **`_cuebert_description`** in the JSON root:
  short human summary surfaced by `comfyui_list_workflows`.
- Keep graphs **version-controlled** as plain JSON (no secrets, no API keys).

## Expected graph shape (M4-P4)

Cuebert assumes a standard ComfyUI API graph: string node IDs mapping to
objects with `class_type` and `inputs`. For asset generation the graph
should include at least:

- A **`KSampler`** (or equivalent sampler) node for denoising.
- One or more **`CLIPTextEncode`** nodes; the toolkit applies the MCP
  `prompt` string to every `CLIPTextEncode` node as a **stub** until M4-P4
  adds targeted template substitution for positive vs negative prompts.

Workflows that omit these node types may still queue on ComfyUI but will not
receive predictable prompt injection from this toolkit.

## Authoring and export

1. Build and debug the graph in the ComfyUI web UI against your local models.
2. Use **Save** / **Export (API format)** so the JSON matches the `/prompt`
   payload shape (node graph, not UI-only layout).
3. Drop the exported file here and re-run `comfyui_list_workflows` to confirm
   discovery.

## Planned stock workflows (M4-P4)

The gaming plan reserves these names (graphs are **not** shipped in M4-P1):

- `texture_tileable.json` — seamless tiling textures.
- `concept_character.json` — character concept sheets.
- `icon_flat.json` — flat game icons.

Real workflows land in **M4-P4**. This directory is intentionally empty in
M4-P1 aside from this README and `.gitkeep`.

## Queue and rate limits

ComfyUI runs jobs in a single-node queue by default. MCP callers should avoid
hammering `comfyui_generate_asset` in tight loops; explicit backoff is **not**
implemented in M4-P1 and may be added if operators see queue saturation.
