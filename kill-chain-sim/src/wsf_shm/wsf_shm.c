// wsf_shm.c - AFSIM plugin with SHM command polling
// MSVC build: cl ... wsf_shm.c /Fe:wsf_shm.dll /link /DLL kernel32.lib user32.lib
// Entry: WsfPluginVersion (SDK API) + WsfPluginSetup (starts polling thread)
// No AFSIM SDK headers needed - pure Windows API + AFSIM plugin API

#include <windows.h>
#include <stdio.h>
#include <string.h>
#include <stdint.h>

// ============================================================================
// AFSIM Plugin API (from UtPlugin.hpp SDK)
// UtPluginVersion struct layout MUST match SDK exactly (x64):
//   offset 0:  uint32_t mMajor           (4 bytes)
//   offset 4:  uint32_t mMinor           (4 bytes)
//   offset 8:  const char* mCompilerVersion (8 bytes, POINTER!)
// Total: 16 bytes — third field is POINTER not uint32_t
// ============================================================================
struct UtPluginVersion {
    uint32_t mMajor;
    uint32_t mMinor;
    const char* mCompilerVersion;
};

// MSVC _MSC_VER=1916 = VS2019 16.x (matches original wsf_air_combat.dll)
// AFSIM checks compiler string for compatibility — must match known toolchain
#define COMPILER_STRING "win_1916_64bit_release-hwe"

// ============================================================================
// SHM Constants (must match Python shm_client.py layout exactly)
// ============================================================================
#define SHM_NAME          "kill_chain_shm"
#define HEADER_SIZE        128
#define TRACK_SIZE         72    // TrackEntry: matches shm_client.py ctypes
#define TRACKS_OFFSET      HEADER_SIZE
#define MAX_TRACKS         512
#define TRACKS_SIZE        (MAX_TRACKS * TRACK_SIZE)
#define CMDS_OFFSET        (TRACKS_OFFSET + TRACKS_SIZE)
#define CMD_SIZE           44     // matches shm_client.py CmdEntry
#define MAX_CMDS           256
#define SHM_FILE_SIZE      (CMDS_OFFSET + MAX_CMDS * CMD_SIZE)

// ============================================================================
// SHM Structs (layout matches Python shm_client.py exactly)
// ============================================================================
typedef struct {
    uint32_t track_id;
    double   lat;
    double   lon;
    double   altitude;
    double   velocity;
    double   heading;
    double   timestamp_ms;
    uint8_t  type;
    uint8_t  force;
    uint8_t  track_quality;
    uint16_t padding;
} TrackEntry;

typedef struct {
    uint32_t cmd_id;
    uint8_t  type;
    uint8_t  sender_id;
    uint16_t reserved;
    uint32_t target_id;
    uint32_t param1;
    uint32_t param2;
    float    param3;
    char     description[64];
} CmdEntry;

typedef struct {
    uint32_t magic;
    uint16_t version;
    uint16_t track_count;
    uint16_t sensor_count;
    uint16_t weapon_count;
    uint32_t timestamp_ms;
    uint32_t cmd_in;
    uint32_t cmd_out;
    uint8_t  afsim_ready;
    uint8_t  padding[5];
    uint64_t fence;
} ShmHeader;

#define MAGIC_VALUE  0x4B494C4C  // "KILL"
#define FENCE_VALUE  0xDEADBEEFDEADBEEFULL

// ============================================================================
// Logging (separate from AFSIM output dir)
// ============================================================================
static FILE *g_log = NULL;
static CRITICAL_SECTION g_log_lock;
static int g_log_initialized = 0;

static void init_log(void) {
    if (g_log_initialized) return;
    InitializeCriticalSection(&g_log_lock);
    EnterCriticalSection(&g_log_lock);
    if (!g_log_initialized) {
        g_log = fopen("D:\\afsim-2.9.0-win64\\bin\\wsf_shm_debug.log", "a");
        if (g_log) {
            fprintf(g_log, "\n=== WSF_SHM plugin loaded (MSVC) at %.3f ===\n", GetTickCount64() / 1000.0);
            fflush(g_log);
        }
        g_log_initialized = 1;
    }
    LeaveCriticalSection(&g_log_lock);
}

static void log_msg(const char *fmt, ...) {
    if (!g_log_initialized) init_log();
    EnterCriticalSection(&g_log_lock);
    if (g_log) {
        char buf[512];
        va_list args;
        va_start(args, fmt);
        vsnprintf(buf, sizeof(buf), fmt, args);
        va_end(args);
        fprintf(g_log, "[%.3f] %s", GetTickCount64() / 1000.0, buf);
        fflush(g_log);
    }
    LeaveCriticalSection(&g_log_lock);
}

// ============================================================================
// SHM State
// ============================================================================
static HANDLE  g_shm_file = NULL;
static void   *g_shm_base = NULL;
static HANDLE  g_timer_thread = NULL;
static volatile LONG g_running = 0;
static int     g_shm_opened = 0;
static uint32_t g_last_cmd_in = 0;

static ShmHeader *get_header(void) { return (ShmHeader *)g_shm_base; }
static TrackEntry *get_track(int i) {
    if (!g_shm_base || i < 0 || i >= MAX_TRACKS) return NULL;
    return (TrackEntry *)((uint8_t *)g_shm_base + TRACKS_OFFSET + i * TRACK_SIZE);
}
static CmdEntry *get_cmd(int i) {
    if (!g_shm_base || i < 0 || i >= MAX_CMDS) return NULL;
    return (CmdEntry *)((uint8_t *)g_shm_base + CMDS_OFFSET + i * CMD_SIZE);
}

// ============================================================================
// SHM Open/Close
// ============================================================================
static int open_shm(const char *name) {
    if (g_shm_base) return 1;
    char path[512];
    // Match Python shm_client.py path exactly:
    // shm_path = "C:/Users/15041/.openclaw/workspace/kill-chain-sim/{name}.dat"
    snprintf(path, sizeof(path),
        "C:\\Users\\15041\\.openclaw\\workspace\\kill-chain-sim\\%s.dat", name);
    g_shm_file = CreateFileA(path, GENERIC_READ | GENERIC_WRITE,
        FILE_SHARE_READ | FILE_SHARE_WRITE, NULL, OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (g_shm_file == INVALID_HANDLE_VALUE) {
        log_msg("CreateFile '%s' failed: %lu\n", path, GetLastError());
        g_shm_file = NULL;
        return 0;
    }
    HANDLE mapping = CreateFileMappingA(g_shm_file, NULL, PAGE_READWRITE, 0, SHM_FILE_SIZE, NULL);
    if (!mapping) {
        log_msg("CreateFileMapping '%s' failed: %lu\n", name, GetLastError());
        CloseHandle(g_shm_file);
        g_shm_file = NULL;
        return 0;
    }
    g_shm_base = MapViewOfFile(mapping, FILE_MAP_READ | FILE_MAP_WRITE, 0, 0, 0);
    CloseHandle(mapping);
    if (!g_shm_base) {
        log_msg("MapViewOfFile '%s' failed: %lu\n", name, GetLastError());
        CloseHandle(g_shm_file);
        g_shm_file = NULL;
        return 0;
    }
    ShmHeader *h = get_header();
    log_msg("SHM opened '%s' base=%p magic=0x%08X\n", path, g_shm_base, h ? h->magic : 0);
    g_shm_opened = 1;
    return 1;
}

static void close_shm(void) {
    if (g_shm_base) { UnmapViewOfFile(g_shm_base); g_shm_base = NULL; }
    if (g_shm_file) { CloseHandle(g_shm_file); g_shm_file = NULL; }
    g_shm_opened = 0;
    log_msg("SHM closed\n");
}

// ============================================================================
// Timer Thread: polls SHM commands at ~60Hz
// ============================================================================
static DWORD WINAPI timer_thread(LPVOID lpParam) {
    (void)lpParam;
    log_msg("Timer thread started (60Hz polling)\n");
    uint32_t last_track_count = 0;
    DWORD last_tick = GetTickCount();

    while (g_running) {
        // Poll every ~16ms (60Hz)
        Sleep(16);

        if (!g_shm_opened) {
            // Try to open SHM if not yet open
            open_shm(SHM_NAME);
            continue;
        }

        ShmHeader *h = get_header();
        if (!h || h->magic != MAGIC_VALUE) continue;

        // Check for new tracks
        if (h->track_count != last_track_count) {
            log_msg("TRACKS: count=%u ts=%u\n", h->track_count, h->timestamp_ms);
            last_track_count = h->track_count;
        }

        // Process new commands
        if (h->cmd_in != g_last_cmd_in) {
            uint32_t n_new = h->cmd_in - g_last_cmd_in;
            if (n_new > MAX_CMDS) n_new = MAX_CMDS;

            for (uint32_t i = 0; i < n_new; i++) {
                uint32_t idx = (g_last_cmd_in + i) % MAX_CMDS;
                CmdEntry *c = get_cmd(idx);
                if (c && c->cmd_id != 0) {
                    log_msg("CMD id=%u type=%u target=%u param1=%u param2=%u desc='%.40s'\n",
                        c->cmd_id, c->type, c->target_id, c->param1, c->param2, c->description);
                }
            }
            g_last_cmd_in = h->cmd_in;
        }
    }

    log_msg("Timer thread exiting\n");
    return 0;
}

// ============================================================================
// AFSIM Plugin Entry Points (extern "C", called by name from WsfPluginManager)
// ============================================================================
__declspec(dllexport)
void WsfPluginVersion(struct UtPluginVersion *out) {
    out->mMajor = 2;
    out->mMinor = 9;
    out->mCompilerVersion = COMPILER_STRING;
}

__declspec(dllexport)
void WsfPluginSetup(void) {
    init_log();
    log_msg("WsfPluginSetup called\n");

    // Open SHM
    open_shm(SHM_NAME);

    // Mark AFSIM as ready
    if (g_shm_base) {
        ShmHeader *h = get_header();
        if (h && h->magic == MAGIC_VALUE) {
            h->afsim_ready = 1;
            log_msg("AFSIM marked ready, track_count=%u\n", h->track_count);
        }
    }

    // Start timer thread at ~60Hz polling
    g_running = 1;
    DWORD thread_id;
    g_timer_thread = CreateThread(NULL, 0, timer_thread, NULL, 0, &thread_id);
    if (g_timer_thread) {
        log_msg("Timer thread created (tid=%lu)\n", thread_id);
    } else {
        log_msg("CreateThread failed: %lu\n", GetLastError());
    }
}

// ============================================================================
// Public SHM API - callable from Python ctypes
// ============================================================================
__declspec(dllexport)
int wsf_shm_open(const char *name) {
    return open_shm(name);
}

__declspec(dllexport)
void wsf_shm_close(void) {
    close_shm();
}

__declspec(dllexport)
int wsf_shm_set_debug(int enable) {
    (void)enable;
    return 1;
}

__declspec(dllexport)
int wsf_shm_get_track_count(void) {
    if (!g_shm_base) return 0;
    ShmHeader *h = get_header();
    return h ? (int)h->track_count : 0;
}

__declspec(dllexport)
int wsf_shm_get_cmd_in(void) {
    if (!g_shm_base) return 0;
    ShmHeader *h = get_header();
    return h ? (int)h->cmd_in : 0;
}

__declspec(dllexport)
int wsf_shm_read_track(int index, uint32_t *track_id, double *lat, double *lon,
                       double *alt, double *vel, double *heading) {
    TrackEntry *t = get_track(index);
    if (!t) return 0;
    if (track_id) *track_id = t->track_id;
    if (lat)      *lat      = t->lat;
    if (lon)      *lon      = t->lon;
    if (alt)      *alt      = t->altitude;
    if (vel)      *vel      = t->velocity;
    if (heading)  *heading  = t->heading;
    return 1;
}

__declspec(dllexport)
int wsf_shm_write_cmd(uint8_t type, uint32_t target_id, uint32_t param1, uint32_t param2) {
    if (!g_shm_base) return 0;
    ShmHeader *h = get_header();
    if (!h) return 0;
    uint32_t idx = h->cmd_in % MAX_CMDS;
    CmdEntry *c = get_cmd(idx);
    if (!c) return 0;
    memset(c, 0, sizeof(CmdEntry));
    c->cmd_id = h->cmd_in + 1;
    c->type = type;
    c->target_id = target_id;
    c->param1 = param1;
    c->param2 = param2;
    h->cmd_in++;
    log_msg("wsf_shm_write_cmd: type=%u target=%u cmd_in=%u\n", type, target_id, h->cmd_in);
    return 1;
}

__declspec(dllexport)
int wsf_shm_process_new_commands(void) {
    if (!g_shm_base) return 0;
    ShmHeader *h = get_header();
    if (!h) return 0;
    if (h->cmd_in == g_last_cmd_in) return 0;
    uint32_t n_new = h->cmd_in - g_last_cmd_in;
    if (n_new > MAX_CMDS) n_new = MAX_CMDS;
    for (uint32_t i = 0; i < n_new; i++) {
        uint32_t idx = (g_last_cmd_in + i) % MAX_CMDS;
        CmdEntry *c = get_cmd(idx);
        if (c) {
            log_msg("WSF_SHM_CMD[%u] type=%u target=%u\n", c->cmd_id, c->type, c->target_id);
        }
    }
    h->cmd_out += n_new;
    g_last_cmd_in = h->cmd_in;
    return (int)n_new;
}

__declspec(dllexport)
int wsf_shm_read_header(uint32_t *track_count, uint32_t *timestamp_ms,
                         uint32_t *cmd_in, uint32_t *cmd_out) {
    if (!g_shm_base) return 0;
    ShmHeader *h = get_header();
    if (!h || h->magic != MAGIC_VALUE) return 0;
    if (track_count)  *track_count  = h->track_count;
    if (timestamp_ms) *timestamp_ms = h->timestamp_ms;
    if (cmd_in)       *cmd_in       = h->cmd_in;
    if (cmd_out)      *cmd_out      = h->cmd_out;
    return 1;
}

// ============================================================================
// DLL entry
// ============================================================================
// Forward declaration
static void start_polling(void);

BOOL WINAPI DllMain(HINSTANCE hinstDLL, DWORD fdwReason, LPVOID lpvReserved) {
    (void)hinstDLL; (void)lpvReserved;
    if (fdwReason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(hinstDLL);
        init_log();
        log_msg("DllMain PROCESS_ATTACH\n");
        start_polling();
    } else if (fdwReason == DLL_PROCESS_DETACH) {
        log_msg("DllMain PROCESS_DETACH\n");
        g_running = 0;
        if (g_timer_thread) {
            WaitForSingleObject(g_timer_thread, 2000);
            CloseHandle(g_timer_thread);
            g_timer_thread = NULL;
        }
        close_shm();
        EnterCriticalSection(&g_log_lock);
        if (g_log) { fclose(g_log); g_log = NULL; }
        g_log_initialized = 0;
        LeaveCriticalSection(&g_log_lock);
    }
    return TRUE;
}

static void start_polling(void) {
    open_shm(SHM_NAME);
    if (g_shm_base) {
        ShmHeader *h = get_header();
        if (h && h->magic == MAGIC_VALUE) {
            h->afsim_ready = 1;
            log_msg("AFSIM ready flag set from DllMain, track_count=%u\n", h->track_count);
        }
    }
    g_running = 1;
    DWORD thread_id;
    g_timer_thread = CreateThread(NULL, 0, timer_thread, NULL, 0, &thread_id);
    if (g_timer_thread) {
        log_msg("Timer thread started from DllMain (tid=%lu)\n", thread_id);
    } else {
        log_msg("CreateThread failed: %lu\n", GetLastError());
    }
}
