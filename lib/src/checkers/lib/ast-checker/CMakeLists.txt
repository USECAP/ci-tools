add_library(ast-checker-plugin MODULE
        PrintFunctionsAction.cpp
        FunctionFinderAction.cpp
        LocationFinderAction.cpp
        )

add_library(ast-checker SHARED
        PrintFunctionsAction.cpp
        FunctionFinderAction.cpp
        LocationFinderAction.cpp
        )
add_dependencies(ast-checker-plugin helper-lib)
add_dependencies(ast-checker helper-lib)

target_include_directories(ast-checker
        INTERFACE ${CMAKE_CURRENT_SOURCE_DIR}
        PRIVATE $<TARGET_PROPERTY:helper-lib,INTERFACE_INCLUDE_DIRECTORIES>
        )

target_include_directories(ast-checker
        INTERFACE ${CMAKE_CURRENT_SOURCE_DIR}
        PRIVATE ${INTERFACE_INCLUDE_DIRECTORIES}
        )

target_link_libraries(ast-checker
        helper-lib
        )


install(TARGETS ast-checker DESTINATION lib)