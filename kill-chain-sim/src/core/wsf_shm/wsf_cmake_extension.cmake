# AFSIM CMake extension for wsf_shm plugin
# Requires AFSIM SDK (WSF_ROOT must point to afsim swdev/core)
set(WSF_EXT_NAME wsf_shm)
if(WSF_PLUGIN_BUILD)
   set(WSF_EXT_TYPE plugin)
endif()
set(WSF_EXT_SOURCE_PATH .)