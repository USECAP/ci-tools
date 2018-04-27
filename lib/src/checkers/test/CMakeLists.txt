project(ci-checkers-tests)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

#add_library(testlib
# files.c
#  functions.c
#)

enable_testing()
find_package(GTest REQUIRED)

set(CMAKE_CXX_FLAGS_DEBUG "${CMAKE_CXX_FLAGS_DEBUG} -fno-omit-frame-pointer -fsanitize=address")
set(CMAKE_LINKER_FLAGS_DEBUG "${CMAKE_STATIC_LINKER_FLAGS_DEBUG} -fno-omit-frame-pointer -fsanitize=address")

if (LLVM_ENABLE_ASSERTIONS)
    add_definitions(-DLLVM_ENABLE_ASSERTIONS=${LLVM_ENABLE_ASSERTIONS})
endif()

llvm_map_components_to_libnames(REQ_LLVM_LIBRARIES ${LLVM_TARGETS_TO_BUILD}
        core support option
        )

add_executable(ast-checker-test ast-checker-test.cpp)

target_link_libraries(ast-checker-test
        GTest::GTest
        GTest::Main
        ast-checker
        preprocessor-lib
        ${LibClangTooling_LIBRARIES}
        ${REQ_LLVM_LIBRARIES}
        )


target_include_directories(ast-checker-test
        PRIVATE $<TARGET_PROPERTY:ast-checker,INTERFACE_INCLUDE_DIRECTORIES>
        )

add_test(NAME gtest-suite-ast-checker COMMAND ast-checker-test)



