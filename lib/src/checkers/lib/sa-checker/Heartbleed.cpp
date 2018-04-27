#include "Heartbleed.h"

  using namespace CI;

// checker logic
bool NetworkTaintChecker::isArgUnConstrained(Optional<NonLoc> Arg,
                                             SValBuilder &builder,
                                             ProgramStateRef state) const {
  bool result = false;

  if (Arg) {
    // so 5000 is chosen as an arbitrary value. reall what we should do is
    // compare the range on the value with the range of the memory object
    // pointed to by either the base pointer, in an array dereference, or the
    // first and second parameters to memcpy, in a call to memcpy. however,
    // frequently this information is opaque to the analyzer. what I mostly
    // wanted to answer was, show me locations in the code where NO constraints,
    // practically, had been applied to the size. this would still permit
    // technically incorrect constraints to be passed, so there is room for
    // improvement, but I think that generally, something sound is unattainable
    // here so we just do what we can in the time allotted
    llvm::APInt V(32, 5000);
    SVal Val = builder.makeIntVal(V, false);

    Optional<NonLoc> NLVal = Val.getAs<NonLoc>();

    if (!NLVal) {
      return result;
    }

    SVal cmprLT = builder.evalBinOpNN(state, BO_GT, *Arg, *NLVal,
                                      builder.getConditionType());

    Optional<NonLoc> NLcmprLT = cmprLT.getAs<NonLoc>();

    if (!NLcmprLT) {
      return result;
    }

    std::pair<ProgramStateRef, ProgramStateRef> p = state->assume(*NLcmprLT);

    ProgramStateRef trueState = p.first;

    if (trueState) {
      result = true;
    }
  }

  return result;
}

// check memcpy / memset calls
void NetworkTaintChecker::checkPreCall(const CallEvent &Call,
                                       CheckerContext &C) const {
  ProgramStateRef State = C.getState();
  const IdentifierInfo *ID = Call.getCalleeIdentifier();

  if (ID == nullptr) {
    return;
  }

  if (ID->getName() == "memcpy") {
    // check if the 3rd argument is tainted and constrained
    SVal SizeArg = Call.getArgSVal(2);
    ProgramStateRef state = C.getState();

    if (state->isTainted(SizeArg)) {
      SValBuilder &svalBuilder = C.getSValBuilder();
      Optional<NonLoc> SizeArgNL = SizeArg.getAs<NonLoc>();

      if (this->isArgUnConstrained(SizeArgNL, svalBuilder, state)) {
        ExplodedNode *loc = C.generateErrorNode(state);
        if (loc) {
          C.emitReport(std::make_unique<BugReport>(
              *this->BT, "Tainted, unconstrained value used in memcpy size",
              loc));
        }
      }
    }
  }
}

// also check address arithmetic
void NetworkTaintChecker::checkLocation(SVal l, bool isLoad, const Stmt *LoadS,
                                        CheckerContext &C) const {
  const MemRegion *R = l.getAsRegion();
  if (!R) {
    return;
  }

  const auto *ER = dyn_cast<ElementRegion>(R);
  if (!ER) {
    return;
  }

  auto Idx = ER->getIndex().castAs<DefinedOrUnknownSVal>();
  ProgramStateRef state = C.getState();

  if (state->isTainted(Idx)) {
    SValBuilder &svalBuilder = C.getSValBuilder();

    Optional<NonLoc> idxNL = Idx.getAs<NonLoc>();

    if (this->isArgUnConstrained(idxNL, svalBuilder, state)) {
      // report a bug!
      ExplodedNode *loc = C.generateErrorNode(state);
      if (loc) {
        C.emitReport(std::make_unique<BugReport>(
            *this->BT, "Tainted, unconstrained value used in array index",
            loc));
      }
    }
  }
}

// check for htonl/htons
void NetworkTaintChecker::checkPostCall(const CallEvent &Call,
                                        CheckerContext &C) const {
  // is htons or htonl?
  const IdentifierInfo *ID = Call.getCalleeIdentifier();

  if (ID == nullptr) {
    return;
  }

  if (ID->getName() == "ntohl" || ID->getName() == "xyzzy" ||
      ID->getName() == "ntohs") {
    ProgramStateRef State = C.getState();
    // taint the value written to by this call
    SymbolRef Sym = Call.getReturnValue().getAsSymbol();

    if (Sym) {
      ProgramStateRef newState = State->addTaint(Sym);
      C.addTransition(newState);
    }
  }
}

