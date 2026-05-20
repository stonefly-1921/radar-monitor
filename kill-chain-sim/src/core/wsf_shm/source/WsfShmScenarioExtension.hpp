// WsfShmScenarioExtension.hpp
// Shared Memory Command Plugin - AFSIM Scenario Extension
// AFSIM SDK integration: wsf_shm plugin

#ifndef WSF_SHM_SCENARIO_EXTENSION_HPP
#define WSF_SHM_SCENARIO_EXTENSION_HPP

#include "wsf_export.h"

#include <memory>
#include <string>

#include "WsfScenarioExtension.hpp"
#include "WsfSimulationExtension.hpp"

// DIS component interface (must forward-declare, real SDK has it)
namespace wsf { namespace dis { class Component; } }

class WsfSimulation;
class WsfScenario;
class WsfShmComponent;

//! Scenario extension that registers the SHM command processor
class WSF_EXPORT WsfShmScenarioExtension : public WsfScenarioExtension
{
public:
    WsfShmScenarioExtension();
    ~WsfShmScenarioExtension() override = default;

    //! Called when added to a scenario
    void AddedToScenario() override;

    //! Called when a simulation is created from the scenario
    void SimulationCreated(WsfSimulation& aSimulation) override;

    static const std::string cNAME;

private:
    std::unique_ptr<WsfShmComponent> mComponent;
    bool mRegistered;
};

#endif // WSF_SHM_SCENARIO_EXTENSION_HPP