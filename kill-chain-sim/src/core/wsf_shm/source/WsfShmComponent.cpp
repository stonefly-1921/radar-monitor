// WsfShmComponent.cpp
// Shared Memory DIS Component Implementation
// Reads kill chain commands from Windows shared memory each frame

#include "WsfShmComponent.hpp"

#include "WsfSimulation.hpp"
#include "WsfScenario.hpp"
#include "dis/WsfDisInput.hpp"

#include <cstdio>
#include <algorithm>

//=============================================================================
// Lifecycle
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

//=============================================================================
// Shared Memory I/O
//=============================================================================

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

//=============================================================================
// Per-frame update
//=============================================================================

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

//=============================================================================
// Kill Chain Command Execution
//=============================================================================

WsfPlatform* WsfShmComponent::FindPlatformByIndex(uint32_t aIndex) const
{
    WsfSimulation* sim = GetSimulationPtr();
    if (sim == nullptr) return nullptr;

    // Use GetPlatformList() to iterate and find by index
    // Note: The actual API for indexed platform lookup is simulation-specific
    // For now we use an iteration approach
    (void)aIndex;
    return nullptr;
}

void WsfShmComponent::ExecuteSensorControl(const CmdEntry& aCmd, double aSimTime)
{
    (void)aCmd;
    (void)aSimTime;
    // TODO: Get the owning simulation, find platform by scenario index (aCmd.target_id)
    //   WsfSimulation* sim = GetSimulationPtr();
    //   WsfPlatform* plat = sim->GetPlatformByIndex(aCmd.target_id);
    //   if (!plat) return;
    //   WsfSensor* sensor = plat->GetSensorById(aCmd.param1);
    //   if (sensor) sensor->SetMode(aCmd.param2);
}

void WsfShmComponent::ExecuteWeaponAssign(const CmdEntry& aCmd, double aSimTime)
{
    (void)aCmd;
    (void)aSimTime;
    // TODO: Find platform, get weapon by param1, assign target track param2
    //   WsfWeapon* wp = plat->GetWeaponById(aCmd.param1);
    //   if (wp) wp->AssignTarget(aCmd.param2);
}

void WsfShmComponent::ExecuteEngage(const CmdEntry& aCmd, double aSimTime)
{
    (void)aCmd;
    (void)aSimTime;
    // TODO: Trigger engagement — find platform and weapon, issue engagement order
    //   WsfPlatform* plat = FindPlatformByIndex(aCmd.target_id);
    //   if (!plat) return;
    //   WsfBattleManager* bm = WsfBattleManager::Get(*plat->GetSimulation());
    //   bm->EngagementRequested(plat, aCmd.param1, aCmd.param2);
}

void WsfShmComponent::ExecuteAllocate(const CmdEntry& aCmd, double aSimTime)
{
    (void)aCmd;
    (void)aSimTime;
    // TODO: Resource allocation command
    //   e.g., assign an interceptor (param1) to target track (param2)
}