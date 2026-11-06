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

## Follow-up from nxnative

The final chain is `totk-native-v12-guarded-hmma`, incorporating MIT nxnative 9507c221's guarded deferred-write correction via Kolkka's patch 0009 (PR1836 revision f70b81ba). A deferred register write records the predicate at issue and only commits if it held; a final predicated instruction must not jump past pending commits. The focused constructed-instruction regression fails with the old translator and passes with the new one. This is the fix the upstream OoT work associates with lost glyph-quad coordinates.

The LightEvent-wrapper test verifies all original calls, the full 64-bit timeout and 32-bit return value with logging off and on. The full generic graphics probe separately exposed an existing NS2 minimal-layout/oracle mismatch; the new `probe-nvn-properties` checks the production device thunks independently of that unrelated layout case.

The first combined unit run had a timeout-fixture error (its fake tar never wrote its PID under concurrent build load). The final suite is run again after builds complete; no change to the archive tests is made.

Final combined validation: 1482 tests, 165 skipped, no failures/errors (238.442 s), with heavy builds complete before the suite. All eight Mac runtime targets build, and base/NS2 host syntax checks pass for iOS. The independent device-property probe is recorded below after its run. Whole-game visual output remains to be confirmed in one new launch.

Production-thunk `probe-nvn-properties` passed on OoT (NVN major 231, minor 40). The single follow-up launch uses v12, standard NDVE and a fresh isolated shader cache. The text-only audit confirms native matrix code in the newly generated movie shaders; image output is pending user confirmation. The existing explicit c0+0x640-zero diagnostic remains enabled only by the local launcher. No direct-movie scaling is enabled.
