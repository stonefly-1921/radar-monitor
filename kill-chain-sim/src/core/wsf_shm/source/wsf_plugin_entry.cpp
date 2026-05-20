// wsf_plugin_entry.cpp
// AFSIM Plugin Entry Point for wsf_shm
//
// SDK analysis findings:
// - Plugin manager calls GetSymbol("WSF_PluginVersion") (with underscore)
// - Function: void WSF_PluginVersion(UtPluginVersion* aOutVersion)
// - UtPluginVersion (MSVC x64 layout, 16 bytes total):
//   uint32_t mMajor (4 bytes) at offset 0
//   uint32_t mMinor (4 bytes) at offset 4
//   const char* mCompilerVersion (8 bytes) at offset 8
// - Compiler string: "win_1916_64bit_release-hwe" (must match MSVC _MSC_VER=1916)

#define WSF_STATIC_DEFINE
#define UT_STATIC_DEFINE

// Mimic MSVC compiler version for ABI compatibility
#ifndef _MSC_VER
#define _MSC_VER 1916
#endif

// Only include what we need - avoids windows.h / COM header conflicts
#include "WsfPlugin.hpp"
#include "WsfPluginManager.hpp"
#include "WsfApplication.hpp"

extern "C" {

    // Primary entry point - AFSIM plugin manager looks up this exact symbol name
    UT_PLUGIN_EXPORT
    void WSF_PluginVersion(UtPluginVersion* aOutVersion)
    {
        if (aOutVersion != nullptr)
        {
            aOutVersion->mMajor = WSF_PLUGIN_API_MAJOR_VERSION;      // 2
            aOutVersion->mMinor = WSF_PLUGIN_API_MINOR_VERSION;      // 9
            aOutVersion->mCompilerVersion = WSF_PLUGIN_API_COMPILER_STRING; // "win_1916_64bit_release-hwe"
        }
    }

    // Secondary entry point - called after successful version check
    UT_PLUGIN_EXPORT
    void WsfPluginSetup(WsfApplication& aApplication)
    {
        (void)aApplication;
        // Note: extensions are registered via WsfModuleInitialize in WsfShmScenarioExtension.cpp
    }

}
