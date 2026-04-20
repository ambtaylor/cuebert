# Certification report — hello-level (indie-light)

**Generated:** 2026-04-20T12:48:00Z  
**Profile:** indie-light  
**Project:** hello-level  
**Platforms:** Win64, Mac

## Summary

All blocking checks passed for this documentation-only example. Two **warn** findings were recorded for naming and metadata consistency. No **fail** findings.

## Findings

### WARN — Executable naming

- **Check:** `cert.indie-light.exec-name`  
- **Evidence:** `.cuebert/traces/ship/example-2026-04-20T12-30-00Z/cooked/Win64/HelloLevel-Win64-Shipping-42.exe`  
- **Detail:** Executable stem includes the build number suffix (`42`). For `indie-light`, this is treated as a hygiene warning rather than a blocker.

### WARN — Version metadata drift

- **Check:** `cert.indie-light.metadata-slice`  
- **Evidence:** `HelloLevel-Mac-Shipping.app/Contents/Info.plist`  
- **Detail:** Short marketing version string does not exactly match the ship plan semver patch segment. Operator acknowledged for this drop.

## Platform notes

- **Win64:** Cook output path present; checks executed against synthetic inventory counts in envelope only.  
- **Mac:** Cook output path present; plist slice reviewed as text metadata only (no vendor-specific compliance prose).

## Footer

Fixture status: M3-P3 documentation-only. Real checklist engines ship in M8-P2.
