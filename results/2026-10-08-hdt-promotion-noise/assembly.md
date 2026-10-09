# Frozen-binary code inspection

[assembly.json](assembly.json) records tool/version/commands and normalization. Raw excerpts and normalized diffs are saved per row in order. Only instruction-address prefixes and numeric target addresses preceding symbol annotations are removed; symbol offsets, registers and other immediates remain. Equality is textual under those rules, not full binary equality.

| Symbol | Before address | After address | Instructions before/after | Normalized equal | Exact disassembly prefix |
|---|---|---|---:|---|---:|
| `<knotrel_core::hdt_forest::Forest>::link` | `000000010004c7d4` | `000000010004c7d4` | 150/150 | False | 128 |
| `<knotrel_core::hdt_forest::Forest>::join` | `000000010004c53c` | `000000010004c53c` | 166/166 | False | 69 |
| `<knotrel_core::hdt_forest::Forest>::reroot` | `000000010004cf68` | `000000010004cf68` | 79/79 | False | 18 |
| `<knotrel_core::hdt_forest::Forest>::connected` | `000000010004d394` | `000000010004d394` | 54/54 | False | 20 |
| `<knotrel_core::hdt::HdtGraph>::cut` | `000000010004d46c` | `000000010004d46c` | 640/640 | False | 169 |
| `<knotrel_core::hdt::HdtGraph>::link` | `000000010004de6c` | `000000010004de6c` | 733/733 | False | 18 |
| `<knotrel_core::hdt::HdtGraph>::promote` | `000000010004e9e0` | `000000010004e9e0` | 205/334 | False | 0 |
| `<knotrel_core::hdt::HdtGraph>::connected` | `000000010004ef10` | `000000010004f114` | 78/78 | False | 0 |

The ordinary Forest::link retains its address and instruction count; its disassembly is identical through the first return. Differences afterward include relocated allocation-call targets and panic metadata. There is no extra wrapper call visible on that ordinary return path. HdtGraph::promote grows by 129 AArch64 instructions (516 bytes); later symbols move by 0x204. The compiler incorporated the promoted-link work into promote rather than emitting a separate promoted-link symbol.

This rules against an obvious added ordinary-link wrapper on the inspected path. It does not rule out data/code layout or hardware effects, and does not establish them as the timing cause. No performance counters, affinity control or cache flushing were used.
