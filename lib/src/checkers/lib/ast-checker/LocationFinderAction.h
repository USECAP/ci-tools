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

#ifndef LOCATION_FINDER_ACTION_H
#define LOCATION_FINDER_ACTION_H

#include <iostream>

#include <clang/Frontend/CompilerInstance.h>
#include <clang/Frontend/FrontendDiagnostic.h>
#include <llvm/IRReader/IRReader.h>
#include <llvm/Support/Timer.h>

#include <clang/AST/ASTConsumer.h>
#include <clang/AST/ASTContext.h>
#include <clang/AST/ASTConsumer.h>
#include <clang/AST/RecursiveASTVisitor.h>
#include <clang/Rewrite/Core/Rewriter.h>
#include <clang/Rewrite/Frontend/Rewriters.h>

#include "../../lib/preprocessor/PPContext.h"

/// @brief class inherited from RecursiveASTVisitor and travers through the AST
class LocationFinderVisitor : public RecursiveASTVisitor<LocationFinderVisitor> {
private:
    /// @brief private variable used to search for the starting position of elements.
    string startPos;
    Rewriter &TheRewriter;

    stringstream getLocation(std::stringstream *start);

public:
    LocationFinderVisitor(Rewriter &R, string start)
        : startPos(start), TheRewriter(R) {}

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


class LocationFinderASTConsumer : public ASTConsumer {
private:
    LocationFinderVisitor Visitor;

public:
    /// Constructor of class traversASTTree
    /// @param Object Rewriter
    /// @param String startposition
    /// @return this object
    LocationFinderASTConsumer(Rewriter &R, string start)
        : Visitor(R, start) {}


    /// HandleTopLevelDecl is entrypoint to start traversing through the AST
    /// @param DeclGroupRef decls
    /// @return true or false
    bool HandleTopLevelDecl(DeclGroupRef decls) override;
};


class LocationFinderAction {
private:
    PPContext &pre_processor_context;

public:
    /// Constructor of class FileAnalyser
    /// @param Object PPContext of clang tooling
    /// @return this object
    LocationFinderAction(PPContext &pre_processor_context);

    /// Analyse Methode of class FileAnalyser
    /// pass the AST (abstract syntax tree) of the sourcefile
    /// @param ASTConsumer * custom_ast_consumer
    /// @return void
    bool run(ASTConsumer *custom_ast_consumer);

};


#endif //LOCATION_FINDER_ACTION_H
