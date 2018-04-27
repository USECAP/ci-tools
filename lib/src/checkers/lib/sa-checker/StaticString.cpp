//
// Created by sirko on 27.03.18.
//

#include "StaticString.h"

using namespace CI;

void StaticStringChecker::checkPreCall(const CallEvent &Call,
                                       CheckerContext &C) const {
  ProgramStateRef State = C.getState();
  const IdentifierInfo *ID = Call.getCalleeIdentifier();

  if (ID == nullptr) {
    return;
  }

  //check some string ang mem functions
  /*
  if(ID->getName() == "strcmp"){
    auto funcDecl = dyn_cast<FunctionDecl>(Call.getDecl());
    funcDecl->getLocStart().dump(C.getSourceManager());
    llvm::outs() << " " << funcDecl->getName() << "\n";
  }
  */
}

void StaticStringChecker::checkPreStmt(const StringLiteral *DS, CheckerContext &C) const{
  auto lValue = DS->getBytes();
  DS->getLocStart().dump(C.getSourceManager());
  llvm::outs() << " " << lValue << '\n';
}