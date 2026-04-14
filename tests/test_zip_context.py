from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1] / "zip-context" / "scripts" / "zip_context.py"
)


class ZipContextCliTest(unittest.TestCase):
    def write_text(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def write_binary(self, path: Path, content: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    def run_zip(self, root: Path, output: Path, *extra_args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT_PATH),
                "zip",
                "--root",
                str(root),
                "--output",
                str(output),
                *extra_args,
            ],
            capture_output=True,
            text=True,
        )

    def archive_names(self, archive_path: Path) -> list[str]:
        with zipfile.ZipFile(archive_path) as archive:
            return sorted(archive.namelist())

    def test_zip_archives_full_project_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            archive_path = root / "output" / "default.zip"

            self.write_text(root / "src" / "app.py", "print('ok')\n")
            self.write_text(root / "docs" / "notes.md", "# Notes\n")
            self.write_text(root / ".env", "SECRET=1\n")
            self.write_binary(root / "assets" / "logo.png", b"\x89PNG\r\n\x1a\n")

            completed = self.run_zip(root, archive_path)

            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
            self.assertEqual(
                self.archive_names(archive_path),
                ["docs/notes.md", "src/app.py"],
            )

    def test_zip_can_archive_only_task_related_files_from_paths_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            archive_path = root / "output" / "billing.zip"
            paths_file = root / "billing-selection.txt"

            self.write_text(root / "billing" / "service.py", "def bill():\n    return True\n")
            self.write_text(root / "billing" / "tests" / "test_service.py", "def test_bill():\n    assert True\n")
            self.write_text(root / "auth" / "service.py", "def login():\n    return True\n")
            self.write_text(root / "README.md", "# Project\n")
            self.write_text(root / "build" / "generated.txt", "generated but relevant\n")
            self.write_text(root / ".env", "SECRET=1\n")
            self.write_text(
                paths_file,
                "\n".join(
                    [
                        "# billing scope",
                        "billing/",
                        "README.md",
                        "build/generated.txt",
                        ".env",
                        "missing.py",
                    ]
                )
                + "\n",
            )

            completed = self.run_zip(
                root,
                archive_path,
                "--paths-file",
                str(paths_file),
            )

            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
            self.assertEqual(
                self.archive_names(archive_path),
                [
                    "README.md",
                    "billing/service.py",
                    "billing/tests/test_service.py",
                    "build/generated.txt",
                ],
            )
            self.assertNotIn(".env", self.archive_names(archive_path))
            self.assertNotIn("auth/service.py", self.archive_names(archive_path))


if __name__ == "__main__":
    unittest.main()
