// WsfShmSimulationExtension.hpp
// Shared Memory Command Plugin - AFSIM Simulation Extension
// Per-frame polling of shared memory commands

#ifndef WSF_SHM_SIMULATION_EXTENSION_HPP
#define WSF_SHM_SIMULATION_EXTENSION_HPP

#include "wsf_export.h"

#include <cstdint>

#include "WsfSimulationExtension.hpp"

#define SHM_NAME "kill_chain_shm"
#define MAX_TRACKS 256
#define MAX_CMDS 256
#define TRACK_OFFSET 128
#define CMD_OFFSET (TRACK_OFFSET + MAX_TRACKS * 64)

#pragma pack(push, 1)
struct ShmHeader {
    uint32_t track_count;
    uint32_t timestamp_ms;
    uint32_t cmd_in;
    uint32_t cmd_out;
    uint8_t  reserved[112];
};

struct CmdEntry {
    uint32_t cmd_id;
    uint8_t  type;          // 1=SENSOR, 2=WEAPON, 3=ENGAGE, 4=ALLOCATE
    uint8_t  sender_id;
    uint16_t reserved;
    uint32_t target_id;      // platform index in scenario
    uint32_t param1;        // sensor_id, weapon_id, or interceptor_track_id
    uint32_t param2;        // mode or target_track_id
    float    param3;        // auxiliary parameter
    char     description[64];
};
#pragma pack(pop)

class WsfShmSimulationExtension : public WsfSimulationExtension
{
public:
    WsfShmSimulationExtension();
    ~WsfShmSimulationExtension() override = default;

    // WsfSimulationExtension: per-frame update
    bool PrepareExtension() override;

private:
    bool  OpenShm();
    void  ProcessNewCommands(double aSimTime);

    void*  mShmBase;
    uint32_t mLastCmdIn;
    int    mUpdateCount;
    bool   mDebug;
};

#endif // WSF_SHM_SIMULATION_EXTENSION_HPP
