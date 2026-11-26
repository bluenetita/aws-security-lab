"""Only side-effect-free branches of the restricted command are executed."""

import subprocess
import unittest

from _support import CONTROL


RECEIVER = CONTROL / "blueguard-ssh-receiver"


class ReceiverTests(unittest.TestCase):
    def invoke(self, command):
        env = {"PATH": "/usr/bin:/bin", "SSH_ORIGINAL_COMMAND": command}
        return subprocess.run(
            ["/bin/sh", str(RECEIVER)],
            env=env, input=b"", capture_output=True, timeout=3, check=False,
        )

    def test_health_command(self):
        result = self.invoke("health")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, b"BLUEGUARD_RECEIVER_READY\n")

    def test_arbitrary_command_is_rejected(self):
        result = self.invoke("id")
        self.assertEqual(result.returncode, 126)
        self.assertEqual(result.stdout, b"")
        self.assertIn(b"not authorized", result.stderr)

    def test_ingest_with_extra_arguments_is_rejected(self):
        result = self.invoke("ingest extra")
        self.assertEqual(result.returncode, 126)


if __name__ == "__main__":
    unittest.main()
