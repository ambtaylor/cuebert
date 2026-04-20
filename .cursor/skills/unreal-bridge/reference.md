# unreal-bridge — agent reference

Companion to `SKILL.md`. Covers MCP tool contracts, `_unreal_client.py` HTTP
semantics, dry-run behavior, Remote Control preset concepts, environment
variables, failure modes, vault integration, and planned future tools.

## Tool catalog

### `unreal_health_check() -> dict`

**Purpose:** `GET {base_url}/remote/info` when mode is `live` and the toolkit is
explicitly configured; otherwise return synthetic or `not_configured` envelopes.

**Returns (stable keys):**

| Key | Type | Notes |
|-----|------|-------|
| `status` | str | `ok`, `unreachable`, `not_configured`, `dry_run`, or `error` |
| `base_url` | str | Resolved URL after sanitization |
| `mode` | str | Effective `live` or `dry_run` |
| `version` | str or null | Engine / API version string when known |
| `plugins` | list[str] or null | Parsed plugin hints when present |
| `error` | str or null | Human-readable diagnostic |
| `warnings` | list[str] or null | Non-fatal notices (e.g., non-loopback host) |

**`not_configured`:** Neither `CUEBERT_UNREAL_BASE_URL` nor vault `unreal.base_url`
is set **and** `CUEBERT_UNREAL_MODE` is not explicitly `dry_run`. This mirrors
`comfyui_health_check`: harnesses should treat it as a soft signal to stay on
dry-run rails.

**`dry_run`:** Synthetic `version` (**5.4.0-dry_run**) and bundled Remote Control
plugin names; no outbound HTTP from `_unreal_client.health_probe` while mode is
`dry_run`.

---

### `unreal_list_presets() -> dict`

**Purpose:** `GET {base_url}/remote/presets` in `live` mode; fixtures in `dry_run`.

**Returns:**

| Key | Type | Notes |
|-----|------|-------|
| `status` | str | `ok`, `error`, or `dry_run` |
| `base_url` | str | Resolved Remote Control base |
| `mode` | str | `live` or `dry_run` |
| `preset_count` | int | Length of `presets` |
| `presets` | list[dict] | `{name, path, exposed_count}` |
| `error` | str or null | Transport / HTTP errors |

**Dry-run fixtures:** Three deterministic presets (`ExamplePreset`, `PlayerControls`,
`LightingRig`) documented in `_unreal_client._DRY_RUN_PRESETS`.

---

### `unreal_describe_preset(preset_name: str) -> dict`

**Purpose:** `GET {base_url}/remote/preset/<name>` (URL-encoded) with tolerant JSON
normalization.

**Args:**

| Arg | Type | Requirement |
|-----|------|---------------|
| `preset_name` | str | Regex `^[A-Za-z0-9_.-]{1,128}$` |

**Returns:**

| Key | Type | Notes |
|-----|------|-------|
| `status` | str | `ok`, `error`, `dry_run`, or `not_found` |
| `base_url` | str | Resolved base |
| `mode` | str | `live` or `dry_run` |
| `preset_name` | str | Echo / canonical name |
| `properties` | list[dict] | `{object_path, property_name, type, exposed_name}` |
| `functions` | list[dict] | `{object_path, function_name, arg_count, exposed_name}` |
| `error` | str or null | Validation or transport errors |

**`not_found`:** HTTP **404** or empty preset payload treated as missing asset.

**Dry-run:** Always returns the seeded two-property / one-function bundle defined
in `_unreal_client._DRY_RUN_PRESET_DETAIL` (name reflects the requested preset).

---

### `unreal_ping_actor(preset_name: str, actor_label: str) -> dict`

**Purpose:** Read-only probe: `GET {base_url}/remote/preset/<preset>/expose/actor/<label>`
(both path segments URL-encoded). If Epic’s build differs, expect `error`
metadata and treat failures as **not_found** only when the server clearly
returns **404**.

**Args:**

| Arg | Type | Requirement |
|-----|------|-------------|
| `preset_name` | str | Same regex as `unreal_describe_preset` |
| `actor_label` | str | `^[A-Za-z0-9_. -]{1,256}$` (space allowed) |

**Returns:**

| Key | Type | Notes |
|-----|------|-------|
| `status` | str | `ok`, `error`, `dry_run`, or `not_found` |
| `base_url` | str | Resolved base |
| `mode` | str | `live` or `dry_run` |
| `preset_name` | str | Echo |
| `actor_label` | str | Echo / canonical label |
| `found` | bool | Whether exposure exists |
| `error` | str or null | Validation / transport errors |

**Dry-run:** Always `{found: true}` for valid labels (harness smoke tests).

---

## Client behavior (`_unreal_client.py`)

### URL resolution

1. `CUEBERT_UNREAL_BASE_URL` (must survive `_sanitize_url`).
2. Vault `unreal.base_url` via `get_resolver()` from `lib/_vault.py` (exceptions
   are swallowed; fall through to default hint).
3. Default `http://localhost:30010` (informational only until explicitly
   configured).

### HTTP stack

- **Stdlib `urllib.request`** with a redirect handler that **returns `None` from
  `redirect_request`**, causing a **terminal `HTTPError`** for 3xx responses
  (redirects are **not** followed; the first redirect logs a **single WARNING**).
- **Redirects policy:** do **not** auto-follow. Same-origin upgrades that rely on
  3xx are unsupported in P1; configure the final `http(s)://` base explicitly.
- **Retries:** none in **M5-P1** (unlike ComfyUI’s 5xx retry loop). Transient
  failures surface immediately so operators can distinguish editor restarts
  from logic bugs.
- **No third-party HTTP** dependencies.
- **Timeouts:** `CUEBERT_UNREAL_TIMEOUT_S` or vault `unreal.timeout_s`, default
  **10s**, **hard-capped at 30s** for every call.
- **`urllib` limitation:** connect vs read timeouts are **not** split; optional
  `CUEBERT_UNREAL_CONNECT_TIMEOUT_S` is reserved for documentation parity but is
  **not** honored separately until a future client revision.

### Response handling

- Response bodies are capped at **10MB** (`_MAX_BODY_BYTES`). Oversize payloads
  return a structured error without buffering unbounded memory.
- UTF-8 decoding uses **`errors="replace"`** for resilience.
- JSON parse failures on success HTTP codes yield `null` structured payloads;
  tools treat that as soft-empty data where appropriate.

### Endpoints (P1)

| Step | Method | Path |
|------|--------|------|
| Health | GET | `/remote/info` |
| List presets | GET | `/remote/presets` |
| Describe preset | GET | `/remote/preset/<name>` |
| Ping actor | GET | `/remote/preset/<name>/expose/actor/<label>` |

`PUT /remote/object/property` and `PUT /remote/object/call` will reuse
`_http_put` in **M5-P4**.

---

## Dry-run semantics (tool-by-tool)

| Tool | HTTP | Behavior |
|------|------|-----------|
| `unreal_health_check` | Skipped while `_get_mode()` is `dry_run` inside `health_probe` | Synthetic `version` + `plugins` |
| `unreal_list_presets` | Skipped in `dry_run` | Fixture `presets` array |
| `unreal_describe_preset` | Skipped in `dry_run` | Fixture properties/functions |
| `unreal_ping_actor` | Skipped in `dry_run` | `found: true` |

Configured-but-offline editors return **`unreachable` / `error`** envelopes in
`live` mode rather than silently pretending success.

---

## Remote Control preset primer

A **Remote Control preset** is an Unreal asset authored in-editor that groups
**exposed** UObject fields and **UFUNCTION** entry points for HTTP/Web clients.
Presets are the **API boundary** between cuebert tooling and engine state: you
cannot set arbitrary properties on random actors unless the preset (and Unreal’s
security filters) expose them. Operators should treat presets like mini service
contracts—stable labels, minimal surface area, and version control inside the
`.uproject` the same as any other gameplay asset.

---

## Environment variables

| Variable | Values | Default | Meaning |
|----------|--------|---------|---------|
| `CUEBERT_UNREAL_MODE` | `live`, `dry_run` | unset → `dry_run` if unconfigured, else `live` | Forces synthetic vs HTTP |
| `CUEBERT_UNREAL_BASE_URL` | `http(s)://host:port` | _(none)_ | Overrides vault URL |
| `CUEBERT_UNREAL_TIMEOUT_S` | float seconds | `10` | Per-request urllib timeout (capped at 30) |
| `CUEBERT_UNREAL_CONNECT_TIMEOUT_S` | float seconds | _(reserved)_ | Documented for future split timeouts |

---

## Failure modes

| Scenario | Typical `status` / `error` |
|----------|---------------------------|
| Editor not running / port closed | `unreachable`, socket error string |
| Plugins disabled | `unreachable` or HTTP 4xx with diagnostic body |
| Unknown preset | `not_found` (`unreal_describe_preset`, `unreal_ping_actor`) |
| Unknown property/function (future writes) | deferred **M5-P4** |
| Function rejected by engine guardrails | deferred **M5-P4** |
| Timeouts | `error` / `unreachable` with timeout text |

---

## Vault integration

Hub shared `credentials.yaml` may expose:

```yaml
unreal:
  base_url: "http://localhost:30010"
  mode: "dry_run"        # optional
  timeout_s: "15"      # optional, still capped at 30
  token: "placeholder" # reserved for future reverse-proxy auth — unused in P1
```

Resolver paths:

- **`unreal.base_url`** (logical `shared/unreal/base_url`)
- **`unreal.mode`** (logical `shared/unreal/mode`)
- **`unreal.timeout_s`**
- **`unreal.token`** (reserved; **not** sent on the wire in **M5-P1**)

---

## Proposed future tools (M5-P4+)

| Tool | Intent |
|------|--------|
| `unreal_import_asset` | Stage external files into Unreal content paths |
| `unreal_spawn_actor` | Instantiate vetted classes via exposed calls |
| `unreal_set_property` | `PUT /remote/object/property` with validation |
| `unreal_call_function` | `PUT /remote/object/call` with JSON args |

Websocket listeners (`ws://localhost:30020`) remain **out of scope** until a
later milestone explicitly schedules them.

---

## Type stability

All tools return **JSON-serializable dicts** suitable for orchestration logs and
`memory-toolkit` text mode (no binary payloads embedded in JSON).

## Versioning

Aligned with `SKILL.md` frontmatter (`0.1.0`, **alpha**). Bump both files together.
