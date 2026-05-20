/* wsf_shm.c
 * Shared Memory Command Reader/Writer for AFSIM - Pure C implementation
 *
 * Build (MinGW-w64 gcc):
 *   x86_64-w64-mingw32-gcc -shared -o wsf_shm.dll wsf_shm.c -lkernel32
 *
 * AFSIM WSF_SCRIPT_PROCESSOR calls the READ functions (wsf_shm_open, wsf_shm_get_track_count,
 * wsf_shm_read_track, wsf_shm_process_new_commands) from on_update().
 *
 * Python ctypes calls the WRITE function (wsf_shm_write_cmd) to inject commands.
 */

#include <windows.h>
#include <stdio.h>
#include <string.h>
#include <stdint.h>

#pragma comment(lib, "kernel32.lib")

/* SHM layout */
#define SHM_NAME_MAX 128
#define MAX_TRACKS 256
#define MAX_CMDS 256

/* Offsets within SHM file view */
#define TRACK_OFFSET    128
#define CMD_OFFSET      (TRACK_OFFSET + MAX_TRACKS * 64)
#define MAX_SHM_SIZE    (CMD_OFFSET + MAX_CMDS * 128)

/* Track entry (64 bytes) - AFSIM writes, Python reads */
typedef struct {
    uint32_t track_id;
    double   lat;
    double   lon;
    double   alt_m;
    double   vel_mps;
    double   heading_deg;
    uint32_t track_type;
    uint8_t  padding[36];
} TrackEntry;

/* Command entry (44 bytes) - Python writes, AFSIM reads via process_new_commands() */
typedef struct {
    uint32_t cmd_id;
    uint8_t  type;          /* 1=SENSOR, 2=WEAPON, 3=ENGAGE, 4=ALLOCATE */
    uint8_t  sender_id;
    uint16_t reserved;
    uint32_t target_id;     /* platform index or track_id */
    uint32_t param1;        /* sensor_id, weapon_id, or interceptor_track_id */
    uint32_t param2;        /* mode or engagement rules */
    float    param3;
    char     description[64];
} CmdEntry;

/* SHM header (first 128 bytes) */
typedef struct {
    uint32_t track_count;
    uint32_t timestamp_ms;
    uint32_t cmd_in;        /* written by Python */
    uint32_t cmd_out;       /* advanced by AFSIM after processing */
    uint8_t  reserved[112];
} ShmHeader;

/* Per-instance state */
static HANDLE  g_shm_file = NULL;
static void   *g_shm_base = NULL;
static char    g_shm_name[SHM_NAME_MAX] = {0};
static uint32_t g_last_cmd_in = 0;
static int     g_debug = 0;

/* Logging via Windows debug output */
static void debug_log(const char *fmt, ...) {
    if (!g_debug) return;
    char buf[512];
    va_list args;
    va_start(args, fmt);
    vsnprintf(buf, sizeof(buf), fmt, args);
    va_end(args);
    OutputDebugStringA(buf);
}

/* Open shared memory by name (used by AFSIM side) */
static int open_shm(const char *name) {
    if (g_shm_base) {
        debug_log("WSF_SHM: already open\n");
        return 1;
    }

    char path[SHM_NAME_MAX + 16];
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

    strncpy(g_shm_name, name, SHM_NAME_MAX - 1);
    g_shm_name[SHM_NAME_MAX - 1] = 0;
    debug_log("WSF_SHM: opened '%s' at %p\n", name, g_shm_base);
    return 1;
}

/* Create shared memory (used by Python/Python side to initialize) */
static int create_shm(const char *name, uint64_t size) {
    if (g_shm_base) {
        debug_log("WSF_SHM: already open\n");
        return 1;
    }

    char path[SHM_NAME_MAX + 16];
    snprintf(path, sizeof(path), "Global\\%s", name);

    g_shm_file = CreateFileMappingA(INVALID_HANDLE_VALUE, NULL,
        PAGE_READWRITE, (DWORD)((uint64_t)size >> 32), (DWORD)(size & 0xFFFFFFFF), path);
    if (!g_shm_file) {
        debug_log("WSF_SHM: CreateFileMapping '%s' failed: %lu\n", name, GetLastError());
        return 0;
    }

    g_shm_base = MapViewOfFile(g_shm_file, FILE_MAP_READ | FILE_MAP_WRITE, 0, 0, 0);
    if (!g_shm_base) {
        debug_log("WSF_SHM: MapViewOfFile failed: %lu\n", GetLastError());
        CloseHandle(g_shm_file);
        g_shm_file = NULL;
        return 0;
    }

    /* Initialize header */
    memset(g_shm_base, 0, sizeof(ShmHeader));
    strncpy(g_shm_name, name, SHM_NAME_MAX - 1);
    g_shm_name[SHM_NAME_MAX - 1] = 0;
    debug_log("WSF_SHM: created '%s' size=%llu at %p\n", name, (unsigned long long)size, g_shm_base);
    return 1;
}

/* Close shared memory */
static void close_shm(void) {
    if (g_shm_base) {
        UnmapViewOfFile(g_shm_base);
        g_shm_base = NULL;
    }
    if (g_shm_file) {
        CloseHandle(g_shm_file);
        g_shm_file = NULL;
    }
    g_shm_name[0] = 0;
    debug_log("WSF_SHM: closed\n");
}

/* Read header */
static int read_header(ShmHeader *hdr) {
    if (!g_shm_base) return 0;
    memcpy(hdr, g_shm_base, sizeof(ShmHeader));
    return 1;
}

/* Write header (for Python side initialization) */
static int write_header(const ShmHeader *hdr) {
    if (!g_shm_base) return 0;
    memcpy(g_shm_base, hdr, sizeof(ShmHeader));
    return 1;
}

/* Read all tracks */
static int read_tracks(TrackEntry *tracks, int max_tracks, int *out_count) {
    if (!g_shm_base) return 0;
    ShmHeader hdr;
    read_header(&hdr);
    *out_count = 0;
    if (hdr.track_count == 0) return 1;

    int count = hdr.track_count < max_tracks ? hdr.track_count : max_tracks;
    uint8_t *base = (uint8_t *)g_shm_base + TRACK_OFFSET;
    for (int i = 0; i < count; i++) {
        memcpy(&tracks[i], base + i * sizeof(TrackEntry), sizeof(TrackEntry));
    }
    *out_count = count;
    return 1;
}

/* Read a single command by circular index */
static int read_cmd(CmdEntry *cmd, uint32_t index) {
    if (!g_shm_base) return 0;
    if (index >= MAX_CMDS) return 0;
    uint8_t *base = (uint8_t *)g_shm_base + CMD_OFFSET;
    memcpy(cmd, base + index * sizeof(CmdEntry), sizeof(CmdEntry));
    return 1;
}

/* Write a command entry (Python calls this) */
static int write_cmd(const CmdEntry *cmd) {
    if (!g_shm_base) return 0;
    ShmHeader hdr;
    read_header(&hdr);

    uint32_t index = hdr.cmd_in % MAX_CMDS;
    uint8_t *base = (uint8_t *)g_shm_base + CMD_OFFSET;
    memcpy(base + index * sizeof(CmdEntry), cmd, sizeof(CmdEntry));

    hdr.cmd_in++;
    write_header(&hdr);
    debug_log("WSF_SHM: wrote cmd[%u] type=%u target=%u\n", index, cmd->type, cmd->target_id);
    return 1;
}

/* Advance cmd_out pointer in header (called by AFSIM after processing) */
static void advance_cmd_out(uint32_t count) {
    if (!g_shm_base) return;
    ShmHeader hdr;
    read_header(&hdr);
    hdr.cmd_out += count;
    memcpy(g_shm_base, &hdr, sizeof(ShmHeader));
}

/* =========================================================================
   PUBLIC API - callable from AFSIM WSF_SCRIPT_PROCESSOR (READ side)
   ========================================================================= */

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
    g_debug = enable;
    return g_debug;
}

__declspec(dllexport)
int wsf_shm_get_track_count(void) {
    if (!g_shm_base) return 0;
    ShmHeader hdr;
    read_header(&hdr);
    return (int)hdr.track_count;
}

__declspec(dllexport)
int wsf_shm_get_cmd_in(void) {
    if (!g_shm_base) return 0;
    ShmHeader hdr;
    read_header(&hdr);
    return (int)hdr.cmd_in;
}

__declspec(dllexport)
int wsf_shm_read_header(uint32_t *track_count, uint32_t *timestamp_ms,
                        uint32_t *cmd_in, uint32_t *cmd_out) {
    if (!g_shm_base) return 0;
    ShmHeader hdr;
    read_header(&hdr);
    if (track_count) *track_count = hdr.track_count;
    if (timestamp_ms) *timestamp_ms = hdr.timestamp_ms;
    if (cmd_in) *cmd_in = hdr.cmd_in;
    if (cmd_out) *cmd_out = hdr.cmd_out;
    return 1;
}

__declspec(dllexport)
int wsf_shm_read_track(int index, uint32_t *track_id, double *lat, double *lon,
                       double *alt_m, double *vel_mps, double *heading_deg) {
    if (!g_shm_base) return 0;
    TrackEntry t;
    uint8_t *base = (uint8_t *)g_shm_base + TRACK_OFFSET;
    memcpy(&t, base + index * sizeof(TrackEntry), sizeof(TrackEntry));
    if (track_id) *track_id = t.track_id;
    if (lat) *lat = t.lat;
    if (lon) *lon = t.lon;
    if (alt_m) *alt_m = t.alt_m;
    if (vel_mps) *vel_mps = t.vel_mps;
    if (heading_deg) *heading_deg = t.heading_deg;
    return 1;
}

__declspec(dllexport)
int wsf_shm_read_cmd(int index, uint32_t *cmd_id, uint8_t *type,
                     uint32_t *target_id, uint32_t *param1, uint32_t *param2) {
    if (!g_shm_base) return 0;
    CmdEntry c;
    uint8_t *base = (uint8_t *)g_shm_base + CMD_OFFSET;
    memcpy(&c, base + index * sizeof(CmdEntry), sizeof(CmdEntry));
    if (cmd_id) *cmd_id = c.cmd_id;
    if (type) *type = c.type;
    if (target_id) *target_id = c.target_id;
    if (param1) *param1 = c.param1;
    if (param2) *param2 = c.param2;
    return 1;
}

__declspec(dllexport)
int wsf_shm_process_new_commands(void) {
    if (!g_shm_base) return 0;
    ShmHeader hdr;
    read_header(&hdr);
    if (hdr.cmd_in == g_last_cmd_in) return 0;

    uint32_t new = hdr.cmd_in - g_last_cmd_in;
    if (new > MAX_CMDS) new = MAX_CMDS;

    for (uint32_t i = 0; i < new; i++) {
        uint32_t idx = (g_last_cmd_in + i) % MAX_CMDS;
        CmdEntry c;
        read_cmd(&c, idx);
        debug_log("WSF_SHM_CMD[%u] type=%u target=%u param1=%u param2=%u\n",
                  c.cmd_id, c.type, c.target_id, c.param1, c.param2);
    }

    advance_cmd_out(new);
    g_last_cmd_in = hdr.cmd_in;
    return (int)new;
}

/* =========================================================================
   PUBLIC API - Python ctypes WRITES commands via these functions
   ========================================================================= */

/* Create and initialize shared memory (call from Python first) */
__declspec(dllexport)
int wsf_shm_create(const char *name) {
    return create_shm(name, MAX_SHM_SIZE);
}

/* Write a command entry to the SHM (Python calls this) */
__declspec(dllexport)
int wsf_shm_write_cmd(uint8_t type, uint32_t target_id, uint32_t param1, uint32_t param2) {
    if (!g_shm_base) return 0;
    ShmHeader hdr;
    read_header(&hdr);

    uint32_t index = hdr.cmd_in % MAX_CMDS;
    uint8_t *base = (uint8_t *)g_shm_base + CMD_OFFSET;

    CmdEntry cmd;
    memset(&cmd, 0, sizeof(CmdEntry));
    cmd.cmd_id = hdr.cmd_in + 1;
    cmd.type = type;
    cmd.target_id = target_id;
    cmd.param1 = param1;
    cmd.param2 = param2;

    memcpy(base + index * sizeof(CmdEntry), &cmd, sizeof(CmdEntry));

    hdr.cmd_in++;
    write_header(&hdr);
    debug_log("WSF_SHM_WRITE: type=%u target=%u param1=%u param2=%u cmd_in=%u\n",
              type, target_id, param1, param2, hdr.cmd_in);
    return 1;
}

/* Write a track entry to the SHM (Python can also write tracks for AFSIM to consume) */
__declspec(dllexport)
int wsf_shm_write_track(uint32_t track_id, double lat, double lon,
                        double alt_m, double vel_mps, double heading_deg) {
    if (!g_shm_base) return 0;
    ShmHeader hdr;
    read_header(&hdr);

    if (hdr.track_count >= MAX_TRACKS) return 0;

    uint8_t *base = (uint8_t *)g_shm_base + TRACK_OFFSET;
    TrackEntry t;
    memset(&t, 0, sizeof(TrackEntry));
    t.track_id = track_id;
    t.lat = lat;
    t.lon = lon;
    t.alt_m = alt_m;
    t.vel_mps = vel_mps;
    t.heading_deg = heading_deg;
    t.track_type = 1;

    memcpy(base + hdr.track_count * sizeof(TrackEntry), &t, sizeof(TrackEntry));
    hdr.track_count++;
    write_header(&hdr);
    return 1;
}

/* Clear all tracks (reset track buffer) */
__declspec(dllexport)
int wsf_shm_clear_tracks(void) {
    if (!g_shm_base) return 0;
    ShmHeader hdr;
    read_header(&hdr);
    hdr.track_count = 0;
    write_header(&hdr);
    return 1;
}

/* DLL entry point */
BOOL WINAPI DllMain(HINSTANCE hinstDLL, DWORD fdwReason, LPVOID lpvReserved) {
    (void)hinstDLL;
    (void)lpvReserved;
    if (fdwReason == DLL_PROCESS_DETACH) {
        close_shm();
    }
    return TRUE;
}
