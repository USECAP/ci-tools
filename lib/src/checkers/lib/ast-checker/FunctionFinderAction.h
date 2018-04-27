/**
 * @file locationFinderASTConsumer.h
 * @author Sirko Höer
 * @date 19.12.2017
 * @brief headerfile from locationFinderASTConsumer.cpp.
 * The locationFinderASTConsumer ste the MainFileID and start the ParseAST routine
 * This class requirerd a instance of PPContext.
 *
 * @copyright Copyright (c) 2018 Code Intelligence. All rights reserved.
 */

#ifndef FUNCTION_FINDER_ACTION_H
#define FUNCTION_FINDER_ACTION_H

#include <iostream>
#include <string>
#include <sstream>
#include <clang/AST/ASTConsumer.h>
#include <clang/AST/ASTContext.h>
#include <clang/AST/RecursiveASTVisitor.h>
#include <clang/Rewrite/Core/Rewriter.h>
#include <clang/Rewrite/Frontend/Rewriters.h>

#include "FunctionFinderAction.h"
#include "../preprocessor/PPContext.h"

using namespace clang;
using namespace llvm;
using namespace std;


/// @brief class inherited from RecursiveASTVisitor and travers through the AST
class FunctionFinderVisitor : public RecursiveASTVisitor<FunctionFinderVisitor> {
private:
    /// @brief private variable used to search for the starting position of elements.
    string startPos;
    Rewriter &TheRewriter;
    FunctionDecl *targetFunction;
    bool resolved = false;

    stringstream getLocation(std::stringstream *start);
    stringstream getLine(std::stringstream *line);

public:
    FunctionFinderVisitor(Rewriter &R, string start)
        : startPos(start), TheRewriter(R), resolved(false) {}

    /// VisitStmt function, travers through the AST-Statements
    /// @param Stmt Pointer
    /// @return bool
    bool VisitStmt(Stmt *s);

    /// VisitFunctionDecl function, travers through the function in a AST
    /// @param FunctionDecl Pointer
    /// @return bool
    bool VisitFunctionDecl(FunctionDecl *f);

    /// VisitVarDecl function, travers through the var declaration in a AST
    /// @param VarDecl Pointer
    /// @return bool
    bool VisitVarDecl(VarDecl *v);
};



class FunctionFinderASTConsumer : public ASTConsumer {
private:
    FunctionFinderVisitor Visitor;

public:
    /// Constructor of class traversASTTree
    /// @param Object Rewriter
    /// @param String startposition
    /// @return this object
    FunctionFinderASTConsumer(Rewriter &R, string start)
        : Visitor(R, start) {}


    /// HandleTopLevelDecl is entrypoint to start traversing through the AST
    /// @param DeclGroupRef decls
    /// @return true or false
    bool HandleTopLevelDecl(DeclGroupRef decls) override;
};

class FunctionFinderAction {
private:
    PPContext &pre_processor_context;

public:
    /// Constructor of class FileAnalyser
    /// @param Object PPContext of clang tooling
    /// @return this object
    FunctionFinderAction(PPContext &pre_processor_context);

    /// Analyse Methode of class FileAnalyser
    /// pass the AST (abstract syntax tree) of the sourcefile
    /// @param ASTConsumer * custom_ast_consumer
    /// @return void
    bool run(ASTConsumer *custom_ast_consumer);

};

#endif //FUNCTION_FINDER_ACTION_H
