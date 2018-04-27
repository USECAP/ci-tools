"""Settings module for ci-tools

"""
import functools
import logging
import re
import os
import subprocess
import sys
from shutil import which

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
CROSS_COMPILE_PATH = ROOT_DIR + "/cross-compile"
SPECS_DIR = ROOT_DIR + "/config/specs"
SA_VULNERABILITY_SCHEMA = SPECS_DIR + "/vulnerability_schema.json"
CI_REPORT_FILE = "ci-report.json"
CHECKER_PATH = ROOT_DIR + "/lib/sa-checker"
FUZZING_DIR = "ci-fuzzing-targets"

REQUIRED_CLANG_VERSION = "6.0"
CLANG_REGEX = r"^clang-[2-7]\.[0-9]$"

WS_HOST = "localhost"
WS_PORT = 5000

TEST_DIR = "tests"
TEST_PROJECT_PATH_ARGS = ['--project-path', 'tests']


def get_clang_version(cmd):
    """Gets the highest installed version of clang on the system."""
    versions = []

    clang_path = which(cmd)
    if clang_path:
        process = subprocess.run(
            [cmd, "-v"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        version = process.stderr.split()[2]
        versions.append((version.decode('utf-8'), os.path.basename(clang_path)))

    for path in os.environ['PATH'].split(':'):
        try:
            names = (n for n in os.listdir(path) if re.match(CLANG_REGEX, n))
            candidates = ((name.split('-')[-1], name) for name in names)
            versions += ((version, name) for version, name in candidates)
        except FileNotFoundError:
            # we don't care about directories that do not exist
            continue

    return max(versions)


def verify_version(required, version, name):
    """Verifies that version is at least required."""
    if version < required:
        logger = logging.getLogger(name=__name__)
        logger.error("Clang version is not compatible! "
                     "Version required: %s", required)
        sys.exit(1)
    return version, name


CLANG_VERSION, CLANG = verify_version(REQUIRED_CLANG_VERSION,
                                      *get_clang_version("clang"))
CLANGPP_VERSION, CLANGPP = get_clang_version("clang++")


def command_entry_point(func):
    # type: (Callable[[], int]) -> Callable[[], int]
    """ Decorator for command entry methods.

    The decorator initialize/shutdown logging and guard on programming
    errors (catch exceptions).

    The decorated method can have arbitrary parameters, the return value will
    be the exit code of the process. """

    @functools.wraps(func)
    def wrapper(args=None):
        # type: () -> int
        """ Do housekeeping tasks and execute the wrapped method. """
        if args is None:
            args = sys.argv[1:]

        try:
            logging.basicConfig(format='%(name)s: %(message)s',
                                level=logging.WARNING,
                                stream=sys.stdout)
            # this hack to get the executable name as %(name)
            logging.getLogger().name = os.path.basename(sys.argv[0])

            return func(args)
        except KeyboardInterrupt:
            logging.warning('Keyboard interrupt')
            return 130  # signal received exit code for bash
        except (OSError, subprocess.CalledProcessError):
            logging.exception('Internal error.')
            if logging.getLogger().isEnabledFor(logging.DEBUG):
                logging.error("Please report this bug and attach the output "
                              "to the bug report")
            else:
                logging.error("Please run this command again and turn on "
                              "verbose mode (add '-vvvv' as argument).")
            return 64  # some non used exit code for internal errors
        finally:
            logging.shutdown()

    return wrapper
