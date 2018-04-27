"""Tests to test the libfuzzer module
"""
import os
from functools import lru_cache

import pytest

import fuzzing
from fuzzing import libfuzzer
from streams.linestream import LineStream

import compile as compilation

from settings import TEST_PROJECT_PATH_ARGS

CWD = os.getcwd()


def log_files():
    """Gathers all the logfiles in ci-tools/tests/fuzzing."""
    log_dir = os.path.dirname(__file__)
    log_dir = os.path.join(log_dir, "fuzzing")
    files = os.listdir(log_dir)
    files = list(filter(lambda f: f.endswith(".log"), files))
    return [os.path.join(log_dir, file_name) for file_name in files]


LOG_FILES = log_files()


def test_simple_parsing():
    """Tests a simple log file"""

    with open('tests/fuzzing/fuzz-0.log', 'rb') as log:
        content = LineStream(log.read())
        while libfuzzer.get_next_error(content):
            vulnerabilities = fuzzing.parse_libfuzzer(content)
            assert len(vulnerabilities) == 1


@pytest.fixture(name="is_built", scope="module", autouse=True)
def build_fuzztargets():
    """Builds the fuzz targets and the project with sanitization before
    running additional tests"""

    # builds the project with sanitization
    with pytest.raises(SystemExit) as exit_exception:
        compilation.build_main(
            args=TEST_PROJECT_PATH_ARGS + ['--sanitize-build', 'make'])
    assert exit_exception.type == SystemExit
    assert exit_exception.value.code == 0
    os.chdir(CWD)

    # builds the fuzzing targets and links them to the project
    with pytest.raises(SystemExit) as exit_exception:
        compilation.build_main(
            args=TEST_PROJECT_PATH_ARGS + ['--fuzzing-targets'])
    assert exit_exception.type == SystemExit
    assert exit_exception.value.code == 0
    os.chdir(CWD)

    return True


def test_fuzzing_execution(is_built):
    """Test running a simple fuzzer"""
    assert is_built is True
    vulnerabilities = fuzzing.run_fuzzer(
        args=TEST_PROJECT_PATH_ARGS + ['fuzz_target'])
    assert len(vulnerabilities) == 1


@lru_cache()
def parsed_log(filename):
    """Parses filename and returns a list of json objects."""
    with open(filename, 'rb') as log:
        content = LineStream(log.read())
        while libfuzzer.get_next_error(content):
            return fuzzing.parse_libfuzzer(content)


@pytest.mark.parametrize("filename", LOG_FILES)
def test_not_empty(filename):
    """Asserts that the returned json objects are not empty."""
    json_objects = parsed_log(filename)
    assert json_objects
    for json_object in json_objects:
        assert json_object


@pytest.mark.parametrize("filename", LOG_FILES)
def test_attributes(filename):
    """Tests whether attributes are valid."""
    for json_object in parsed_log(filename):
        assert json_object.get("category") in ["Memory error", "Logic error"]
        assert json_object.get("description")


def test_path_contains_fuzz_me():
    """Specific test for fuzz-1.log."""
    json_object = parsed_log("tests/fuzzing/fuzz-1.log")[0]

    def contains_fuzz_me(event):
        """Lookup for FuzzMe msg"""
        return event.get("message") == "FuzzMe"

    assert any(map(contains_fuzz_me, json_object.get("path")))


@pytest.mark.parametrize("filename", LOG_FILES)
def test_no_instrumentation_in_path(filename):
    """Tests whether the path events contain information on
    instrumentation.
    """
    def contains_instrumentation(event):
        """Lookup for location"""
        location = event.get("location", {}).get("file", "")
        return "/lib/asan/" in location

    for json_object in parsed_log(filename):
        path = json_object.get("path", [])
        assert not any(map(contains_instrumentation, path))
