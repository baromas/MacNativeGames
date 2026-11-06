# Image bindings without the allocation hint

Follow-up to `fix/oot-ldsm-shared-ordering`. Comparison with nxnative's MIT image preparation path
([PR #1299](https://github.com/seedds/nxnative/pull/1299), revision
`ee9b7765d579c46e45a7297493565e098f3bda33`, `dm/gfx/nvn/nvn_mtl.m`, `image_prepare` / `img_binding`)
identified a missing platform operation. This is a narrow implementation using this renderer's existing storage
recreation and descriptor invalidation; it does not copy the whole upstream renderer.

A storage image binding establishes image use even without the optional NVN IMAGE allocation hint. The old renderer
substituted its discard dummy when such a texture lacked Metal ShaderWrite usage. It also required ShaderWrite for
read-only images, although existing reflection already distinguishes those access modes.

- Prepare writable plain RGBA8 images before opening a compute encoder or drawing. Recreate storage with ShaderWrite
  on the GPU timeline, copying all levels/slices through the existing usage-upgrade mechanism. Split an active render
  pass before recreation. Sampling aliases re-resolve after the storage generation changes.
- Preserve the guest descriptor. Only the renderer's registered descriptor gains its discovered usage requirement.
- Mark actual image writes GPU-owned so an unrelated CPU write in the same pool does not restore stale upload data.
- Read-only images retain CPU upload behavior and need no ShaderWrite usage. Unsupported formats retain the explicit
  diagnostic/dummy path; this patch does not claim to implement every image format, atomic or uniform-handle image.
- No game instruction, image data, shader source, resolution or reconstruction pass is changed.

## Checks

`probe-gpu-image-usage` uses generated 16x16 textures and two short test Metal kernels, through production resource
preparation, compute dispatch and argument encoding. It checks 12,288 values: preserved source pixels, real compute
writes, sampling aliases, retention of the old in-flight texture, render-pass splitting, no stale CPU restoration,
and read-only image updates without GPU ownership. Metal API validation is enabled.

The probe also passes with pre-encoded arguments disabled (`TOTK_DISP_PREARGS=0`) and with compute encoder reuse
disabled (`TOTK_DISPATCH_REUSE=0`). Negative control `TOTK_PROBE_NEGATIVE=31` disables only the upgrade in this probe:
it fails numeric output validation, reproducing the discard-dummy behavior. Existing storage-view, sRGB-view and
linear render-target probes pass. This is offscreen synthetic readback, not game-window inspection.

All eight shared Mac runtime targets and iOS syntax checks are exercised locally; the final validation record is
recorded with the commit. No complete iOS app or device test is claimed.

## Game relevance and limits

A text-only OoT movie trace reports the first conversion output as RGBA8 (`format=0x25`, flags=0, usage=0x5,
pool_flags=0x24), causing the old path to write a dummy. This fix addresses that concrete missing output operation.
A subsequent game trial stalled before AV1 initialization, so it cannot establish whether the complete movie picture
is correct. Black/pink video is not claimed fixed. Installed TOTK and its settings are untouched.
