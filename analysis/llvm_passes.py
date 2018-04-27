"""
Module dealing with Code Intelligence LLVM passes
"""
import logging
import json
import subprocess
import sys

import jsonschema
import yaml

from settings import ROOT_DIR, SPECS_DIR

VULN_SCHEMA = SPECS_DIR + "/vulnerability_schema.json"


# Internal logger
LOGGER = logging.getLogger(name=__name__)


class LLVMAnalyzer(object):
    """
    Dealing with vulnerabilities coming from Code Intelligence LLVM passes
    """
    LLVM_PASSES_PATH = ROOT_DIR + "/libs/llvm-passes"
    PASSES_LIB = LLVM_PASSES_PATH + "/ci.so"

    def __init__(self):
        self._vulnerabilities = []
        with open(VULN_SCHEMA, "r") as file:
            self.vulnerability_schema = json.load(file)

    def run(self, file):
        """
        Runs required passes in a specific order (this can be done via vfinder
         or opt). Here, the results are stored in a list.
        :param file: bitcode file which needs to be analyzed
        :return: returncode coming from vfinder
        """
        cmd = ["opt-5.0", "-load=" + self.PASSES_LIB, "-print-report", "-yaml",
               "-ci-zero-alloc", "-ci-hardcoded-passwords",
               "-ci-unsafe-function", "-ci-unsanitized-inputs",
               "-o", "/dev/null", file]
        logging.debug("Command: %s", " ".join(cmd))
        proc = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=sys.stderr)
        if proc.returncode != 0:
            return proc.returncode

        string = proc.stdout.decode('utf-8')
        results = yaml.load_all(string, Loader=yaml.CBaseLoader)
        for vuln in results:
            if vuln and isinstance(vuln, list):
                self._vulnerabilities.extend(vuln)

        return proc.returncode

    @property
    def vulnerabilities(self):
        """returns the vulnerability list"""
        return self._vulnerabilities

    def export_json(self):
        """Exports everything to JSON"""
        i = 0
        for vuln in self.vulnerabilities:
            with open("{}.json".format(i), "w") as file:
                if jsonschema.validate(vuln, self.vulnerability_schema):
                    file.write(json.dumps(vuln))
                    i += 1
