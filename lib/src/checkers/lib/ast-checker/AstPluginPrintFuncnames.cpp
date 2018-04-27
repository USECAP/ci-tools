//------------------------------------------------------------------------------
// plugin_print_funcnames Clang sample. Demonstrates:
//
// * How to create a Clang plugin.
// * How to use AST actions to access the AST of the parsed code.
//
// Once the .so is built, it can be loaded by Clang. For example:
//
// $ clang -cc1 -load build/plugin_print_funcnames.so -plugin print-fns <cfile>
//
// Taken from the Clang distribution. LLVM's license applies.
//------------------------------------------------------------------------------
#include <algorithm>
#include "clang/AST/AST.h"
#include "clang/AST/ASTConsumer.h"
#include "clang/Frontend/CompilerInstance.h"
#include "clang/Frontend/FrontendPluginRegistry.h"
#include "llvm/Support/Format.h"

using namespace clang;

namespace {

/**
 * This class takes the top-level declarations in a source code file and exports
 * them in JSON
 */
class PrintFunctionsConsumer : public ASTConsumer {
 public:
  /**
   * The function consumer needs to be instantiated with:
   * @param SM SourceManager coming from the CompilerInstance from the ASTAction
   * @param InFile The current input file
   */
  PrintFunctionsConsumer(SourceManager *SM, llvm::StringRef InFile) : SM(SM) {
    this->InFile = InFile;
    llvm::outs() << "[\n";
  }
  ~PrintFunctionsConsumer() override { llvm::outs() << "]\n"; }

  /**
   * HandleTopLevelDecl implementation for an ASTConsumer - Handle the specified
   * top-level declaration.  This is called by the parser to process every
   * top-level Decl*.
   *
   * @param DG
   * @return true to continue parsing, or false to abort parsing
   */
  bool HandleTopLevelDecl(DeclGroupRef DG) override {
    for (auto D : DG) {
      if (SM->getFilename(D->getLocation()) == InFile && D->isFunctionOrFunctionTemplate()) {
        auto ND = D->getAsFunction();
        writeFunctionOutput(
            ND->getQualifiedNameAsString(), ND->getVisibility() == true,
            ND->getSourceRange().getBegin().printToString(*SM),

            ND->parameters(), ND->param_begin(), ND->param_end());
      }
    }

    return true;
  }

  void writeFunctionOutput(llvm::StringRef fname, bool visibility,
                           llvm::StringRef location,
                           llvm::ArrayRef<ParmVarDecl *> parameters,
                           FunctionDecl::param_iterator begin,
                           FunctionDecl::param_iterator end) {
    if (empty)
      empty = false;
    else
      llvm::outs() << ",";

    std::vector<std::string> params;
    std::transform(begin, end, std::back_inserter(params),
                   [](ParmVarDecl *param) -> std::string {
                     return param->getQualifiedNameAsString();
                   });
    std::string json_array = llvm::join(params, ",\n\t\t");

    llvm::outs() << llvm::format(
        "\n{\n\t\"name\": %s,\n"
        "\t\"visible\": %d,\n"
        "\t\"location\": %s,\n"
        "\t\"parameters\": [\n\t\t%s\n\t]\n}",
        fname.str().c_str(), visibility, location.str().c_str(),
        json_array.c_str(), json_array.c_str());
  }

 private:
  SourceManager *SM;
  std::string InFile;
  bool empty = true;
};

class PrintFunctionNamesAction : public PluginASTAction {
 protected:
  std::unique_ptr<ASTConsumer> CreateASTConsumer(
      CompilerInstance &CI, llvm::StringRef InFile) override {
    CI.getPreprocessor().SetSuppressIncludeNotFoundError(true);
    CI.getDiagnostics().setSuppressAllDiagnostics(true);
    return llvm::make_unique<PrintFunctionsConsumer>(&CI.getSourceManager(),
                                                     InFile);
  }

  bool ParseArgs(const CompilerInstance &CI,
                 const std::vector<std::string> &args) override {
    for (unsigned long i = 0, e = args.size(); i != e; ++i) {
      llvm::errs() << "PrintFunctionNames arg = " << args[i] << "\n";

      // Example error handling.
      if (args[i] == "-an-error") {
        DiagnosticsEngine &D = CI.getDiagnostics();
        unsigned DiagID = D.getCustomDiagID(DiagnosticsEngine::Error,
                                            "invalid argument '%0'");
        D.Report(DiagID) << args[i];
        return false;
      }
    }
    if (!args.empty() && args[0] == "help") PrintHelp(llvm::errs());

    return true;
  }
  void PrintHelp(llvm::raw_ostream &ros) {
    ros << "Help for PrintFunctionNames plugin goes here\n";
  }
};
}  // namespace

static FrontendPluginRegistry::Add<PrintFunctionNamesAction> X(
    "print-fns", "print function names");
