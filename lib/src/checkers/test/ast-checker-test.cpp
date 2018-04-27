//
// Created by sirko on 19.03.18.
//

#include <clang/Tooling/Tooling.h>
#include <clang/Tooling/CommonOptionsParser.h>
#include <gtest/gtest.h>
#include "PPContext.h"
#include "FunctionFinderAction.h"
#include "LocationFinderAction.h"

using namespace std;
using namespace llvm;
using namespace clang;
using namespace clang::tooling;

static llvm::cl::OptionCategory tool_category("tool-function-finder-tests");

static cl::opt<std::string> positionOption{"pos",
                                           cl::desc{"Startposition from function or element"},
                                           cl::Optional,
                                           cl::cat{tool_category}};



class ASTCheckerTest : public ::testing::Test {
public:
    Rewriter RW;
    PPContext *PreProcessorContext;
    string pos;

    void SetUp(string pos_input) {
      pos = pos_input;
      int argc = 2;
      const char *argv[] = {"dummy","../../test/data/func.c"};

      // Initial CommonOptionParser with the args from the commandline
      CommonOptionsParser OptionsParser(argc, argv, tool_category);
      ClangTool Tool(OptionsParser.getCompilations(),
                     OptionsParser.getSourcePathList());

      // create und initialize the essential components for traversing an AST
      PreProcessorContext = new PPContext(Tool, OptionsParser);
      PreProcessorContext->createPreprocessor();
      PreProcessorContext->createASTContext();


      // Initialize a Rewriter Object and set the source manager
      RW.setSourceMgr(
          PreProcessorContext->getCompilerInstance().getSourceManager(),
          PreProcessorContext->getCompilerInstance().getLangOpts());
    }

    void TearDown(){
      delete PreProcessorContext;
    }

};


TEST_F(ASTCheckerTest, find_function_definition_position) {
  SetUp("3:3");

  // Create a AST-Consumer
  FunctionFinderASTConsumer TheASTConsumer(RW, pos);

  // Set the AST-Consumer to the compiler instanze
  FunctionFinderAction find_function_definition(*PreProcessorContext);

  // start find location ...
  ASSERT_EQ(true, find_function_definition.run(&TheASTConsumer));
}

TEST_F(ASTCheckerTest, find_end_location_position) {
  SetUp("1:1");

  // Create a AST-Consumer
  LocationFinderASTConsumer TheASTConsumer(RW, pos);

  // Set the AST-Consumer to the compiler instanze
  LocationFinderAction location_finder_definition(*PreProcessorContext);

  // start find location ...
  ASSERT_EQ(true, location_finder_definition.run(&TheASTConsumer));
}

int main(int argc, char **argv) {
  ::testing::InitGoogleTest(&argc, argv);
  return RUN_ALL_TESTS();
}