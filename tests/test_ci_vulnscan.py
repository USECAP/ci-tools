"""Testing module to test ci-vulnscan functionality
"""
import subprocess

import analysis

from settings import TEST_DIR, TEST_PROJECT_PATH_ARGS


def test_executable():
    """
    Tests ci-vulnscan executable
    :return:
    """
    proc = subprocess.run(["ci-vulnscan"], cwd=TEST_DIR)
    assert proc.returncode == 0
    proc = subprocess.run(["ci-vulnscan"] + TEST_PROJECT_PATH_ARGS)
    assert proc.returncode == 0


def test_ci_vulnscan():
    """Tests basic ci-vulnscan functionality"""
    analysis.analyze_main(args=TEST_PROJECT_PATH_ARGS)
