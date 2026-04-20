# Commandlet allowlist (unreal-build)

## Purpose

`unreal_run_commandlet` invokes Unreal Editor in headless mode with `-run=<Name>`.
That is a high-privilege surface. This directory holds an **allowlist** of
commandlet names backed by small JSON descriptors so operators and agents only
run commandlets that have been reviewed for cuebert harness use.

## Expected format

One JSON file per commandlet (any filename ending in `.json`). Each descriptor
should include:

| Field | Type | Meaning |
| --- | --- | --- |
| `name` | string | Commandlet name as passed to `-run=` |
| `description` | string | Human-readable purpose |
| `allowed_arg_patterns` | list of strings | Regexes each extra CLI arg may match |
| `notes` | string | Caveats, engine version, or harness ownership |

The loader reads every `*.json` here and collects the `name` field. Unknown files
without a valid `name` are skipped with a log warning.

## M6-P1 seed

The allowlist is **empty** on purpose. Populate alongside **M6-P4** /
**M8** when cook and package agents land (for example `CookCommandlet`,
`ResavePackages`).

## Development bypass

For local experimentation only, set:

`CUEBERT_UNREAL_BUILD_ALLOW_UNLISTED_COMMANDLETS=1`

When set, commandlet names must still match the bypass regex
(`^[A-Za-z][A-Za-z0-9_]{0,127}$`) and extra arguments must pass the per-arg
regex enforced in `_build_runner.py`. Do not enable in shared CI secrets or
production profiles.
