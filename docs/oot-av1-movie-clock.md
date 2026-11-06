# AV1 movie time follows timestamps

At 20 rendered frames/s, handing out one picture of a 60 fps movie per render plays it at about one third speed while its audio continues at normal speed. This matches the user report after the native HMMA work. MIT nxnative PR1379 fixes that queue behavior; the local adaptation uses the existing VideoToolbox/dav1d backend without changing game logic or the renderer.

Before filling a released AV1 picture buffer, choose the newest queued picture whose next picture is at least 50 ms overdue. Do not drop the end-of-stream picture. A new stream, timestamp reversal or Reset starts a new clock. A long pause with at least six presents without a picture, or a guest-visible focus transition, also starts a new clock. A host stall with no presents (such as pipeline compilation) keeps the clock and skips late queued pictures to catch up with audio.

Mac time is CLOCK_UPTIME_RAW, the existing sleep-excluding uptime timebase used by the guest/audio host. Mac guest focus intentionally remains active when switching applications, so merely switching to chat must not reset the movie clock while audio keeps running. iOS records its lifecycle focus transitions; AV1 itself is still unavailable there in this backend. This is an explicit adaptation of the upstream guest_ns/focus APIs, not a claim that their deterministic-clock facility is implemented here.

`DM_CV_LATE=0` restores sequential AV1 delivery for comparison. VP8/VP9 keep sequential behavior. Existing TOTK files/settings and game NSO bytes are untouched. The optional codec log reports movie_ms and clock_ms to compare the delivered timestamps against the same clock; it does not read the game window or capture pictures.

## Validation

The production codec probe adds 93 deterministic clock/queue assertions on each backend: 60 fps timestamps through drain at 20 renders/s, 60 Hz delivery with ahead-of-time pictures and no skipped frames, the 50 ms allowance, EOS preservation, timestamp reversal, a real pause, a host stall, guest focus and Reset. Both automatic VideoToolbox/fallback and forced dav1d pass all six existing SDK/API/native-pool cases. ASan/UBSan pass. With the option disabled, the 20 Hz integration assertion fails as expected.

The output at 20 renders/s is about 0.95 s of movie per elapsed second rather than 0.33 s; the bounded 50 ms lag is intentional. This verifies queue timing, not measured in-game audiovisual sync. The hardware decoder, async frame-thread optimization and GPU FPS are separate topics. The asynchronous decoder PR1377 is not required by the existing synchronous VideoToolbox timestamp contract and has not been imported as part of this fix.

Final builds, full-suite results and the warm-cache game trial are recorded as they complete. No iOS game run is claimed.

Final validation: all eight shared Mac runtime targets built, with the three NS2 binaries rebuilt after the final codec edits; iOS codec/frontend syntax checks pass (no complete iOS app/device run). Full suite with the actual pinned dav1d prefix: 1482 tests, 164 skipped, no failures/errors, 278.620 seconds. Warm-cache in-game audiovisual confirmation is pending.
