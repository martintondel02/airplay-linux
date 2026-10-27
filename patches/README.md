# Patches

These files modify [doubletake](https://github.com/omarroth/doubletake), which is
licensed under the **GNU Lesser General Public License v3.0 or later**. The
patches are therefore derivative works and are distributed under the same
license (LGPL-3.0-or-later), not under this repository's MIT license.

## 0001-optional-va-scaling-opt-out.patch

Adds a `DOUBLETAKE_DISABLE_VA_SCALING` environment variable that makes
doubletake skip the VA postprocessor capture plans on Wayland and use the
system-memory plan instead.

Why: on some Mesa/GStreamer combinations (reproduced on Fedora 44, GStreamer
1.28, AMD Radeon 840M with radeonsi) the VA plan passes startup validation,
streams for roughly 60 frames, and then the GStreamer child dies:

```
[CAPTURE] using openh264enc with VA scaling to plain raw video
screen capture started at 1920x1080 using h264
mirror session ready (data port: …)
streaming error: capture process exited unexpectedly (EOF)
```

The failure is data-volume dependent rather than time dependent (fps 30 → ~2 s,
fps 10 → ~6 s, always ~60 frames), and the existing runtime fallback never
triggers because startup validation already succeeded. The system-memory plan
does not hit it.

With a software encoder the system-memory plan costs nothing extra: the frame
had to be downloaded from VA memory before `openh264enc` anyway. Machines with a
working hardware encoder (`vah264enc`) can set `DOUBLETAKE_VA_SCALING=1` in the
wrapper to keep the VA path.

Remove this patch (build unpatched) if upstream fixes the fallback.
