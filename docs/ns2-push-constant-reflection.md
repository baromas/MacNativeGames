# NVN2 push constants were mistaken for driver c0

The Ampere translator intentionally maps the compute push region to c24 and emits `kind: drvcb, bank: 24`. Command recording and replay already supported the graphics/compute push blocks, including argument invalidation and immutable snapshots. But the JSON reader classified every driver bank except 2 as driver c0. A c24-only shader therefore received the zero bank rather than the current push bytes.

The movie's NV12-to-RGBA shader reads its conversion coefficients from this block. Zero coefficients explain a black conversion output even with decoding, dispatch and image writes working. Other NDVE kernels also read c24; this is a platform binding defect, not a per-game shader patch.

The reader now routes bank 24 to the existing CBUF/NVN_PUSH_BANK path. Constants are shared with command recording through nvn_push.h. c0/c2 behavior is unchanged. Existing cached reflection is sufficient; no translator rebuild, shader cache invalidation or game-byte change is needed. nxnative already makes this distinction using its separate NVN_RB_PUSH kind; the local renderer already had the equivalent replay branch.

## Checks

- Synthetic JSON reader check in base and NS2 configurations: bank 24 reaches push storage, c0/c2 remain driver banks.
- `probe-gpu-drv-c0` now additionally runs a constructed kernel through production JSON parsing, OP_PUSH_CONST replay and dispatch. Three dispatches read all 256 bytes, with a partial compute update and an independent graphics update before GPU completion. 192 new values plus the existing 102 checks pass under Metal API validation.
- Negative control `TOTK_PROBE_NEGATIVE=32` restores the erroneous classification only in the fixture and fails the first nonzero expected value.
- iOS syntax checks for nvn_mtl.m and nvn_refl.m pass. No complete iOS app or device run is claimed.
- Full Mac build/test and actual OoT results are recorded below after completion. Installed TOTK is unchanged. No game image readback is performed.

Validation completed: all eight shared Mac runtime targets built; full suite 1479 tests, 165 skipped, no failures/errors (246.997 s). Installed TOTK executable SHA256 remains `d19f79370e2b116eaf5c1a382b109b6af0d8c2fbd2ac0dbf10acb8907e7acfeb`. The next v131072 trial uses normal NDVE (direct scaling off) and the existing explicit c0+0x640 diagnostic; visual confirmation is pending.
