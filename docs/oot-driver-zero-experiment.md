# OoT c0+0x640 diagnostic — not an established driver implementation

An OoT v131072 trial reached AV1, audio and the movie compute passes, then stopped while loading a vertex shader:
its reflection reads driver c0+0x640, which this translator deliberately marks unfillable. The crash report and text
log both identify the shader-load abort. This is different from a timeout, out-of-memory failure or GPU fault.

At nxnative main `0f510fd53372704eb7eb70d1cc88f4b4afa7b0fe`, `dm/gfx/nvn/nvn_mtl.m` explicitly says c0+0x640 is
added to the vertex ID but its driver meaning is not established, and leaves it zero. The neighboring c0+0x644 is a
known base-instance field; that does not establish the meaning of 0x640. Do not infer one from the other.

`TOTK_OOT_C0_640_ZERO=1` permits **only** a vertex reflection whose sole unfillable field is exactly c0+0x640 in the
OoT build. The existing zero-initialized driver bank supplies zero and the log prints an EXPERIMENT warning. It does
not edit cached reflection, change the shader translator, or skip the draw. Default behavior still rejects the field.
Any other unknown field, multiple missing fields, other stage, other variant, or other switch value still fails.

This is a temporary, explicitly enabled compatibility experiment, **not a claim of driver correctness**. A positive
picture result would identify a remaining barrier, not prove that zero is right for all draws. Do not enable it in
installed TOTK or advertise this flag as a release fix. The separate sRGB image fix is tested independently.

`test_oot_driver_zero.py` compiles the actual reflection parser for base/DKB/OoT and checks 24 synthetic policy cases.
The test uses no game shader, GPU dispatch or game window. A bounded local game run can use the experiment to inspect
text execution progress; visual correctness still needs the user's report.

Validation of this combined checkpoint: all eight Mac runtime targets compile, both changed Objective-C files
pass iOS syntax checks, and the root suite passes (1,478 tests, 164 skipped, no failures/errors). The existing
production driver c0/c2 GPU probe passes 102 checks. These checks do not establish the unknown word's semantics.

## Bounded game trial with the switch

The combined sRGB build with the explicit diagnostic reached first present at 3.139 s, AV1 decode, repeated movie
compute passes and the experimental word's load. The user reports a **black screen with music and the FPS counter
still running**. The text trace records all 13 NDVE dispatches and real image bindings, followed by sampling of its
sRGB output. This establishes execution/binding progress, not correct image contents.

The process did not hit the prior c0+0x640 abort during this trial. The local helper terminated its own process at
80.27 s (75 seconds after observing first present), exit SIGTERM, not an application crash. No game-window pixels
were read or captured. Full video correctness is still unresolved; zero must not be promoted to a verified default.

Next investigation: NDVE reconstruction and raw-memory data propagation, against nxnative's current implementation.
Upstream #1331 offers an opt-in bilinear diagnostic substitute for NDVE. It is not imported/enabled here and is not
a quality-preserving fix. The upstream write-log bitmap/chunk hints are not ported yet either.
