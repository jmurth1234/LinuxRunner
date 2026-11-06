"""Check session environment changes with real Unix sockets in private fixtures."""
import os
import pathlib
import socket
import subprocess
import tempfile
import unittest

BUNDLE = pathlib.Path(__file__).resolve().parents[3] / 'app/LinuxRunner/GUISupport.bundle'


class WaylandEnvironmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='lr-env-', dir='/tmp')
        self.addCleanup(self.temp.cleanup)
        self.path = pathlib.Path(self.temp.name)
        self.home = self.path / 'home'
        self.cache = self.home / '.cache/linuxrunner'
        self.cache.mkdir(parents=True)
        self.support = self.path / 'gui'
        self.session = self.support / 'session-12345678-1234-1234-1234-123456789abc'
        self.session.mkdir(parents=True)
        (self.session / 'authority').write_text('auxiliary cookie')
        (self.session / 'display').write_text('7')
        self.runtime = self.path / 'lrh-1000'
        self.runtime.mkdir(mode=0o700)
        self.x11 = self.path / 'x11'
        self.x11.mkdir()
        self.bind(self.x11 / 'X7')
        self.wayland = self.runtime / 'wayland-0'
        self.bind(self.wayland)
        self.env_file = self.cache / 'desktop.env'
        self.write_environment()
        for name in ['desktop-env.sh', 'publish-wayland-env.sh']:
            source = (BUNDLE / name).read_text()
            source = source.replace('/home/mobile/Downloads/.linuxrunner/gui', str(self.support))
            source = source.replace('/tmp/.X11-unix', str(self.x11))
            source = source.replace('/tmp/lrh-', str(self.path / 'lrh-'))
            source = source.replace('/root/.cache', str(self.home / '.cache'))
            source = source.replace('/home/*/.cache', str(self.path / 'unused/*/.cache'))
            (self.path / name).write_text(source)
        self.env = dict(os.environ, HOME=str(self.home), LR_DESKTOP_SESSION=str(self.session),
                        XDG_RUNTIME_DIR=str(self.runtime), WAYLAND_DISPLAY=str(self.wayland),
                        MOZ_ENABLE_WAYLAND="1", ELECTRON_OZONE_PLATFORM_HINT="auto",
                        QT_QPA_PLATFORM="wayland;xcb", GDK_BACKEND="wayland,x11")

    def bind(self, path):
        connection = socket.socket(socket.AF_UNIX)
        self.addCleanup(connection.close)
        connection.bind(str(path))

    def write_environment(self, wayland=True):
        content = f'DISPLAY=:7\nXAUTHORITY={self.session}/authority\nXDG_RUNTIME_DIR={self.runtime}\nDBUS_SESSION_BUS_ADDRESS=unix:path={self.runtime}/bus\n'
        if wayland:
            content += f'WAYLAND_DISPLAY={self.wayland}\n'
        self.env_file.write_text(content)

    def shell(self, commands, uid=1000):
        script = f'id() {{ echo {uid}; }}\nset -eu\n. "{self.path}/desktop-env.sh"\n' + commands
        return subprocess.run(['/bin/sh', '-c', script], env=self.env, text=True,
                              capture_output=True, check=True).stdout

    def publish(self, *arguments, **environment):
        return subprocess.run(['/bin/sh', str(self.path / 'publish-wayland-env.sh'), *arguments],
                              env=dict(self.env, **environment), text=True, capture_output=True, check=True)

    def test_terminal_adopts_compositor_runtime_and_bus(self):
        result = self.shell('printf "%s\\n" "$XDG_SESSION_TYPE" "$XDG_RUNTIME_DIR" "$DBUS_SESSION_BUS_ADDRESS" "$QT_QPA_PLATFORM"')
        self.assertEqual(result.splitlines(), ['wayland', str(self.runtime),
                         f'unix:path={self.runtime}/bus', 'wayland;xcb'])

    def test_launcher_refreshes_runtime_and_bus(self):
        result = self.shell('unset XDG_RUNTIME_DIR DBUS_SESSION_BUS_ADDRESS WAYLAND_DISPLAY\nlinuxrunner_wayland\nprintf "%s\\n" "$XDG_RUNTIME_DIR" "$DBUS_SESSION_BUS_ADDRESS"')
        self.assertEqual(result.splitlines(), [str(self.runtime), f'unix:path={self.runtime}/bus'])

    def test_x11_clears_stale_wayland_settings(self):
        self.write_environment(wayland=False)
        result = self.shell('printf "%s\\n" "$XDG_SESSION_TYPE" "${WAYLAND_DISPLAY-unset}" "$QT_QPA_PLATFORM" "$GDK_BACKEND" "${MOZ_ENABLE_WAYLAND-unset}"')
        self.assertEqual(result.splitlines(), ['x11', 'unset', 'xcb', 'x11', 'unset'])

    def test_dead_compositor_uses_x11(self):
        self.wayland.unlink()
        result = self.shell('printf "%s\\n" "$XDG_SESSION_TYPE" "${WAYLAND_DISPLAY-unset}"')
        self.assertEqual(result.splitlines(), ['x11', 'unset'])

    def test_root_does_not_adopt_user_runtime_or_bus(self):
        self.env.pop('XDG_RUNTIME_DIR')
        self.env.pop('WAYLAND_DISPLAY')
        self.env.pop('DBUS_SESSION_BUS_ADDRESS', None)
        result = self.shell('printf "%s\\n" "$DISPLAY" "${XDG_RUNTIME_DIR-unset}" "${DBUS_SESSION_BUS_ADDRESS-unset}" "${WAYLAND_DISPLAY-unset}"', uid=0)
        self.assertEqual(result.splitlines(), [':7', 'unset', 'unset', 'unset'])

    def test_publisher_replaces_runtime_and_keeps_bus(self):
        self.env_file.write_text(self.env_file.read_text().replace(str(self.runtime), '/tmp/lr-runtime.old'))
        self.publish(str(self.wayland))
        content = self.env_file.read_text()
        self.assertIn(f'XDG_RUNTIME_DIR={self.runtime}\n', content)
        self.assertIn('DBUS_SESSION_BUS_ADDRESS=unix:path=/tmp/lr-runtime.old/bus\n', content)
        self.assertEqual(content.count('XDG_RUNTIME_DIR='), 1)
        self.assertEqual(self.env_file.stat().st_mode & 0o777, 0o600)

    def test_publisher_adopts_xwayland_display_and_authority(self):
        self.bind(self.x11 / 'X8')
        self.publish(DISPLAY=':8', XAUTHORITY=str(self.session / 'authority'))
        content = self.env_file.read_text()
        self.assertIn('DISPLAY=:8\n', content)
        self.assertIn(f'XAUTHORITY={self.session}/xwayland-authority\n', content)
        self.assertEqual((self.session / 'xwayland-authority').read_text(), 'auxiliary cookie')

    def test_stopped_session_cannot_publish(self):
        (self.session / 'stop').touch()
        before = self.env_file.read_bytes()
        self.publish(str(self.wayland))
        self.assertEqual(self.env_file.read_bytes(), before)
        self.assertFalse((self.session / 'environment.lock').exists())

    def test_previous_session_cannot_replace_current_environment(self):
        self.env_file.write_text(self.env_file.read_text().replace('/authority', '/other-authority'))
        before = self.env_file.read_bytes()
        self.publish(str(self.wayland))
        self.assertEqual(self.env_file.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
