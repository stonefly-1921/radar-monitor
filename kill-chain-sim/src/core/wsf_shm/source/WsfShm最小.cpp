// WsfShm最小.cpp
// 最小的 AFSIM 插件 - 只实现 WsfScenarioExtension
#include "wsf_export.h"
#include "WsfScenarioExtension.hpp"
#include "WsfApplicationExtension.hpp"
#include <windows.h>
#include <stdio.h>

// Application Extension - 每个 scenario 创建时调用
class WsfShmAppExtension : public WsfApplicationExtension {
public:
    void ScenarioCreated(WsfScenario& aScenario) override;
    void AddedToApplication(WsfApplication& aApplication) override;
};

// Scenario Extension - 实际处理
class WsfShmScenarioExtension : public WsfScenarioExtension {
public:
    void SimulationCreated(WsfSimulation& aSimulation) override;
    bool ProcessInput(UtInput& aInput) override;
};

static WsfShmScenarioExtension* g_instance = nullptr;

void WsfShmAppExtension::AddedToApplication(WsfApplication& aApplication) {
    // nothing
}

void WsfShmAppExtension::ScenarioCreated(WsfScenario& aScenario) {
    // 注册 scenario extension
    aScenario.RegisterExtension("shm", ut::make_unique<WsfShmScenarioExtension>());
}

void WsfShmScenarioExtension::SimulationCreated(WsfSimulation& aSimulation) {
    // Simulation 级别初始化
    OutputDebugStringA("[WsfShm] SimulationCreated\n");
}

bool WsfShmScenarioExtension::ProcessInput(UtInput& aInput) {
    // 从 scenario 文件读取 shm 配置
    if (aInput.GetName() == "shm") {
        OutputDebugStringA("[WsfShm] ProcessInput: shm\n");
        return true;
    }
    return false;
}

// Application Extension 实例
extern "C" __declspec(dllexport)
WsfApplicationExtension* WsfShmPlugin(WsfApplication& aApplication) {
    OutputDebugStringA("[WsfShm] WsfShmPlugin called\n");
    return new WsfShmAppExtension();
}
