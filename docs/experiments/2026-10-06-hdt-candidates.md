# Preserved HDT candidate patches

These patches and complete before/after forest sources are saved in this checkout,
independently of temporary build directories. They are separate alternatives
against the frozen current-ranking core; do not blindly combine them. No commit
or staging action is implied by this inventory.

| Candidate | Saved file | SHA-256 |
|---|---|---|
| Rank-zero early return; experimental, not integrated | [patch](../../results/2026-10-06-hdt-reroot/candidate.patch) | `28818b211f780437efc89a5d74b92271d10875439da60b05405422bcfd0741e9` |
| Single-pass root/rank; experimental, not integrated | [patch](../../results/2026-10-06-hdt-root-rank/candidate.patch) | `c00ae032d60798a87fa84bfda71e9be1a025d7c21f75c0570fcd3c2d35a1c9c3` |
| Dedicated concat extraction; pilot gate not met, not integrated | [patch](../../results/2026-10-07-hdt-concat/candidate.patch) | `09b904c31a2309276d6e4336239dd3481716a5c45f96191a8ea07386759eef62` |
| Right-associated tour joins; pilot gate not met, not integrated | [patch](../../results/2026-10-07-hdt-join-order/candidate.patch) | `306a4ac697cb6da67ce02248b702b6a9114140a2624f46735950d13a90f82527` |
| Promotion-only right-associated joins; pilot passed; full matrix has 7 regression flags, not integrated | [patch](../../results/2026-10-07-hdt-promotion-joins/candidate.patch) | `7d96115df8d72a6f6374b0a9637d1ff215c76b91a3e8eef69f179884cecad3d3` |
| Packed optional indices; 64-byte tokens, integrated 2026-10-09 for memory savings; original matrix flag retained | [patch](../../results/2026-10-08-hdt-packed-tokens/candidate.patch) | `75c9ddbb86393e9822c520efe0a19d87ccb36c6d5f96980e1fb1d0b951c0c942` |

Each result directory retains the build script, compiler/source metadata and
measurements needed to rebuild a candidate if temporary binaries disappear.

Packed-index integration preserves the original measurements and adverse pairs.
See the [follow-up diagnosis](../../results/2026-10-09-hdt-packed-resources/README.md)
for the separate confirmation and limits; historical result files are unchanged.

## ETT candidate

The [ETT packed-index pilot](../../results/2026-10-09-ett-packed-tokens/README.md)
ports only the optional-index representation to the separate ETT forest.
Integrated into ETT on 2026-10-09; this is not a combined HDT patch.
Saved [patch](../../results/2026-10-09-ett-packed-tokens/candidate.patch) SHA-256: `1c38ea0df38b8a5cdf16cfdc1d5445b9a14f1b1a2a8bbb82cb6b284fc23729db`.

The [full ETT matrix](../../results/2026-10-09-ett-packed-tokens-matrix/README.md)
completes 38 cells with no runtime screening flags, while retaining sparse setup
regressions. The measured ETT candidate was integrated on 2026-10-09, retaining the setup tradeoff and experimental status.
