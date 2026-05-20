// WsfShmScenarioExtension.cpp
// Shared Memory Command Plugin - AFSIM Scenario Extension
// Reads kill chain commands from Windows shared memory

#include "WsfShmScenarioExtension.hpp"

#include "WsfSimulation.hpp"
#include "WsfScenario.hpp"
#include "WsfShmComponent.hpp"

#include <windows.h>
#include <cstdio>
#include <cstring>
#include <algorithm>

const std::string WsfShmScenarioExtension::cNAME = "wsf_shm";

//=============================================================================
// WsfShmComponent — reads commands from shared memory each frame
//=============================================================================

WsfShmComponent::WsfShmComponent()
    : WsfDisComponent(),
      mShmBase(nullptr),
      mLastCmdIn(0),
      mUpdateCount(0),
      mDebug(true)
{
}

WsfShmComponent::~WsfShmComponent()
{
    CloseShm();
}

WsfComponent* WsfShmComponent::CloneComponent() const
{
    return new WsfShmComponent(*this);
}

WsfStringId WsfShmComponent::GetComponentName() const
{
    static WsfStringId id("WSF_SHM");
    return id;
}

const int* WsfShmComponent::GetComponentRoles() const
{
    static int roles[] = { 0 };
    return roles;
}

void* WsfShmComponent::QueryInterface(int aRole)
{
    (void)aRole;
    return nullptr;
}

bool WsfShmComponent::OpenShm()
{
    if (mShmBase != nullptr) return true;

    char path[256];
    snprintf(path, sizeof(path), "Global\\%s", SHM_NAME);
    HANDLE h = OpenFileMappingA(FILE_MAP_READ | FILE_MAP_WRITE, FALSE, path);
    if (!h) {
        if (mDebug) OutputDebugStringA("[WSF_SHM] OpenFileMapping failed\n");
        return false;
    }
    mShmBase = MapViewOfFile(h, FILE_MAP_READ | FILE_MAP_WRITE, 0, 0, 0);
    CloseHandle(h);
    if (!mShmBase) {
        if (mDebug) OutputDebugStringA("[WSF_SHM] MapViewOfFile failed\n");
        return false;
    }
    if (mDebug) OutputDebugStringA("[WSF_SHM] opened SHM\n");
    return true;
}

void WsfShmComponent::CloseShm()
{
    if (mShmBase) {
        UnmapViewOfFile(mShmBase);
        mShmBase = nullptr;
    }
}

void WsfShmComponent::PrepareComponent(double aSimTime)
{
    (void)aSimTime;
    mUpdateCount++;
    if (mUpdateCount % 100 != 0) return;
    if (!OpenShm()) return;

    ShmHeader hdr;
    memcpy(&hdr, mShmBase, sizeof(ShmHeader));

    if (mDebug) {
        char buf[256];
        snprintf(buf, sizeof(buf),
            "[WSF_SHM] t=%.1f tracks=%u cmd_in=%u\n",
            aSimTime, hdr.track_count, hdr.cmd_in);
        OutputDebugStringA(buf);
    }

    if (hdr.cmd_in != mLastCmdIn) {
        ProcessNewCommands(aSimTime);
        mLastCmdIn = hdr.cmd_in;
    }
}

void WsfShmComponent::ProcessNewCommands(double aSimTime)
{
    if (!mShmBase) return;
    ShmHeader hdr;
    memcpy(&hdr, mShmBase, sizeof(ShmHeader));

    uint32_t newCount = hdr.cmd_in - mLastCmdIn;
    if (newCount > MAX_CMDS) newCount = MAX_CMDS;
    if (newCount == 0) return;

    if (mDebug) {
        char buf[128];
        snprintf(buf, sizeof(buf), "[WSF_SHM] %u new commands\n", newCount);
        OutputDebugStringA(buf);
    }

    for (uint32_t i = 0; i < newCount; i++) {
        uint32_t idx = (mLastCmdIn + i) % MAX_CMDS;
        CmdEntry cmd;
        memcpy(&cmd, (uint8_t*)mShmBase + CMD_OFFSET + idx * sizeof(CmdEntry), sizeof(CmdEntry));

        if (mDebug) {
            char buf[512];
            snprintf(buf, sizeof(buf),
                "[WSF_SHM] CMD type=%u target=%u param1=%u param2=%u desc='%.64s'\n",
                cmd.type, cmd.target_id, cmd.param1, cmd.param2, cmd.description);
            OutputDebugStringA(buf);
        }

        // Execute the command
        switch (cmd.type) {
        case 1: ExecuteSensorControl(cmd, aSimTime); break;
        case 2: ExecuteWeaponAssign(cmd, aSimTime); break;
        case 3: ExecuteEngage(cmd, aSimTime); break;
        case 4: ExecuteAllocate(cmd, aSimTime); break;
        default: break;
        }
    }

    // Acknowledge processed commands
    hdr.cmd_out = hdr.cmd_in;
    memcpy(mShmBase, &hdr, sizeof(ShmHeader));
}

void WsfShmComponent::ExecuteSensorControl(const CmdEntry& aCmd, double aSimTime)
{
    (void)aCmd;
    (void)aSimTime;
    // TODO: Use GetSimulation().FindPlatform(aCmd.target_id)
    // Then: sensor = platform->GetSensorById(aCmd.param1); sensor->SetMode(aCmd.param2);
}

void WsfShmComponent::ExecuteWeaponAssign(const CmdEntry& aCmd, double aSimTime)
{
    (void)aCmd;
    (void)aSimTime;
    // TODO: Use GetSimulation().FindPlatform(aCmd.target_id)
    // Then: weapon = platform->GetWeaponById(aCmd.param1); weapon->AssignTarget(aCmd.param2);
}

void WsfShmComponent::ExecuteEngage(const CmdEntry& aCmd, double aSimTime)
{
    (void)aCmd;
    (void)aSimTime;
    // TODO: Trigger engagement via GetSimulation().FindPlatform(aCmd.target_id)
}

void WsfShmComponent::ExecuteAllocate(const CmdEntry& aCmd, double aSimTime)
{
    (void)aCmd;
    (void)aSimTime;
    // TODO: Resource allocation command
}

//=============================================================================
// WsfShmScenarioExtension — registers with AFSIM scenario
//=============================================================================

WsfShmScenarioExtension::WsfShmScenarioExtension()
    : WsfScenarioExtension(),
      mComponent(nullptr),
      mRegistered(false)
{
    InitializeExtensionName("wsf_shm");
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

    // Create the SHM DIS component
    mComponent = std::make_unique<WsfShmComponent>();

    // Cast simulation to DIS interface and add our component
    // WsfSimulation inherits from WsfDisInterface, so this cast is safe
    WsfDisInterface* disIf = static_cast<WsfDisInterface*>(&aSimulation);
    if (disIf) {
        disIf->AddComponent(mComponent.get());
        OutputDebugStringA("[WSF_SHM] Component added to DIS interface\n");
    } else {
        OutputDebugStringA("[WSF_SHM] WARNING: cannot cast simulation to WsfDisInterface\n");
    }

    // Release ownership — simulation now owns the component
    (void)mComponent.release();
}

//=============================================================================
// Module entry point
//=============================================================================

extern "C" {

    WSF_EXPORT
    void WsfModuleInitialize(const WsfScenario* aScenarioPtr)
    {
        if (aScenarioPtr == nullptr) return;
        OutputDebugStringA("[WSF_SHM] WsfModuleInitialize called\n");

        auto ext = std::make_unique<WsfShmScenarioExtension>();
        const_cast<WsfScenario*>(aScenarioPtr)->RegisterExtension(
            WsfShmScenarioExtension::cNAME, std::move(ext));
    }

    WSF_EXPORT
    WsfScenarioExtension* wsf_module_create(const char* aName)
    {
        (void)aName;
        OutputDebugStringA("[WSF_SHM] wsf_module_create called\n");
        return new WsfShmScenarioExtension();
    }
}