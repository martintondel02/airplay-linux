// Doubletake AirPlay — top bar control for the doubletake AirPlay sender.
//
// Drives the `doubletake` CLI (installed in ~/.local/bin) as a subprocess:
// start/stop mirroring, pair with a PIN, and pick quality.

import GObject from 'gi://GObject';
import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import St from 'gi://St';

import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

const BINARY = GLib.build_filenamev([GLib.get_home_dir(), '.local', 'bin', 'doubletake']);
const ZENITY = '/usr/bin/zenity';
const CONFIG_DIR = GLib.build_filenamev([GLib.get_user_config_dir(), 'doubletake']);
const CONFIG_PATH = GLib.build_filenamev([CONFIG_DIR, 'shell.json']);

const DEFAULT_CONFIG = {
    target: '192.168.1.169',
    name: 'Living Room',
    bitrate: 12000,
    fps: 30,
};

const QUALITY_CHOICES = [
    {label: 'High — 12 Mbps', bitrate: 12000},
    {label: 'Balanced — 8 Mbps', bitrate: 8000},
    {label: 'Data saver — 4 Mbps', bitrate: 4000},
];

const FPS_CHOICES = [30, 60];

// Ornament is stable across recent Shell versions; keep a fallback so a change
// cannot take the whole indicator down.
const ORNAMENT_NONE = PopupMenu.Ornament?.NONE ?? 0;
const ORNAMENT_DOT = PopupMenu.Ornament?.DOT ?? 1;

function loadConfig() {
    try {
        const [, bytes] = GLib.file_get_contents(CONFIG_PATH);
        const text = new TextDecoder().decode(bytes).replace(/\u0000+$/, '');
        const parsed = JSON.parse(text);
        return {...DEFAULT_CONFIG, ...parsed};
    } catch (e) {
        return {...DEFAULT_CONFIG};
    }
}

function saveConfig(config) {
    try {
        GLib.mkdir_with_parents(CONFIG_DIR, 0o755);
        GLib.file_set_contents(CONFIG_PATH, JSON.stringify(config, null, 2));
    } catch (e) {
        console.error(`doubletake: failed to save ${CONFIG_PATH}: ${e}`);
    }
}

function decode(bytes) {
    return new TextDecoder().decode(bytes.get_data());
}

const DoubletakeIndicator = GObject.registerClass(
class DoubletakeIndicator extends PanelMenu.Button {
    _init() {
        super._init(0.0, 'Doubletake AirPlay', false);

        this._config = loadConfig();
        this._proc = null;
        this._state = 'idle';
        this._tail = '';
        this._pinPrompted = false;

        this._icon = new St.Icon({
            icon_name: 'video-display-symbolic',
            style_class: 'system-status-icon',
        });
        this.add_child(this._icon);

        this._statusItem = new PopupMenu.PopupMenuItem('Not mirroring', {reactive: false});
        this.menu.addMenuItem(this._statusItem);

        this._deviceItem = new PopupMenu.PopupMenuItem(this._deviceLabel(), {reactive: false});
        this.menu.addMenuItem(this._deviceItem);

        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());

        this._toggleItem = new PopupMenu.PopupMenuItem('Start mirroring');
        this._toggleItem.connect('activate', () => this._toggle());
        this.menu.addMenuItem(this._toggleItem);

        this._pairItem = new PopupMenu.PopupMenuItem('Pair with Apple TV…');
        this._pairItem.connect('activate', () => this._pair());
        this.menu.addMenuItem(this._pairItem);

        this._buildQualityMenu();

        this._addressItem = new PopupMenu.PopupMenuItem('Set Apple TV address…');
        this._addressItem.connect('activate', () => this._askAddress());
        this.menu.addMenuItem(this._addressItem);

        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());

        this._errorItem = new PopupMenu.PopupMenuItem('', {reactive: false});
        this._errorItem.visible = false;
        this.menu.addMenuItem(this._errorItem);

        if (!GLib.file_test(BINARY, GLib.FileTest.EXISTS)) {
            this._setError(`${BINARY} not found — is doubletake installed?`);
        }
    }

    _deviceLabel() {
        const {name, target} = this._config;
        return name ? `${name} · ${target}` : target;
    }

    _buildQualityMenu() {
        const quality = new PopupMenu.PopupSubMenuMenuItem('Quality');

        this._bitrateItems = [];
        for (const choice of QUALITY_CHOICES) {
            const item = new PopupMenu.PopupMenuItem(choice.label);
            item.connect('activate', () => {
                this._config.bitrate = choice.bitrate;
                saveConfig(this._config);
                this._syncQuality();
                this._setStatus(this._idleStatusText());
            });
            quality.menu.addMenuItem(item);
            this._bitrateItems.push({item, bitrate: choice.bitrate});
        }

        quality.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());

        this._fpsItems = [];
        for (const fps of FPS_CHOICES) {
            const item = new PopupMenu.PopupMenuItem(`${fps} fps`);
            item.connect('activate', () => {
                this._config.fps = fps;
                saveConfig(this._config);
                this._syncQuality();
                this._setStatus(this._idleStatusText());
            });
            quality.menu.addMenuItem(item);
            this._fpsItems.push({item, fps});
        }

        this.menu.addMenuItem(quality);
        this._syncQuality();
    }

    _syncQuality() {
        for (const {item, bitrate} of this._bitrateItems)
            item.setOrnament(bitrate === this._config.bitrate ? ORNAMENT_DOT : ORNAMENT_NONE);

        for (const {item, fps} of this._fpsItems)
            item.setOrnament(fps === this._config.fps ? ORNAMENT_DOT : ORNAMENT_NONE);
    }

    _idleStatusText() {
        return `Not mirroring · ${this._config.bitrate / 1000} Mbps, ${this._config.fps} fps`;
    }

    _setStatus(text, iconName) {
        this._statusItem.label.text = text;
        if (iconName)
            this._icon.icon_name = iconName;
    }

    _setError(text) {
        this._errorItem.label.text = text;
        this._errorItem.visible = Boolean(text);
        if (text)
            this._setStatus('Error — see below', 'dialog-warning-symbolic');
    }

    _toggle() {
        if (this._proc) {
            this._stop();
            return;
        }
        this._setError('');
        this._start([]);
    }

    _start(extraArgs) {
        if (this._proc)
            return;

        const args = [
            BINARY,
            '-target', String(this._config.target),
            '-bitrate', String(this._config.bitrate),
            '-fps', String(this._config.fps),
            ...extraArgs,
        ];

        this._tail = '';
        this._pinPrompted = false;

        try {
            this._proc = Gio.Subprocess.new(
                args,
                Gio.SubprocessFlags.STDIN_PIPE |
                Gio.SubprocessFlags.STDOUT_PIPE |
                Gio.SubprocessFlags.STDERR_MERGE);
        } catch (e) {
            this._setError(`Could not start doubletake: ${e.message}`);
            this._proc = null;
            return;
        }

        this._state = extraArgs.includes('-pair') ? 'pairing' : 'starting';
        this._toggleItem.label.text = 'Stop mirroring';
        this._setStatus(extraArgs.includes('-pair') ? 'Pairing…' : 'Starting…',
            'media-playback-start-symbolic');

        this._readLoop();
        this._proc.wait_async(null, (proc, res) => {
            try {
                proc.wait_finish(res);
            } catch (e) {
                // Cancelled or already reaped.
            }
            this._onExit();
        });
    }

    _readLoop() {
        const stdout = this._proc.get_stdout_pipe();
        const read = () => {
            stdout.read_bytes_async(4096, GLib.PRIORITY_DEFAULT, null, (stream, res) => {
                let bytes;
                try {
                    bytes = stream.read_bytes_finish(res);
                } catch (e) {
                    return;
                }
                if (bytes.get_size() === 0)
                    return;

                this._handleOutput(decode(bytes));
                read();
            });
        };
        read();
    }

    _handleOutput(text) {
        this._tail += text;
        if (this._tail.length > 8000)
            this._tail = this._tail.slice(-4000);

        if (!this._pinPrompted && this._tail.includes('PIN shown on the receiver'))
            this._promptPin();

        for (const raw of text.split('\n')) {
            const line = raw.trim();
            if (line)
                this._handleLine(line);
        }
    }

    _handleLine(line) {
        if (line.includes('connected to: ')) {
            const match = line.match(/connected to: (.+?) \(model:/);
            if (match) {
                this._config.name = match[1];
                saveConfig(this._config);
                this._deviceItem.label.text = this._deviceLabel();
            }
        } else if (line.includes('pairing complete')) {
            Main.notify('Doubletake', 'Pairing complete');
            this._setStatus('Paired', 'object-select-symbolic');
        } else if (line.includes('mirror session ready')) {
            this._state = 'streaming';
            this._setError('');
            this._setStatus('Mirroring', 'media-record-symbolic');
        } else if (line.includes('streaming error')) {
            this._setError(line.replace(/^.*streaming error: /, ''));
        } else if (line.includes('mirror setup failed')) {
            this._setError(line.replace(/^.*mirror setup failed: /, ''));
        } else if (line.includes('stream ended')) {
            this._setStatus('Not mirroring', 'video-display-symbolic');
        }
    }

    _promptPin() {
        this._pinPrompted = true;
        this._runZenity(
            ['--entry', '--title=Pair with Apple TV',
                '--text=Enter the PIN shown on your Apple TV',
                '--ok-label=Pair'],
            pin => {
                if (!pin) {
                    this._stop();
                    return;
                }
                try {
                    const stdin = this._proc?.get_stdin_pipe();
                    if (stdin) {
                        stdin.write_all(new TextEncoder().encode(`${pin}\n`), null);
                        stdin.flush(null);
                    }
                } catch (e) {
                    this._setError(`Could not send PIN: ${e.message}`);
                    this._stop();
                }
            });
    }

    _askAddress() {
        this._runZenity(
            ['--entry', '--title=Apple TV address',
                '--text=IP address or hostname of the Apple TV',
                `--entry-text=${this._config.target}`],
            value => {
                if (!value)
                    return;
                this._config.target = value.trim();
                this._config.name = '';
                saveConfig(this._config);
                this._deviceItem.label.text = this._deviceLabel();
                this._setStatus(this._idleStatusText());
            });
    }

    _runZenity(args, callback) {
        try {
            const proc = Gio.Subprocess.new(
                [ZENITY, ...args],
                Gio.SubprocessFlags.STDOUT_PIPE);
            proc.communicate_utf8_async(null, null, (p, res) => {
                try {
                    const [, stdout] = p.communicate_utf8_finish(res);
                    callback((stdout ?? '').trim());
                } catch (e) {
                    callback('');
                }
            });
        } catch (e) {
            this._setError(`Could not open dialog: ${e.message}`);
            callback('');
        }
    }

    _pair() {
        if (this._proc)
            this._stop();
        this._setError('');
        this._start(['-pair']);
    }

    _stop() {
        const proc = this._proc;
        if (!proc)
            return;

        this._proc = null;
        try {
            proc.send_signal(2); // SIGINT
        } catch (e) {
            // Already gone.
        }

        GLib.timeout_add(GLib.PRIORITY_DEFAULT, 1500, () => {
            try {
                proc.force_exit();
            } catch (e) {
                // Already gone.
            }
            return GLib.SOURCE_REMOVE;
        });

        this._state = 'idle';
        this._toggleItem.label.text = 'Start mirroring';
        this._setStatus(this._idleStatusText(), 'video-display-symbolic');
    }

    _onExit() {
        if (!this._proc)
            return;
        this._proc = null;
        this._toggleItem.label.text = 'Start mirroring';
        if (this._state !== 'error')
            this._setStatus(this._idleStatusText(), 'video-display-symbolic');
        this._state = 'idle';
    }

    destroy() {
        this._stop();
        super.destroy();
    }
});

export default class DoubletakeExtension extends Extension {
    enable() {
        this._indicator = new DoubletakeIndicator();
        Main.panel.addToStatusArea('doubletake', this._indicator);
    }

    disable() {
        this._indicator?.destroy();
        this._indicator = null;
    }
}
