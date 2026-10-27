# Troubleshooting

## The stream dies after a second or two

Symptom:

```
screen capture started at 1920x1080 using h264
mirror session ready (data port: 50861)
streaming error: capture process exited unexpectedly (EOF)
```

This is the VA-postprocessor capture path failing on some Mesa/GStreamer
combinations (seen on AMD radeonsi with GStreamer 1.28). The wrapper installed by
this project disables that path by default, which avoids it.

Check which path you are on:

```sh
doubletake -target <ip> -debug 2>&1 | grep "\[CAPTURE\] using"
```

- `using openh264enc with system-memory frame staging` — good, the workaround is active.
- `using openh264enc with VA scaling to plain raw video` — you are on the buggy path.
  Unset `DOUBLETAKE_VA_SCALING` / remove it from the wrapper.

If you want the VA path (for a hardware encoder) and it breaks, set
`DOUBLETAKE_VA_SCALING=1` **only** if you actually use `vah264enc`/`vah265enc`.

## The top bar icon does not appear

GNOME only scans for new extensions **at session start**. Log out and back in
once after installing.

If it is still missing:

```sh
gnome-extensions info doubletake@local
journalctl --user -b | grep -i -E "doubletake|JS ERROR|extension"
```

Common causes:

- the UUID is not in the enabled list:
  `gsettings get org.gnome.shell enabled-extensions`
- the Shell version is not declared in `metadata.json` (`"shell-version": ["50"]`
  — adjust for your GNOME version)
- user extensions disabled entirely:
  `gsettings get org.gnome.shell disable-user-extensions` (should be `false`)

## A "Share your screen" dialog appears on every start

That is GNOME's screen-cast portal asking for permission. Choose **Share** once;
doubletake requests a persistent token and should not ask again. If it keeps
asking, the token was invalidated — delete it and re-approve:

```sh
python3 - <<'PY'
import json, pathlib
p = pathlib.Path.home() / ".config/doubletake/credentials.json"
data = json.loads(p.read_text())
for record in data.values():
    record.pop("restore_token", None)
p.write_text(json.dumps(data, indent=2))
PY
```

## `mirror setup failed: HTTP 401` / nothing happens after pairing

The Apple TV has **Settings → AirPlay and HomeKit → Require Password** enabled.
Pass that password:

```sh
DOUBLETAKE_CODE='your-password' doubletake -target <ip>
```

## No audio

Screen audio needs the receiver to advertise a format doubletake can encode
(ALAC by default). If audio fails but video works:

```sh
doubletake -target <ip> -no-audio
```

Check that `gst-inspect-1.0 avenc_alac` exists.

## The TV shows the desktop but text looks soft

The captured image is your *logical* display resolution. At 125 % scaling on a
1920×1200 panel that is 1536×960, upscaled to the TV's 1080p canvas. Options:

1. Set display scaling to 100 % (sharpest, smaller UI).
2. Raise the bitrate: `-bitrate 12000` or `DOUBLETAKE_BITRATE=12000`.
3. Lower the frame rate to spend more bits per frame: `-fps 24 -bitrate 12000`.

## Mirroring is laggy or drops frames

- Check CPU: `ps -C gst-launch-1.0 -o pcpu=` — a software 1080p30 encode uses
  most of one core.
- Lower `-fps` (30 → 24) or `-bitrate`.
- Wi-Fi: 12 Mbps plus audio is usually fine, but 60 fps doubles the video rate.
- The encoder here is software (`openh264enc`); Fedora's patent-free repo has no
  `x264enc`/`vah264enc`. Installing RPM Fusion's `gstreamer1-plugins-ugly`
  (x264) or a `gst-plugin-va` build enables faster paths — then unset
  `DOUBLETAKE_VA_SCALING` in the wrapper.

## Start over

```sh
./uninstall.sh            # remove binaries, app, extension
rm -rf ~/.config/doubletake   # forget settings and pairing
./install.sh              # reinstall
```
