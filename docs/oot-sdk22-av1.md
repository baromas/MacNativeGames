# OoT SDK 22 AV1 integration (Mac)

Work branch: `baromas/MacNativeGames:feat/oot-sdk22-av1`, based on MD5Visual's `feat/oot-boot` at `2e7e6036`,
with the address-wait and host-stack ABI tests. This is a codec/platform contribution, not a claim of playable OoT.
It does not change guest game instructions, game state or the installed TOTK app.

## What changed

- Adapt nxnative's MIT AV1 backend at `865cc35fad7034d17c2190f8ce349f61f5bcaba1`: VideoToolbox hardware decode,
  with dav1d fallback for older hardware or a rejected stream. `DM_AV1_DAV1D=1` forces the fallback for diagnosis.
- Build dav1d 1.5.4 from its official SHA256-pinned archive as an arm64 static library. The build records source,
  script/tool/options and output identities. No Homebrew dav1d dylib is needed by the runtime. Retain both upstream
  licenses and package them with NS2 runtime installs/updates.
- Serve SDK 22 VP8/VP9/AV1 transfer-memory and remote-memory initialization, the direct submission-event getter,
  the updated image preference and five-argument image pool initializer. The ninth/tenth enum parameters use
  full-width guest stack slots, with explicit narrowing; width/height are explicitly narrowed too.
- Preserve the existing VP8/VP9 CPU picture route. AV1 feeds owned I420 pictures through that same queue, timestamps,
  events, sync generations, reset/EOS and teardown path. An AV1 picture allocation failure is returned as an error.
- SDK 22 pools reserve aligned, strided RGBA storage. Publish the complete converted picture before signaling
  readiness, expose a native image handle and map it to an NVN linear RGBA texture. Legacy CPU pool sizing remains
  unchanged and does not expose an unwritten native surface. Finalized pools invalidate their handles.
- Answer NVN2 device property `0x67` with the shader code/control alignment (256), matching nxnative. OoT's movie
  library queries it before loading its reconstruction shaders; the previous runtime aborted on the query.

The backend and new native-image NVN implementation are Mac/NS2-gated. iOS retains the explicit unsupported AV1
route; no new decoder dependency is introduced there. Non-NS2 targets do not link dav1d or VideoToolbox for this work.

## Validation on M3 Pro / 18 GB / macOS 27.0 / Xcode 27.2

- Six generated-packet API cases per backend: legacy, transfer-memory and remote-memory initialization at 64x64
  and 66x48. Every NV12 pixel and RGBA conversion is checked, along with dimensions, timestamps, alignment,
  stride/tail canaries, events, sync generations, reset, EOS and teardown. Hardware and forced dav1d runs pass.
  The small 66x48 case is refused by VideoToolbox on this machine and successfully exercises automatic fallback.
- Production native-image adapter with mock resource calls: valid/rejected handles and formats, exact device/format/
  dimensions/stride/storage flags, pool reuse and exactly-once cleanup pass. ASan/UBSan adapter/backend runs pass;
  the separately built codec libraries themselves are not sanitizer-instrumented.
- Existing `probe-gpu-linear-rt`, with Metal validation, passes 430,480 checks of cold upload, CPU updates and GPU
  rendering retained across dirty pool writes. This is synthetic GPU validation, not a readback of the game window.
- All eight Mac runtime executables build: TOTK 1.0.0/1.2.1/1.4.3, BotW 1.6.0/1.9.0, Bananza, Pokopia and OoT.
  Only OoT was run against game data. These are runtime builds, not eight packaged app/playthrough checks.
- Changed C files pass an iOS arm64 SDK compile/syntax check both with and without NS2 defines. No full iOS app
  build, device test, AV1 movie throughput benchmark or HDR validation is claimed.
- Root unittest suite: 1,460 tests, 164 skipped, no failures/errors. The additional license packaging test also
  passes in the focused 22-test game-data suite. See `games/totk/tests/ns2_codec/README.md` for reproducible probes.

## Actual game result and remaining work

Local title `0400486024DEC000`, standalone update `v131072`, own verified NUP. Bounded launches use a separate
OoT profile/cache and the normal one-game lock. No game window or pixel capture was read by the assistant.

Before this work the SDK aborts in AV1 initialization. The modified runtime initializes the 1920x1080 AV1 decoder,
decodes actual pictures through VideoToolbox, delivers them into the SDK 22 pool, and translates/dispatches movie
compute shaders. The user heard audio, initially saw no video, then reported an all-pink picture around 20 FPS.
Correct movie presentation and gameplay therefore remain **unconfirmed/broken**; decoded pictures alone are not
evidence of a correct frame on screen.

Text traces also captured intervals with no further graphics submissions while audio and host clock calls continued.
Window occlusion and the native settings panel were involved in some runs, so these intervals do not by themselves
prove a new decoder deadlock or the cause of the pink picture. Early startup was sensitive to a quiet-light-event
logging experiment; that experiment was discarded and the author's service observers are unchanged.

Next: capture text-only bindings/dispatches during the active movie; separate YUV conversion, NDVE reconstruction,
resource write-back and presentation, and verify each platform fix synthetically before another game comparison.
Do not skip NDVE, substitute lower quality scaling or force gameplay state as a supposed correctness fix.

## Relevant nxnative work (snapshot 2026-11-06)

- [#1299](https://github.com/seedds/nxnative/pull/1299), `ee9b7765`: initial movie/title/save/Kokiri route, chiefly
  tested on M5/24 GB. Includes global-write tracking/pool lookup improvements, texture lifetime/cache fixes,
  conditional rendering configuration and mesh/task shader inventory handling. Still WIP, not a full playthrough.
- [#1312](https://github.com/seedds/nxnative/pull/1312), `ac024428`: indirect mesh/task replay, atomic color-view
  aliasing and deferred release partitioning; opening-route coverage on M3 Max with v131072. The release partition
  change is already in MD5Visual's base. The other renderer changes are not imported by this codec contribution.
- [#1376](https://github.com/seedds/nxnative/pull/1376): LDSM subgroup barriers for NDVE shared-memory ordering;
  [#1377](https://github.com/seedds/nxnative/pull/1377): parallel dav1d decode and packet timestamps;
  [#1379](https://github.com/seedds/nxnative/pull/1379): movie-clock late-picture handling. Not included here.
- [#1331](https://github.com/seedds/nxnative/pull/1331) is an optional direct movie scaling workaround that bypasses
  NDVE reconstruction, not a fix for its shader translation. It is not enabled or imported here.

Source attribution: `THIRD_PARTY_NOTICES.md`. There are no game modules, shaders, movies, keys, fonts or saves in this
change. The generated red AV1 packets are original synthetic fixtures, with generation instructions beside them.
