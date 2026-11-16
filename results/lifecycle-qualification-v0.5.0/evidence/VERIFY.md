# Verifying and extracting the v0.5.0 qualification evidence

The package is stored in the private repository
`knotrel/knotrel-qualification-evidence`, directory `v0.5.0/` (see
`INVENTORY.md` for the commit and how to request access).

## 1. Fetch the exact commit and verify the archives

```sh
mkdir v050-check && cd v050-check
git init -q
git fetch --depth 1 https://github.com/knotrel/knotrel-qualification-evidence.git 83ec5474b62d9506352e93a95cf54069826052d7
git checkout -q FETCH_HEAD
cd v0.5.0
shasum -a 256 knotrel-v0.5.0-evidence.tar.gz knotrel-v0.5.0-measured-executables.tar.gz MANIFEST.sha256
```

Compare with the digests in `INVENTORY.md`.

## 2. Extract

```sh
mkdir ../../extract && cd ../../extract
tar -xzf ../v050-check/v0.5.0/knotrel-v0.5.0-evidence.tar.gz
tar -xzf ../v050-check/v0.5.0/knotrel-v0.5.0-measured-executables.tar.gz
```

## 3. Verify every file against the manifest

```sh
shasum -a 256 -c v0.5.0-MANIFEST/MANIFEST.sha256
```

All 8,693 lines must report `OK`.

Executables are macOS arm64 binaries built with rustc 1.100.0, preserved as
measured artifacts, not as distributable software.
