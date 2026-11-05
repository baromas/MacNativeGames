# OoT AV1 integration groundwork

This is preparation for an SDK adapter, not a working OoT movie implementation. No game bytes or video are included.
The local title is 0400486024DEC000, standalone update v131072. MD5Visual's bring-up base is `2e7e6036`.

## Reuse within this repository

Canonical main was inspected at `5843ee56f3ab6911e32d61d46e96fee4ce8137de`:

| Port | Relevant implementation | Useful parts / limits |
| --- | --- | --- |
| Bananza / Pokopia | `games/totk/runtime/ns2_codec.c` | VP8/VP9, image pools and sync events already present in the OoT base. The file is identical between the inspected main and bring-up base. AV1 is not implemented. |
| Mario Kart World | `games/mkw/runtime/codec_host.c`, `games/mkw/tests/codec_host.c` | VP9 CPU/NV12, completion events, backpressure, frame pacing, late-frame handling, bounded rectangular copies with row strides and teardown tests. AV1 and native GPU image delivery explicitly fail. |

MKW supplies a useful full-width guest-stack adapter pattern. Its preference, pool and decoder layouts and its
older symbols are not a specification for SDK 22. Its native-image getter is not a ready GPU movie bridge.

## Existing AV1 backend

[nxnative's AV1 backend](https://github.com/seedds/nxnative/blob/865cc35fad7034d17c2190f8ce349f61f5bcaba1/dm/host/hle_movie_av1.c)
already supports VideoToolbox and dav1d. Its repository is MIT; dav1d retains its BSD-2-Clause license. No copy of
that backend or decoder library is added by this change. The pinned backend was exercised unchanged in a local
standalone harness with synthetic data.

On M3 Pro / macOS 27.0 / Xcode 27.2:

- VideoToolbox reports hardware AV1 support and actually decodes a generated lossless 64x64 limited-range frame.
- Reset followed by decoding the same frame succeeds.
- Forced dav1d 1.5.4 passes the same checks; both packed NV12 outputs are byte-identical.
- Expected Y/U/V values are checked for every pixel, not just a successful decoder return.

This does not check OoT integration, movie timing, 1080p60 throughput, HDR or NDVE reconstruction. The open nxnative
[parallel decoding PR](https://github.com/seedds/nxnative/pull/1377),
[movie-clock PR](https://github.com/seedds/nxnative/pull/1379) and
[NDVE output PR](https://github.com/seedds/nxnative/pull/1331) are related ongoing work; their code is not included here.

## SDK 22 boundary

The recorded local startup abort enters `InitializeAv1DecoderByTransferMemory`; it was reproduced with both the
bring-up base runtime and the address-validation fix. This identifies the initialization path, not every internal
reason for the abort. The current resolver has no host override for that exact entry point.

Other differences identified in the local SDK export inventory:

- Transfer-memory initialization has ten parameters, including a trailing output mode. The two stack enums occupy
  separate eight-byte guest slots. Remote-memory initialization is a separate entry point.
- The submission-ready event getter returns its pointer directly. Reusing an older output-pointer-plus-Result
  wrapper would be the wrong ABI.
- Image-pool initialization has a different symbol/signature; image preference uses ImageTilingMode rather than the
  older CodecMode type.
- Register, submit, acquire/release, properties, start/stop and flush need corresponding AV1 handlers. Installing
  only an initializer does not implement the client protocol.

See [the native host-stack ABI probe](host-stack-abi-tests.md), which tests the stack boundary with synthetic calls
through the production bridge. Original game instructions and files stay local. A resolver audit is not evidence
that every exported function is used by the game or that every resolved handler implements its feature.

## Coordination

MD5Visual explicitly retained the render-pass-gate investigation and assigned the thread/address tests to baromas.
AV1 was listed as available work to coordinate, not as an explicit assignment. A question about unpublished AV1
work has been posted by baromas. These probes and notes are independent groundwork; full integration should be
coordinated before overlapping another contributor's decoder or graphics changes.
