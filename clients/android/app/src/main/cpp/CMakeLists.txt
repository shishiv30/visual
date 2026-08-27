cmake_minimum_required(VERSION 3.22)
project(core_map_jni)

add_library(core_map SHARED
    ${CMAKE_CURRENT_SOURCE_DIR}/../../../../../../native/core_map/core_map.c
    core_map_jni.cpp)
target_include_directories(core_map PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/../../../../../../native/core_map)
target_link_options(core_map PRIVATE "-Wl,-z,max-page-size=16384")
