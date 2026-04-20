# Gauntlet test plan registry

This directory holds **JSON descriptors** for Gauntlet test nodes that teams
consider safe and supported for automation. Each file describes one logical test
plan: the Gauntlet `ITestNode` name, what role and build artifacts it needs, and
operator notes.

## Purpose

- Document **known-good** Gauntlet tests per project or campaign.
- Give `/play` QA and CI harnesses a stable place to discover metadata (role,
  timeouts, whether a cooked build is mandatory).
- M6-P2 seeds only documentation and an example; real entries arrive as games
  onboard.

## Descriptor format (per file)

Each `*.json` file SHOULD include:

| Field | Type | Meaning |
| --- | --- | --- |
| `name` | string | Gauntlet test node id (e.g. `HelloLevelTests.BootTest`). |
| `description` | string | Human-readable intent. |
| `required_role` | string | `Editor`, `Client`, `Server`, or `CookedClient`. |
| `required_build` | boolean | If true, a staged/cooked `build_path` is required. |
| `timeout_s` | number | Suggested per-run ceiling (still clamped by the MCP tool). |
| `notes` | string | Caveats, flaky hardware, or data deps. |

Unknown fields are ignored by the MCP tool.

## Enforcement

`unreal_run_gauntlet` does **not** block unlisted `test_name` values. If the name
is missing from this registry, the tool logs an **info**-level notice and still
runs the test so local experimentation stays frictionless.

## Onboarding

Add a new JSON file when a Gauntlet node is merged and trusted. Prefer one test
per file for clarity; filenames are arbitrary (`my-smoke-test.json` is fine).
