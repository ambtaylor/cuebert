# Cook and package — UAT command catalog

Normative **Unreal Automation Tool (UAT)** invocations for **`agent-cook-package-game`** (**M8-P1**). This document is the argv catalog; execution wiring lands in **M8-P3**.

---

## Introduction

**UAT** is Epic’s **Unreal Automation Tool** — a Python-driven orchestration layer that wraps **UnrealBuildTool (UBT)**, **ShaderCompileWorker**, cook, stage, and package steps into coherent pipelines.

**Location (typical engine layout):**

- Windows: `<Engine>/Build/BatchFiles/RunUAT.bat`
- macOS / Linux: `<Engine>/Build/BatchFiles/RunUAT.sh`

**Why UAT for cook + stage + package (vs raw UBT):**

- **UBT** compiles targets (game/editor modules). It does **not** own the full **cook → stage → archive → package** story.
- **`BuildCookRun`** (a UAT command) sequences **build**, **cook**, **stage**, **archive**, and **package** with consistent logging, `-project=` resolution, and platform SDK hooks.

Cuebert documents **`RunUAT … BuildCookRun`** as the primary surface. **M8-P1** publishes a **Win64 Shipping** reference (single combined invocation + phased split in `agent-cook-package-game.md` §4). **Mac**, **Linux**, **IOS**, and **Android** are documented with the same structural headings; **IOS** and **Android** are **skeletons** (`todo_m8_p2`) for toolchain and store policy.

---

## Platform matrix (M8-P1 summary)

| Platform | Catalog section | M8-P1 status | Default `clientconfig` | Default compression |
|----------|-----------------|-------------|------------------------|---------------------|
| **Win64** | § Win64 Shipping | **Reference path** | Shipping | zlib |
| **Mac** | § Mac Shipping | Documented; codesign **out of scope** | Shipping | zlib |
| **Linux** | § Linux Shipping | Documented; **internal** store focus | Shipping | zlib |
| **IOS** | § IOS (skeleton) | **`todo_m8_p2`** | Shipping | zlib |
| **Android** | § Android (skeleton) | **`todo_m8_p2`** | Shipping | zlib |

---

## Phased argv templates (all platforms)

These mirror **`agent-cook-package-game`** §4. Replace `<platform>` with **`Win64`**, **`Mac`**, **`Linux`**, **`IOS`**, or **`Android`**.

**Phase A — cook**

```text
RunUAT.{sh,bat} BuildCookRun \
  -project=<uproject> \
  -noP4 \
  -platform=<platform> \
  -clientconfig=<Shipping|Test|Development> \
  -cook \
  -pak \
  -compress=<zlib|oodle|none>
```

**Phase B — stage**

```text
RunUAT.{sh,bat} BuildCookRun \
  -project=<uproject> \
  -noP4 \
  -platform=<platform> \
  -clientconfig=<config> \
  -stage \
  -archive \
  -archivedirectory=<output_dir>
```

(Add **`-skipcook`** when reusing a successful cook from the same workspace session — policy in **M8-P3**.)

**Phase C — package**

```text
RunUAT.{sh,bat} BuildCookRun \
  -project=<uproject> \
  -noP4 \
  -platform=<platform> \
  -clientconfig=<config> \
  -package \
  -skipcook \
  -skipstage
```

**Optional `-build`** may prefix cook or be folded into a single CI invocation (Win64 reference section below).

---

## Section: Win64 Shipping (reference path)

**Combined CI-style invocation** (cook + stage + package in one process — valid for clean builds):

```text
RunUAT.{sh,bat} BuildCookRun \
  -project=<uproject>         # Absolute path to .uproject
  -noP4                        # Disable Perforce integration
  -platform=Win64              # Target platform
  -clientconfig=Shipping       # Build configuration
  -cook                        # Run cook phase
  -pak                         # Package cooked content into .pak
  -compress=zlib               # Compression (default zlib for M8-P1)
  -build                       # Build binaries before cook
  -stage                       # Stage to archive directory
  -archive                     # Enable archive
  -archivedirectory=<dir>     # Staged output root
  -package                     # Create final installer/zip
```

**Phased split** (per-phase envelopes — see `docs/_ai_system/agents/agent-cook-package-game.md` §4):

1. **Cook:** `-cook -pak -compress=<zlib|oodle|none>` (omit `-stage` / `-package` when isolating cook).
2. **Stage:** `-stage -archive -archivedirectory=<dir>` (often with `-skipcook` when cook already succeeded).
3. **Package:** `-package -skipcook -skipstage`.

**Expected output tree (illustrative):**

```text
<archivedirectory>/Win64/
├── <ProjectName>.exe
├── <ProjectName>.pdb (absent in Shipping when pdb_excluded_in_shipping rule passes)
├── <ProjectName>/Content/Paks/
│   ├── <ProjectName>-Win64.pak
│   └── <ProjectName>-Win64.sig
└── Manifest_NonUFSFiles_Win64.txt
```

**Success signal:** process exit code **0** AND **`<archivedirectory>/Win64/<ProjectName>.exe`** exists.

**Failure signals:**

- Non-zero UAT exit code.
- Log lines matching **`LogCook: Error:`** in **`Saved/Logs/<Project>.log`** (or the active log path for the run).
- After a cook phase, **`Saved/Cooked/Win64/`** missing or empty when cook was requested.

**Steam-ready focus:** Depot layout, Steamworks redistributables, and SDK copy steps are **ship-plan** concerns for **M8-P1**; this catalog stops at staged/player artifacts.

---

## Section: Mac Shipping

**Invocation shape** matches Win64 with platform token **`Mac`**:

```text
RunUAT.sh BuildCookRun \
  -project=<uproject> \
  -noP4 \
  -platform=Mac \
  -clientconfig=Shipping \
  -cook -pak -compress=zlib \
  -build -stage -archive -archivedirectory=<dir> -package
```

**Differences vs Win64:**

- Output is a **`.app` bundle** under the staged tree, not a standalone `.exe`.
- **Codesigning and notarization** are **out of scope** for **M8-P1**; **`agent-prod-readiness-game`** may REJECT missing signing evidence when `build_path` is supplied (**M7-P2** rules). **M8-P2** cert checklist (`agent-cert-game`, planned) will surface advisory TRC-style gaps.

**Success signal:** exit **0** AND staged **`.app`** present under **`Mac/`** (exact layout varies by project name and UE version).

**`todo_m8_p2`:** Harden notarization/stapling notes and store-specific bundle checks.

---

## Section: Linux Shipping

```text
RunUAT.sh BuildCookRun \
  -project=<uproject> \
  -noP4 \
  -platform=Linux \
  -clientconfig=Shipping \
  -cook -pak -compress=zlib \
  -build -stage -archive -archivedirectory=<dir> -package
```

**Notes:**

- Expect an **unsigned** player binary plus **`.pak`** files under the staged layout.
- **M8-P1** treats **`target_store: internal`** as the only first-class store token for Linux in hub defaults; other stores are **`todo_m8_p2`** unless project YAML opts in explicitly.

---

## Section: IOS (skeleton)

**Requirements (operator-managed):**

- Build host **must** be **macOS**.
- **Xcode** installed; valid **provisioning profile** and signing identity for the bundle id.
- **Bundle ID** aligns with project metadata (for example **`DefaultGame.ini`** / **Project Settings**).

**Illustrative argv (documentation only — full packaging deferred):**

```text
RunUAT.sh BuildCookRun \
  -project=<uproject> \
  -noP4 \
  -platform=IOS \
  -clientconfig=Shipping \
  -cook -pak -compress=zlib \
  -build -stage -archive -archivedirectory=<dir> -package
```

**`todo_m8_p2`:** Provision profile validation, IPA export rules, and cert checklist integration. **M8-P1** does not require a working IPA pipeline in automation.

---

## Section: Android (skeleton)

**Requirements (operator-managed):**

- **Android NDK** and SDK versions matched to the engine’s **SetupAndroid** expectations.
- **Gradle** / AGP toolchain as required by the engine version.
- **Keystore** configuration for signing (still **external CI** responsibility for store keys in **M8-P1**).
- **Package name** matches **`AndroidManifest`** / project settings.

**Illustrative argv (documentation only):**

```text
RunUAT.sh BuildCookRun \
  -project=<uproject> \
  -noP4 \
  -platform=Android \
  -clientconfig=Shipping \
  -cook -pak -compress=zlib \
  -build -stage -archive -archivedirectory=<dir> -package
```

**`todo_m8_p2`:** AAB/APK export policy, Play compliance hooks, and keystore handling documentation.

---

## Section: Maps, cultures, and optional argv

- **`maps`:** When the caller supplies an explicit list, the harness MAY append engine-supported switches (for example per-map cook flags). **M8-P1** does not standardize a single spelling across all UE 5.x minors; project **`cook-package.yaml`** overrides should record the chosen argv fragments once validated on that engine.
- **`cultures`:** Locales to cook (default **`["en"]`** in hub YAML). Map to **`-cultures=`** or equivalent per engine documentation when enabling non-default sets.
- **`extra_uat_args`:** See § UAT argument allowlist.

---

## Section: UAT argument allowlist (`extra_uat_args`)

Each extra token MUST match:

```text
^-[A-Za-z][A-Za-z0-9_=./\\+-]{1,127}$
```

**Rules:**

- **Max 16** extra arguments per invocation.
- **No shell metacharacters** (no `;`, `|`, `` ` ``, `$()`, `&&`, whitespace inside a token, etc.).
- Tokens must begin with **`-`** (UAT long-style switches as single argv cells).

**Python validation (hub checks):**

```python
import re
re.compile(r"^-[A-Za-z][A-Za-z0-9_=./\\+-]{1,127}$")
```

---

## Section: Troubleshooting

| Symptom | Likely cause | Remediation |
|--------|----------------|-------------|
| **Cooking failed** (UAT summary) | Missing content, bad map reference, DDC issues | Open **`Saved/Logs/<Project>.log`**; search **`LogCook: Error:`** |
| **Platform not supported** | Missing platform SDK or wrong engine prerequisites | Run **`UnrealBuildTool -Help`** / platform setup docs; verify SDK install |
| **Shader compile worker failed** | Stale DDC, bad drivers, or OOM during compile | Clear derived data cache; retry; reduce shader complexity |
| **Pak file missing after cook** | **`-pak`** omitted or cook aborted early | Ensure **`-pak`** on cook argv; verify exit code 0 |
| **Staging directory empty** | Wrong **`-archivedirectory`**, or stage step skipped | Confirm path is writable; rerun stage with **`-skipcook`** if cook succeeded |
| **Package step cannot find staged build** | Prior stage failed or paths moved | Verify **`Manifest_*`** files and **`Win64/`** (or platform dir) under archive root |
| **No valid provisioning** (iOS) | Profile / cert mismatch | Fix signing in Xcode; align bundle id |
| **No valid keystore** (Android) | Keystore path or alias wrong | Reconfigure **Project Settings → Android** |
| **Out of memory** | Cook too large for RAM | Reduce **`cultures`**, maps, or texture footprint; try lower compression cost; split cooks |
| **Perforce / P4 errors** | Accidental P4 integration | Always pass **`-noP4`** for cuebert harness runs unless a project explicitly opts in |

### Log locations (typical)

| Artifact | Path |
|----------|------|
| Editor / UAT log | **`Saved/Logs/<Project>.log`** (name varies by executable) |
| Cook output | **`Saved/Cooked/<Platform>/`** |
| Staged build | **`archivedirectory>/<Platform>/`** |

### When to escalate to operators

- **SDK install** or **OS image** changes (not automated by cuebert in **M8-P1**).  
- **Code signing** and **notarization** (external CI; see **`agent-prod-readiness-game`** signing rules when **`build_path`** is present).  
- **Store-specific** packaging (Steam depot scripts, EGS chunking) — ship plan + **post-M8** tooling.

---

## Section: Cross-references

| Doc | Role |
|-----|------|
| `docs/_ai_system/agents/agent-cook-package-game.md` | Agent envelope, phased gating, scope matrix |
| `.cursor/skills/unreal-build/SKILL.md` | **`unreal-build`** MCP skill entry |
| `.cursor/skills/unreal-build/reference.md` | Tool contracts (`unreal_build_target`, `unreal_run_commandlet`, `unreal_tail_log`) |
| `docs/_ai_system/standards/ship-guards.md` | **`ship.prod_readiness`**, **`ship.qa_resilience`**, future **`ship.cook_package`** |
| `docs/projects/cue/plans/active/cuebert-gaming-system.md` | Plan **M8** |

---

Status: **M8-P1** catalog only. **Win64 Shipping** is the reference path; **IOS** / **Android** are skeletons until **M8-P2+**.
