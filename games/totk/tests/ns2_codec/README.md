# SDK 22 AV1 and native movie images

These probes use the production codec/API adapters and native-image bridge. They do not load a game, translated
shader, movie, key or save, and do not read a game window. The resource adapter uses mock NVN calls; the decoder
uses real VideoToolbox or the pinned static dav1d library, and real libvpx image allocation/conversion.

Run on an Apple silicon Mac with the normal build dependencies:

```
make probe-ns2-codec
.venv/bin/python tests/ns2_codec/run.py --sanitize
```

The sanitizer run instruments our adapters/backend; the separately built static codec libraries are uninstrumented.
Both modes test automatic backend selection and `DM_AV1_DAV1D=1`. Automatic selection need not use hardware on
older chips or for formats rejected by VideoToolbox. On M3 Pro, 64x64 uses hardware and 66x48 deliberately exercises
fallback after VideoToolbox refuses that size. No FPS or real-time throughput claim follows from these tiny frames.

The root unittest runner always runs the native-image adapter on Darwin arm64. To enable its codec case against an
existing prepared build without rebuilding dav1d in the source checkout:

```
MNG_DAV1D_PREFIX=/absolute/path/to/build/dav1d/install python -m unittest discover -s tests -p test_ns2_codec.py -v
```

Six cases per backend cover two sizes and legacy / transfer-memory / remote-memory initialization; SDK symbols,
full-width guest ABI argument narrowing; native pool sizing/alignment; completion events and sync generations;
packet timestamps; every NV12 pixel and RGBA conversion; row/tail canaries; reset, EOS and teardown/handle invalidation.
The separate resource probe checks device, target, format, stride, storage flags, rejection of invalid handles/formats,
reuse of the pool across texture initialization and exactly-once pool teardown. Actual Metal linear surface upload,
CPU writes and GPU rendering are covered separately by the existing `probe-gpu-linear-rt` runtime probe.

## Synthetic packets

`synthetic_av1.h` holds locally generated, single-frame, lossless AV1 temporal units. They contain a constant red
I420 image (Y=81, U=90, V=240), 64x64 or 66x48, limited BT.601. No console or game content was used. Generate
the YUV file by concatenating `w*h` bytes of 81 and two `(w/2)*(h/2)` planes of 90 and 240, then run FFmpeg's
libaom encoder:

```
ffmpeg -f rawvideo -pixel_format yuv420p -video_size 64x64 -framerate 60 -i red.yuv \
  -frames:v 1 -c:v libaom-av1 -cpu-used 8 -crf 0 -b:v 0 -aom-params lossless=1 \
  -colorspace smpte170m -color_primaries smpte170m -color_trc smpte170m -color_range tv red.ivf
```

Strip the 32-byte IVF file header and the 12-byte frame header. The remaining bytes are the packet. Repeat with
`66x48`. The checked golden values, not an FFmpeg version's byte-identical compression, define the fixture contract.
