# Optional direct movie diagnostic

`TOTK_OOT_MOVIE_DIRECT=1` is an OoT-only, off-by-default experiment inspired by nxnative PR #1331 (76c20edba480db753ce7092cd2677f6c4a8daa15, MIT). It remembers the output of the exact 1080p conversion shader in the current submission and replaces only the matched final 1440p reconstruction dispatch with a bilinear compute scale. The intermediate dispatches still execute. There is no command-stream lookahead or gameplay change.

The source must be RGBA8, the destination RGBA8 or RGBA8-sRGB, both 2D/single-sample/default-swizzle, at the observed dimensions and with writable image reflection. A missing binding, wrong key/layout, stale submission or failed preparation falls back to the original dispatch. Successful output is marked GPU-owned and aliases remain coherent. No shader bytes, translated game code or image captures are included.

This deliberately substitutes simpler scaling for NDVE reconstruction. It is **not** a lossless correctness fix or an optimization claim. No default setting or installed TOTK file is changed.

## Validation

- `probe-gpu-oot-movie`: 68 checks through production matching, reflection bindings and dispatch, including a generated gradient, sRGB encoding/alpha, missing output, stale submission, and an actual fallback kernel. Metal API validation enabled. Synthetic pixels only.
- All eight shared Mac binaries built. Full-suite and iOS checks recorded with the follow-up validation.
- On M3 Pro / macOS 27, the bounded v131072 game run reached the replacement and ran until the helper stopped it at 80.52 seconds; no crash. The user reported black video with music/FPS followed by the Zelda logo and menu. Video is **not fixed**. No live window or game texture pixels were read.

The next comparison found bank c24 being parsed as driver c0 despite the replay already supporting NVN2 push constants. That issue is investigated separately, without treating this workaround as its fix.

Combined validation with the subsequent c24 fix: 1479 tests / 165 skipped, no errors, all eight Mac runtime targets built and changed Objective-C files passed iOS syntax checks. A complete iOS app/device run is still unverified.
