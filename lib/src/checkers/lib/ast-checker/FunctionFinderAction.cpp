/**
 * @file locationFinderASTConsumer.cpp
 * @author Sirko Höer
 * @date 18.11.2017
 * @brief
 * The locationFinderASTConsumer ste the MainFileID and start the ParseAST routine
 * This class requirerd a instance of PPContext.
 *
 * @copyright Copyright (c) 2017 Code Intelligence. All rights reserved.
 */


#include <clang/AST/AST.h>
#include <clang/Parse/ParseAST.h>

#include <iostream>
#include <clang/AST/ASTConsumer.h>
#include <clang/AST/ASTContext.h>
#include <clang/AST/RecursiveASTVisitor.h>
#include <clang/Rewrite/Core/Rewriter.h>
#include <clang/Rewrite/Frontend/Rewriters.h>

#include "FunctionFinderAction.h"

#include "../preprocessor/PPContext.h"

using namespace std;
using namespace clang;
using namespace clang::tooling;
using namespace llvm;


stringstream getLocation(stringstream *start);

stringstream getLine(stringstream *line);

FunctionFinderAction::FunctionFinderAction(PPContext &pre_processor_context) : pre_processor_context(
    pre_processor_context) {}

/// Constructor of class FileAnalyser
/// pass the AST (abstract syntax tree) of the sourcefile
/// @param ASTConsumer * custom_ast_consumer
/// @return void
bool FunctionFinderAction::run(ASTConsumer *custom_ast_consumer) {

  std::vector<string> source_file = pre_processor_context.getSourceFile();
  auto &compiler_instance = pre_processor_context.getCompilerInstance();

  compiler_instance.setASTConsumer(llvm::make_unique<ASTConsumer>(*custom_ast_consumer));

  for (const auto &item : source_file) {
    pre_processor_context.setMainFileToParse(item);
    compiler_instance.getDiagnosticClient().BeginSourceFile(compiler_instance.getLangOpts(),
                                                            &compiler_instance.getPreprocessor());

    ParseAST(compiler_instance.getPreprocessor(), custom_ast_consumer, compiler_instance.getASTContext());
    break;
  }
  return true;
}

/// HandleTopLevelDecl is entrypoint to start traversing through the AST
/// @param DeclGroupRef decls
/// @return true or false
bool FunctionFinderASTConsumer::HandleTopLevelDecl(DeclGroupRef decls) {
  for (auto &decl : decls) {
    Visitor.TraverseDecl(decl);
  }
  return true;
}

bool FunctionFinderVisitor::VisitStmt(Stmt *s) {

  if (resolved) {
    return true;
  }

  stringstream sstream_start;
  stringstream sstream_line;
  auto start_location = s->getLocStart();
  sstream_start << start_location.printToString(TheRewriter.getSourceMgr());
  sstream_line << start_location.printToString(TheRewriter.getSourceMgr());

  auto current_start_position = getLocation(&sstream_start);
  auto current_line = getLine(&sstream_line);

  if (current_start_position.str() == startPos || current_line.str() == startPos) {
    errs() << targetFunction->getName() << " (";
    targetFunction->getLocStart().print(errs(), TheRewriter.getSourceMgr());
    errs() << ")" << '\n';
    resolved = true;
  }

  return true;
}


bool FunctionFinderVisitor::VisitFunctionDecl(FunctionDecl *f) {
  if (clang::isa<clang::FunctionDecl>(f)) {
    resolved = false;
    targetFunction = f;
    stringstream sstream_start;
    stringstream sstream_line;
    auto start_location = f->getLocStart();
    sstream_start << start_location.printToString(TheRewriter.getSourceMgr());
    sstream_line << start_location.printToString(TheRewriter.getSourceMgr());

    auto current_start_position = getLocation(&sstream_start);
    auto current_line = getLine(&sstream_line);

    if (current_start_position.str() == startPos || current_line.str() == startPos) {
      errs() << f->getName() << " (";
      f->getLocStart().print(errs(), TheRewriter.getSourceMgr());
      errs() << ")" << '\n';
      resolved = true;
    }
  }
  return true;
}

bool FunctionFinderVisitor::VisitVarDecl(VarDecl *v) {

  if (resolved) {
    return true;
  }

  stringstream sstream_start;
  stringstream sstream_line;
  auto start_location = v->getLocStart();
  sstream_start << start_location.printToString(TheRewriter.getSourceMgr());
  sstream_line << start_location.printToString(TheRewriter.getSourceMgr());

  auto current_start_position = getLocation(&sstream_start);
  auto current_line = getLine(&sstream_line);

  if (current_start_position.str() == startPos || current_line.str() == startPos) {
    errs() << targetFunction->getName() << " (";
    targetFunction->getLocStart().print(errs(), TheRewriter.getSourceMgr());
    errs() << ")" << '\n';
    resolved = true;
  }

  return true;
}

stringstream FunctionFinderVisitor::getLocation(std::stringstream *start) {
  stringstream result;
  string output;

  bool flg = false;
  bool first_iteration = false;

  while (getline(*start, output, ':')) {
    if (first_iteration == false) {
      first_iteration = true;
    } else if (flg == false) {
      result << output << ':';
      flg = true;
    } else {
      result << output;
    }
  }

  return result;
}

stringstream FunctionFinderVisitor::getLine(std::stringstream *line) {
  stringstream result;
  string output;

  bool first_iteration = false;

  while (getline(*line, output, ':')) {
    if (first_iteration == false) {
      first_iteration = true;
    } else {
      result << output;
      break;
    }
  }

  return result;
}