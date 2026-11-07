# The Legend of Zelda: Ocarina of Time (Switch 2)

Experimental development variant on `games/totk` (`GAME_OOT` / `GAME_NS2`), following the existing DKB/PKP arrangement. Title `0400486024DEC000`, standalone update v131072, main BuildID `e0f3ccfaf50065ae4ea01eb5aeb13b1a`. No game content is included.

The current integration combines the MD5Visual boot work, selected changes from Kolkka/MacNativeGames through `e8ee7448`, and OoT-related MIT nxnative fixes through `581f9c1d`. It preserves this branch's tested SDK 22 codec ABI, event counters, native HMMA, push snapshots and AV1 movie clock. See [the integration report](../../docs/oot-batch-integration.md) for what is checked and what remains unverified.

Before this batch, the user confirmed visible movie/menu output, but also slow video, subtitle drift and a subsequent abort. Other contributors report a loaded save reaching Kokiri Forest. Their play results are not evidence that this exact combined build is playable.

Build from lawfully obtained, original game files using import_dump, prepare_modules and prepare_runtime; do not edit an already rewritten module. From a prepared `games/totk` work tree:

```sh
make -j2 binary-oot SHADER_LIST=../oot/assets/shader_list.tsv
TOTK_GPU_ALLOW_SUBMIT=1 TOTK_GPU_BLOCKRT=1 TOTK_GPU_MIDCLEAR=1 TOTK_GPU_WIDEN=1 \
  build/totk-native-oot rewritten/oot boot
```

Use the matching rebuilt NativeAOT translator and shader chain `totk-native-v16-ns2-mesh-layout`. Old shader libraries cannot be reused unchanged after this chain update. There is no packaged OoT .app/iOS build flow yet.

For development runs, keep `TOTK_SHADER_CACHE` on a persistent OoT directory for this translator chain and keep `DM_PSO_USER` on a persistent TSV. The runtime stores translated variants and Metal pipeline archives in the cache, and pipeline descriptors in the TSV. Set `TOTK_SHADER_CONTRIB` to a separate local OoT file to record shareable identifiers as you play.

To collect past sessions, run `games/totk/scripts/shader_list.py merge <list> <cache-dir> <pso-user.tsv>` with a copy of the list under an `oot/assets` directory. Pass the cache before its TSV so recorded pipeline names resolve to their portable bind states. Run `stats` on the result. Share only the list as described in [the contribution guide](../../docs/shader-list.md). Preparing a seed from another player's list still depends on finding the recorded shader keys in the local dump. The development corpus and seed tools do not cover all OoT shader archive formats or task/mesh stages yet.

The complete reconstruction network runs by default. Lossy `TOTK_NDSR_BYPASS=1` and the separate direct-movie experiment are diagnostic opt-ins. `TOTK_BARRIER_GAME=1` enables the newly imported barrier-order optimization; it remains off while this integration is being validated. `DM_FRAME_DELTA=0` selects the original fixed game step for comparison. No image-quality trade-off is required by the default path.

Memory remains a limitation on 16/18 GB machines. Only addressable pools enter the raw pool table; resource lifetimes and the system wired-memory guard are retained. The texture table has finite capacity and does not yet handle every image/buffer-texture handle read from memory. Full-game appearance, long-session stability and iOS device operation still require testing.
