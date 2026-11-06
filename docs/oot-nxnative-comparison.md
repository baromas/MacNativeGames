# nxnative comparison snapshot — 2026-11-06

Verified main: `0f510fd53372704eb7eb70d1cc88f4b4afa7b0fe`. PR #1299 is now closed after upstream landing in `b1d7c707` / `6121fd75`.
This record describes primary-source reports; it is not local gameplay validation.

## Immediate correctness work in this checkout

- LDSM shared-memory subgroup ordering: published as `9013a233`.
- Written RGBA8 image usage, read-only image access and ownership: `32bc167d`.
- Local event-counter service: current follow-up branch, with production-source tests. Fixes status/value/error/flag
  contracts, lost Select requests and virtual-core retention during host sleeps.
- The last game trial stalled before AV1; no correct video or stable gameplay is claimed yet.

## Other upstream work still absent or only partly covered here

1. Full-frame raw memory writes: bitmap by pool-table entry plus tagged 2 MiB lookup hints. Important for NDVE movie
   performance. Requires coherent translator/ABI/backend updates and synthetic GPU checks; do not copy just one half.
2. Raw lookup per-invocation range cache: main `0f510fd5`, PR #1464. Upstream reports about 2 ms less GPU at Kokiri
   Forest. Optimization after correctness; not itself a remedy for missing image outputs.
3. Prewarm the movie compute pipelines to avoid long cold first-frame compilation stalls. Existing game logs are
   needed to distinguish a compile stall from a thread/core deadlock.
4. Conditional rendering, NVN2 task/mesh indirect commands, shader discovery in BNSH slots 7/8 and NDSR records.
   Required before drawing the 3D world faithfully; current runtime-only translator should not be assumed complete.
5. F2FP/F2IP, float and image atomics, gather offsets and dead-code multi-output handling. Do not treat every
   upstream fix as implemented because the base advertises Ampere support.
6. Memory: incremental bindless pool tables, finalized/shared texture lifetimes, mapped pipeline archives; pending
   placement-heap and pressure retirement PRs are especially relevant to this 18 GB Mac. They need validation for
   this renderer's different storage/dirty tracking; increasing the memory cap is not a fix.
7. AV1 asynchronous/dav1d throughput and movie-clock scheduling remain separate pending PRs. This M3 Pro uses
   VideoToolbox when possible; software-decoder speed fixes alone cannot explain its absent video.

## PR state at this snapshot

| PR | State | Merged | Head | Topic |
|---|---|---|---|---|
| [#1444](https://github.com/seedds/nxnative/pull/1444) | open | False | `d2aff9f07ff0` | The Legend of Zelda: Ocarina of Time (Switch 2, 0400486024DEC000, v0 & v131072): playable at 60 fps through Dodongo's Cavern |
| [#1453](https://github.com/seedds/nxnative/pull/1453) | open | False | `85be79094325` | A GPU-only pool's render targets share one placement heap: Ocarina of Time's 3 GB of render targets fit in 0.7 GB |
| [#1455](https://github.com/seedds/nxnative/pull/1455) | open | False | `74c5abf86d7a` | Shared textures no live object resolves to are retired when GPU memory runs short: Ocarina of Time no longer freezes after the talk with Saria |
| [#1462](https://github.com/seedds/nxnative/pull/1462) | open | False | `cd67c65f5446` | Restore six Ocarina foliage libraries with Ampere CAS and record M3 Pro validation |
| [#1464](https://github.com/seedds/nxnative/pull/1464) | open | False | `360ab21fcd39` | Raw global memory lookups reuse the range they last chose: about 3 ms less GPU a frame in Ocarina of Time's Kokiri Forest |
| [#1377](https://github.com/seedds/nxnative/pull/1377) | open | False | `d234d4f629ff` | AV1 on dav1d decodes frames in parallel, each picture with its packet's timestamp, outside the decoder lock |
| [#1379](https://github.com/seedds/nxnative/pull/1379) | open | False | `7ee81e9185bf` | AV1 pictures by the movie's clock: a game slower than its movie skips late pictures instead of playing the movie slowly |

PR #1444 reports a 94-minute run through Dodongo’s Cavern on M5 Pro. Main's game note and M3 Pro reports still
list shader, memory and picture limitations. These are upstream observations, not proof of equivalent behavior on
our M3 Pro or this MacNativeGames stack. The v131072 main BuildID matches this user’s own prepared update.

Installed TOTK is outside this experiment and remains untouched. No game content or generated game shaders are
published. Current code branches are on baromas/MacNativeGames; no new PR or merge was requested.
