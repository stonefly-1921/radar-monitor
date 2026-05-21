// WsfShmScenarioExtension.hpp
// Shared Memory Command Plugin - AFSIM Scenario Extension
// Registers the SHM simulation extension with each simulation created from the scenario

#ifndef WSF_SHM_SCENARIO_EXTENSION_HPP
#define WSF_SHM_SCENARIO_EXTENSION_HPP

#include "wsf_export.h"

#include <memory>
#include <string>

#include "WsfScenarioExtension.hpp"

class WsfSimulation;

class WsfShmScenarioExtension : public WsfScenarioExtension
{
public:
    WsfShmScenarioExtension();
    ~WsfShmScenarioExtension() override = default;

    //! Called when added to a scenario
    void AddedToScenario() override;

    //! Called when a simulation is created — registers the SHM simulation extension
    void SimulationCreated(WsfSimulation& aSimulation) override;

    static const std::string cNAME;

private:
    bool mRegistered;
};

#endif // WSF_SHM_SCENARIO_EXTENSION_HPP
