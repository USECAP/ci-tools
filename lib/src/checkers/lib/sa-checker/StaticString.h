//
// Created by sirko on 27.03.18.
//

#ifndef CI_CHECKERS_STATICSTRING_H
#define CI_CHECKERS_STATICSTRING_H

#include "clang/StaticAnalyzer/Core/BugReporter/BugType.h"
#include "clang/StaticAnalyzer/Core/Checker.h"
#include "clang/StaticAnalyzer/Core/PathSensitive/CallEvent.h"
#include "clang/StaticAnalyzer/Core/PathSensitive/CheckerContext.h"
#include "clang/StaticAnalyzer/Core/PathSensitive/ConstraintManager.h"

#include "llvm/Support/raw_ostream.h"

using namespace clang;
using namespace ento;

namespace CI {

    class StaticStringChecker : public Checker<
        check::PreCall,
        check::PreStmt<StringLiteral>> {

        std::unique_ptr<BugType> BT;

    public:

        StaticStringChecker() {
          BT = std::make_unique<BugType>(this, "Get static Strings", "Custom Analyzer");
        }

        void checkPreCall(const CallEvent &, CheckerContext &) const;
        void checkPreStmt(const StringLiteral *DS, CheckerContext &C) const;
    };

}  // namespace


#endif //CI_CHECKERS_STATICSTRING_H
