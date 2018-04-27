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

#include <iostream>
#include <sstream>
#include <string>

#include <clang/Frontend/CompilerInstance.h>
#include <clang/Frontend/FrontendDiagnostic.h>

#include <clang/AST/AST.h>
#include <clang/Parse/ParseAST.h>
#include <clang/AST/ASTConsumer.h>
#include <clang/AST/ASTContext.h>
#include "../preprocessor/PPContext.h"

#include "LocationFinderAction.h"


using namespace std;
using namespace clang;
using namespace clang::tooling;
using namespace llvm;


LocationFinderAction::LocationFinderAction(PPContext &pre_processor_context) : pre_processor_context(pre_processor_context) {}

/// Constructor of class FileAnalyser
/// pass the AST (abstract syntax tree) of the sourcefile
/// @param ASTConsumer * custom_ast_consumer
/// @return void
bool LocationFinderAction::run(ASTConsumer *custom_ast_consumer) {

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
bool LocationFinderASTConsumer::HandleTopLevelDecl(DeclGroupRef decls) {
  for (auto &decl : decls) {
    Visitor.TraverseDecl(decl);
  }
  return true;
}

stringstream getLocation(stringstream *start);

bool LocationFinderVisitor::VisitStmt(Stmt *s) {
  auto stmt_start_location = s->getLocStart();
  stringstream sstream_start;
  sstream_start << stmt_start_location.printToString(TheRewriter.getSourceMgr());
  auto current_start_position = getLocation(&sstream_start);

  if (current_start_position.str() == startPos) {
    s->getLocEnd().print(errs(), TheRewriter.getSourceMgr());
    errs() << '\n';
  }

  return true;
}


bool LocationFinderVisitor::VisitFunctionDecl(FunctionDecl *f) {
  if (clang::isa<clang::FunctionDecl>(f)) {
    stringstream sstream_start;
    auto start_location = f->getLocStart();
    sstream_start << start_location.printToString(TheRewriter.getSourceMgr());

    auto current_start_position = getLocation(&sstream_start);

    if (current_start_position.str() == startPos) {
      f->getLocEnd().print(errs(), TheRewriter.getSourceMgr());
      errs() << '\n';
    }
  }
  return true;
}

bool LocationFinderVisitor::VisitVarDecl(VarDecl *v) {
  auto stmt_start_location = v->getLocStart();
  stringstream sstream_start;
  sstream_start << stmt_start_location.printToString(TheRewriter.getSourceMgr());
  auto current_start_position = getLocation(&sstream_start);

  if (current_start_position.str() == startPos) {
    v->getLocEnd().print(errs(), TheRewriter.getSourceMgr());
    errs() << '\n';
  }

  return true;
}

stringstream LocationFinderVisitor::getLocation(std::stringstream *start) {
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
