"""Testing module to test ci-build functionality
"""
import subprocess

import pytest

import compile as compilation
from settings import TEST_DIR, TEST_PROJECT_PATH_ARGS


def test_subprocesses():
    """
    Tests ci-build executable with a simple Makefile provided by tests
    :return:
    """
    proc = subprocess.run(["ci-build", "make"], cwd=TEST_DIR)
    assert proc.returncode == 0
    proc = subprocess.run(["ci-build"] + TEST_PROJECT_PATH_ARGS + ["make"])
    assert proc.returncode == 0


def test_ci_build():
    """Tests ci-build without subprocessing (this way it's easier to track code
    coverage"""

    # simply builds the project
    with pytest.raises(SystemExit) as exit_exception:
        compilation.build_main(args=TEST_PROJECT_PATH_ARGS + ["make"])
    assert exit_exception.type == SystemExit
    assert exit_exception.value.code == 0

    # builds the project without build command
    with pytest.raises(SystemExit) as exit_exception:
        compilation.build_main(args=[])
    assert exit_exception.type == SystemExit
    assert exit_exception.value.code == 2

    # builds the project with sanitizers but without build command
    with pytest.raises(SystemExit) as exit_exception:
        compilation.build_main(args=["--sanitize-build"])
    assert exit_exception.type == SystemExit
    assert exit_exception.value.code == 2

    # builds the project without build command but project path
    with pytest.raises(SystemExit) as exit_exception:
        compilation.build_main(args=TEST_PROJECT_PATH_ARGS)
    assert exit_exception.type == SystemExit
    assert exit_exception.value.code == -1

    # builds the project with a wrong command
    with pytest.raises(SystemExit) as exit_exception:
        compilation.build_main(args=["fofgsdagtwsa"])
    assert exit_exception.type == SystemExit
    assert exit_exception.value.code == -1
