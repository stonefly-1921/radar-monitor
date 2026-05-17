cmake_minimum_required(VERSION 3.14)
project(shared_mem CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

include(FetchContent)
FetchContent_Declare(
    googletest
    URL https://github.com/google/googletest/archive/refs/tags/v1.14.0.zip
)
FetchContent_MakeAvailable(googletest)

enable_testing()

add_library(shared_mem STATIC shm_client.cpp shm_types.h)
target_include_directories(shared_mem PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})

add_executable(test_shm_client tests/unit/test_shm_client.cpp)
target_link_libraries(test_shm_client shared_mem gtest gtest_main)

include(GoogleTest)
gtest_discover_tests(test_shm_client)