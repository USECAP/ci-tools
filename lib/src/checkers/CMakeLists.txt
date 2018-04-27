project(ci-checkers)
cmake_minimum_required(VERSION 3.8)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(PACKAGE_NAME ci-checkers)
set(PACKAGE_VERSION 0.1)
set(PACKAGE_STRING "${PACKAGE_NAME} ${PACKAGE_VERSION}")
set(PACKAGE_BUGREPORT "bugs@code-intelligence.info")

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -std=c++14 -fno-rtti -fno-omit-frame-pointer -Wno-unused-function")

set(CMAKE_RUNTIME_OUTPUT_DIRECTORY "${PROJECT_BINARY_DIR}/bin")
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY "${PROJECT_BINARY_DIR}/lib")
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY "${PROJECT_BINARY_DIR}/lib")

list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake")

# Configure LibClangTooling
find_package(LibClangTooling REQUIRED)
include_directories(${LibClangTooling_INCLUDE_DIRS})

include(ExternalProject)

############## JSON CONFIGURATION ######################################################################################
set(JSON_URL https://github.com/nlohmann/json/releases/download/v3.1.2/include.zip)
set(JSON_SHA256 495362ee1b9d03d9526ba9ccf1b4a9c37691abe3a642ddbced13e5778c16660c)
ExternalProject_Add(nlohmann_json
        URL ${JSON_URL}
        URL_HASH SHA256=${JSON_SHA256}
        CONFIGURE_COMMAND ""
        BUILD_COMMAND ""
        INSTALL_COMMAND ""
        LOG_DOWNLOAD ON
        )
ExternalProject_Get_Property(nlohmann_json source_dir)
set(JSONIncludeDir ${source_dir})
message(${JSONIncludeDir})
########################################################################################################################

find_package(LLVM 6.0 REQUIRED CONFIG HINTS ${LLVM_DIR})
message(STATUS "Found LLVM ${LLVM_PACKAGE_VERSION}")
message(STATUS "Using LLVMConfig.cmake in: ${LLVM_DIR}")
list(APPEND CMAKE_MODULE_PATH "${LLVM_CMAKE_DIR}")
include(AddLLVM)

# LLVM_DIR must be set to the prefix of /share/llvm/cmake via commandline
find_package(Clang REQUIRED)

option(LLVM_ENABLE_CXX1Y  "Enable C++1Y" ON)
option(LLVM_INCLUDE_TOOLS "Generate build targets for the LLVM tools." ON)
option(LLVM_ENABLE_PLUGINS "Generate build targets for LLVM plugins." ON)
option(LLVM_BUILD_TOOLS
        "Build the LLVM tools. If OFF, just generate build targets." ON)

message("LLVM STATUS:
  Definitions ${LLVM_DEFINITIONS}
  Includes    ${LLVM_INCLUDE_DIRS}
              ${CLANG_INCLUDE_DIRS}
  Libraries   ${LLVM_LIBRARY_DIRS}")

# Now set the LLVM header and library paths:
include_directories(SYSTEM ${LLVM_INCLUDE_DIRS} ${CLANG_INCLUDE_DIRS})
link_directories(${LLVM_LIBRARY_DIRS})
add_definitions(${LLVM_DEFINITIONS})

############## FINAL PROJECT CONFIG #################

# And the project header and library paths
include_directories(${CMAKE_SOURCE_DIR}/include ${CMAKE_SOURCE_DIR}/helper ${JSONIncludeDir})
link_directories(${LIBRARY_OUTPUT_PATH})
set(CMAKE_TEMP_LIBRARY_PATH "${PROJECT_BINARY_DIR}/lib")

add_subdirectory(helper)
add_subdirectory(lib)
add_subdirectory(tools)
add_subdirectory(test)


