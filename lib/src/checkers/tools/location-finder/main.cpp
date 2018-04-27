/**
 * @file fuzzy_clang.cpp
 * @author Sirko Höer
 * @date 18.11.2017
 * @brief Entrypoint for the fuzzy-clang ...
 *
 * @copyright Copyright (c) 2018 Code Intelligence. All rights reserved.
 */

#include <clang/Tooling/Tooling.h>
#include <clang/Tooling/CommonOptionsParser.h>

#include "PPContext.h"
#include "LocationFinderAction.h"

using namespace llvm;
using namespace clang;
using namespace clang::tooling;

static cl::OptionCategory tool_category("location-finder-options");

static cl::opt<std::string> positionOption{"pos",
                                           cl::desc{"Startposition from function or element"},
                                           cl::Optional,
                                           cl::cat{tool_category}};

static cl::opt<bool> jsonOption{"json",
                                cl::desc{"Json output enable"},
                                cl::Optional,
                                cl::cat{tool_category}};


int main(int argc, const char **argv) {
  // Initial CommonOptionParser with the args from the commandline
  CommonOptionsParser OptionsParser(argc, argv, tool_category);
  ClangTool Tool(OptionsParser.getCompilations(),
                 OptionsParser.getSourcePathList());

  // create und initialize the essential components for traversing an AST
  PPContext ppC{Tool, OptionsParser};
  ppC.createPreprocessor();
  ppC.createASTContext();

  // Initialize a Rewriter Object and set the source manager
  Rewriter RW;
  RW.setSourceMgr(
      ppC.getCompilerInstance().getSourceManager(),
      ppC.getCompilerInstance().getLangOpts());

  // Create a AST-Consumer
  LocationFinderASTConsumer TheASTConsumer(RW, positionOption.getValue());

  // Set the AST-Consumer to the compiler instanze
  LocationFinderAction find_location(ppC);

  // start find location ...
  find_location.run(&TheASTConsumer);

  return 0;
}
