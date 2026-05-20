// wsf_shm_v2.cpp — Self-contained AFSIM C++ Plugin (Minimal Build)
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <cstdio>
#include <cstring>
#include <string>

// ============================================================================
// AFSIM Plugin Interface (verified ABI from wsf_air_combat.dll exports)
// ============================================================================

struct UtPluginVersion {
    uint32_t mMajor;           // offset 0
    uint32_t mMinor;           // offset 4
    const char* mCompilerVersion; // offset 8 (pointer, 8 bytes on x64)
};
// Total: 16 bytes on x64

class WsfApplication;

// ============================================================================
// SHM Structures (must match Python shm_client.py)
// ============================================================================

#define SHM_NAME "kill_chain_shm"
#define SHM_MAGIC 0x4B494C4C
#define MAX_TRACKS 512
#define MAX_CMDS 64

#pragma pack(push, 1)
struct TrackEntry {
    uint32_t local_track_number;
    float latitude;
    float longitude;
    float altitude_m;
    float speed_mps;
    float heading_deg;
    float range_to_sensors[8];
    uint32_t sensor_count;
    uint32_t padding;
};

struct ShmHeader {
    uint32_t magic;
    uint32_t version;
    uint32_t track_count;
    uint32_t cmd_in;
    uint32_t cmd_out;
    uint32_t sim_time_hi;
    uint32_t sim_time_lo;
    uint8_t  padding[4088];
};

struct CmdEntry {
    uint32_t cmd_type;
    uint32_t cmd_id;
    uint32_t target_track;
    uint32_t priority;
    float    param[8];
    uint32_t flags;
    uint8_t  padding[48];
};

struct ShmData {
    ShmHeader header;
    TrackEntry tracks[MAX_TRACKS];
    CmdEntry   commands[MAX_CMDS];
};
#pragma pack(pop)

// ============================================================================
// Global state
// ============================================================================

static HANDLE   g_shmHandle = nullptr;
static ShmData* g_shmBase  = nullptr;
static bool     g_debug     = true;
static uint32_t g_lastCmdIn = 0;
static FILE*    g_logFile   = nullptr;

// ============================================================================
// SHM open/close
// ============================================================================

static bool OpenShm() {
    if (g_shmBase != nullptr) return true;
    char path[256];
    snprintf(path, sizeof(path), "Global\\%s", SHM_NAME);
    HANDLE h = OpenFileMappingA(FILE_MAP_READ | FILE_MAP_WRITE, FALSE, path);
    if (!h) {
        if (g_debug) OutputDebugStringA("[WSF_SHM] OpenFileMappingA failed\n");
        return false;
    }
    g_shmBase = (ShmData*)MapViewOfFile(h, FILE_MAP_READ | FILE_MAP_WRITE, 0, 0, 0);
    CloseHandle(h);
    if (!g_shmBase) {
        if (g_debug) OutputDebugStringA("[WSF_SHM] MapViewOfFile failed\n");
        return false;
    }
    if (g_debug) OutputDebugStringA("[WSF_SHM] opened shared memory\n");
    return true;
}

static void CloseShm() {
    if (g_shmBase) { UnmapViewOfFile(g_shmBase); g_shmBase = nullptr; }
    if (g_shmHandle) { CloseHandle(g_shmHandle); g_shmHandle = nullptr; }
}

// ============================================================================
// Process new commands
// ============================================================================

static void ProcessNewCommands() {
    if (!g_shmBase) return;
    uint32_t cmdIn = g_shmBase->header.cmd_in;
    if (cmdIn == g_lastCmdIn) return;

    uint32_t processed = 0;
    for (uint32_t i = 0; i < MAX_CMDS && processed < cmdIn - g_lastCmdIn; i++) {
        CmdEntry& cmd = g_shmBase->commands[i % MAX_CMDS];
        if (!(cmd.flags & 1)) continue;
        processed++;

        const char* typeName = "UNKNOWN";
        if (cmd.cmd_type == 1) typeName = "SENSOR_CONTROL";
        else if (cmd.cmd_type == 2) typeName = "WEAPON_ASSIGN";
        else if (cmd.cmd_type == 3) typeName = "ENGAGE";
        else if (cmd.cmd_type == 4) typeName = "ALLOCATE";

        if (g_logFile) {
            fprintf(g_logFile, "[WSF_SHM_V2] CMD id=%u type=%s track=%u prio=%u\n",
                cmd.cmd_id, typeName, cmd.target_track, cmd.priority);
            fflush(g_logFile);
        }
    }
    g_lastCmdIn = cmdIn;
}

// ============================================================================
// DLL entry point
// ============================================================================

BOOL WINAPI DllMain(HINSTANCE hinst, DWORD reason, LPVOID) {
    if (reason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(hinst);
        char logPath[MAX_PATH];
        snprintf(logPath, sizeof(logPath),
            "C:\\Users\\15041\\.openclaw\\workspace\\kill-chain-sim\\wsf_shm_v2.log");
        g_logFile = fopen(logPath, "a");
        if (g_logFile) {
            fprintf(g_logFile, "\n[WSF_SHM_V2] DLL_PROCESS_ATTACH\n");
            fflush(g_logFile);
        }
    } else if (reason == DLL_PROCESS_DETACH) {
        CloseShm();
        if (g_logFile) { fclose(g_logFile); g_logFile = nullptr; }
    }
    return TRUE;
}

// ============================================================================
// AFSIM Plugin Interface Functions
// CRITICAL: Compiler version string must match — AFSIM validates this!
// ============================================================================

extern "C" __declspec(dllexport)
void WsfPluginVersion(UtPluginVersion& version) {
    version.mMajor = 2;
    version.mMinor = 9;
    version.mCompilerVersion = "win_1916_64bit_release-hwe";
}

extern "C" __declspec(dllexport)
void WsfPluginSetup(WsfApplication& app) {
    if (g_logFile) {
        fprintf(g_logFile, "[WSF_SHM_V2] WsfPluginSetup called!\n");
        fflush(g_logFile);
    }
    // In full SDK build: app.RegisterExtension("wsf_shm", ut::make_unique<WsfShmScenarioExtension>());
    // This minimal build: just open SHM for polling
    OpenShm();
}
