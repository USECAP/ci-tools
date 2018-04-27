FIND_PROGRAM(LLVM_CONFIG_TOOL NAMES llvm-config-6.0 llvm-config)
if (NOT LLVM_CONFIG_TOOL)
    message(FATAL_ERROR "llvm-config not found!")
endif ()

execute_process(
        COMMAND ${LLVM_CONFIG_TOOL} --cxxflags
        OUTPUT_VARIABLE LLVM_DEFINITIONS)

execute_process(
        COMMAND ${LLVM_CONFIG_TOOL} --includedir
        OUTPUT_VARIABLE LLVM_INCLUDE_DIR
        OUTPUT_STRIP_TRAILING_WHITESPACE)

execute_process(
        COMMAND ${LLVM_CONFIG_TOOL} --libdir
        OUTPUT_VARIABLE LLVM_LIB_DIR
        OUTPUT_STRIP_TRAILING_WHITESPACE)

execute_process(
        COMMAND ${LLVM_CONFIG_TOOL} --version
        OUTPUT_VARIABLE LLVM_VERSION
        OUTPUT_STRIP_TRAILING_WHITESPACE)

execute_process(
        COMMAND ${LLVM_CONFIG_TOOL} --system-libs
        OUTPUT_VARIABLE LLVM_SYSTEM_LIBS
        OUTPUT_STRIP_TRAILING_WHITESPACE)

execute_process(
        COMMAND ${LLVM_CONFIG_TOOL} --libs
        OUTPUT_VARIABLE LLVM_LIBS
        OUTPUT_STRIP_TRAILING_WHITESPACE)

set(LLVM_LIBRARIES ${LLVM_LIBS} ${LLVM_SYSTEM_LIBS})
set(LLVM_INCLUDE_DIRS ${LLVM_INCLUDE_DIR})
set(LLVM_DEFINITIONS ${LLVM_DEFINITIONS} "-fno-rtti")

include(FindPackageHandleStandardArgs)
find_package_handle_standard_args(LLVM DEFAULT_MSG LLVM_LIBRARIES LLVM_INCLUDE_DIRS)
