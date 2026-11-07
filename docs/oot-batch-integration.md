# OoT host and shader integration, 2026-11-07

This is a development branch, not a claim of parity with nxnative's playable OoT profile. It combines the interdependent graphics paths before another game boot. No game files or translated game shaders are part of the change.

## Sources and boundaries

- MD5Visual `feat/oot-boot` at `a2e9e756`: earlier boot work and native matrix layout, adapted in preceding commits.
- Kolkka/MacNativeGames `aa723802..e11c84a6` (PR1836): task/mesh translation and Metal replay, indirect compute and mesh commands, buffer clears, packed image views, table texture/sampler handles, addressable pool residency, SDK22 output streams and clock entry points, PlayReport completion, and cached pool-liveness checks.
- MIT nxnative `339d9f23`: expanded Ampere instruction lowering, via Kolkka's patch 0010. This retains our native HMMA and LDSM ordering; the reported-regressing matrix-chain optimization was not imported.
- MIT nxnative PR1575 `79b34d15`: reserve primitive-index bytes for every 32-lane block, including padded lanes. The C# adapter already had extra padding, which happens to cover the 126-primitive case, but did not cover every other non-multiple of 32. The allocation now covers all blocks, including blocks needed for vertices.
- MIT nxnative PR1543 `c254ba96`: below-target game-time correction. Adapted as a checked runtime producer in the same private-page/text-padding mechanism used by TOTK, rather than changing this tree's verified NSO rewrite hashes.

Equivalent implementations are not stacked: this branch keeps its existing eventfd errno/status/core-handoff behavior, SDK22 codec/native-image contracts, audio renderer, verified decompression and thread IDs. The duplicate eventfd implementation and duplicate HMMA postprocessor from the incoming topic were removed.

## Correctness changes

Task and mesh stages are lowered to Metal object/mesh functions, including their stage memory and payload. Native direct/indirect mesh draws use those stages. Indirect dispatch counts and their driver-constant copies stay on the GPU timeline. Compute constants at NVN2 c0+4 are supplied in addition to the existing c0+0x200 grid. Buffer fills preserve arbitrary 32-bit values.

NVN2 base instance is resolved to Metal's builtin in the translator before caching and reflection. Only the established scalar read is replaced. Other lanes or unrecognized function forms remain unfillable, and the old explicit zero-value diagnostic is still off by default. Pool reflection recognizes the matching texture/sampler table binding kinds. Shader chain v13 invalidates previous libraries coherently across runtime, seed tools and prebuilt translators.

The game's original frame producer divides a constant by target FPS; at low render rates the game, including subtitle logic, can run behind the audio. The checked veneer retains the original division and takes the larger of it and the measured time scaled by that constant. It uses eight present samples, limits each interval to 0.1 s and the result to four 60 Hz steps, and resets on a backwards/non-advancing clock. This is separate from AV1 queue selection, which is already corrected in the preceding commit. `DM_FRAME_DELTA=0` retains the original step.

The complete reconstruction network remains enabled. Incoming NDSR bypass is explicitly opt-in. The e11c84a6 game-barrier optimization is also opt-in until separately validated. No game boot was used while resolving integration/compile failures. GPU probes caught and corrected an accidental default-setting change during integration; the original existing defaults were restored before any game launch.

## Verification and remaining work

The first batch passed 1,489 tests (164 skipped) and the focused Metal probes. On the first isolated boot, the host presented at 3.509 s and decoded AV1 through movie time 21.833 s. At 30.27 s the runtime aborted on a vertex shader that already had a Metal base-instance parameter and also still read the NVN driver word. The initial adapter accepted only entry points that did not already declare that parameter. Synthetic Metal readbacks contain only constructed test data, never pixels from the running game. User window inspection remains disabled.

OoT iOS packaging is not supported by this tree's IPA builder. The Mac and iOS NativeAOT translators are rebuilt together; host/graphics source compilation is checked separately and must not be described as an iOS device run.

Still to investigate after the combined build: full 3D rendering and material correctness, subtitle/audio timing in play, long-session memory pressure, packed-image families and dynamically fetched image/buffer-texture handles. Optional async AV1 decoding, broad raw-memory range optimizations and prewarm manifests are not prerequisites silently assumed present here. A renderer build passing is not evidence that these are complete.

## Shader and host follow-up

The v14 shader chain fixes the crash from the first batch. A vertex shader can already have a `[[base_instance]]` argument when it still explicitly reads NVN c0+0x644. The adapter now reuses that argument. The previously failing variant was translated offline and compiled to Metal AIR with no remaining unfillable driver words. The constructed regression exercises both forms of the argument list.

The Ampere ALU and memory emitters were compared with nxnative at `6d5ed718`. The follow-up incorporates the new ALU behavior, shared and global atomics, descriptor-address handling and directed rounding. Raw global memory reuses the last matching pool for successive accesses within an invocation. Only pools included in the actual table become resident. An indirect GPU probe writes two sets of counts on the GPU and checks both NVN2 driver aliases, the grid size and the result across the two launches. It also passes with explicit CPU readback as a reference.

The selected `e8ee7448` host changes limit OoT to 60 FPS using the host clock, correct the NVN timestamp unit, and release alternate type views with their owning descriptor. The pool remains scoped to 9 GiB of guest address space. The per-texture ownership and dirty-page checks already in this renderer serve the CPU-upload case fixed by nxnative's terrain patch. The two render and dispatch overlap changes need a separate ordering comparison. The integration keeps its existing measured-time producer.

The first v14 cold test took roughly three minutes to create the heaviest Metal pipelines. The same shader cache on the warm run kept decoder timestamps about 55–70 ms behind the movie clock in steady playback. These measurements describe decoder delivery. Visual subtitle alignment and picture quality require play validation.

The v14 development launcher enables the existing compressed-render, mid-pass-clear and 8-bit-index widening paths. The separate Metal validation probes for each passed, along with GPU-generated dispatch counts and texture retirement. With the flags enabled, the warmed v131072 run passed the compressed-target guard, built task/mesh pipelines and encoded the first mesh draw after the opening movie. The same run also exercised GPU-driven indirect compute and layered passes. Runtime logs establish that these operations were submitted. Scene appearance is still unverified.

The v14 run ended at its 483-second bound with no fatal error, 401 runtime Metal libraries built and approximately 7.51 GiB system wired memory at peak. The scene's first frames were still compiling pipelines. The game completed the opening movie; the run had not created a world save. Several task/mesh c0 diagnostics were false positives: the runtime filled those storage tables already, and v15 teaches the MSL validator the exact ranges.

## v15 follow-up against nxnative main

Compared main through `581f9c1d`. The three applicable changes since the previous comparison were fragment depth, narrow shared stores and zero-copy buffer creation.

- The Ampere fragment depth register follows the sample mask after four slots per enabled render target, even with partial channel masks. On a constructed two-target shader the previous compiler emitted 0.25 from R6; the new one emits the intended 0.75 from R9. The test also covers no color, one RGBA target, and a target at the upper end of the mask. Maxwell retains its existing behavior.
- Known NVN2 8-bit and aligned 16-bit shared writes lower to Metal narrow stores. Adjacent threads writing independent bytes avoid contending on a 32-bit compare-and-swap. Unrecognized helper shapes retain the generic CAS path. Both widths went through the real translator and Metal compiler. No in-game speedup is claimed from the probe.
- On this M3 Pro, a Metal buffer created over an already protected page returned command-buffer success while all three pages retained their old contents. Creating over writable pages and protecting later produced the correct GPU bytes. OoT now opens a short writable window for overlapping tracked ranges while constructing a pool buffer, keeping page-protection changes serialized and preserving dirty stamps. The existing pool probe validates all 49,152 bytes, including the previously protected page, and the unchanged stamp. This follows the existing GPU writeback assumption that the guest synchronizes use of storage during such an operation.
- 1,492 root tests ran, 164 skipped, zero failures. Nine tests exercised the real C# adapters or NativeAOT translator. The production OoT pool probe passed 115,151 checks with Metal validation enabled. Rebuilt Mac and iOS NativeAOT translators. No iOS device run.
- A local-only preparation pass read the game's own Zstandard dictionaries and shader archives using the MIT nxnative BNSH/BAHS/NDSR/NDVE readers. It matched 349 of 385 previously observed keys, including task and mesh stages, and translated 373 v15 variants. This avoids rebuilding those translations during launch. Metal still has to prepare pipelines for the new scene, and the source code, dictionaries and translated artifacts remain local.

## End-to-end validation on M3 Pro

The v15 development build with v131072 presented at 2.4 s in the long run and encoded the first scene's native task/mesh draw at about 278 s after scripted title confirmation. A later frame recorded 840 draw records across 76 render passes. The renderer continued beyond frame 11,400, with median present intervals of 25–36 ms in the measured scene windows. The run stopped at its 843-second test bound without a fatal or a reported GPU command error. Peak system wired memory was 9.72 GiB, below the 12 GiB guard. This used an isolated empty profile. No world save was created, and the test did not inspect the window, subtitle positions or final picture.

Some cold scene transitions still took up to about 100 seconds. Stack sampling and per-frame counters located the stalls in synchronous Metal library and pipeline creation. After the long run, 1,021 exact-source Metal libraries compiled offline with the same safe math mode. The local launcher uses this cache and the isolated run's pipeline metadata with background warm-up. A short launch of the final signed binary presented at 2.06 s and loaded at least 401 prebuilt libraries without on-the-spot library compilation. This short test does not establish a warm in-world timing comparison.

The long-run logs also exposed missing Metal GPU start timestamps being counted as the host's uptime. The follow-up discards incomplete or non-finite timestamp pairs while still retiring completions. The FPS/load overlay probe passed 712 checks and the updated graphics sources passed iOS-target syntax checking. All eight Mac targets built for v15 before this telemetry-only follow-up, and the final OoT runtime rebuilt and passed signature verification. The separate 64-threadgroup Metal readback checked byte and half-word stores into adjacent lanes and contention on one byte through the production shared-store rewrite.
