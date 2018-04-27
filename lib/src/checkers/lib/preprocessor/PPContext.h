/**
 * @file PPContext.h
 * @author Sirko Höer
 * @date 19.12.2017
 * @brief headerfile from PPontext.
 *
 * @copyright Copyright (c) 2018 Code Intelligence. All rights reserved.
 */

#ifndef LLVM_PASSES_PREPROC_H
#define LLVM_PASSES_PREPROC_H

#include "clang/Frontend/CompilerInstance.h"
#include "clang/Tooling/Tooling.h"
#include "clang/Tooling/CommonOptionsParser.h"

using namespace std;
using namespace clang;
using namespace llvm;
using namespace frontend;

/**
* @class PPConstext
*
* @brief
* This Class create the preprocessor context.
* in the first step the Diagnostics is created.
* After that we set the FileManager and create the
* SourceManager. Afterwards wie set some target parameter and
* headersearchoptions. Finaly we create the preprocessor instance.
*/
class PPContext {
private:
    // Class attributes
    tooling::ClangTool &clang_tool;
    tooling::CommonOptionsParser &common_options_parser;
    std::vector<string> source_file;
    CompilerInstance compiler_instance;

public:

    /// Constructor of class PPContext
    /// @param Object CLangTool of clang tooling
    /// @param Object CommonOptionsParser clang tooling
    /// @return this object
    PPContext(clang::tooling::ClangTool &, clang::tooling::CommonOptionsParser &);

    /// getterfunction for compile instance
    /// @param void
    /// @return CompilerInstance &
    CompilerInstance &getCompilerInstance();

    /// getterfunction for ClangTools Object
    /// @param void
    /// @return clang::tooling::ClangTool &
    clang::tooling::ClangTool &getClangTool() const;

    /// getterfunction for CommonOptionsParser
    /// @param void
    /// @return clang::tooling::CommonOptionsParser &
    clang::tooling::CommonOptionsParser &getCommonOptionsParser() const;

    /// getterfunction for const std::vector<std::string> &
    /// @param void
    /// @return const std::vector<std::string> &
    const std::vector<std::string> &getSourceFile() const;

    /// set optional include path to headersearchoptions
    /// @param include path
    /// @return void
    void setHeaderPath(string header_path);

    /// create Preprocessor Instance
    /// @return void
    void createPreprocessor();

    /// create ASTContext Instance
    /// @return void
    void createASTContext();

    /// create Semantics Instance
    /// @return void
    void createSemaContext();

    /// set actual sourcefile to the MainFileID and enter this to the
    /// Preprocessor instance
    /// @param source file
    /// @return void
    void setMainFileToParse(StringRef item);

};


#endif //LLVM_PASSES_PREPROC_H
