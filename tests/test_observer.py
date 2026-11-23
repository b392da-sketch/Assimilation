import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest


class ObserverTests(unittest.TestCase):
    def test_interactive_inspection_and_export_preserve_replay(self):
        command = [
            sys.executable, "-m", "assimilation", "--scenario", "low-fuel", "--seed", "1",
        ]
        batch = subprocess.run(
            [*command, "--ticks", "20", "--events"],
            check=True, capture_output=True, text=True,
        )
        batch_lines = batch.stdout.splitlines()
        restored = next(json.loads(line) for line in batch_lines
                        if json.loads(line).get("action") == "power_main")
        with TemporaryDirectory() as directory:
            output = Path(directory) / "test history.jsonl"
            interactive = subprocess.run(
                [*command, "--interactive"],
                input="\n".join([
                    "status", "step 8", "inspect Anika", "events 1", "step 12",
                    f"trace {restored['id']}", f'export "{output}"', "quit", "",
                ]),
                check=True, capture_output=True, text=True,
            )
            self.assertEqual(output.read_text().splitlines(), batch_lines[:-1])
            self.assertIn('"tick": 0', interactive.stdout)
            self.assertIn('"last_intent"', interactive.stdout)
            self.assertIn("Both supplies are out of fuel.", interactive.stdout)
            self.assertIn("The second refueling action transferred reserve fuel", interactive.stdout)
            self.assertIn("The main supply has fuel again.", interactive.stdout)
