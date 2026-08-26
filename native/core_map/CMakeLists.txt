cmake_minimum_required(VERSION 3.16)
project(core_map C)

add_library(core_map SHARED core_map.c)
target_include_directories(core_map PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
set_target_properties(core_map PROPERTIES C_STANDARD 99 OUTPUT_NAME core_map)

if(WIN32)
  target_compile_definitions(core_map PRIVATE CORE_MAP_EXPORTS)
endif()
