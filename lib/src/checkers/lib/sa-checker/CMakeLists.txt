add_library(sa-checker MODULE
        SimpleStreamChecker.cpp
        Heartbleed.cpp
        Checkers.cpp
        StaticString.cpp)

add_dependencies(sa-checker nlohmann_json)

target_include_directories(sa-checker
        INTERFACE ${CMAKE_CURRENT_SOURCE_DIR}
        )

install(TARGETS sa-checker DESTINATION lib/sa-checker)

