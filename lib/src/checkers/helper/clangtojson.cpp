#include "clangtojson.h"
#include <clang/AST/AST.h>
using namespace nlohmann;
using namespace clang;

namespace {

std::vector<json> createParameterObjects(const FunctionDecl *F,
                                         const SourceManager &SM) {
  std::vector<json> params;
  params.reserve(F->param_size());
  std::transform(F->param_begin(), F->param_end(), std::back_inserter(params),
                 [&](ParmVarDecl *P) -> nlohmann::json {
                   return ToJson(P, SM);
                 });
  return params;
}

} // end anonymous namespace

json ToJson(const FunctionDecl *F, const SourceManager &SM) {
  return {
      {"name", F->getQualifiedNameAsString()},
      {"visible", F->getVisibility()},
      {"location", ToJson(F->getSourceRange(), SM)},
      {"parameters", createParameterObjects(F, SM)}
  };
}

json ToJson(SourceRange SR, const SourceManager &SM) {
  return {SR.getBegin().printToString(SM), SR.getEnd().printToString(SM)};
}

json ToJson(const ParmVarDecl *P, const SourceManager &SM) {
  return {
      {"name", P->getQualifiedNameAsString()},
      {"type", P->getType().getAsString()},
      {"location", ToJson(P->getSourceRange(), SM)}
  };
}
