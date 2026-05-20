# wsf_shm - Shared Memory Command Plugin for AFSIM
# Reads kill chain commands from Windows shared memory and executes them in AFSIM

cmake_minimum_required(VERSION 3.14)
project(wsf_shm)

# This plugin integrates with AFSIM's WSF framework via the SDK
# It provides DIS-compatible component for reading shared memory commands
# and executing them as platform sensor/weapon operations

FILE(GLOB SRCS source/*.cpp)
FILE(GLOB HDRS source/*.hpp)

wsf_project_template(${PROJECT_NAME} PLUGIN
    SRCS ${SRCS}
    HDRS ${HDRS}
)

install_sources(source wsf_plugins/${PROJECT_NAME})
install_source_files(wsf_module wsf_plugins)
install_source_files(wsf_cmake_extension.cmake wsf_plugins/${PROJECT_NAME})
install_source_files(NO_EXPORT.md wsf_plugins/${PROJECT_NAME})
install_source_files(README.md wsf_plugins/${PROJECT_NAME})