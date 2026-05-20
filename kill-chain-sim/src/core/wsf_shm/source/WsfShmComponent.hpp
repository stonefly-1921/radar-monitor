// WsfShmComponent.hpp
// Shared Memory Component - AFSIM DIS Component
// Implements WsfDisComponent for reading kill chain commands from shared memory

#ifndef WSF_SHM_COMPONENT_HPP
#define WSF_SHM_COMPONENT_HPP

#include <cstdint>
#include <string>

class WsfSimulation;

#include <windows.h>

// SHM layout constants (must match Python shm_client.py)
#define SHM_NAME "kill_chain_shm"
#define MAX_TRACKS 256
#define MAX_CMDS 256
#define TRACK_OFFSET 128
#define CMD_OFFSET (TRACK_OFFSET + MAX_TRACKS * 64)
#define MAX_SHM_SIZE (CMD_OFFSET + MAX_CMDS * 128)

#pragma pack(push, 1)
struct TrackEntry {
    uint32_t track_id;
    double   lat;
    double   lon;
    double   alt_m;
    double   vel_mps;
    double   heading_deg;
    uint32_t track_type;
    uint8_t  padding[36];
};

struct CmdEntry {
    uint32_t cmd_id;
    uint8_t  type;          // 1=SENSOR, 2=WEAPON, 3=ENGAGE, 4=ALLOCATE
    uint8_t  sender_id;
    uint16_t reserved;
    uint32_t target_id;     // platform index in scenario
    uint32_t param1;        // sensor_id, weapon_id, or interceptor_track_id
    uint32_t param2;        // mode or target_track_id
    float    param3;        // auxiliary parameter
    char     description[64];
};

struct ShmHeader {
    uint32_t track_count;
    uint32_t timestamp_ms;
    uint32_t cmd_in;
    uint32_t cmd_out;
    uint8_t  reserved[112];
};
#pragma pack(pop)

//! DIS component that reads commands from Windows shared memory
class WSF_EXPORT WsfShmComponent : public WsfDisComponent
{
public:
    WsfShmComponent();
    ~WsfShmComponent() override;

    // WsfComponent overrides
    WsfComponent* CloneComponent() const override;
    WsfStringId   GetComponentName() const override;
    const int*    GetComponentRoles() const override;
    void*         QueryInterface(int aRole) override;

    // WsfDisComponent — called every frame
    void PrepareComponent(double aSimTime) override;

private:
    bool  OpenShm();
    void  CloseShm();
    void  ProcessNewCommands(double aSimTime);

    void ExecuteSensorControl(const CmdEntry& aCmd, double aSimTime);
    void ExecuteWeaponAssign(const CmdEntry& aCmd, double aSimTime);
    void ExecuteEngage(const CmdEntry& aCmd, double aSimTime);
    void ExecuteAllocate(const CmdEntry& aCmd, double aSimTime);

    void*  mShmBase;
    uint32_t mLastCmdIn;
    int    mUpdateCount;
    bool   mDebug;
};

#endif // WSF_SHM_COMPONENT_HPP