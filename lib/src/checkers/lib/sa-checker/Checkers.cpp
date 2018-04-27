#include "clang/StaticAnalyzer/Core/CheckerRegistry.h"

#include "Heartbleed.h"
#include "SimpleStreamChecker.h"
#include "StaticString.h"

// See clang/StaticAnalyzer/Core/CheckerRegistry.h for details on  creating
// plugins for the clang static analyzer. The requirements are that each
// plugin include the version string and registry function below. The checker
// should then be usable with:
//
//   clang -cc1 -load </path/to/plugin> -analyze
//   -analyzer-checker=<prefix.checkername>
//
// You can double check that it is working/found by listing the available
// checkers with the -analyzer-checker-help option.

using namespace clang;
using namespace ento;

extern "C" const char clang_analyzerAPIVersionString[] =
    CLANG_ANALYZER_API_VERSION_STRING;

extern "C" void clang_registerCheckers(CheckerRegistry &registry) {
  registry.addChecker<CI::SimpleStreamChecker>(
      "demo.streamchecker", "Invokes the SimplesStreamChecker of the LLVM demo");
  registry.addChecker<CI::NetworkTaintChecker>(
      "ci.NetworkTaint", "heartbleed checker");
  registry.addChecker<CI::StaticStringChecker>(
      "ci.StaticString", "StaticString checker");
}
