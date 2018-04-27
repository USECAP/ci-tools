#include <algorithm>

#include <clang/Frontend/CompilerInstance.h>
#include <clang/Frontend/FrontendPluginRegistry.h>
#include <clang/AST/RecursiveASTVisitor.h>

#include "PrintFunctionsAction.h"
#include "clangtojson.h"

using namespace printfunctions;
using namespace clang;

static clang::FrontendPluginRegistry::Add<PrintFunctionsAction> X(
    "function-printer-demo", "Print the names of functions inside the file.");

class FunctionNameVisitor
    : public clang::RecursiveASTVisitor<FunctionNameVisitor> {
public:
  FunctionNameVisitor(SourceManager *SM, llvm::StringRef InFile)
      : SM(SM), InFile(InFile) {}
  ~FunctionNameVisitor() { llvm::outs() << JsonObject << "\n"; }

  bool VisitFunctionDecl(clang::FunctionDecl *F) {
    if (SM->getFilename(F->getLocation()) == InFile) {
      JsonObject.push_back(ToJson(F, *SM));
    }
    return true;
  }

private:
  nlohmann::json JsonObject;
  SourceManager *SM;
  std::string InFile;
};

void PrintFunctionsAction::EndSourceFileAction() {
  auto &ci = getCompilerInstance();
  auto &context = ci.getASTContext();

  auto &input = getCurrentInput();
  std::string InFile = input.getFile();
  llvm::outs() << "Filename in Action: " << InFile << "\n";

  auto *unit = context.getTranslationUnitDecl();
  FunctionNameVisitor visitor(&ci.getSourceManager(), InFile);
  visitor.TraverseDecl(unit);

  clang::ASTFrontendAction::EndSourceFileAction();
}
