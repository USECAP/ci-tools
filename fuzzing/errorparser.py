"""Module for parsing libfuzzer logfiles produced by the compiler-rt toolchain.
"""

# Important files are the sanitizer_stacktrace_printer.cc in sanitizer_common
# and the asan_error.cc file in asan."""

import re
from abc import ABC, abstractmethod


class LogParserException(Exception):
    """An Exception that signals an error in the libfuzzer log parsing process.
    """
    pass


class ErrorParserStrategy(ABC):
    """An interface defining methods that parse a single error instance."""
    MEMORY_ERROR = "Memory error"
    LOGIC_ERROR = "Logic error"
    INSTRUMENTATION_PATH = "compiler-rt/lib/"

    MODULE_LOCATION_RE = re.compile(r"\((.+)\+(0x[0-9a-fA-F]+)\)$")
    SOURCE_LOCATION_RE = re.compile(r"(.+):(\d+):(\d+)$|(.+):(\d+)$")
    SOURCE_LOCATION_VS = re.compile(r"(.+)\((\d+),(\d+)\)$|(.+)\((\d+)\)$")

    BASE_UNIT_STR = "base unit:"

    @abstractmethod
    def get_vulnerabilities(self, header, report):
        """Returns a list of Json objects conforming to SA_VULNERABILITY_SCHEMA
        """
        pass

    def parse_stack_trace(self, stack_trace):
        """Parses stack_trace and returns vulnerability location and path."""
        location, path = {}, []
        if not stack_trace:
            return location, path

        stack_top = stack_trace.readline()
        while self.__is_instrumentation(stack_top):
            # skip instrumentation
            stack_top = stack_trace.readline()

        if stack_top.strip():
            _, src_location = self.__get_name_and_src_location(stack_top)
            location = self.parse_source_location(src_location)

            path = self.__convert_stack_trace_to_path(stack_trace)
            path.append(self.__get_path_event(stack_top))

        return location, path

    @classmethod
    def __is_instrumentation(cls, line):
        """Returns True if we can assume that the stack_trace line covers
        instrumentation.
        """
        line = line.split()
        if not line:
            return False
        return cls.INSTRUMENTATION_PATH in line[-1]

    def __convert_stack_trace_to_path(self, stack_trace):
        """Converts stack_trace into a sequence of path-events."""
        path = []
        for line in stack_trace:
            if "Fuzzer::ExecuteCallback" in line or not line.strip():
                break
            path.append(self.__get_path_event(line))
        path.reverse()
        return path

    def __get_path_event(self, line):
        """Takes a line of a stack trace and creates an event from its
        content.
        """
        func_name, src_location = self.__get_name_and_src_location(line)
        event = {"kind": "event",
                 "message": func_name,
                 "location": self.parse_source_location(src_location)}
        return event

    @classmethod
    def parse_source_location(cls, src_location):
        """Turns a src_location of any form into a location specified by
        VULNERABILITY_SCHEMA
        """
        match = re.match(cls.SOURCE_LOCATION_RE, src_location)
        if not match:
            match = re.match(cls.SOURCE_LOCATION_VS, src_location)
        if match:
            groups = match.groups()
            if groups[0]:
                path, row, col, *_ = groups
            else:
                path, row = groups[3:]
                col = 0

            return {
                "file": path,
                "line": int(row),
                "col": int(col)
            }

        match = re.match(cls.MODULE_LOCATION_RE, src_location)
        # module location, probably no debug information
        if match:
            path, col = match.groups()
            return {
                "file": path,
                "line": 0,
                "col": int(col, 16)
            }

        raise LogParserException("Invalid source location: {}"
                                 .format(src_location))

    @staticmethod
    def __get_name_and_src_location(line):
        """Splits a stack trace line into a function name and a source
        location.
        """
        line = line.split()
        func_name = "" if len(line) < 4 else line[3]
        func_name = func_name.split("(")[0]
        src_location = line[-1]
        return func_name, src_location

    def get_crash_input(self, report):
        """Get the input that triggered the error."""
        for line in report:
            if self.is_next_error(line):
                report.putback_line()
                return "", ""

            if self.BASE_UNIT_STR in line:
                break

        hex_output = next(report, "").strip()
        ascii_output = next(report, "").strip()

        return hex_output, ascii_output

    def find_stack_trace(self, report):
        """Skips to the stack_trace inside the report.
        Returns the stream report if it could be found, None otherwise.
        """
        for line in report:
            if self.is_next_error(line):
                report.putback_line()
                return None

            if line.strip().startswith("#0"):
                report.putback_line()
                return report

        return None

    @staticmethod
    def is_next_error(line):
        """Return True if line is the start of a new error,
        False otherwise.
        """
        return line.startswith("==") and "ERROR" in line


class AsanDescription(ABC):
    """A class for building descriptions informational, customized to fit each
    bug type.
    """
    def get(self, error_parser, report, info):
        """Returns a description crafted from information given in report and
        info.
        """
        description = self.build_description(error_parser, report, info)
        hex_in, ascii_in = error_parser.get_crash_input(report)
        description += "on input:\nHex: {}\nASCII: {}\n".format(hex_in, ascii_in)
        return description

    @abstractmethod
    def build_description(self, error_parser, report, info):
        """Info:
        (bug-type, further information on bug, location in file, path to file)
        """
        pass

    @staticmethod
    def reassemble_location(loc):
        """Reassembles a json location to a string."""
        return "{}:{}:{}".format(loc["file"], loc["line"], loc["col"])


class DoubleFreeDescription(AsanDescription):
    """Class that builds a customized description for the double-free bug type.
    """
    def build_description(self, error_parser, report, info):
        stack_trace = error_parser.find_stack_trace(report)
        location, _ = error_parser.parse_stack_trace(stack_trace)
        first_free = self.reassemble_location(location)
        second_free = self.reassemble_location(info[2])
        return "Freed allocated memory twice:\nHere: {}\nand here: {}\n" \
               .format(first_free, second_free)


class AllocDeallocMisDescription(AsanDescription):
    """Class that builds a customized description for the
    alloc-dealloc-mismatch bug type.
    """
    def build_description(self, error_parser, report, info):
        bug_type, header_info, dealloc_location, _ = info
        stack_trace = error_parser.find_stack_trace(report)
        alloc_location, _ = error_parser.parse_stack_trace(stack_trace)
        alloc_location = self.reassemble_location(alloc_location)
        dealloc_location = self.reassemble_location(dealloc_location)
        alloc, dealloc = re.search(r"\((.+) vs (.+)\)", header_info).groups()
        return "{}: Used {} to allocate memory here:\n{}\n" \
               "but used {} to deallocate it here:\n{}\n" \
               .format(bug_type, alloc, alloc_location,
                       dealloc, dealloc_location)


class NegativeSizeParamDescription(AsanDescription):
    """Class that builds a customized description for the
    negative-size-parameter bug type.
    """
    def build_description(self, error_parser, report, info):
        _, header_info, location, _ = info
        location = self.reassemble_location(location)
        negative_size = re.search(r"\(size=([-0-9]+)\)", header_info).group(1)
        return "Passed negative size parameter ({}) to function here:\n{}\n" \
               .format(negative_size, location)


class DefaultDescription(AsanDescription):
    """Class that builds a default description for bug types that need no
    special handling.
    """
    def build_description(self, error_parser, report, info):
        typ, _, _, path = info
        description = typ
        if path:
            final_event = path[-1]
            func_name = final_event.get("message", "")
            path_name = final_event.get("location", {}).get("file", "")
            description += ": {} in {}".format(path_name, func_name)
        return description


class AsanParserStrategy(ErrorParserStrategy):
    """ErrorParserStrategy for the AddressSanitizer."""
    MEMORY_ERROR = ErrorParserStrategy.MEMORY_ERROR
    LOGIC_ERROR = ErrorParserStrategy.LOGIC_ERROR

    GENERIC_ERROR_TYPE = {
        "unknown-crash": MEMORY_ERROR,
        "heap-buffer-overflow": MEMORY_ERROR,
        "heap-use-after-free": MEMORY_ERROR,
        "stack-buffer-underflow": MEMORY_ERROR,
        "initialization-order-fiasco": LOGIC_ERROR,
        "stack-buffer-overflow": MEMORY_ERROR,
        "stack-use-after-return": MEMORY_ERROR,
        "use-after-poison": MEMORY_ERROR,
        "container-overflow": MEMORY_ERROR,
        "stack-use-after-scope": MEMORY_ERROR,
        "global-buffer-overflow": MEMORY_ERROR,
        "intra-object-overflow": MEMORY_ERROR,
        "dynamic-stack-buffer-overflow": MEMORY_ERROR,
        "alloc-dealloc-mismatch": LOGIC_ERROR,
        "new-delete-type-mismatch": LOGIC_ERROR,
        "negative-size-param": MEMORY_ERROR,
        "invalid-pointer-pair": MEMORY_ERROR
    }

    ATTEMPTING_ERRORS = [
        ("free", (MEMORY_ERROR, "free-not-malloced")),
        ("double", (MEMORY_ERROR, "double-free")),
        ("to call malloc", (LOGIC_ERROR, "malloc_usable_size")),
        ("to call __s", (LOGIC_ERROR, "__sanitizer_get_allocated_size"))
    ]

    DESCRIPTIONS = {
        "double-free": DoubleFreeDescription,
        "alloc-dealloc-mismatch": AllocDeallocMisDescription,
        "negative-size-param": NegativeSizeParamDescription,
    }

    def get_vulnerabilities(self, header, report):
        category, bug_type, header_info = self.__parse_error_header(header)
        location, path = self.parse_stack_trace(self.find_stack_trace(report))
        info = (bug_type, header_info, location, path)

        description = self.DESCRIPTIONS.get(bug_type, DefaultDescription)()

        return [{
            "category": category,
            "type": bug_type,
            "description": description.get(self, report, info),
            "location": location,
            "path": path
        }]

    def __parse_error_header(self, header):
        """Parses the first line of an error instance and returns the category
        and the type of the bug."""
        header = header.split(": ")
        potential_type = header[2].split()[0]
        header_description = ": ".join(header[2:])

        try:
            category = self.__get_generic_category(potential_type)
            return category, potential_type, header_description

        except KeyError:
            if header_description.startswith("attempting"):
                attempting_to = " ".join(header_description.split()[1:])
                for prefix, (category, typ) in self.ATTEMPTING_ERRORS:
                    if attempting_to.startswith(prefix):
                        return category, typ, header_description

            if potential_type.endswith("param-overlap"):
                return self.MEMORY_ERROR, potential_type, header_description

            # only a few left but me might want to work on this one
            raise LogParserException("Unknown asan error header:\n{}\n"
                                     .format(header_description))

    @classmethod
    def __get_generic_category(cls, typ):
        """Returns the appropriate error category for the corresponding
        typ(e).
        """
        return cls.GENERIC_ERROR_TYPE[typ]


class LsanParserStrategy(ErrorParserStrategy):
    """ErrorParserStrategy for the LeakSanitizer."""
    TYPE = "memory-leak"
    HEADER_PATTERN = re.compile(r"of ([0-9]+) byte\(s\) in ([0-9]+) ")

    def get_vulnerabilities(self, header, report):
        vulnerabilities = []
        leaks = self.gather_leaks(report)
        for num_bytes, num_objects, location, path in leaks.values():
            vulnerabilities.append({
                "category": self.MEMORY_ERROR,
                "type": self.TYPE,
                "description": self.__get_description(num_bytes, num_objects),
                "location": location,
                "path": path
            })

        return vulnerabilities

    def gather_leaks(self, report):
        """Gathers leaks and makes sure we don't have multiple reports and the
        same leak cause.
        """
        leaks = {}
        for line in report:
            if "SUMMARY" in line:
                report.putback_line()
                break

            if line.startswith("Direct") or line.startswith("Indirect"):
                no_bytes, no_objects = re.search(self.HEADER_PATTERN, line).groups()
                no_bytes, no_objects = int(no_bytes), int(no_objects)
                location, path = self.parse_stack_trace(report)
                file_name = location["file"]
                details = leaks.get(file_name)
                if details:
                    details[0] += no_bytes
                    details[1] += no_objects
                    leaks[file_name] = details
                else:
                    leaks[file_name] = [no_bytes, no_objects, location, path]

        return leaks

    @staticmethod
    def __get_description(num_bytes, num_objects):
        return "{} byte(s) leaked in {} object(s)" \
               .format(num_bytes, num_objects)


class TimeoutParserStrategy(ErrorParserStrategy):
    """ErrorParserStrategy for timeout-errors."""
    TIMEOUT_CRASH_INPUT_OFFSET = 6
    TYPE = "timeout"
    ALARM_CALLBACK = "Fuzzer::StaticAlarmCallback"

    def get_vulnerabilities(self, header, report):
        description = self.TYPE

        on_input = self.__get_on_input_string(report)
        location, path = self.parse_stack_trace(self.find_stack_trace(report))

        if path:
            final_event = path[-1]
            func_name = final_event.get("message", "")
            path_name = final_event.get("location", {}).get("file", "")
            description += " %s in %s %s" % (path_name, func_name, on_input)

        return [{
            "category": self.LOGIC_ERROR,
            "type": self.TYPE,
            "description": description,
            "location": location,
            "path": path
        }]

    def __get_on_input_string(self, report):
        position = report.tell()
        # in timeout logfiles some of the information is stored before
        # the ==ERROR== tag
        report.putback_line(self.TIMEOUT_CRASH_INPUT_OFFSET)

        hex_in, ascii_in = self.get_crash_input(report)
        # and skip to the error line again
        report.seek(position)
        return "on input:\nHex: %s\nASCII: %s\n" % (hex_in, ascii_in)

    def parse_stack_trace(self, stack_trace):
        if not stack_trace:
            return {}, []

        pos = stack_trace.tell()
        for line in stack_trace:
            if self.ALARM_CALLBACK in line:
                stack_trace.readline()
                return super().parse_stack_trace(stack_trace)

        stack_trace.seek(pos)
        return super().parse_stack_trace(stack_trace)
