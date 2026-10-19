"""Exercise the actual inline prerelease programs without GitHub or release writes."""

import json
import os
import re
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from zipfile import ZipFile

WORKFLOW = Path(__file__).parents[1] / ".github/workflows/ha-prerelease.yml"


def program(step):
    section = WORKFLOW.read_text().split(f"- name: {step}\n", 1)[1].split("\n      - ", 1)[0]
    match = re.search(r"^          python - <<'PY'\n(.*?)^          PY$", section, re.M | re.S)
    if match is None:
        raise AssertionError(f"Python program not found: {step}")
    return textwrap.dedent(match[1])


class PrereleaseTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.environment = {
            **os.environ,
            "INTEGRATION": "example",
            "TARGET_SHA": "a" * 40,
            "VERSION": "3.0.0-rc.1.capabilities",
            "MANIFEST_VERSION": "3.0.0rc1",
            "MAKE_TARGET": "",
            "NODE_VERSION_FILE": "",
            "PUBLISH": "false",
            "RELEASE_NOTES": "",
            "GITHUB_OUTPUT": str(self.root / "output"),
            "GITHUB_REPOSITORY": "owner/example",
            "GITHUB_SERVER_URL": "https://github.com",
            "GITHUB_RUN_ID": "123",
        }
        self.source = self.root / "custom_components/example"
        self.source.mkdir(parents=True)
        (self.source / "__init__.py").write_text('"""Example integration."""\n')
        (self.source / "manifest.json").write_text('{"domain":"example","version":"2.0.0"}\n')

    def run_step(self, step, **environment):
        return subprocess.run(
            [sys.executable, "-c", program(step)],
            cwd=self.root,
            env={**self.environment, **environment},
            capture_output=True,
            text=True,
        )

    def assert_step(self, step, **environment):
        result = self.run_step(step, **environment)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_version_and_publish_validation(self):
        self.assert_step("Validate inputs")
        self.assertIn("manifest_version=3.0.0rc1\n", (self.root / "output").read_text())
        for values in (
            {"VERSION": "3.0.0"},
            {"VERSION": "3.0.0-rc.01.label"},
            {"VERSION": "3.0.0-rc.1\ninjected=yes"},
            {"TARGET_SHA": "main"},
            {"INTEGRATION": "../other"},
            {"MAKE_TARGET": "package; echo unsafe"},
            {"NODE_VERSION_FILE": "../.node-version"},
            {"PUBLISH": "true"},
        ):
            with self.subTest(values=values):
                self.assertNotEqual(self.run_step("Validate inputs", **values).returncode, 0)
        self.assert_step("Validate inputs", PUBLISH="true", RELEASE_NOTES="Approved notes.")

    def test_reproducible_archive_and_publication_provenance(self):
        (self.source / ".private").write_text("excluded")
        cache = self.source / "__pycache__"
        cache.mkdir()
        (cache / "example.pyc").write_bytes(b"excluded")
        self.assert_step("Stamp package version")
        self.assert_step("Package and verify runtime files")
        archive = self.root / "dist/example.zip"
        first = archive.read_bytes()
        os.utime(self.source / "__init__.py", (1234567890, 1234567890))
        self.assert_step("Package and verify runtime files")
        self.assertEqual(archive.read_bytes(), first)
        with ZipFile(archive) as package:
            self.assertEqual(package.namelist(), ["__init__.py", "manifest.json"])
            self.assertEqual(json.loads(package.read("manifest.json"))["version"], "3.0.0rc1")
        self.assert_step("Verify publication inputs")
        result = self.run_step("Verify publication inputs", TARGET_SHA="b" * 40)
        self.assertNotEqual(result.returncode, 0)
        archive.write_bytes(first + b"tampered")
        self.assertNotEqual(self.run_step("Verify publication inputs").returncode, 0)

    def test_repository_archive_is_verified_not_silently_repacked(self):
        self.assert_step("Stamp package version")
        self.assert_step("Package and verify runtime files")
        self.assert_step("Package and verify runtime files", MAKE_TARGET="package")
        (self.source / "__init__.py").write_text("changed_after_build = True\n")
        self.assertNotEqual(self.run_step("Package and verify runtime files", MAKE_TARGET="package").returncode, 0)

    def test_symlinks_and_wrong_manifest_are_rejected(self):
        (self.source / "linked.py").symlink_to(self.source / "__init__.py")
        self.assert_step("Stamp package version")
        self.assertNotEqual(self.run_step("Package and verify runtime files").returncode, 0)
        (self.source / "manifest.json").write_text('{"domain":"other","version":"2.0.0"}\n')
        self.assertNotEqual(self.run_step("Stamp package version").returncode, 0)


if __name__ == "__main__":
    unittest.main()
