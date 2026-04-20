# HelloLevel

Minimal Unreal Engine 5.4 project scaffold for testing cuebert harnesses.

This is a synthetic project — it does not contain compiled binaries or full
engine content. It provides the file structure that cuebert's `/play`,
`/ship`, and `/asset` harnesses expect to find when resolving a project.

## Usage

```
/play --preview --project hello-level
/ship --preview --project hello-level
/asset --preview --project hello-level
```

## Files

- `HelloLevel.uproject` — engine association and module list
- `.cuebert-assets.yaml` — asset manifest for `/asset` harness
- `Config/DefaultEngine.ini` — engine settings
- `Config/DefaultGame.ini` — game metadata
- `Source/HelloLevel/HelloLevel.Build.cs` — build rules
