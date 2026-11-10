"""Wymagane lokalne pliki tunelu: test bez prawdziwego tokenu i sieci."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


@unittest.skipUnless(os.name=='nt','Windows CMD')
class TunnelLauncherTests(unittest.TestCase):
    def test_missing_binary_exits_without_starting_network(self):
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            env=dict(os.environ,LOCALAPPDATA=directory)
            result=subprocess.run(['cmd.exe','/c',str(root/'TUNEL.cmd')],env=env,
                                  capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,1)
        self.assertIn('Brak programu tunelu',result.stdout)
