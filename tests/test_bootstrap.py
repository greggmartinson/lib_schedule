from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from library_schedule.bootstrap import project_venv_python, should_reexec_with_venv


class BootstrapTests(unittest.TestCase):
    def test_should_reexec_is_false_without_project_venv(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.assertFalse(should_reexec_with_venv(root, current_executable="/usr/bin/python3"))

    def test_should_reexec_is_false_when_already_using_project_venv(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            venv_python = project_venv_python(root)
            venv_python.parent.mkdir(parents=True)
            venv_python.touch()

            self.assertFalse(should_reexec_with_venv(root, current_executable=venv_python))

    def test_should_reexec_is_true_when_project_venv_exists(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            venv_python = project_venv_python(root)
            venv_python.parent.mkdir(parents=True)
            venv_python.touch()

            self.assertTrue(should_reexec_with_venv(root, current_executable="/usr/bin/python3"))


if __name__ == "__main__":
    unittest.main()
