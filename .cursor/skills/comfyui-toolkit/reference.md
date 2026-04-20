# ComfyUI toolkit — agent reference

Deep-dive companion to `SKILL.md`. Covers MCP tool contracts, HTTP client
behavior, dry-run semantics, workflow expectations, security, environment
variables, and stable `error_code` strings.

## Tool catalog

### `comfyui_health_check() -> dict`

**Purpose:** Probe the configured ComfyUI HTTP endpoint (`GET /system_stats`).

**Returns (stable keys):**

| Key | Type | Notes |
|-----|------|-------|
| `status` | str | `ok`, `unreachable`, `not_configured`, `dry_run`, or `error` |
| `base_url` | str | Resolved base (env / vault / documented default hint) |
| `mode` | str | Effective `live` or `dry_run` |
| `version` | str or null | Server version string when reachable |
| `queue_remaining` | int or null | Hint from `exec_info` when present |
| `error` | str or null | Human-readable diagnostic |

**`not_configured` semantics:** Returned when **neither**
`CUEBERT_COMFYUI_BASE_URL` **nor** vault `comfyui.base_url` is set **and** the
operator has not forced `CUEBERT_COMFYUI_MODE=dry_run`. This is **non-fatal**:
callers should treat it as a signal to stay on dry-run rails. See
`docs/_ai_system/standards/vault-standard.md`.

**Example (dry-run harness):**

```json
{
  "status": "not_configured",
  "base_url": "http://127.0.0.1:8188",
  "mode": "dry_run",
  "version": null,
  "queue_remaining": null,
  "error": "ComfyUI base URL is not configured..."
}
```

---

### `comfyui_generate_asset(workflow_name, prompt, seed=None, destination=None, params=None) -> dict`

**Purpose:** Validate inputs, submit `/prompt`, poll `/history/<prompt_id>`,
fetch `/view`, and write `.cuebert/traces/asset/...` outputs plus envelope JSON.

**Args:**

| Arg | Type | Requirement |
|-----|------|---------------|
| `workflow_name` | str | Must be a stem returned by `comfyui_list_workflows` |
| `prompt` | str | Non-empty after sanitization; max 4096 raw chars |
| `seed` | int or null | Optional KSampler override (live stub) |
| `destination` | str or null | Optional path; must stay under `.cuebert/traces/asset/` |
| `params` | dict or null | Shallow overrides (deferred to M4-P4 for real templating) |

**Returns:** `status`, `prompt_id`, `assets` (list of written paths),
`envelope_path`, `duration_ms`, `dry_run`, optional `error`, `error_code`.

**Example error (`unknown_workflow`):**

```json
{
  "status": "error",
  "prompt_id": null,
  "assets": [],
  "envelope_path": null,
  "duration_ms": 3,
  "dry_run": true,
  "error": "Unknown workflow 'icon_flat'. Available: []",
  "error_code": "unknown_workflow"
}
```

---

### `comfyui_list_workflows() -> dict`

**Purpose:** Filesystem scan of `workflows/*.json` (no HTTP).

**Returns:** `status`, `workflows` (list of `{name, path, description, last_modified_iso}`), `count`, `source_dir`.

**`description`:** Pulled from optional top-level `"_cuebert_description"` in each JSON file; `null` when absent.

---

### `comfyui_asset_status(prompt_id) -> dict`

**Purpose:** Query `/history/<prompt_id>` (live) or synthesize completion for
`dryrun-*` IDs.

**Returns:** `status` (`pending`, `running`, `completed`, `failed`, `unknown`),
`assets`, `error`, `dry_run`, optional `error_code`.

---

## Client behavior (`_comfyui_client.py`)

### URL resolution

1. `CUEBERT_COMFYUI_BASE_URL` (highest priority).
2. Vault `comfyui.base_url` via `get_resolver()` from `lib/_vault.py` (raises are caught; falls through).
3. Default `http://127.0.0.1:8188` (informational only until configured).

### HTTP stack

- Uses **`urllib.request`** (stdlib) with a **same-host redirect** handler;
  cross-host redirects raise `URLError` and surface as `network_error`.
- **Retries:** up to three attempts on HTTP **5xx** with simple linear backoff.
- **Timeouts:** `CUEBERT_COMFYUI_TIMEOUT_S` (default **120** seconds) applies per
  blocking HTTP call.
- **Polling interval:** `CUEBERT_COMFYUI_POLL_INTERVAL_S` (default **2** seconds).

### Endpoints

| Step | Method | Path |
|------|--------|------|
| Health | GET | `/system_stats` |
| Submit | POST | `/prompt` JSON `{"prompt": <graph>, "client_id": ...}` |
| Poll / status | GET | `/history/<prompt_id>` |
| Download | GET | `/view?filename=...&subfolder=...&type=output` |

Responses larger than **500 bytes** log a UTF-8 tail at **DEBUG** severity (never
`print`).

### Live prompt injection (M4-P1 stub)

The client deep-copies the graph and assigns:

- Every `CLIPTextEncode.inputs.text` → sanitized MCP prompt.
- `KSampler.inputs.seed` → provided `seed` when not `None`.
- `extra_params` shallow-merge: only keys already present in a node's `inputs`
  dict are overwritten.

**M4-P4** replaces this stub with selective template substitution.

---

## Dry-run semantics (tool-by-tool)

| Tool | HTTP | Behavior |
|------|------|----------|
| `comfyui_health_check` | Skipped when effective mode is `dry_run` or status is `not_configured` before probe | Synthetic `version`, `queue_remaining` |
| `comfyui_generate_asset` | Skipped for submit/poll/fetch | Fabricates `dryrun-<hash>` IDs, instant completion, writes `.png.txt` placeholder |
| `comfyui_list_workflows` | Never | Pure directory scan |
| `comfyui_asset_status` | Skipped for `dryrun-*` | Returns `completed` with placeholder asset names |

Dry-run **still requires** workflow names to exist in the allow-list (on disk)
before `comfyui_generate_asset` will synthesize a submission; with an empty
`workflows/` directory the tool legitimately returns `unknown_workflow`.

---

## Workflow graph format

ComfyUI workflows are JSON objects whose keys are stringified node IDs and
whose values contain `class_type` plus `inputs`. Cuebert stores only **trusted**
graphs checked into `workflows/`. Runtime callers supply **names**, never raw
JSON graphs.

**Future (M4-P4):** targeted template substitution for positive vs negative
prompts and latent dimensions.

---

## Prompt injection / security

User prompts are forwarded into `CLIPTextEncode` nodes only after
sanitization (control characters stripped, max length **4096**). There is **no
arbitrary code execution** inside this toolkit: execution is delegated to the
operator's ComfyUI server and its installed custom nodes.

**Hard rule:** never accept arbitrary workflow JSON from untrusted chat input.
The client enforces an **allow-list** of stems discovered under `workflows/`
with path traversal defenses (`..`, `/`, `\` rejected).

---

## Environment variables

| Variable | Values | Default | Meaning |
|----------|--------|---------|---------|
| `CUEBERT_COMFYUI_MODE` | `live`, `dry_run` | unset → `dry_run` if unconfigured, else `live` | Forces synthetic vs HTTP |
| `CUEBERT_COMFYUI_BASE_URL` | absolute http(s) URL | _(none)_ | Overrides vault URL |
| `CUEBERT_COMFYUI_TIMEOUT_S` | float seconds | `120` | Per HTTP call + poll budget for `generate` |
| `CUEBERT_COMFYUI_POLL_INTERVAL_S` | float seconds | `2` | Sleep between `/history` polls |

---

## Failure modes (`error_code`)

| Code | When |
|------|------|
| `unknown_workflow` | Name not in `workflows/*.json` stems |
| `prompt_empty` | Missing/blank prompt or >4096 chars |
| `network_error` | DNS/socket/HTTP transport failures, timeouts |
| `workflow_validation_error` | Invalid graph JSON, bad ComfyUI response shape, bad destination |
| `comfyui_execution_error` | History reports failure status |

Unknown prompt IDs in live mode yield `status: "unknown"` without a dedicated
code (optional `error` message only).

---

## Trace paths

Outputs must live under:

`<hubRoot>/.cuebert/traces/asset/<timestamp>/<workflow>/<slug>.png`

Sidecar envelopes: `<same>.json` (next to the `.png` basename).

---

## Rate limits

ComfyUI queues jobs server-side. This toolkit **does not** implement automatic
backoff in M4-P1; callers should space submissions if they saturate the queue.

---

## Vault mapping

Hub shared `credentials.yaml` should expose:

```yaml
comfyui:
  base_url: "http://127.0.0.1:8188"
```

Resolver path: **`comfyui.base_url`** (logical `shared/comfyui/base_url` tier).

---

## Testing notes

1. Run `comfyui_health_check` after changing `.env` or vault files.
2. Use `comfyui_list_workflows` to confirm filenames before `generate`.
3. For CI, leave configuration unset and assert `not_configured` / `dry_run`.

---

## Type stability

All tools return plain JSON-serializable dicts suitable for `json.dumps` in
envelopes and for `CUEBERT_MEMORY_MODE=text` orchestration (no binary blobs in
JSON).

---

## Version

Aligned with `SKILL.md` frontmatter (`0.1.0`, alpha). Update both files when bumping.
