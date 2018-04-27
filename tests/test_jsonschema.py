"""Tests to test ci-tools jsonschemas"""
import glob
import json
import os

import jsonschema

from analysis import interpret_plist_report as interpret_report
from settings import TEST_DIR

with open('config/specs/vulnerability_schema.json', 'r') as f:
    SCHEMA = json.load(f)


def test_jsonschema():
    """Tests a plist report"""
    vulnerabilities = interpret_report(
        os.path.join(TEST_DIR, "test_clang_sa_output.plist"))
    assert not jsonschema.validate(vulnerabilities, SCHEMA)


def test_clang_sa_output():
    """Tests with all our collected plist reports"""
    vulnerabilities = []
    path = os.path.join(TEST_DIR, "scan_build_report", "report-*.plist")
    for file in glob.iglob(path):
        interpret_report(file, vulnerabilities)

    assert not jsonschema.validate(vulnerabilities, SCHEMA)
