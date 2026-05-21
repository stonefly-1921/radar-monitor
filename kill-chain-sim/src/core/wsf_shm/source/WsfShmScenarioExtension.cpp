// WsfShmScenarioExtension.cpp
// Shared Memory Command Plugin - AFSIM Scenario Extension
// Registers the SHM simulation extension when a simulation is created

#include "WsfShmScenarioExtension.hpp"

#include "WsfSimulation.hpp"
#include "WsfScenario.hpp"
#include "WsfShmSimulationExtension.hpp"
#include "WsfApplicationExtension.hpp"
#include "WsfPlugin.hpp"

#include <windows.h>
#include <cstdio>

const std::string WsfShmScenarioExtension::cNAME = "wsf_shm";

WsfShmScenarioExtension::WsfShmScenarioExtension()
    : WsfScenarioExtension()
    , mRegistered(false)
{
}

void WsfShmScenarioExtension::AddedToScenario()
{
    // Nothing needed here
}

void WsfShmScenarioExtension::SimulationCreated(WsfSimulation& aSimulation)
{
    WsfScenarioExtension::SimulationCreated(aSimulation);

    if (mRegistered) return;
    mRegistered = true;

    // Register the SHM simulation extension with this simulation
    aSimulation.RegisterExtension("wsf_shm_sim",
        ut::make_unique<WsfShmSimulationExtension>());

    OutputDebugStringA("[WSF_SHM] SimulationCreated - SHM extension registered\n");
    (void)aSimulation;
}

//=============================================================================
// AFSIM Plugin Entry Point — REQUIRED by WsfPluginManager
//=============================================================================

#include "UtPlugin.hpp"
#include "WsfApplication.hpp"

namespace
{
class ApplicationExtension : public WsfApplicationExtension
{
public:
    ApplicationExtension()
    {
        // Set the extension name
    }

    void ScenarioCreated(WsfScenario& aScenario) override
    {
        aScenario.RegisterExtension(WsfShmScenarioExtension::cNAME,
            ut::make_unique<WsfShmScenarioExtension>());
    }
};
} // namespace

extern "C" {

    WSF_EXPORT
    void WsfPluginVersion(UtPluginVersion& aOutVersion)
    {
        aOutVersion = UtPluginVersion(WSF_PLUGIN_API_MAJOR_VERSION,
                                      WSF_PLUGIN_API_MINOR_VERSION,
                                      WSF_PLUGIN_API_COMPILER_STRING);
    }

    WSF_EXPORT
    void WsfPluginSetup(WsfApplication& aApp)
    {
        OutputDebugStringA("[WSF_SHM] WsfPluginSetup called\n");
        if (!aApp.ExtensionIsRegistered("wsf_shm")) {
            aApp.RegisterExtension("wsf_shm",
                ut::make_unique<ApplicationExtension>());
        }
    }

} // extern "C"
