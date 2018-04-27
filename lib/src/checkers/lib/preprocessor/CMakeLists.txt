add_library(preprocessor-lib SHARED
        PPContext.cpp
        PPContext.h
        )

target_include_directories(preprocessor-lib
        INTERFACE ${CMAKE_CURRENT_SOURCE_DIR}
        )

install(TARGETS preprocessor-lib DESTINATION lib)


