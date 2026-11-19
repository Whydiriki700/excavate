import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import excavate


def git(root, *args, author="Alice"):
    env = dict(os.environ)
    env["GIT_AUTHOR_NAME"] = author
    env["GIT_AUTHOR_EMAIL"] = f"{author.lower()}@example.com"
    env["GIT_COMMITTER_NAME"] = author
    env["GIT_COMMITTER_EMAIL"] = f"{author.lower()}@example.com"
    subprocess.run(["git", "-C", root] + list(args),
                   check=True, env=env, capture_output=True, text=True)


def commit_file(root, path, content, subject, author="Alice"):
    full = os.path.join(root, path)
    os.makedirs(os.path.dirname(full), exist_ok=True) if "/" in path else None
    with open(full, "w", encoding="utf-8") as fh:
        fh.write(content)
    git(root, "add", path)
    git(root, "commit", "-q", "-m", subject, author=author)


class RepoFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        git(self.root, "init", "-q", "-b", "main")
        with open(os.path.join(self.root, "a.py"), "w") as fh: fh.write("1\n")
        with open(os.path.join(self.root, "b.py"), "w") as fh: fh.write("1\n")
        git(self.root, "add", "a.py", "b.py")
        git(self.root, "commit", "-q", "-m", "add a and b together")
        # touch both a and b in one commit for a real co-change
        with open(os.path.join(self.root, "a.py"), "a") as fh: fh.write("2\n")
        with open(os.path.join(self.root, "b.py"), "a") as fh: fh.write("2\n")
        git(self.root, "add", "a.py", "b.py")
        git(self.root, "commit", "-q", "-m", "change both")
        commit_file(self.root, "a.py", "3\n", "tune a", author="Bob")
        commit_file(self.root, "a.py", "1\n", 'Revert "tune a"', author="Bob")
        commit_file(self.root, "lib/c.py", "x\n", "add lib c", author="Bob")

    def tearDown(self):
        self.tmp.cleanup()

    def report(self):
        return excavate.analyze(excavate.git_log(self.root))


class TestAnalyze(RepoFixture):
    def test_commit_count(self):
        self.assertEqual(self.report()["commits"], 5)

    def test_hotspot_is_a(self):
        path, n = self.report()["hotspots"][0]
        self.assertEqual(path, "a.py")
        self.assertGreaterEqual(n, 4)

    def test_cursed_contains_a(self):
        cursed = dict(self.report()["cursed"])
        self.assertEqual(cursed.get("a.py"), 1)

    def test_cochange_pair(self):
        pairs = {tuple(p): n for p, n in self.report()["cochange"]}
        self.assertGreaterEqual(pairs.get(("a.py", "b.py"), 0), 2)

    def test_ownership_root(self):
        own = self.report()["ownership"]
        self.assertIn("(root)", own)
        self.assertIn("lib", own)

    def test_main_ok(self):
        self.assertEqual(excavate.main(["--root", self.root]), 0)


class TestErrors(unittest.TestCase):
    def test_not_a_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(excavate.main(["--root", tmp]), 2)


if __name__ == "__main__":
    unittest.main()
