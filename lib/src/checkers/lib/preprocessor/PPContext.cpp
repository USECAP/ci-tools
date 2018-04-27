/**
 * @file PPContext.cpp
 * @author Sirko Höer
 * @date 19.12.2017
 * @brief PPContext create a preprocessor instance to get token from
 * source file.
 *
 * @copyright Copyright (c) 2018 Code Intelligence. All rights reserved.
 */

#include <iostream>
#include <memory>

#include "llvm/Support/raw_ostream.h"
#include "llvm/Support/Host.h"
#include "llvm/ADT/IntrusiveRefCntPtr.h"
#include "llvm/Support/Memory.h"

#include "clang/Basic/DiagnosticOptions.h"
#include "clang/Basic/LangOptions.h"
#include "clang/Basic/FileSystemOptions.h"
#include "clang/Basic/SourceManager.h"
#include "clang/Basic/TargetOptions.h"
#include "clang/Basic/TargetInfo.h"

#include "clang/Frontend/TextDiagnosticPrinter.h"
#include "clang/Frontend/DiagnosticRenderer.h"
#include "clang/Frontend/CompilerInstance.h"

#include "clang/Lex/HeaderSearch.h"
#include "clang/Lex/Preprocessor.h"
#include "clang/Lex/PreprocessorOptions.h"

#include "clang/AST/ASTDiagnostic.h"
#include "clang/AST/ASTContext.h"

#include "clang/Tooling/Tooling.h"
#include "clang/Tooling/CommonOptionsParser.h"

#include "clang/Driver/DriverDiagnostic.h"
#include "PPContext.h"

using namespace std;
using namespace llvm;
using namespace clang;

/// Constructor of class PPContext
/// @param Object CLangTool of clang tooling
/// @param Object CommonOptionsParser clang tooling
/// @return this object
PPContext::PPContext(clang::tooling::ClangTool &clang_tools,
                     clang::tooling::CommonOptionsParser &common_options_parser) :
    clang_tool(clang_tools),
    common_options_parser(common_options_parser) {
  source_file = common_options_parser.getSourcePathList();

  compiler_instance.createDiagnostics();
  std::shared_ptr<clang::TargetOptions> pto = std::make_shared<clang::TargetOptions>();
  pto->Triple = llvm::sys::getDefaultTargetTriple();
  TargetInfo *pti = TargetInfo::CreateTargetInfo(compiler_instance.getDiagnostics(), pto);
  compiler_instance.setTarget(pti);
  compiler_instance.setFileManager(&clang_tool.getFiles());
  compiler_instance.createSourceManager(compiler_instance.getFileManager());
}

/// getterfunction for ClangTools Object
/// @param void
/// @return clang::tooling::ClangTool &
clang::tooling::ClangTool &PPContext::getClangTool() const {
  return clang_tool;
}

/// getterfunction for CommonOptionsParser
/// @param void
/// @return clang::tooling::CommonOptionsParser &
clang::tooling::CommonOptionsParser &PPContext::getCommonOptionsParser() const {
  return common_options_parser;
}

/// getterfunction for const std::vector<std::string> &
/// @param void
/// @return const std::vector<std::string> &
const std::vector<std::string> &PPContext::getSourceFile() const {
  return source_file;
}

/// getterfunction for compile instance
/// @param void
/// @return CompilerInstance &
CompilerInstance &PPContext::getCompilerInstance() {
  return compiler_instance;
}

/// set optional include path to headersearchoptions
/// @param include path
/// @return void
void PPContext::setHeaderPath(string header_path) {
  HeaderSearchOptions &hso = compiler_instance.getHeaderSearchOpts();
  hso.AddPath(header_path, clang::frontend::Angled, false, false);
}

/// create Preprocessor Instance
/// @return void
void PPContext::createPreprocessor() {
  compiler_instance.createPreprocessor(clang::TU_Complete);
  compiler_instance.getPreprocessor().SetSuppressIncludeNotFoundError(true);
}

/// create ASTContext Instance
/// @return void
void PPContext::createASTContext() {
  compiler_instance.createASTContext();
}

/// create Semantics Instance
/// @return void
void PPContext::createSemaContext() {
  compiler_instance.createSema(TU_Complete, nullptr);
}


/// set actual sourcefile to the MainFileID and enter this to the
/// Preprocessor instance
/// @param source file
/// @return void
void PPContext::setMainFileToParse(StringRef item) {
  const FileEntry *pFile = compiler_instance.getFileManager().getFile(item);

  compiler_instance.getSourceManager().setMainFileID(
      compiler_instance.getSourceManager().createFileID(pFile,
                                                        SourceLocation(),
                                                        SrcMgr::C_User)
  );

}


