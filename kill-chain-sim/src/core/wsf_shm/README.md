# wsf_shm - AFSIM Shared Memory Command Plugin

Reads kill chain commands from shared memory and executes them in AFSIM.

## Build Requirements

- Visual Studio 2022 with C++ Desktop Development
- AFSIM 2.9.0 SDK (swdev source tree)
- CMake 3.14+

## Build Instructions

### Option 1: Integrate into AFSIM SDK Build

```bat
:: 1. Copy this directory into the AFSIM plugin tree
xcopy /E src\core\wsf_shm C:\path\to\afsim\swdev\src\wsf_plugins\wsf_shm\

:: 2. Add to wsf_plugins/CMakeLists.txt
echo add_subdirectory(wsf_shm) >> C:\path\to\afsim\swdev\src\wsf_plugins\CMakeLists.txt

:: 3. Open AFSIM solution in Visual Studio 2022
::    ($AFSIM/swdev/AFSIM.sln or Mission.sln)
:: 4. Build wsf_shm project → wsf_shm.dll
:: 5. Copy wsf_shm.dll to $AFSIM/bin/wsf_plugins/
```

### Option 2: Standalone Stub (CI only)

Without AFSIM SDK headers, builds a stub DLL (non-functional):

```bash
cd src/core/wsf_shm
cmake -B build .
cmake --build build --config Release
```

## AFSIM Scenario Usage

```
extension shm_interface
   shm_name kill_chain_shm
   debug true
end_extension
```

Then in the scenario, a script processor can trigger SHM command processing:

```
on_update
   WsfShmExtension* shm = static_cast<WsfShmExtension*>(
       GetScenario().FindExtension("shm_interface"));
   if (shm) shm.Update(TIME_NOW);
end_on_update
```

## SHM Memory Layout

| Offset | Size | Field |
|--------|------|-------|
| 0 | 128B | Header (track_count, timestamp, cmd_in, cmd_out) |
| 128 | 64KB | Tracks (256 × 64B each) |
| 66KB | 16KB | Sensors |
| 82KB | 16KB | Weapons |
| 98KB | 32KB | Commands (256 × 44B) |
| 130KB | 16KB | Command Acks |
| 146KB | 8B | Fence |

See `src/core/shared_mem/shm_types.h` for full structure definitions.

## Command Types

| Type | Description | Params |
|------|-------------|--------|
| 1 | SENSOR_CONTROL | param1=sensor_id, param2=mode |
| 2 | WEAPON_ASSIGN | param1=weapon_id, param2=target_track_id |
| 3 | ENGAGE | param1=target_track_id |

## Platform Integration

The extension looks up platforms by:
- `FindPlatformById(uint32_t platformIndex)` — by scenario index
- `FindPlatformByName(string)` — by platform name

These require full WsfScenario.hpp / WsfPlatform.hpp SDK headers.

## Status

- SHM read loop: implemented
- Platform lookup: stub (requires SDK headers)
- Sensor/Weapon/Engage execution: stub (requires SDK headers)
- Full build: pending VS2022 + AFSIM SDK environment
