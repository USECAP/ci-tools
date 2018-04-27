"""Module providing functionality on clang static code analyzer

"""
import argparse  # noqa: ignore=F401 pylint: disable=unused-import
import glob
import json
import logging
import subprocess
import plistlib
import os
import re
import sys
import tempfile
from typing import Any, Dict  # noqa: ignore=F401 pylint: disable=unused-import

import jsonschema

from libscanbuild import analyze, arguments, compilation, reconfigure_logging

from settings import (SA_VULNERABILITY_SCHEMA, CI_REPORT_FILE, CLANG, ROOT_DIR,
                      REQUIRED_CLANG_VERSION, CHECKER_PATH, command_entry_point,
                      CLANG_VERSION)

LOGGER = logging.getLogger(name=__name__)

with open(SA_VULNERABILITY_SCHEMA, 'r') as schema:
    VULNERABILITY_SCHEMA = json.load(schema)

OPTION_FLAG_REGEX = re.compile(r"^--?(\w[\w|-]*)=(\w[\w|-]*)$")
ACTIVATED_CHECKERS = [
    'alpha.core',
    'alpha.unix',
    'alpha.cplusplus',
    'alpha.security'
]

# Clang has a list of checkers which will be run by default, this list disables
# those explicitly
DISABLED_CHECKERS = [
    'deadcode'
]


__all__ = ['analyze_main', 'ClangAnalyzer', 'FlagListFilter',
           'interpret_plist_report', 'interpret_plist_reports']


@analyze.require(['flags'])
def classify_parameters(opts, continuation=analyze.arch_check):
    # type: (...) -> Dict[str, Any]
    """ Prepare compiler flags (filters some and add others) and take out
    language (-x) and architecture (-arch) flags for future processing. """
    flag_filter = FlagListFilter(opts['flags'])
    opts.update(flag_filter.results)
    return continuation(opts)


@analyze.require(['flags',  # entry from compilation
                  'compiler',  # entry from compilation
                  'directory',  # entry from compilation
                  'source',  # entry from compilation
                  'clang',  # clang executable name (and path)
                  'direct_args',  # arguments from command line
                  'excludes',  # list of directories
                  'force_debug',  # kill non debug macros
                  'output_dir',  # where generated report files shall go
                  'output_format',  # it's 'plist', 'html', 'plist-html',
                  # 'text' or 'plist-multi-file'
                  'output_failures'])  # generate crash reports or not
def run(opts):
    # type: (Dict[str, Any]) -> Dict[str, Any]
    """ Entry point to run (or not) static analyzer against a single entry
    of the compilation database.

    This complex task is decomposed into smaller methods which are calling
    each other in chain. If the analysis is not possible the given method
    just returns and breaks the chain.

    The passed parameter is a python dictionary. Each method first checks
    that the needed parameters are received. (This is done by the 'require'
    decorator. It's like an 'assert' to check the contract between the
    caller and the called method.) """

    command = [opts['compiler'], '-c'] + opts['flags'] + [opts['source']]
    logging.info("Analyzing '%s'", opts['source'])
    logging.debug("Command '%s'", " ".join(command))
    return analyze.exclude(opts)


# Monkey patch run to get info
analyze.run = run

# Monkey patch to replace the parameter classification from scan build
analyze.classify_parameters = classify_parameters
# Since the method is used as an argument default we need to replace it as well
analyze.exclude.__globals__['classify_parameters'] = classify_parameters
# find a solution working with python2
analyze.exclude.__dict__['__wrapped__'].__defaults__ = (classify_parameters,)


class ClangAnalyzer(object):
    """Clang static analyzer wrapper
    """

    def __init__(self, cmd):
        self.cmd = cmd + ["-c", "-o-", "--analyze", "--analyze-auto"]
        self._vulnerabilities = []

    def run(self, src):
        """Analyzes a source code file with the clang static code analyzer

        "/usr/share/clang/scan-build-5.0/libexec/ccc-analyzer"
        """

        cmd = self.cmd
        cmd.append(src)

        proc = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            LOGGER.warning(proc.stderr)
            return proc.returncode

        obj = plistlib.loads(proc.stdout)
        if obj["files"]:
            for diag in obj['diagnostics']:
                vuln = {
                    "name": diag["description"],
                    "category": diag["category"],
                    "file": obj["files"][diag["location"]["file"]],
                    "steps": []
                }
                for path in diag["path"]:
                    path = {
                        "type": path["kind"],
                    }
                    vuln["steps"].append(path)

        return proc

    @staticmethod
    def create_analyze_parser():
        # type: () -> argparse.ArgumentParser
        """ Creates a parser for command-line arguments to 'analyze'. """

        parser = arguments.create_default_parser()

        arguments.parser_add_cdb(parser)

        parser.add_argument(
            '--status-bugs',
            action='store_true',
            help="""The exit status of '%(prog)s' is the same as the executed
            build command. This option ignores the build exit status and sets to
            be non zero if it found potential bugs or zero otherwise.""")
        parser.add_argument(
            '--exclude',
            metavar='<directory>',
            dest='excludes',
            action='append',
            default=[],
            help="""Do not run static analyzer against files found in this
            directory. (You can specify this option multiple times.)
            Could be useful when project contains 3rd party libraries.""")

        output = parser.add_argument_group('output control options')
        output.add_argument(
            '--output',
            '-o',
            metavar='<path>',
            default=tempfile.gettempdir(),
            help="""Specifies the output directory for analyzer reports.
            Subdirectory will be created if default directory is targeted.""")
        output.add_argument(
            '--keep-empty',
            action='store_true',
            help="""Don't remove the build results directory even if no issues
            were reported.""")
        output.add_argument(
            '--html-title',
            metavar='<title>',
            help="""Specify the title used on generated HTML pages.
            If not specified, a default title will be used.""")

        format_group = output.add_mutually_exclusive_group()
        format_group.add_argument(
            '--plist',
            '-plist',
            dest='output_format',
            const='plist',
            default='html',
            action='store_const',
            help="""Cause the results as a set of .plist files.""")
        format_group.add_argument(
            '--plist-html',
            '-plist-html',
            dest='output_format',
            const='plist-html',
            default='html',
            action='store_const',
            help="""Cause the results as a set of .html and .plist files.""")
        format_group.add_argument(
            '--plist-multi-file',
            '-plist-multi-file',
            dest='output_format',
            const='plist-multi-file',
            default='html',
            action='store_const',
            help="""Cause the results as a set of .plist files with extra
            information on related files.""")

        advanced = parser.add_argument_group('advanced options')
        advanced.add_argument(
            '--use-analyzer',
            metavar='<path>',
            dest='clang',
            default='clang',
            help="""'%(prog)s' uses the 'clang' executable relative to itself for
            static analysis. One can override this behavior with this option by
            using the 'clang' packaged with Xcode (on OS X) or from the PATH.
            """)
        advanced.add_argument(
            '--no-failure-reports',
            '-no-failure-reports',
            dest='output_failures',
            action='store_false',
            help="""Do not create a 'failures' subdirectory that includes analyzer
            crash reports and preprocessed source files.""")
        parser.add_argument(
            '--analyze-headers',
            action='store_true',
            help="""Also analyze functions in #included files. By default, such
            functions are skipped unless they are called by functions within the
            main source file.""")
        advanced.add_argument(
            '--stats',
            '-stats',
            action='store_true',
            help="""Generates visitation statistics for the project.""")
        advanced.add_argument(
            '--internal-stats',
            action='store_true',
            help="""Generate internal analyzer statistics.""")
        advanced.add_argument(
            '--maxloop',
            '-maxloop',
            metavar='<loop count>',
            type=int,
            help="""Specifiy the number of times a block can be visited before
            giving up. Increase for more comprehensive coverage at a cost of
            speed.""")
        advanced.add_argument(
            '--store',
            '-store',
            metavar='<model>',
            dest='store_model',
            choices=['region', 'basic'],
            help="""Specify the store model used by the analyzer. 'region'
            specifies a field- sensitive store model. 'basic' which is far less
            precise but can more quickly analyze code. 'basic' was the default
            store model for checker-0.221 and earlier.""")
        advanced.add_argument(
            '--constraints',
            '-constraints',
            metavar='<model>',
            dest='constraints_model',
            choices=['range', 'basic'],
            help="""Specify the constraint engine used by the analyzer. Specifying
            'basic' uses a simpler, less powerful constraint model used by
            checker-0.160 and earlier.""")
        advanced.add_argument(
            '--analyzer-config',
            '-analyzer-config',
            metavar='<options>',
            help="""Provide options to pass through to the analyzer's
            -analyzer-config flag. Several options are separated with comma:
            'key1=val1,key2=val2'

            Available options:
                stable-report-filename=true or false (default)

            Switch the page naming to:
            report-<filename>-<function/method name>-<id>.html
            instead of report-XXXXXX.html""")
        advanced.add_argument(
            '--force-analyze-debug-code',
            dest='force_debug',
            action='store_true',
            help="""Tells analyzer to enable assertions in code even if they were
            disabled during compilation, enabling more precise results.""")

        plugins = parser.add_argument_group('checker options')
        plugins.add_argument(
            '--load-plugin',
            '-load-plugin',
            metavar='<plugin library>',
            dest='plugins',
            action='append',
            help="Loading external checkers using the clang plugin interface.")
        plugins.add_argument(
            '--enable-checker',
            '-enable-checker',
            metavar='<checker name>',
            default=ACTIVATED_CHECKERS,
            action=arguments.AppendCommaSeparated,
            help="""Enable specific checker.""")
        plugins.add_argument(
            '--disable-checker',
            '-disable-checker',
            metavar='<checker name>',
            action=arguments.AppendCommaSeparated,
            default=DISABLED_CHECKERS,
            help="""Disable specific checker.""")
        plugins.add_argument(
            '--help-checkers',
            action='store_true',
            help="""A default group of checkers is run unless explicitly disabled.
            Exactly which checkers constitute the default group is a function of
            the operating system in use. These can be printed with this flag.
            """)
        plugins.add_argument(
            '--help-checkers-verbose',
            action='store_true',
            help="""Print all available checkers and mark the enabled ones.""")

        return parser

    @classmethod
    def parse_args_for_analyze_build(cls, args=None):
        # type: () -> argparse.Namespace
        """ Parse and validate command-line arguments for analyze-build. """

        parser = cls.create_analyze_parser()
        parser.add_argument(
            '--project-path',
            metavar="<path>",
            dest='cwd',
            type=str,
            default=os.getcwd(),
            help="""used path where the analyzer tools are invoked """)
        args = parser.parse_args(args=args)
        os.chdir(args.cwd)

        reconfigure_logging(args.verbose)
        logging.debug('Raw arguments %s', sys.argv)

        from_build_command = False
        arguments.normalize_args_for_analyze(args, from_build_command)
        libs = list(glob.iglob(os.path.join(CHECKER_PATH, "*.so")))
        args.plugins.extend(libs)
        args.enable_checker.extend(['ci.NetworkTaint'])
        LOGGER.error(args.enable_checker)
        arguments.validate_args_for_analyze(parser, args, from_build_command)
        logging.debug('Parsed arguments: %s', args)
        return args

    @classmethod
    def analyze_build(cls, args):
        # type: () -> str
        """ Entry point for analyze-build command. """

        args = cls.parse_args_for_analyze_build(args=args)
        # Overwrite arguments with our custom settings
        args.output = os.getcwd()
        args.output_format = 'plist-multi-file'

        # will re-assign the report directory as new output
        with analyze.report_directory(args.output,
                                      args.keep_empty) as args.output:
            # run the analyzer against a compilation db
            compilations = compilation.CompilationDatabase.load(args.cdb)
            analyze.run_analyzer_parallel(compilations, args)
            # set exit status as it was requested
            return args.output


class FlagListFilter(object):
    """Filters arguments to clang SA

    """
    IGNORED_FLAGS = analyze.IGNORED_FLAGS
    IGNORED_FLAGS.update({
        "-mthumb": 0,
        "-mthumb-interwork": 0,
        "-target-cpu": 1
    })

    def __init__(self, flags, ignored_flags=None):
        if ignored_flags:
            self.IGNORED_FLAGS.update(ignored_flags)

        self._ignore_flags_patterns = {
            'march': self.march_filter
        }

        self.result = {
            'flags': [],  # the filtered compiler flags
            'arch_list': [],  # list of architecture flags
            'language': None,  # compilation language, None, if not specified
        }  # type: Dict[str, Any]

        # iterate on the compile options
        args = iter(flags)
        for arg in args:
            # take arch flags into a separate basket
            if arg == '-arch':
                self.result['arch_list'].append(next(args))
            # take language
            elif arg == '-x':
                self.result['language'] = next(args)
            # ignore some flags
            elif arg in self.IGNORED_FLAGS:
                count = self.IGNORED_FLAGS[arg]
                for _ in range(count):
                    next(args)
            # we don't care about extra warnings, but we should suppress ones
            # that we don't want to see.
            elif re.match(r'^-W.+', arg) and not re.match(r'^-Wno-.+', arg):
                pass
            elif OPTION_FLAG_REGEX.match(arg):
                match = OPTION_FLAG_REGEX.match(arg)
                if match.group(1) in self._ignore_flags_patterns:
                    self._ignore_flags_patterns[match.group(1)](match.group(2))
                else:
                    self.result['flags'].append(arg)
                logging.warning("ARG: %s", arg)
            # and consider everything else as compilation flag.
            else:
                self.result['flags'].append(arg)

    def march_filter(self, cpu):
        """Sets the CPU type """
        pass

    @property
    def results(self):
        """Returns filtered results"""
        return self.result


def interpret_plist_report(file, vulnerabilities=None, validate=False):
    """Interprets the plist files generated by clang SA (unvalidated per default)

    :param file: file url
    :param vulnerabilities: vulnerability list for incremental reports
    :param validate: whether schema validation is applied (False per default)
    :return:
    """
    if vulnerabilities is None:
        vulnerabilities = []
    with open(file, 'rb') as report_file:
        report = plistlib.load(report_file)

        def reindex_location(location, used):
            """clang SA reports files based on index, we need the file paths"""
            used_file = location['file']
            location['file'] = report['files'][used_file]
            used[location['file']] = 1

        for diag in report['diagnostics']:
            used_files = {}
            reindex_location(diag['location'], used_files)
            for item in diag['path']:
                if item['kind'] == 'event':
                    reindex_location(item['location'], used_files)
                    if 'ranges' not in item:
                        continue
                    for rng in item['ranges']:
                        reindex_location(rng[0], used_files)
                        reindex_location(rng[1], used_files)
                elif item['kind'] == 'control':
                    for edge in item['edges']:
                        for pos in ['start', 'end']:
                            pos = edge[pos]
                            reindex_location(pos[0], used_files)
                            reindex_location(pos[1], used_files)
            diag['files'] = list(used_files.keys())
            diag['clang_version'] = report['clang_version']
            vulnerabilities.append(diag)
    if validate:
        jsonschema.validate(vulnerabilities, VULNERABILITY_SCHEMA)

    return vulnerabilities


def interpret_plist_reports(files, vulnerabilities=None, validate=True):
    """Returns the validated vulnerability list (validated per default)

    :param files: file url
    :param vulnerabilities: vulnerability list for incremental reports
    :param validate: whether schema validation is applied (True per default)
    :return:
    """
    if vulnerabilities is None:
        vulnerabilities = []
    for file in files:
        try:
            interpret_plist_report(file, vulnerabilities)
        except plistlib.InvalidFileException as ex:
            logging.error("Invalid clang SA report found: %s\n,"
                          "THIS!!! should never happen", file)
            logging.error(ex)

    if validate:
        jsonschema.validate(vulnerabilities, VULNERABILITY_SCHEMA)
    return vulnerabilities


def report_compatibility():
    """Tests system for compatibility and generates a report on errors found"""
    error_reports = []

    if not compatible_version():
        error_reports.append("Clang version is not compatible! "
                             "Version required: " + REQUIRED_CLANG_VERSION)
        return error_reports

    checkers = [f for f in os.listdir(CHECKER_PATH) if f.endswith('.so')]
    cmd = [CLANG, '--analyze', '-Xclang', '-load', '-Xclang']
    no_output = ['--output=/dev/null']
    test_file = [ROOT_DIR + '/tests/hello.c']

    for check in checkers:
        try:
            command = cmd + [os.path.join(CHECKER_PATH, check)] + no_output + test_file
            subprocess.run(command,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           check=True)
        except subprocess.CalledProcessError as err:
            error_reports.append(create_error_report(check, err))

    return error_reports


def compatible_version():
    """Returns True if the systems clang version is equal to or above the
    required_clang_version and False otherwise.
    """
    return CLANG_VERSION >= REQUIRED_CLANG_VERSION


def create_error_report(check, err):
    """Creates a String from the subprocess.CalledProcessError instance err"""
    error_messages = err.stderr.decode('ascii').split('\n')
    error_messages = ['\t' + e for e in error_messages]
    output = '\n'.join(error_messages)

    return "---------------------------------------------------------------\n" \
           "Error report on " + check + ":\n" \
           "---------------------------------------------------------------\n" \
           "Clang returned with error code: " + str(err.returncode) + "\n" \
           "The error message(s) was/were the following:\n" + output


@command_entry_point
def analyze_main(args=None):
    """Main function"""
    report = report_compatibility()
    if report:
        for message in report:
            LOGGER.error(message)
        sys.exit(1)

    directory = ClangAnalyzer.analyze_build(args)

    files = list(glob.iglob(os.path.join(directory, "report-*.plist")))
    vulnerabilities = interpret_plist_reports(files)

    with open(CI_REPORT_FILE, "w") as report_file:
        json.dump(vulnerabilities, report_file)
        for file in files:
            os.remove(file)
        os.rmdir(directory)
