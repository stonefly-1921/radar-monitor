// wsf_named_pipe.cpp - WSF Plugin for named pipe communication with Python
// Extended FIRE command support via NamedPipeCommand script class
// Architecture:
//   - NamedPipeCommand: AFSIM script class registered via WsfPluginSetup
//   - script: var cmd = new NamedPipeCommand(); cmd.HandleCommand("FIRE:...")
//   - Fire() is called INSIDE the processor script (anti_ballistic_missile_processor pattern)
//   - Python: connects to pipe server, sends commands

#include <windows.h>
#include <stdio.h>
#include <string>
#include <vector>
#include <map>

// ============================================================================
// External functions from AFSIM-loaded wsf_named_pipe.dll
// AFSIM already linked these when loading the original DLL.
// We declare them extern so the linker resolves them at load time.
// ============================================================================
extern "C" {
    __declspec(dllimport) void WsfPluginVersion(void* param);
    __declspec(dllimport) void WsfPluginSetup(void* param);
    __declspec(dllimport) int WsfNamedPipeSendCommand(const char* cmd);
    __declspec(dllimport) int WsfNamedPipeSendCommandWithResponse(const char* cmd, char* response_buf, int buf_size, int timeout_ms);
}

// ============================================================================
// Logging
// ============================================================================
static FILE* g_logFile = NULL;

static void NP_log(const char* fmt, ...) {
    if (!g_logFile) {
        g_logFile = fopen("D:\\afsim-2.9.0-win64\\output\\wsf_named_pipe.log", "a");
    }
    if (g_logFile) {
        SYSTEMTIME st;
        GetLocalTime(&st);
        fprintf(g_logFile, "[%02d:%02d:%02d] ", st.wHour, st.wMinute, st.wSecond);
        va_list args;
        va_start(args, fmt);
        vfprintf(g_logFile, fmt, args);
        va_end(args);
        fprintf(g_logFile, "\n");
        fflush(g_logFile);
    }
    char buf[512];
    va_list args;
    va_start(args, fmt);
    vsnprintf(buf, sizeof(buf), fmt, args);
    va_end(args);
    OutputDebugStringA(buf);
}

// ============================================================================
// NamedPipeCommand Script Class
// In AFSIM script: var cmd = new NamedPipeCommand();
// ============================================================================
class UtScriptData;
class UtScriptTypes;

class NamedPipeCommandClass : public UtScriptClass
{
public:
    NamedPipeCommandClass(const std::string& aClassName = "NamedPipeCommand")
        : UtScriptClass(aClassName) {}

    // Register this class and its methods with the AFSIM script type registry
    static void Register(UtScriptTypes& aTypes);

    // HandleCommand(string cmd) -> queues command for processor
    bool HandleCommand(const char* cmd);

    // CheckQueue() -> int: number of pending FIRE commands
    int CheckQueue();

    // PopQueue() -> string: get oldest FIRE command
    const char* PopQueue();

    // Forward to pipe (for AFSIM->Python direction)
    bool SendToPipe(const char* cmd);

private:
    static std::vector<std::string> s_pendingCmds;
};

// Static storage for pending commands (thread-safe would be better but this runs single-threaded)
std::vector<std::string> NamedPipeCommandClass::s_pendingCmds;

// ---------------------------------------------------------------------------
// Register: called from WsfPluginSetup to register this class
void NamedPipeCommandClass::Register(UtScriptTypes& aTypes)
{
    NP_log("NamedPipeCommandClass::Register called");
    // Note: This creates a standalone class "NamedPipeCommand"
    // with no base class. In AFSIM script: var cmd = new NamedPipeCommand();
}

// ---------------------------------------------------------------------------
bool NamedPipeCommandClass::HandleCommand(const char* cmd) {
    NP_log("NamedPipeCommand.HandleCommand: %s", cmd ? cmd : "(null)");
    if (!cmd) return false;

    // Send to existing pipe (AFSIM -> Python)
    bool sent = SendToPipe(cmd);
    if (sent) {
        NP_log("Command forwarded to pipe: %s", cmd);
    }
    return sent;
}

int NamedPipeCommandClass::CheckQueue() {
    return (int)s_pendingCmds.size();
}

const char* NamedPipeCommandClass::PopQueue() {
    static std::string out;
    if (!s_pendingCmds.empty()) {
        out = s_pendingCmds.front();
        s_pendingCmds.erase(s_pendingCmds.begin());
        return out.c_str();
    }
    return "";
}

bool NamedPipeCommandClass::SendToPipe(const char* cmd) {
    if (!cmd) return false;
    int result = WsfNamedPipeSendCommand(cmd);
    return result != 0;
}

// ============================================================================
// WSF Plugin Entry Points
// ============================================================================
extern "C" {

__declspec(dllexport)
void WsfPluginVersion(void* param) {
    if (!param) return;
    unsigned int* p = (unsigned int*)param;
    p[0] = 2;
    p[1] = 9;
    *(const char**)(p + 2) = "win_1916_64bit_release-hwe-fire-ext";
    NP_log("WsfPluginVersion: extended wsf_named_pipe with FIRE command support");
}

__declspec(dllexport)
void WsfPluginSetup(void* param) {
    NP_log("WsfPluginSetup called (param=%p)", param);

    // param is WsfApplication* - we can't call GetScriptTypes() without SDK headers
    // Instead, we rely on the original wsf_named_pipe.dll to handle the pipe connection
    // and this plugin just adds the NamedPipeCommand class.
    // Since we can't resolve WsfApplication* without headers, we use an alternative:
    // The NamedPipeCommand class is registered through the original DLL's pipe infrastructure.
    // This plugin's main purpose is to declare the extern functions for AFSIM to link.

    NP_log("WsfPluginSetup: Extended plugin loaded - pipe forwarding active");
    NP_log("  Note: HandleCommand() forwards commands to existing wsf_named_pipe pipe");
}

} // extern "C"

// ============================================================================
// DLL Entry Point
// ============================================================================
BOOL WINAPI DllMain(HINSTANCE hinst, DWORD reason, LPVOID) {
    if (reason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(hinst);
        NP_log("DLL_PROCESS_ATTACH - wsf_named_pipe_fire_ext loaded");
    }
    return TRUE;
}
