// wsf_shm_timer.c - Pure C AFSIM plugin with timer-based file polling
// Polls AFSIM output log file every 16ms, writes parsed tracks to SHM
// Compiles with: gcc -shared -o wsf_shm.dll wsf_shm_timer.c -lkernel32 -lws2_32 -luser32
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <stdint.h>

#pragma comment(lib, "kernel32.lib")
#pragma comment(lib, "user32.lib")

// ============================================================================
// AFSIM Plugin API
// ============================================================================
struct UtPluginVersion {
    uint32_t mMajor;
    uint32_t mMinor;
    const char* mCompilerVersion;
};

#define COMPILER_STRING "win_1916_64bit_release-hwe"

// ============================================================================
// SHM Constants (matches Python shm_client.py layout exactly)
// ============================================================================
#define SHM_NAME          "kill_chain_shm"
#define HEADER_SIZE        128
#define TRACK_SIZE         72
#define TRACKS_OFFSET      HEADER_SIZE
#define MAX_TRACKS         512
#define TRACKS_SIZE        (MAX_TRACKS * TRACK_SIZE)
#define CMDS_OFFSET        (TRACKS_OFFSET + TRACKS_SIZE)
#define CMD_SIZE           44
#define MAX_CMDS           256

#define MAGIC_VALUE        0x4B494C4C  // "KILL"
#define POLL_INTERVAL_MS   16          // ~60Hz polling

// ============================================================================
// SHM Structs
// ============================================================================
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

// ============================================================================
// Global state
// ============================================================================
static HANDLE  g_timer_queue = NULL;
static HANDLE  g_shutdown_event = NULL;
static volatile int g_running = 0;

// Track file polling state
static FILE* g_track_file = NULL;
static char  g_track_file_path[MAX_PATH] = "";
static int   g_track_count = 0;
static uint64_t g_last_file_size = 0;

// SHM state
static HANDLE  g_shm_file = NULL;
static void*   g_shm_base = NULL;

// ============================================================================
// Debug
// ============================================================================
static void debug_log(const char *fmt, ...) {
    char buf[512];
    va_list args;
    va_start(args, fmt);
    vsnprintf(buf, sizeof(buf), fmt, args);
    va_end(args);
    OutputDebugStringA(buf);
}

// ============================================================================
// SHM
// ============================================================================
static int open_shm(const char *name) {
    if (g_shm_base) return 1;
    char path[256];
    snprintf(path, sizeof(path), "Global\\%s", name);
    g_shm_file = OpenFileMappingA(FILE_MAP_READ | FILE_MAP_WRITE, FALSE, path);
    if (!g_shm_file) {
        debug_log("WSF_SHM: OpenFileMapping '%s' failed: %lu\n", name, GetLastError());
        return 0;
    }
    g_shm_base = MapViewOfFile(g_shm_file, FILE_MAP_READ | FILE_MAP_WRITE, 0, 0, 0);
    if (!g_shm_base) {
        debug_log("WSF_SHM: MapViewOfFile failed: %lu\n", GetLastError());
        CloseHandle(g_shm_file);
        g_shm_file = NULL;
        return 0;
    }
    debug_log("WSF_SHM: opened '%s' at %p\n", name, g_shm_base);
    return 1;
}

static void close_shm(void) {
    if (g_shm_base) { UnmapViewOfFile(g_shm_base); g_shm_base = NULL; }
    if (g_shm_file) { CloseHandle(g_shm_file); g_shm_file = NULL; }
}

static int is_shm_valid(void) {
    if (!g_shm_base) return 0;
    ShmHeader *h = (ShmHeader*)g_shm_base;
    return h->magic == MAGIC_VALUE;
}

static void update_shm_header(int track_count) {
    if (!is_shm_valid()) return;
    ShmHeader *h = (ShmHeader*)g_shm_base;
    h->track_count = track_count;
    h->timestamp_ms = (uint32_t)(GetTickCount64() & 0xFFFFFFFF);
}

static void write_track_to_shm(int slot, uint32_t track_id, double lat, double lon,
                               double alt, double vel, double hdg) {
    if (!is_shm_valid()) return;
    uint8_t *base = (uint8_t*)g_shm_base;
    TrackEntry *t = (TrackEntry*)(base + TRACKS_OFFSET + slot * TRACK_SIZE);
    memset(t, 0, sizeof(TrackEntry));
    t->track_id = track_id;
    t->lat = lat;
    t->lon = lon;
    t->altitude = alt;
    t->velocity = vel;
    t->heading = hdg;
    t->timestamp_ms = (double)(GetTickCount64() & 0xFFFFFFFF);
    t->type = 2;    // UCAV
    t->force = 1;   // hostile
    t->track_quality = 75;
}

// ============================================================================
// Track File Parsing
// ============================================================================
// Format: "TRACK: id=2 lat=38.0694 lon=-117.233 alt=1524 vel=0 hdg=0"
// We parse from EOF: the last complete TRACK: line in the file

static int parse_track_from_line(const char *line, uint32_t *track_id,
                                  double *lat, double *lon, double *alt,
                                  double *vel, double *hdg) {
    int matched = sscanf(line,
        "TRACK: id=%u lat=%lf lon=%lf alt=%lf vel=%lf hdg=%lf",
        track_id, lat, lon, alt, vel, hdg);
    return (matched == 6);
}

static void poll_track_file(void) {
    // Open file if not open
    if (!g_track_file && g_track_file_path[0]) {
        g_track_file = fopen(g_track_file_path, "r");
        if (g_track_file) {
            debug_log("WSF_SHM: opened track file: %s\n", g_track_file_path);
            fseek(g_track_file, 0, SEEK_END);
            g_last_file_size = ftell(g_track_file);
        }
    }

    if (!g_track_file) return;

    fseek(g_track_file, 0, SEEK_END);
    uint64_t size = ftell(g_track_file);

    if (size > g_last_file_size) {
        // Read new content from last known position
        fseek(g_track_file, (long)g_last_file_size, SEEK_SET);
        char buf[4096];
        size_t n = fread(buf, 1, sizeof(buf) - 1, g_track_file);
        buf[n] = '\0';

        // Find the last complete TRACK: line
        char *last_track = NULL;
        char *p = buf;
        while (*p) {
            char *line_end = strchr(p, '\n');
            if (!line_end) break;
            *line_end = '\0';
            if (strstr(p, "TRACK:") == p) {
                last_track = p;
            }
            p = line_end + 1;
        }

        if (last_track) {
            uint32_t tid;
            double lat, lon, alt, vel, hdg;
            if (parse_track_from_line(last_track, &tid, &lat, &lon, &alt, &vel, &hdg)) {
                g_track_count++;
                int slot = (g_track_count - 1) % MAX_TRACKS;
                write_track_to_shm(slot, tid, lat, lon, alt, vel, hdg);
                update_shm_header(g_track_count);
                debug_log("WSF_SHM: track %u lat=%.4f lon=%.4f alt=%.0f\n",
                         tid, lat, lon, alt);
            }
        }

        g_last_file_size = size;
    } else if (size < g_last_file_size) {
        // File was truncated/rotated
        fseek(g_track_file, 0, SEEK_SET);
        g_last_file_size = 0;
        g_track_count = 0;
    }
}

// ============================================================================
// Timer callback - called every POLL_INTERVAL_MS
// ============================================================================
static void CALLBACK timer_callback(PVOID param, BOOLEAN timer_or_wait_fired) {
    (void)param;
    (void)timer_or_wait_fired;

    if (!g_running) return;
    poll_track_file();

    if (g_shutdown_event && WaitForSingleObject(g_shutdown_event, 0) == WAIT_OBJECT_0) {
        g_running = 0;
    }
}

// ============================================================================
// AFSIM Plugin Entry Points
// ============================================================================
__declspec(dllexport)
void WsfPluginVersion(struct UtPluginVersion *out) {
    out->mMajor = 2;
    out->mMinor = 9;
    out->mCompilerVersion = COMPILER_STRING;
    debug_log("WSF_SHM: WsfPluginVersion called -> 2.9\n");
}

__declspec(dllexport)
void WsfPluginSetup(void) {
    debug_log("WSF_SHM: WsfPluginSetup called\n");

    open_shm(SHM_NAME);

    // Set track file path from environment or default
    const char *scenario_dir = getenv("AFSIM_SCENARIO_DIR");
    if (scenario_dir) {
        snprintf(g_track_file_path, MAX_PATH, "%s/output/kill_chain.log", scenario_dir);
    } else {
        snprintf(g_track_file_path, MAX_PATH,
                 "C:/Users/15041/.openclaw/workspace/kill-chain-sim/output/kill_chain.log");
    }

    debug_log("WSF_SHM: Track file path: %s\n", g_track_file_path);

    g_shutdown_event = CreateEventA(NULL, TRUE, FALSE, NULL);
    g_timer_queue = CreateTimerQueue();
    if (!g_timer_queue) {
        debug_log("WSF_SHM: CreateTimerQueue failed: %lu\n", GetLastError());
        return;
    }

    g_running = 1;
    HANDLE timer;
    if (!CreateTimerQueueTimer(&timer, g_timer_queue, timer_callback, NULL,
                               POLL_INTERVAL_MS, POLL_INTERVAL_MS, WT_EXECUTEINTIMERTHREAD)) {
        debug_log("WSF_SHM: CreateTimerQueueTimer failed: %lu\n", GetLastError());
        g_running = 0;
        return;
    }

    debug_log("WSF_SHM: Timer started (%d ms interval)\n", POLL_INTERVAL_MS);
}

// ============================================================================
// DLL entry
// ============================================================================
BOOL WINAPI DllMain(HINSTANCE hinstDLL, DWORD fdwReason, LPVOID lpvReserved) {
    (void)hinstDLL;
    (void)lpvReserved;

    if (fdwReason == DLL_PROCESS_DETACH) {
        g_running = 0;
        if (g_shutdown_event) SetEvent(g_shutdown_event);
        Sleep(50);
        if (g_timer_queue) DeleteTimerQueue(g_timer_queue);
        if (g_track_file) fclose(g_track_file);
        close_shm();
        debug_log("WSF_SHM: DLL unloaded\n");
    }
    return TRUE;
}
