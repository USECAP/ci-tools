"""
Fuzzing engine
"""
import argparse
import glob
import json
import os
import stat
import subprocess

import logging

import jsonschema

from settings import (SA_VULNERABILITY_SCHEMA, CI_REPORT_FILE, FUZZING_DIR,
                      command_entry_point)

from streams.linestream import LineStream
from fuzzing.errorparser import (AsanParserStrategy,
                                 LsanParserStrategy,
                                 TimeoutParserStrategy,
                                 LogParserException)

with open(SA_VULNERABILITY_SCHEMA, 'r') as schema:
    VULNERABILITY_SCHEMA = json.load(schema)

FUZZER_DEFAULT_OPTIONS = {
    'verbosity': 1,
    'error_exitcode': 77,
    'timeout_exitcode': 78
}


def fuzzer_options(options=None, type_=list):
    """

    :param options: dict with fuzzing options, default: FUZZER_DEFAULT_OPTIONS
    :param type_: type of the options, str or list
    :return: options
    """
    if options is None:
        options = FUZZER_DEFAULT_OPTIONS
    opt_list = ["-{:s}={:d}".format(key, val) for key, val in options.items()]
    if type_ == str:
        return " ".join(opt_list)
    return opt_list


def get_executables():
    """
    Gets all executables in the current working directory
    :return: all executables in the current working directory as list
    """
    is_executable = stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH
    return [file for file in glob.iglob('*')
            if os.path.isfile(file) and os.stat(file).st_mode & is_executable]


@command_entry_point
def run_fuzzer(args=None):
    """

    :param args: arguments, defaults to sys.argv[:1]
    :return: exit_code
    """
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('files', metavar="fuzzing target names", default=[],
                        help="Fuzzing targets to be run", nargs="*")
    parser.add_argument(
        '--project-path',
        metavar="<path>",
        dest='cwd',
        type=str,
        default=os.getcwd(),
        help="""used path where the fuzzing tools are invoked """)
    args = parser.parse_args(args)
    os.chdir(os.path.join(args.cwd, FUZZING_DIR))
    if not args.files:
        args.files = get_executables()

    vulnerabilities = []
    for file in args.files:
        proc = subprocess.run(["./" + file] + fuzzer_options() + ["CORPUS"],
                              shell=True, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
        if proc.returncode != 0:
            log_file = LineStream(proc.stderr)
            while get_next_error(log_file):
                vulnerabilities.extend(parse_libfuzzer(log_file))

    json_data = json.dumps(vulnerabilities, indent=1)
    print(json_data)
    with open(CI_REPORT_FILE, "w") as report_file:
        json.dump(vulnerabilities, report_file, indent=1)

    return vulnerabilities


STRATEGY_TABLE = {
    "AddressSanitizer": AsanParserStrategy(),
    "LeakSanitizer": LsanParserStrategy()
}


def get_tool_name(header):
    """Gets the name of the tool that was used and that delivered the log."""
    header = header.split(":")
    return header[1].strip(), ":".join(header[2:])


def get_parser_strategy(tool_name, info):
    """Returns the appropriate ErrorParserStrategy."""
    if tool_name == "libFuzzer":
        if "timeout" in info:
            return TimeoutParserStrategy()
        else:
            # deadly signal case, needs special handling
            raise Exception("Not implemented yet.")
    else:
        return STRATEGY_TABLE[tool_name]


def get_error_hash(report):
    """Returns the hash identifying the bug."""
    for line in report:
        if "Test unit written to" in line:
            line = line.split("-")
            return line[-1].strip()
    return ""


def is_error_start(line):
    """Returns true if line marks a new error."""
    return line.startswith("==") and "ERROR" in line


def get_next_error(stream):
    """Sets stream to the next error."""
    if next((line for line in stream if is_error_start(line)), None):
        stream.putback_line()
        return True
    return False


def parse_libfuzzer(report):
    """Function for parsing a single error instance."""
    try:
        header = report.readline()
        parser = get_parser_strategy(*get_tool_name(header))
        vulnerabilities = parser.get_vulnerabilities(header, report)
        issue_hash = get_error_hash(report)
        for vulnerability in vulnerabilities:
            vulnerability["issue_hash"] = issue_hash
    except (LogParserException, IndexError, KeyError) as error:
        # the exception handling here is a temporary solution
        logger = logging.getLogger(name=__name__)
        logger.exception("Apparently the log file could not be parsed appropriately.\n"
                         "The parser concluded with the following information:\n%s\n",
                         error)
        vulnerabilities = []

    jsonschema.validate(vulnerabilities, VULNERABILITY_SCHEMA)
    return vulnerabilities
