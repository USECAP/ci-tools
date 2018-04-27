"""Configurations for pytests
"""
import os

import pytest

PROJECT_PATH_ARGS = ['--project-path', 'tests']


@pytest.fixture(name="cwd", scope="function", autouse=True)
def fix_cwd():
    """Since most of the tests are using cli tools, they might change the cwd"""
    cwd = os.getcwd()
    yield cwd
    os.chdir(cwd)
