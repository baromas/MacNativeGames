# OoT catch-up inventory (2026-11-07)

MD5Visual feat/oot-boot was checked at a2e9e756b9, including a57fb5c2. We adapted changes individually; the entire branch was not merged.

| Area | Local status |
|---|---|
| Address64 waits / thread tests | Implemented and tested here; MD5Visual accepted these tests |
| SDK22 AV1 / native images | Local VideoToolbox + dav1d implementation, legacy/transfer/remote ABI and pool lifecycle tests retained |
| c24 push constants | 6be66776 routes existing cached reflection to immutable push snapshots |
| Native HMMA | bc46bd8a adapts the documented matrix layout; numerical synthetic GPU and actual native-translator tests |
| NVN2 device constants | 9e5b83d9, NS2-only; production-thunk probe passes |
| Frequent LightEvent logging | Off by default, controlled by TOTK_WAIT_LOG; calls/results verified |
| Additional MD5Visual stall / memcpy probes | Diagnostic helpers not copied wholesale; local text-only sampling retained |
| VS c0+0x640 | Still an explicit local zero-value diagnostic; no blanket fillable-field whitelist imported |

nxnative main was checked at b2d46b86d0. Imported pieces include subgroup LDSM ordering, image-write usage preparation, offline eventfd semantics, native matrix lowering and the guarded-deferred-write correction (via Kolkka PR1836). The AV1 movie-clock adaptation is being validated in a separate commit/branch.

Still distinct work: task/mesh pipelines, packed image-write views and pool descriptor arrays, the raw-global bitmap/range-cache optimizations, broader Ampere opcode coverage, pressure-aware resource lifetimes, pipeline prewarm seeds and optional asynchronous decoding. These have not all been imported. PR1456's matrix-chain optimization has a reported dotted-column regression (PR1576 / PR1544), so it was not copied into the current matrix implementation.

User confirmation so far: movie and menu visible after a roughly five-minute cold compile, slow movie relative to audio, working menu input. Full 3D gameplay is not yet established. Do not call this parity with nxnative's playable profile.
