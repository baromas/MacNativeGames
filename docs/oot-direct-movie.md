# Optional direct movie diagnostic

`TOTK_OOT_MOVIE_DIRECT=1` is an OoT-only, off-by-default experiment adapted from [nxnative PR #1331](https://github.com/seedds/nxnative/pull/1331) (76c20edba480db753ce7092cd2677f6c4a8daa15, MIT). After the 1080p movie conversion dispatch, it looks ahead in the same command list for the exact sequence of 13 reconstruction dispatches. It resolves the final output binding and encodes a bilinear scale to 1440p before skipping those dispatches. State and barriers still replay in order. There is no global shader skip list.

The source must be RGBA8, the destination RGBA8 or RGBA8-sRGB, both 2D/single-sample/default-swizzle, at the observed dimensions and with writable image reflection. If the sequence or output preparation fails validation, the intermediate dispatches run normally. The existing final-dispatch-only replacement can still apply independently when its own conditions hold. Successful output is marked GPU-owned.

This substitutes simpler scaling for NDVE reconstruction when explicitly enabled. The default keeps the original reconstruction. The decoder, audio clock and gameplay timing are unchanged by this diagnostic.

## Validation

- `probe-gpu-oot-movie`: 73 synthetic checks with Metal API validation. Coverage includes the matched sequence, indirect-dispatch and fence rejection, missing output, fallback, sRGB, alpha and output ownership.
- On M3 Pro / macOS 27 with v131072, the median frame time during the opening fell from 41.11 ms (24.3 real FPS) to 16.66 ms (60 real FPS). Median GPU time per frame fell from 40.48 ms to 0.85 ms across the same sampled frame windows.
- In the original run the first two measured dialogue cue intervals took 20.715 and 21.440 seconds for 504 and 520 rendered frames. At 60 FPS those frame counts represent 8.4 and 8.67 seconds. The movie decoder was already using wall time. The faster opening restored visible sync with voice and subtitles in a play test of the guarded build. Horizontal green bands on a black background remain an observed artifact.
- Built and signature-checked the OoT Mac binary. Shared Mac graphics and OoT iOS source syntax checks passed. iOS app and device behavior remain unverified.
