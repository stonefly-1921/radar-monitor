// WsfShmSimulationExtension.cpp
// Shared Memory Command Plugin - AFSIM Simulation Extension
// Per-frame polling of shared memory commands

#include "WsfShmSimulationExtension.hpp"

#include "WsfSimulation.hpp"
#include <windows.h>
#include <cstdio>
#include <cstring>

WsfShmSimulationExtension::WsfShmSimulationExtension()
    : mShmBase(nullptr)
    , mLastCmdIn(0)
    , mUpdateCount(0)
    , mDebug(true)
{
}

bool WsfShmSimulationExtension::OpenShm()
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

bool WsfShmSimulationExtension::PrepareExtension()
{
    mUpdateCount++;
    if (mUpdateCount % 100 != 0) return true;

    double simTime = GetSimulation().GetSimTime();

    if (!OpenShm()) return true;

    ShmHeader hdr;
    memcpy(&hdr, mShmBase, sizeof(ShmHeader));

    if (mDebug) {
        char buf[256];
        snprintf(buf, sizeof(buf),
            "[WSF_SHM] t=%.1f tracks=%u cmd_in=%u\n",
            simTime, hdr.track_count, hdr.cmd_in);
        OutputDebugStringA(buf);
    }

    if (hdr.cmd_in != mLastCmdIn) {
        ProcessNewCommands(simTime);
        mLastCmdIn = hdr.cmd_in;
    }

    return true;
}

void WsfShmSimulationExtension::ProcessNewCommands(double aSimTime)
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

        // Execute the command (stubs — requires full WsfPlatform API)
        switch (cmd.type) {
        case 1: /* ExecuteSensorControl(cmd, aSimTime); */ break;
        case 2: /* ExecuteWeaponAssign(cmd, aSimTime); */ break;
        case 3: /* ExecuteEngage(cmd, aSimTime); */ break;
        case 4: /* ExecuteAllocate(cmd, aSimTime); */ break;
        default: break;
        }
    }

    // Acknowledge processed commands
    hdr.cmd_out = hdr.cmd_in;
    memcpy(mShmBase, &hdr, sizeof(ShmHeader));
}
