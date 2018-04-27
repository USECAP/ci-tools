add_library(helper-lib SHARED
        clangtojson.cpp
        clangtojson.h
        )
add_dependencies(helper-lib nlohmann_json)

target_include_directories(helper-lib
        INTERFACE ${CMAKE_CURRENT_SOURCE_DIR}
        )

install(TARGETS helper-lib DESTINATION lib)

