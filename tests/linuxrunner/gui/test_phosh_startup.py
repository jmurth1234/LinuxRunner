"""Check Phosh schema detection and compositor graphics routing."""
import os
import pathlib
import re
import subprocess
import tempfile
import unittest

BUNDLE = pathlib.Path(__file__).resolve().parents[3] / 'app/LinuxRunner/GUISupport.bundle'

class PhoshStartupTests(unittest.TestCase):
    def test_wayland_compositors_do_not_load_the_glx_bridge(self):
        for desktop in ('phosh', 'wayfire', 'hyprland'):
            for mode in ('mesa', 'mesa-metal-resident', 'mesa-metal-verify'):
                with self.subTest(desktop=desktop, mode=mode):
                    script = '. "$1"; LR_GUI_GPU_MODE=$3; selected=$(lr_desktop_gpu_mode "$2" "$3"); lr_gpu_route "$selected" /missing; printf "%s|%s|%s" "$LR_GUI_GPU_MODE" "$LR_GUI_GPU_ACTIVE" "${LD_PRELOAD:-}"'
                    result = subprocess.run(['/bin/sh', '-ec', script, 'test', str(BUNDLE/'gpu-env.sh'), desktop, mode], capture_output=True, text=True, check=True, env={k:v for k,v in os.environ.items() if k != 'LD_PRELOAD'})
                    self.assertTrue(result.stdout.endswith(f'{mode}|mesa|'), result.stdout)

    def test_x11_desktops_keep_the_application_graphics_setting(self):
        result = subprocess.run(['/bin/sh', '-ec', '. "$1"; lr_desktop_gpu_mode lxqt mesa-metal-resident', 'test', str(BUNDLE/'gpu-env.sh')], capture_output=True, text=True, check=True)
        self.assertEqual(result.stdout.strip(), 'mesa-metal-resident')

    def app_check(self, missing=''):
        source = (BUNDLE/'desktop-profile.sh').read_text()
        function = re.search(r'^phosh_apps_available\(\) \{.*?^\}', source, re.M | re.S).group()
        with tempfile.TemporaryDirectory() as temp:
            command = pathlib.Path(temp)/'dpkg-query'
            command.write_text('#!/bin/sh\n[ "$3" != "$MISSING_PACKAGE" ] || exit 1\nprintf "install ok installed"\n')
            command.chmod(0o755)
            return subprocess.run(['/bin/sh', '-c', function+'\nphosh_apps_available'], env=dict(os.environ, PATH=temp+':'+os.environ['PATH'], MISSING_PACKAGE=missing), capture_output=True).returncode

    def test_complete_app_set_is_accepted(self):
        self.assertEqual(self.app_check(), 0)

    def test_each_missing_app_requires_repair(self):
        for package in ('firefox-esr', 'portfolio-filemanager', 'gnome-text-editor', 'gnome-calculator', 'eog', 'gnome-console'):
            with self.subTest(package=package):
                self.assertNotEqual(self.app_check(package), 0)

    def schema_check(self, schemas, code=0):
        source = (BUNDLE/'desktop-profile.sh').read_text()
        function = re.search(r'^phosh_schema_available\(\) \{.*?^\}', source, re.M | re.S).group()
        with tempfile.TemporaryDirectory() as temp:
            command = pathlib.Path(temp)/'gsettings'
            command.write_text('#!/bin/sh\nprintf "%s\\n" "$TEST_SCHEMAS"\nexit "$TEST_STATUS"\n')
            command.chmod(0o755)
            return subprocess.run(['/bin/sh', '-c', function+'\nphosh_schema_available'], env=dict(os.environ, PATH=temp+':'+os.environ['PATH'], TEST_SCHEMAS=schemas, TEST_STATUS=str(code)), capture_output=True).returncode

    def test_missing_schema_is_rejected(self):
        self.assertNotEqual(self.schema_check('org.gnome.desktop.interface\nsm.puri.phosh'), 0)

    def test_required_schema_is_accepted(self):
        self.assertEqual(self.schema_check('org.gnome.settings-daemon.peripherals.touchscreen'), 0)

    def test_similar_schema_name_is_rejected(self):
        self.assertNotEqual(self.schema_check('org.gnome.settings-daemon.peripherals.touchscreen.extra'), 0)

    def test_failed_schema_query_is_rejected(self):
        self.assertNotEqual(self.schema_check('org.gnome.settings-daemon.peripherals.touchscreen', 1), 0)

if __name__ == '__main__':
    unittest.main()
