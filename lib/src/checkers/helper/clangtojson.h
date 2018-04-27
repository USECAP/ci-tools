/**
 * @file clangtojson.cpp
 * @brief A couple of functions to format information from clang objects to
 * JSON.
 *
 * @copyright Copyright (c) 2018 Code Intelligence. All rights reserved.
 */

#pragma once

#include <string>
#include <clang/Basic/SourceLocation.h>
#include <nlohmann/json.hpp>
#include <clang/AST/Decl.h>
#include <type_traits>

/// Helper-type to force specialization
template<typename T>
struct NotSpecialized : std::false_type {};

namespace clang {
  class FunctionDecl;
  class SourceManager;
  class ParmVarDecl;
}

/// Returns a json object from a FunctionDecl
/// @return json object
nlohmann::json ToJson(
    const clang::FunctionDecl *, const clang::SourceManager &);

/// Returns a json list containing the two SourceLocations from the
/// SourceRange
/// @return json list
nlohmann::json ToJson(
    clang::SourceRange, const clang::SourceManager &);

/// Returns a json object from the ParmVarDecl
nlohmann::json ToJson(
    const clang::ParmVarDecl *, const clang::SourceManager &);

namespace Mod {
/// Modifier type. ToJson Functions with this modifier don't print parameter
/// information
struct WithoutParam {
};

} // end of namespace Mod

template<typename Mod>
nlohmann::json ToJson(
    const clang::FunctionDecl *F, const clang::SourceManager &SM) {
  static_assert(NotSpecialized<Mod>::value, "No specialization for this type.\n");
  return {};
}

template<>
nlohmann::json ToJson<Mod::WithoutParam>(
    const clang::FunctionDecl *F, const clang::SourceManager &SM) {
  return {
      {"name", F->getQualifiedNameAsString()},
      {"location", ToJson(F->getSourceRange(), SM)},
  };
}

/// Convenience output operator for llvm's output streams
inline llvm::raw_ostream &operator<<(
    llvm::raw_ostream &out, const nlohmann::json &J) {
  out << J.dump();
  return out;
}
