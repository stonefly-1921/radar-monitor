#pragma once
#include <cstdint>
#include <vector>
#include <string>

enum class UciMessageType : uint8_t {
    WEAPON_ASSIGN = 0x01,
    SENSOR_CONTROL = 0x02,
    ENGAGE_COMMAND = 0x03,
    ASSESSMENT_REQUEST = 0x04,
    TRACK_UPDATE = 0x05,
    STATUS_REPORT = 0x06
};

enum class SensorMode : uint8_t {
    SEARCH = 0x01,
    TRACK = 0x02,
    ACM = 0x03,  // Air Combat Maneuver
    STARE = 0x04
};

struct WeaponAssignCmd {
    uint32_t weapon_id;
    uint32_t target_id;
    uint8_t priority;
    
    std::vector<uint8_t> Encode() const {
        std::vector<uint8_t> msg;
        msg.push_back(static_cast<uint8_t>(UciMessageType::WEAPON_ASSIGN));
        msg.push_back(0);  // length placeholder
        msg.push_back(0);
        // Encode fields
        msg.push_back(static_cast<uint8_t>(weapon_id & 0xFF));
        msg.push_back(static_cast<uint8_t>((weapon_id >> 8) & 0xFF));
        msg.push_back(static_cast<uint8_t>((weapon_id >> 16) & 0xFF));
        msg.push_back(static_cast<uint8_t>((weapon_id >> 24) & 0xFF));
        msg.push_back(static_cast<uint8_t>(target_id & 0xFF));
        msg.push_back(static_cast<uint8_t>((target_id >> 8) & 0xFF));
        msg.push_back(static_cast<uint8_t>((target_id >> 16) & 0xFF));
        msg.push_back(static_cast<uint8_t>((target_id >> 24) & 0xFF));
        msg.push_back(priority);
        msg[1] = static_cast<uint8_t>(msg.size() & 0xFF);
        msg[2] = static_cast<uint8_t>((msg.size() >> 8) & 0xFF);
        return msg;
    }
};

struct SensorControlCmd {
    uint32_t sensor_id;
    SensorMode mode;
    double azimuth_center;
    double elevation_center;
    
    std::vector<uint8_t> Encode() const {
        std::vector<uint8_t> msg;
        msg.push_back(static_cast<uint8_t>(UciMessageType::SENSOR_CONTROL));
        msg.push_back(0);
        msg.push_back(0);
        msg.push_back(static_cast<uint8_t>(sensor_id & 0xFF));
        msg.push_back(static_cast<uint8_t>((sensor_id >> 8) & 0xFF));
        msg.push_back(static_cast<uint8_t>((sensor_id >> 16) & 0xFF));
        msg.push_back(static_cast<uint8_t>((sensor_id >> 24) & 0xFF));
        msg.push_back(static_cast<uint8_t>(mode));
        // azimuth (4 bytes double)
        uint8_t* az = reinterpret_cast<uint8_t*>(&azimuth_center);
        for (int i = 0; i < 4; ++i) msg.push_back(az[i]);
        // elevation (4 bytes double)
        uint8_t* el = reinterpret_cast<uint8_t*>(&elevation_center);
        for (int i = 0; i < 4; ++i) msg.push_back(el[i]);
        msg[1] = static_cast<uint8_t>(msg.size() & 0xFF);
        msg[2] = static_cast<uint8_t>((msg.size() >> 8) & 0xFF);
        return msg;
    }
};

struct EngageCmd {
    uint32_t weapon_id;
    uint32_t target_id;
    bool holdfire;
    
    std::vector<uint8_t> Encode() const {
        std::vector<uint8_t> msg;
        msg.push_back(static_cast<uint8_t>(UciMessageType::ENGAGE_COMMAND));
        msg.push_back(0);
        msg.push_back(0);
        msg.push_back(static_cast<uint8_t>(weapon_id & 0xFF));
        msg.push_back(static_cast<uint8_t>((weapon_id >> 8) & 0xFF));
        msg.push_back(static_cast<uint8_t>((weapon_id >> 16) & 0xFF));
        msg.push_back(static_cast<uint8_t>((weapon_id >> 24) & 0xFF));
        msg.push_back(static_cast<uint8_t>(target_id & 0xFF));
        msg.push_back(static_cast<uint8_t>((target_id >> 8) & 0xFF));
        msg.push_back(static_cast<uint8_t>((target_id >> 16) & 0xFF));
        msg.push_back(static_cast<uint8_t>((target_id >> 24) & 0xFF));
        msg.push_back(holdfire ? 1 : 0);
        msg[1] = static_cast<uint8_t>(msg.size() & 0xFF);
        msg[2] = static_cast<uint8_t>((msg.size() >> 8) & 0xFF);
        return msg;
    }
};