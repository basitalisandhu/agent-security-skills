"""Literal interpreter reads are inspected, never executed."""
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_hooks import BLOCK, run_hook


class InterpreterReadTests(unittest.TestCase):
    def test_literal_secret_reads_are_blocked(self):
        commands = [
            """python -c "print(open('.env').read())" """,
            """python3 -c "from pathlib import Path; print(Path('.ssh/id_ed25519').read_text())" """,
            """node -e "console.log(require('fs').readFileSync('.env','utf8'))" """,
            """ruby -e "puts File.read('.aws/credentials')" """,
            """php -r "echo file_get_contents('.env');" """,
            """python3.12 -c "print(open(file='.env', mode='rb').read())" """,
            """python -c "import pathlib; print(pathlib.Path('.env').read_bytes())" """,
            """env MODE=test /usr/bin/python3 -c "print(open('.env').read())" """,
            """node --eval "require('fs').readFile('.env',()=>{})" """,
        ]
        for command in commands:
            with self.subTest(command=command):
                rc, out, err = run_hook(BLOCK, command)
                self.assertEqual(rc, 2, err)
                self.assertEqual(out, "")
                self.assertIn("blocked", err)
                self.assertNotIn(command.strip(), err)

    def test_benign_one_liners_are_allowed(self):
        commands = [
            """python -c "print('.env')" """,
            """python -c "print(open('README.md').read())" """,
            """python -c "open('.env', 'w').close()" """,
            """python -c "print(open('.env.example').read())" """,
            """node -e "console.log('.env')" """,
            """node -e "console.log(require('fs').readFileSync('README.md','utf8'))" """,
            """ruby -e "puts File.read('.env.sample')" """,
            """php -r "echo file_get_contents('README.md');" """,
            """python -c "from pathlib import Path; Path('.env').write_text('synthetic')" """,
            """python -c "print('open(\\\".env\\\").read()')" """,
            """python -c "open('.env', mode='wb').close()" """,
            """python -c "print(open('id_rsa.pub').read())" """,
            """python -c "print('not valid python'" """,
        ]
        for command in commands:
            with self.subTest(command=command):
                self.assertEqual(run_hook(BLOCK, command), (0, "", ""))


if __name__ == "__main__":
    unittest.main()
