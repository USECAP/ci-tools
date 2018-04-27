"""
This module provides support to compile files with clang and the
 original compiler at the same time
"""
import glob
import itertools
import logging
import re
import sys
import shlex
import subprocess
from collections import defaultdict
from os import environ as env, path, getcwd, chdir
from pprint import pformat
from pathlib import Path
from shutil import which

from wllvm.arglistfilter import ArgumentListFilter
import libscanbuild
from libscanbuild import intercept, arguments, compilation

import yaml
import yaml.representer

from analysis import ClangAnalyzer
from settings import (CLANG, CLANGPP, CLANG_VERSION, CROSS_COMPILE_PATH, FUZZING_DIR,
                      command_entry_point)

# treat defaultdicts as dicts in yaml
yaml.add_representer(defaultdict, yaml.representer.Representer.represent_dict)

# Internal logger
LOGGER = logging.getLogger(name=__name__)
LOGGER.setLevel(level=logging.INFO)

CLANG_VERSION = CLANG_VERSION
CLANG_VERSION_REGEX = re.compile(r".*version ([0-9]*\.[0-9]*).+", re.MULTILINE)
CLANG_TARGET_REGEX = re.compile(r"^Target: (.*)$", re.MULTILINE)

ARCHIVE_REGEX = re.compile(r"^(\(.*\.a\))(.*\.o)$")
LIBRARY_REGEX = re.compile(r"^-l(.*)\s\((.*\.so)\)")

CLANG_SANITIZERS = ["address", "undefined", "signed-integer-overflow"]
CLANG_COVERAGE = ["edge", "indirect-calls", "trace-pc-guard", "trace-cmp"]
CLANG_SANITIZE_CMD = "-fsanitize={}".format(",".join(CLANG_SANITIZERS))
CLANG_COVERAGE_CMD = "-fsanitize-coverage={}".format(",".join(CLANG_COVERAGE))


class CIArgumentListFilter(ArgumentListFilter):
    """Same as an ArgumentListFilter, but DO NOT change the name of the
    output filename when building the bitcode file so that we don't
    clobber the object file.
    """

    # pylint: disable=invalid-name

    def __init__(self, args):
        self.isLinkOnly = False
        self.isDumpCommand = False
        self.linkLibraries = []
        self.linkDirs = []

        exact_matches = {
            '-g3': (0, ArgumentListFilter.compileUnaryCallback),

            # arm stuff
            '-ffreestanding': (0, ArgumentListFilter.compileUnaryCallback),
            '-mlittle-endian': (0, ArgumentListFilter.compileUnaryCallback),
            '-mbig-endian': (0, ArgumentListFilter.compileUnaryCallback),
            '-mthumb': (0, CIArgumentListFilter.unsupported_flag_cb),
            '-mthumb-interwork': (0, CIArgumentListFilter.unsupported_flag_cb),
            '-T': (1, CIArgumentListFilter.link_only_callback),

            # dump commands
            '--version': (0, CIArgumentListFilter.dump_command_callback),
            '-dumpmachine': (0, CIArgumentListFilter.dump_command_callback),
            '-dumpversion': (0, CIArgumentListFilter.dump_command_callback),
            '-dumpspecs': (0, CIArgumentListFilter.dump_command_callback)
        }
        pattern_matches = {

            # cross compile stuff
            r'^-mcpu=.+$': (0, ArgumentListFilter.compileUnaryCallback),
            r'^-march=.+$': (0, CIArgumentListFilter.cpu_callback),
            r'^--specs=.+$': (0, CIArgumentListFilter.unsupported_flag_cb),
            r'^-mfloat-abi=.+$': (0, ArgumentListFilter.compileUnaryCallback),
            r'^-mfpu=.+$': (0, ArgumentListFilter.compileUnaryCallback),

            # dump commands
            r'^-print-.+$': (0, CIArgumentListFilter.dump_command_callback),

            # linking
            r'^-l.+$': (0, CIArgumentListFilter.add_link_library),
            r'^-L.+$': (0, CIArgumentListFilter.add_link_directory)
        }

        super().__init__(args,
                         exactMatches=exact_matches,
                         patternMatches=pattern_matches)
        if not self.inputFiles and self.objectFiles:
            self.isLinkOnly = True

    def add_link_library(self, flag):
        """Adds library information specified with -l from the compiler
        """
        lib = flag.lstrip("-l").lstrip()
        LOGGER.debug("add_link_library (flag: %s), (lib: %s)", flag, lib)
        self.linkLibraries.append(lib)
        self.linkUnaryCallback(flag)

    def add_link_directory(self, flag):
        """Adds linking directories specified with -L from the compiler
        """
        directory = flag.lstrip("-L").lstrip()
        LOGGER.debug("add_link_library (flag: %s), (lib: %s)", flag, directory)
        self.linkDirs.append(directory)
        self.linkUnaryCallback(flag)

    def cpu_callback(self, flag):
        """Sets the CPU type
        """
        cpu = flag.split("=")[1]
        if cpu == "armv7-m":
            self.compileArgs.append("-march=armv7m")

    def unsupported_flag_cb(self, flag):
        """Ignores specific flags which are not supported by clang
        """
        pass

    def dump_command_callback(self, flag):
        """When dump commands are used in clang and gcc, all other parameters
         are ignored"""
        LOGGER.debug("dumpCommandCallback %s", flag)
        self.isDumpCommand = True

    def link_only_callback(self, flag, link):
        """If the compiler execution only performs linking steps"""
        LOGGER.debug("linkOnlyCallback %s %s", flag, link)
        self.isLinkOnly = True

    def get_filenames(self):
        """returns a pair (srcFile, objectFilename, bitcodeFilename)
        """
        if self.inputFiles:
            input_name = self.inputFiles[0]
        elif self.objectFiles:  # sometimes the compiler is used as linker
            input_name = self.objectFiles[0]
        else:
            input_name = None

        if self.outputFilename:
            output_name = self.outputFilename
        else:
            output_name = "a.out"

        return input_name, output_name


class Clang(object):
    """
    Provides bindings to compile a file with clang and the intended
    compiler (default CC)
    """

    def __init__(self, args, name="clang"):
        self.cc = None
        self.options = {}

        self.cmd = self.get_clang_path(name, CLANG_VERSION)
        self.get_default_compiler(name)

        self.arg_filter = CIArgumentListFilter(args)

        self.clang_compile_args = self.arg_filter.compileArgs
        src_file, obj_file = self.arg_filter.get_filenames()
        self.files = {
            'src': src_file,
            'obj': obj_file,
            'bc': obj_file + ".bc",
            'yml': obj_file + ".yml",
            'plist': src_file + ".plist",
        }

    def analyze(self, cmd):
        """Here, we will implement the analysis passes based on the static clang
        analyzer and vfinder
        """
        argf = self.arg_filter
        cmd = cmd + argf.compileArgs
        if not (argf.isLinkOnly or argf.isDumpCommand or
                argf.isPreprocessOnly or argf.isAssembly):
            analyzer = ClangAnalyzer(cmd)
            analyzer.run(self.files["src"])

    def compile(self):
        """Compiles the intended file with clang and emits llvm bc file
        """
        base_cmd = [self.cmd, "-target", self.options["target"]]

        if "sysroot" in self.options:
            base_cmd.extend(["--sysroot", self.options["sysroot"]])

        if "CLANG_CFLAGS" in env and env["CLANG_CFLAGS"]:
            base_cmd.extend(shlex.split(env["CLANG_CFLAGS"]))

        cmd = base_cmd.copy()
        if self.arg_filter.isDumpCommand or self.arg_filter.isPreprocessOnly:
            cmd.extend(self.arg_filter.inputList)
        elif not self.arg_filter.isLinkOnly:
            cmd.extend(self.clang_compile_args)
            cmd.extend(["-emit-llvm", "-c", "-o", self.files["bc"],
                        self.files["src"]])

        else:
            cmd.extend(["-o", self.files["bc"]])
            cmd.extend(self.arg_filter.linkArgs)
            if self.arg_filter.objectFiles:
                cmd.extend(self.arg_filter.objectFiles)

        # Execute clang
        proc = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            LOGGER.warning("Error during compiling %s: Command: \n----\n"
                           "%s\nOutput:\n----\n%s\n----\n"
                           "Original arguments: %s\n",
                           self.files["src"], " ".join(cmd),
                           proc.stderr.decode('utf-8'),
                           self.arg_filter.inputList)

        if self.files["bc"]:
            self._save_linking_information()

        self.analyze(base_cmd)

        return proc.returncode

    def compile_orig(self):
        """Compiles the intended file with the default compiler ($CC)
        """
        cmd = [self.cc] + self.arg_filter.inputList  # original CC and args

        # Execute default compiler as it is
        # If error, abort the entire build process
        LOGGER.debug("GCC: %s", " ".join(cmd))
        proc = subprocess.run(
            cmd, stdout=sys.stdout, stderr=sys.stderr)
        return proc.returncode

    def get_clang_path(self, cmd, version):
        """Gets the clang executable installed on the system
        """
        name = cmd.split("-")[-1]
        if name == "g++":
            cmd = "clang++"
        else:
            cmd = "clang"
        if which(cmd + "-" + version):
            cmd = cmd + "-" + version
        elif not which(cmd):
            return None
        cmd = which(cmd)

        proc = subprocess.run(
            [cmd, "-v"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output = proc.stderr.decode('utf-8')

        search = CLANG_VERSION_REGEX.search(output)
        if not search or not search.group(1) == CLANG_VERSION:
            LOGGER.error(
                "%s-%s mismatches %s", cmd, CLANG_VERSION, search.group(1))
            return None
        search = CLANG_TARGET_REGEX.search(output)
        self.options['target'] = search.group(1)
        return cmd

    def get_default_compiler(self, name):
        """Gets the default decompiler from the environment
        """
        if "ORIG_CC" in env:
            cc = env["ORIG_CC"]
        elif name == "ci-cc":
            cc = "gcc"
        elif name == "clang":
            cc = self.cmd
        else:
            cc = name

        if name == "arm-none-eabi-gcc":
            self.options["target"] = "armv7m-none-eabi"
            path = CROSS_COMPILE_PATH + "/arm-none-eabi"
            self.options["sysroot"] = path + "/arm-none-eabi"

        self.cc = which(cc)
        LOGGER.debug("Compiler path %s", self.cc)
        if not self.cc:
            LOGGER.warning("CC (%s) does not exist", cc)
            raise Exception()

    def _save_linking_information(self):
        """Stores linking information to a yaml file
        """
        cmd = [self.cc, "-Xlinker", "--trace"] + self.arg_filter.inputList
        LOGGER.warning(" ".join(cmd))
        proc = subprocess.run(cmd, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
        if proc.returncode != 0:
            LOGGER.warning("Linking information failed: %s",
                           proc.stderr.decode("utf-8"))
            return
        objects = {
            "archive_files": defaultdict(list),
            "libraries": defaultdict(list),
            "object_files": []
        }
        for line in proc.stdout.decode("utf-8").splitlines()[1:]:
            if ARCHIVE_REGEX.match(line) is not None:
                search = ARCHIVE_REGEX.search(line)
                objects["archive_files"][search.group(1)].append(
                    search.group(2))
            elif LIBRARY_REGEX.match(line) is not None:
                search = LIBRARY_REGEX.search(line)
                objects["libraries"][search.group(1)].append(search.group(2))
            else:
                objects["object_files"].append(line)

        data = {self.files["bc"]: objects}
        with open(self.files["yml"], "w") as file:
            file.write(
                yaml.dump(
                    data,
                    Dumper=yaml.Dumper,  # slow variant because of defaultdict
                    default_flow_style=False  # to use the representer
                )
            )


def build_fuzzing_targets():
    """Build the fuzz targets"""
    compilation_files = list(glob.iglob(path.join(FUZZING_DIR, "*.cc")))
    object_files = list(glob.iglob(path.join("**", "*.o"), recursive=True))
    archive_files = list(glob.iglob(path.join("**", "*.a"), recursive=True))

    for file in compilation_files:
        output_file = "{}/{}".format(FUZZING_DIR, Path(file).stem)
        LOGGER.info("Compiling target: %s (src: %s)", output_file, file)
        cmd = [CLANGPP, "-g", CLANG_SANITIZE_CMD + ",fuzzer", "-I.",
               "-fuse-ld=gold", "-o", output_file]
        proc = subprocess.run(cmd + object_files + archive_files + [file])
        LOGGER.info("Cmd: %s", " ".join(cmd + object_files + archive_files +
                                        [file]))
        if proc.returncode != 0:
            LOGGER.error("Could not compile fuzzing target: %s\n\t"
                         "with parameters: %s", file, " ".join(proc.args))
            sys.exit(proc.returncode)
    return 0


def intercept_build(args):
    # type: () -> int
    """ Entry point for 'intercept-build' command. """

    parser = arguments.create_intercept_parser()
    parser.add_argument(
        '--project-path',
        metavar="<path>",
        dest='cwd',
        type=str,
        default=getcwd(),
        help="""used path where the build tools are invoked""")
    parser.add_argument(
        '--sanitize-build',
        action='store_true',
        help="""Rebuild command with sanitizers enabled""")
    parser.add_argument(
        '--fuzzing-targets',
        action='store_true',
        help="""Build fuzzing targets""")
    args = parser.parse_args(args)
    chdir(args.cwd)

    if args.sanitize_build:
        if not args.build:
            LOGGER.error("Please provide a build command")
            sys.exit(2)
        compiler = "{} -g {} {}"

        LOGGER.debug("Compiler command %s",
                     compiler.format(CLANG, CLANG_SANITIZE_CMD,
                                     CLANG_COVERAGE_CMD))
        proc = subprocess.run(
            args.build, shell=True,
            env={**env,
                 **{'CC': compiler.format(
                     CLANG, CLANG_SANITIZE_CMD, CLANG_COVERAGE_CMD),
                    'CXX': compiler.format(
                        CLANGPP, CLANG_SANITIZE_CMD, CLANG_COVERAGE_CMD)}})
        parser.exit(status=proc.returncode)
    if args.fuzzing_targets:
        LOGGER.info("Building fuzzing targets")
        ret = build_fuzzing_targets()
        parser.exit(status=ret)

    args.append = True

    libscanbuild.reconfigure_logging(args.verbose)
    logging.debug('Raw arguments %s', sys.argv)

    # short validation logic
    if not args.build:
        parser.error(message='missing build command')

    logging.debug('Parsed arguments: %s', args)
    exit_code, current = intercept.capture(args)

    # To support incremental builds, it is desired to read elements from
    # an existing compilation database from a previous run.
    if args.append and path.isfile(args.cdb):
        previous = compilation.CompilationDatabase.load(args.cdb)
        entries = iter(set(itertools.chain(previous, current)))
        compilation.CompilationDatabase.save(args.cdb, entries)
    else:
        compilation.CompilationDatabase.save(args.cdb, current)

    return exit_code


@command_entry_point
def build_main(args=None):
    """Builds current project
    """

    # Internal logger
    logger = logging.getLogger(name=__name__)
    env["CI_LOGFILE"] = getcwd() + "/ci.log"

    try:
        env["ORIG_PATH"] = env["PATH"]
        exit_code = intercept_build(args)
        sys.exit(exit_code)
    except OSError as ex:
        err_msg = pformat(" ".join(args))
        logger.error("ci-build Failed to execute: %s\n"
                     "Given parameters: %s (cwd: %s)",
                     ex.strerror, err_msg, getcwd())
        sys.exit(-1)


@command_entry_point
def compile_main():
    """Compiles a file

    :return: exit_code of the compiler
    """
    if "CI_LOGFILE" in env:
        logging.basicConfig(filename=env["CI_LOGFILE"], level=logging.DEBUG)

    if "ORIG_PATH" in env:
        env["PATH"] = env["ORIG_PATH"]

    logging.warning("COMMAND: %s", " ".join(sys.argv))
    try:
        compiler_name = path.split(sys.argv[0])[1]
        clang = Clang(sys.argv[1:], name=compiler_name)

        returncode = clang.compile_orig()
        if returncode != 0:
            sys.exit(returncode)  # exit with same code as $CC
        clang.compile()
        sys.exit(returncode)
    except BrokenPipeError as exception:
        print(exception)
