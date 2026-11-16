# Verifying and extracting the v0.5.0 qualification evidence

Package contents:

| File | SHA-256 |
|---|---|
| `knotrel-v0.5.0-evidence.tar.gz` | `13e136056d20ee96fcfb534819e1ac10fc85238a54b56b5e8af2dcd0e4c5dce7` |
| `knotrel-v0.5.0-measured-executables.tar.gz` | `b717703c9abaf9d7bff1392e1c8435bee345db316f65953e57d0ad2d2ddbce53` |
| `MANIFEST.sha256` (8,663 evidence files + 30 executables) | `4c30bf09aa93d98c6a50eaab04a86111015306ae600d61db7f875925537e3adb` |
| `INVENTORY.md`, `inventory.json`, `VERIFY.md` | recorded in the versioned copy |

## 1. Verify the archives

```sh
shasum -a 256 knotrel-v0.5.0-evidence.tar.gz knotrel-v0.5.0-measured-executables.tar.gz MANIFEST.sha256
```

Compare with the table above (and with
`results/lifecycle-qualification-v0.5.0/evidence/INVENTORY.md` in
knotrel-benchmarks).

## 2. Extract

```sh
mkdir v050-evidence && cd v050-evidence
tar -xzf ../knotrel-v0.5.0-evidence.tar.gz            # v0.5.0-dev/, v0.5.0-qualification/, v0.5.0-remediation/, v0.5.0-MANIFEST/
tar -xzf ../knotrel-v0.5.0-measured-executables.tar.gz # A-campaign targets/... and lifecycle-probes/...
```

## 3. Verify every file against the manifest

```sh
shasum -a 256 -c v0.5.0-MANIFEST/MANIFEST.sha256
```

All 8,693 lines must report `OK`. Paths are relative to the evidence root;
the probe executables are listed under `lifecycle-probes/` and extract there.

## Notes

- Regenerable build trees, git clones and the isolated Cargo home are not
  included (see `INVENTORY.md`).
- Files contain absolute paths of the qualification host (local user name
  `rt`, `/Users/rt/workspace/knotrel/...`). No credentials, tokens, keys or
  e-mail addresses were found by an automated scan (patterns for GitHub, AWS,
  crates.io and Slack tokens, private keys, bearer headers, password
  assignments and e-mail addresses). Keep the archives private.
- Executables are macOS arm64 binaries built with rustc 1.100.0; they are
  preserved as measured artifacts, not as distributable software.
