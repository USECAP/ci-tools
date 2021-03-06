
#include "clang/Tooling/CompilationDatabase.h"
#include "llvm/Support/CommandLine.h"
#include "llvm/Support/PrettyStackTrace.h"
#include "llvm/Support/Signals.h"
#include "llvm/Support/raw_ostream.h"

#include <clang/Tooling/Tooling.h>
#include <clang/Tooling/CommonOptionsParser.h>

#include "PrintFunctionsAction.h"

using namespace printfunctions;
using namespace llvm;
using namespace clang;
using namespace clang::tooling;


static cl::OptionCategory printFunctionsCategory{"print-functions options"};

static cl::opt<std::string> directCompiler{cl::Positional,
  cl::desc{"[-- <compiler>"},
  cl::cat{printFunctionsCategory},
  cl::init("")};

static cl::list<std::string> directArgv{cl::ConsumeAfter,
  cl::desc{"<compiler arguments>...]"},
  cl::cat{printFunctionsCategory}};


class CommandLineCompilationDatabase : public clang::tooling::CompilationDatabase {
private:
  clang::tooling::CompileCommand compileCommand;
  std::string sourceFile;

public:
  CommandLineCompilationDatabase(llvm::StringRef sourceFile,
                                 std::vector<std::string> commandLine)
    : compileCommand(".", sourceFile, std::move(commandLine), "dummy.o"),
      sourceFile{sourceFile}
      { }

  std::vector<clang::tooling::CompileCommand>
  getCompileCommands(llvm::StringRef filePath) const override {
    if (filePath == sourceFile) {
      return {compileCommand};
    }
    return {};
  }

  std::vector<std::string>
  getAllFiles() const override {
    return {sourceFile};
  }

  std::vector<clang::tooling::CompileCommand>
  getAllCompileCommands() const override {
    return {compileCommand};
  }
};


std::unique_ptr<clang::tooling::CompilationDatabase>
createDBFromCommandLine(llvm::StringRef compiler,
                        llvm::ArrayRef<std::string> commandLine,
                        std::string &errors) {
  auto source = std::find(commandLine.begin(), commandLine.end(), "-c");
  if (source == commandLine.end() || ++source == commandLine.end()) {
    errors = "Command line must contain '-c <source file>'";
    return {};
  }
  llvm::SmallString<128> absolutePath(*source);
  llvm::sys::fs::make_absolute(absolutePath);

  std::vector<std::string> args;
  if (compiler.endswith("++")) {
    args.emplace_back("c++");
  } else {
    args.emplace_back("cc");
  }

  args.insert(args.end(), commandLine.begin(), commandLine.end());
  return std::make_unique<CommandLineCompilationDatabase>(absolutePath,
                                                          std::move(args));
}

static void
processFile(clang::tooling::CompilationDatabase const &database,
            std::string& file) {
  clang::tooling::ClangTool tool{database, file};
  tool.appendArgumentsAdjuster(clang::tooling::getClangStripOutputAdjuster());
  auto frontendFactory =
    clang::tooling::newFrontendActionFactory<PrintFunctionsAction>();
  tool.run(frontendFactory.get());
}


static void
processDatabase(clang::tooling::CompilationDatabase const &database) {
  auto count = 0;
  auto files = database.getAllFiles();
  llvm::outs() << "Number of files: " << files.size() << "\n";

  for (auto &file : files) {
    llvm::outs() << count << ") File: " << file << "\n";
    processFile(database, file);
    ++count;
  }
}


void
warnAboutDebugBuild(llvm::StringRef programName) {
  const unsigned COLUMNS = 80;
  const char SEPARATOR = '*';

  llvm::outs().changeColor(llvm::raw_ostream::Colors::YELLOW, true);
  for (unsigned i = 0; i < COLUMNS; ++i) {
    llvm::outs().write(SEPARATOR);
  }

  llvm::outs().changeColor(llvm::raw_ostream::Colors::RED, true);
  llvm::outs() << "\nWARNING: ";
  llvm::outs().resetColor();
  llvm::outs() << programName << " appears to have been built in debug mode.\n"
               << "Your analysis may take longer than normal.\n";

  llvm::outs().changeColor(llvm::raw_ostream::Colors::YELLOW, true);
  for (unsigned i = 0; i < COLUMNS; ++i) {
    llvm::outs().write(SEPARATOR);
  }
  llvm::outs().resetColor();
  llvm::outs() << "\n\n";
 }


int
main(int argc, char const **argv) {
  sys::PrintStackTraceOnErrorSignal(argv[0]);
  llvm::PrettyStackTraceProgram X(argc, argv);
  llvm_shutdown_obj shutdown;

  cl::HideUnrelatedOptions(printFunctionsCategory);

  CommonOptionsParser OptionsParser(argc, argv, printFunctionsCategory);

#if !defined(NDEBUG) || defined(LLVM_ENABLE_ASSERTIONS)
  warnAboutDebugBuild(argv[0]);
#endif

  auto &compilationDB = OptionsParser.getCompilations();

  if(compilationDB.getAllFiles().size() == 0){
    llvm::errs() << "Error while trying to load a compilation database:\n";
    return -1;
  }

  processDatabase(compilationDB);

  return 0;
}

