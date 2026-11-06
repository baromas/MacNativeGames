# Ampere LDSM shared-memory ordering

This follow-up builds on `feat/oot-sdk22-av1`. It adapts the narrow ordering fix from nxnative
[PR #1376](https://github.com/seedds/nxnative/pull/1376), commit `2d6f86f819c4b80ed4bbd80c66aa623e6e7dc85f` (MIT).

LDSM collectively reads matrix rows that other lanes in the warp stored. The Switch's ordering does not translate
implicitly to Metal: stores can move past another lane's reads without an execution/memory barrier. Patch 0008 emits
one subgroup barrier before the collective shared reads and one after, before subsequent stores reuse the rows.
It does not change the matrix arithmetic, remove reconstruction or change the game's code/state.

## Checks

- A constructed Ampere MOV/LDSM/STS/EXIT program covers normal and transposed four-matrix LDSM layouts. It is assembled
  from ISA fields and contains no game bytes. The previous native translator fails the check with zero barriers in
  both cases; the patched managed build and rebuilt native executable pass.
- The test inspects actual SPIR-V, follows Workgroup pointer access chains and verifies two `OpControlBarrier`s
  surround the shared loads. Execution/memory scopes are Subgroup; memory semantics are acquire-release Workgroup.
- SPIRV-Cross emits two `simdgroup_barrier(mem_flags::mem_threadgroup)` calls. Both generated programs compile to AIR
  with the installed Metal toolchain. This is synthetic compilation, not a game-frame capture.
- Four non-LDSM synthetic service cases, DebugMode on/off, retain byte-identical SPIR-V, intermediate reflection,
  Metal source and final reflection against the previous native executable. No whole-game shader regression is claimed.
- NativeAOT Mac executable and iOS static translator library rebuild from the patched sources (.NET SDK 10.0.401).
  All eight shared Mac runtime targets build. Root suite: 1,462 tests, 164 skipped, no failures/errors.
- New shader chain `totk-native-v10-ldsm-order` is used consistently by the runtime, seed preparation and packaging
  checks; the affected fixture identities follow it. Old generated shaders must not mask the changed translation.

Run:

```
python -m unittest discover -s tests -p test_ldsm_barriers.py -v
MNG_TEST_SPIRV_CROSS=/absolute/path/to/spirv-cross python -m unittest discover -s tests -p test_ldsm_barriers.py -v
```

The second form also checks Metal source and compiles it with `xcrun metal`. `MNG_TEST_XLATE` can point at a managed
`totk_xlate.dll` for a source-build comparison; the default is the repository's checked native executable.

## Game status

The AV1-only build decodes real 1080p pictures and plays audio, but the user reports initially absent video and later
an all-pink movie near 20 FPS. The local text-only movie trace executes the NDVE shaders named in the upstream
ordering report. This establishes relevance; it does not prove that the ordering fix resolves the whole pink picture.

A separate diagnostic also reports the first conversion's image texture lacking ShaderWrite usage: the old binding
path substitutes a dummy image in that case. That resource issue is being investigated separately. Correct video,
gameplay and device iOS behavior are not claimed by the synthetic checks above. Installed TOTK remains untouched.
