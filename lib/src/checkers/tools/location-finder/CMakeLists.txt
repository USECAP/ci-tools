add_executable( location-finder
                main.cpp
        )

if (LLVM_ENABLE_ASSERTIONS)
    add_definitions(-DLLVM_ENABLE_ASSERTIONS=${LLVM_ENABLE_ASSERTIONS})
endif()

llvm_map_components_to_libnames(REQ_LLVM_LIBRARIES ${LLVM_TARGETS_TO_BUILD}
        core support option
        )

target_link_libraries(location-finder
        ast-checker
        preprocessor-lib
        ${LibClangTooling_LIBRARIES}
        ${REQ_LLVM_LIBRARIES}
        )

target_include_directories(location-finder
        PRIVATE $<TARGET_PROPERTY:ast-checker,INTERFACE_INCLUDE_DIRECTORIES>
        )

# Platform dependencies.
if( WIN32 )
    find_library(SHLWAPI_LIBRARY shlwapi)
    target_link_libraries(location-finder
            ${SHLWAPI_LIBRARY}
            )
else()
    find_package(Threads REQUIRED)
    find_package(Curses REQUIRED)
    target_link_libraries(location-finder
            ${CMAKE_THREAD_LIBS_INIT}
            ${CMAKE_DL_LIBS}
            ${CURSES_LIBRARIES}
            )
endif()

set_target_properties(location-finder
        PROPERTIES
        LINKER_LANGUAGE CXX
        PREFIX ""
        )

install(TARGETS location-finder
        RUNTIME DESTINATION bin
        )
