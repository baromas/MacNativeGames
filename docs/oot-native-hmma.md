# Native matrix lowering for OoT movie networks

MD5Visual's a57fb5c2 contained a missing postprocessing step: the Ampere translator emits `dmsh_hmma16816_f16` with a documented scalar placeholder contract, and final MSL must replace it with native SIMD-group matrix operations. This tree did not perform that step. Fixing c24 supplied real parameters, but did not supply the matrix implementation.

`Hmma.cs` adapts MD5Visual's MIT implementation, matching nxnative's established 16x16 by 16x8 half-precision layout. It allocates scratch per SIMD group, orders scratch reads/writes, adds C, returns both packed halves, and gives generated locals collision-free names. An unrecognized helper signature fails explicitly. The newer nxnative accumulator-chain optimization is not imported: PR1576 reports dotted columns and PR1544 proposes a numerical refinement.

The shader chain is now `totk-native-v11-native-hmma`. Mac and iOS native translators were rebuilt from the same source. Runtime, seed and packaging expectations change together so old scalar outputs are not reused. Neither translated game shaders nor guest bytes are committed.

## Checks completed

- Production C# rewriting plus actual Metal dispatch: 896 exact outputs over 1/2/4 SIMD groups, nonzero C and two consecutive accumulations, compared with an independent CPU matrix product. Generated data only. The zero stand-in fails numeric output, and malformed helper/no-helper paths are checked.
- Constructed Ampere instructions through the shipped NativeAOT service generate native matrix operations and compile to AIR with the actual translated helper signature.
- All eight shared Mac runtime binaries built. Native iOS translator library built; no full iOS app or device claim.
- The MD5Visual NS2 device constants are supplied only in NS2 builds. The graphics probe checks them through the production NVN thunk. Unsupported properties still stop explicitly. Existing Switch 1 constants are unchanged.
- Frequent LightEvent observer diagnostics are gated with TOTK_WAIT_LOG, preserving the original guest calls and return values.

Installed TOTK remains untouched. Full-suite and OoT visual results are recorded as they finish. No game window or texture-pixel readback is performed.
