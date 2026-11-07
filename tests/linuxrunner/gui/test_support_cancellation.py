"""Cancellation must wait for a package stage and stay within its operation."""
import os
import pathlib
import shutil
import subprocess
import tempfile
import time
import unittest

BUNDLE = pathlib.Path(__file__).resolve().parents[3] / 'app/LinuxRunner/GUISupport.bundle'


class SupportCancellationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = pathlib.Path(self.temp.name)
        for name in ['support-common.sh', 'support-version']:
            shutil.copyfile(BUNDLE / name, self.path / name)
        self.cancel = self.path / 'install-cancel-current'
        self.env = dict(os.environ, LR_INSTALL_CANCEL_FILE=str(self.cancel))

    def run_script(self, text, **environment):
        script = self.path / 'probe.sh'
        script.write_text('set -eu\n. "$(dirname "$0")/support-common.sh"\n' + text)
        return subprocess.run(['/bin/sh', str(script)], env=dict(self.env, **environment),
                              text=True, capture_output=True)

    def test_no_request_allows_work(self):
        result = self.run_script('support_install_checkpoint\necho COMPLETE\n')
        self.assertEqual(result.returncode, 0)
        self.assertIn('COMPLETE', result.stdout)

    def test_request_before_start_prevents_work(self):
        self.cancel.touch()
        result = self.run_script('echo MUST_NOT_RUN\n')
        self.assertEqual(result.returncode, 130)
        self.assertIn('category=INSTALL_CANCELLED', result.stdout)
        self.assertNotIn('MUST_NOT_RUN', result.stdout)

    def test_another_operations_request_does_not_cancel(self):
        (self.path / 'install-cancel-other').touch()
        result = self.run_script('echo COMPLETE\n')
        self.assertEqual(result.returncode, 0)

    def test_request_outside_support_directory_is_ignored(self):
        self.cancel.touch()
        result = self.run_script('echo COMPLETE\n', LR_INSTALL_CANCEL_FILE=str(self.path.parent / 'install-cancel-current'))
        self.assertEqual(result.returncode, 0)
        self.assertIn('COMPLETE', result.stdout)

    def test_request_during_last_stage_does_not_report_success(self):
        shutil.copyfile(BUNDLE / 'installer-run.sh', self.path / 'installer-run.sh')
        (self.path / 'package-lock.sh').write_text('package_lock_acquire() { return 0; }\npackage_system_ready() { return 0; }\n')
        (self.path / 'desktop-profile.sh').write_text('echo LAST_STAGE_COMPLETE\ntouch "$LR_INSTALL_CANCEL_FILE"\n')
        result = subprocess.run(['/bin/sh', str(self.path / 'installer-run.sh'), 'desktop-profile.sh'],
                                env=self.env, text=True, capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 130, result.stderr)
        self.assertEqual((self.path / 'install-result').read_text().strip(), '130')
        self.assertIn('LAST_STAGE_COMPLETE', (self.path / 'desktop-profile.sh.log').read_text())

    def test_current_stage_finishes_before_cancellation(self):
        script = self.path / 'probe.sh'
        script.write_text('''set -eu
. "$(dirname "$0")/support-common.sh"
echo started > active
while [ ! -f release ]; do sleep .01; done
echo committed > active
support_install_checkpoint
echo SECOND_STAGE > second
''')
        process = subprocess.Popen(['/bin/sh', str(script)], env=self.env,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            deadline = time.monotonic() + 3
            while not (self.path / 'active').exists() and time.monotonic() < deadline:
                time.sleep(.01)
            self.assertTrue((self.path / 'active').exists())
            self.cancel.touch()
            self.assertIsNone(process.poll())
            self.assertEqual((self.path / 'active').read_text().strip(), 'started')
            (self.path / 'release').touch()
            output, error = process.communicate(timeout=3)
            self.assertEqual(process.returncode, 130, error)
            self.assertIn('INSTALL_CANCELLED', output)
            self.assertEqual((self.path / 'active').read_text().strip(), 'committed')
            self.assertFalse((self.path / 'second').exists())
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()


if __name__ == '__main__':
    unittest.main()
