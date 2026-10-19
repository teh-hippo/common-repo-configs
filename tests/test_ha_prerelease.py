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


def publication_script():
    section = WORKFLOW.read_text().split("- name: Publish release without replacing an existing release\n", 1)[1]
    return textwrap.dedent(section.split("        run: |\n", 1)[1])


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
        (self.root / "hacs.json").write_text('{"zip_release":true,"filename":"example.zip"}\n')

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
            {"VERSION": "3.0.0+unexpected"},
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

    def test_stable_packages_and_publication_use_the_stable_version(self):
        environment = {"VERSION": "2.0.0", "MANIFEST_VERSION": "2.0.0"}
        for step in ("Validate inputs", "Stamp package version", "Package and verify runtime files", "Verify publication inputs"):
            self.assert_step(step, **environment)
        self.assertIn("artifact_name=package-example-2.0.0-", (self.root / "output").read_text())
        self.assertIn("is_prerelease=false\n", (self.root / "output").read_text())
        self.assert_step("Validate inputs", **environment, PUBLISH="true", RELEASE_NOTES="Approved notes.")

    def test_publication_requires_hacs_zip_downloads(self):
        for hacs in ({"zip_release": False}, {"zip_release": True, "filename": "wrong.zip"}):
            with self.subTest(hacs=hacs):
                (self.root / "hacs.json").write_text(json.dumps(hacs))
                self.assertNotEqual(self.run_step("Stamp package version", PUBLISH="true").returncode, 0)

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

    def test_package_follows_the_caller_repository_and_integration(self):
        self.source = self.source.rename(self.source.with_name("another_domain"))
        (self.source / "manifest.json").write_text('{"domain":"another_domain","version":"2.0.0"}\n')
        (self.root / "hacs.json").write_text('{"zip_release":true,"filename":"another_domain.zip"}\n')
        environment = {"INTEGRATION": "another_domain", "GITHUB_REPOSITORY": "another-owner/another-project", "PUBLISH": "true"}
        self.assert_step("Stamp package version", **environment)
        self.assert_step("Package and verify runtime files", **environment)
        self.assert_step("Verify publication inputs", **environment)
        metadata = json.loads((self.root / "dist/another_domain.build.json").read_text())
        self.assertEqual(metadata["repository"], environment["GITHUB_REPOSITORY"])
        with ZipFile(self.root / "dist/another_domain.zip") as archive:
            self.assertEqual(json.loads(archive.read("manifest.json"))["domain"], "another_domain")

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

    def run_publication(self, **environment):
        gh = self.root / "gh"
        gh.write_text(
            f"#!{sys.executable}\n" + textwrap.dedent("""\
            import json
            import os
            import sys
            from pathlib import Path

            args = sys.argv[1:]
            if args[0] == "api":
                if "/git/ref/tags/" in args[1]:
                    kind = os.environ.get("TAG_TYPE", "commit")
                    sha = "c" * 40 if kind == "tag" else os.environ["TAG_SHA"]
                    print(json.dumps({"object": {"type": kind, "sha": sha}}))
                elif "/git/tags/" in args[1]:
                    print(json.dumps({"object": {"type": "commit", "sha": os.environ["TAG_SHA"]}}))
                else:
                    raise SystemExit(f"Unexpected GitHub request: {args}")
            elif args[:2] == ["release", "create"]:
                Path(os.environ["COMMAND_LOG"]).write_text(json.dumps(args))
            else:
                raise SystemExit(f"Unexpected GitHub command: {args}")
            """)
        )
        gh.chmod(0o755)
        return subprocess.run(
            ["bash", "-e", "-o", "pipefail", "-c", publication_script()],
            cwd=self.root,
            env={
                **self.environment,
                "PATH": f"{self.root}{os.pathsep}{os.environ['PATH']}",
                "COMMAND_LOG": str(self.root / "publication.json"),
                "TAG_SHA": self.environment["TARGET_SHA"],
                "RELEASE_NOTES": "Approved notes.",
                **environment,
            },
            capture_output=True,
            text=True,
        )

    def test_publication_flags_and_annotated_tags(self):
        for version, prerelease, kind in (
            ("3.0.0-rc.1.capabilities", "true", "commit"),
            ("3.0.0", "false", "tag"),
        ):
            with self.subTest(version=version):
                result = self.run_publication(VERSION=version, IS_PRERELEASE=prerelease, TAG_TYPE=kind)
                self.assertEqual(result.returncode, 0, result.stderr)
                command = json.loads((self.root / "publication.json").read_text())
                self.assertIn(f"--prerelease={prerelease}", command)
                self.assertIn(f"--latest={'false' if prerelease == 'true' else 'true'}", command)
                self.assertEqual(command[command.index("--target") + 1], self.environment["TARGET_SHA"])
                self.assertTrue({"dist/example.zip", "dist/example.zip.sha256", "dist/example.build.json"} <= set(command))

    def test_mismatched_annotated_tag_cannot_publish(self):
        result = self.run_publication(VERSION="3.0.0", IS_PRERELEASE="false", TAG_TYPE="tag", TAG_SHA="b" * 40)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("refusing to replace", result.stderr)
        self.assertFalse((self.root / "publication.json").exists())


if __name__ == "__main__":
    unittest.main()
