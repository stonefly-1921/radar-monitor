#include <gtest/gtest.h>
#include "ucs_types.h"

TEST(WeaponAssignCmdTest, EncodeProducesValidMessage) {
    WeaponAssignCmd cmd;
    cmd.weapon_id = 101;
    cmd.target_id = 5;
    cmd.priority = 1;
    
    std::vector<uint8_t> encoded = cmd.Encode();
    
    EXPECT_GT(encoded.size(), 0);
    EXPECT_EQ(encoded[0], static_cast<uint8_t>(UciMessageType::WEAPON_ASSIGN));
}

TEST(WeaponAssignCmdTest, WeaponIdEncoding) {
    WeaponAssignCmd cmd;
    cmd.weapon_id = 0x01020304;  // Big-endian test
    cmd.target_id = 1;
    cmd.priority = 1;
    
    std::vector<uint8_t> encoded = cmd.Encode();
    
    // Bytes 3-6 should contain weapon_id
    EXPECT_EQ(encoded[3], 0x04);  // LSB
    EXPECT_EQ(encoded[4], 0x03);
    EXPECT_EQ(encoded[5], 0x02);
    EXPECT_EQ(encoded[6], 0x01);  // MSB
}

TEST(SensorControlCmdTest, EncodeProducesValidMessage) {
    SensorControlCmd cmd;
    cmd.sensor_id = 3;
    cmd.mode = SensorMode::TRACK;
    cmd.azimuth_center = 45.0;
    cmd.elevation_center = 0.0;
    
    std::vector<uint8_t> encoded = cmd.Encode();
    
    EXPECT_GT(encoded.size(), 0);
    EXPECT_EQ(encoded[0], static_cast<uint8_t>(UciMessageType::SENSOR_CONTROL));
    EXPECT_EQ(encoded[7], static_cast<uint8_t>(SensorMode::TRACK));
}

TEST(SensorControlCmdTest, DoubleEncoding) {
    SensorControlCmd cmd;
    cmd.sensor_id = 1;
    cmd.mode = SensorMode::SEARCH;
    cmd.azimuth_center = 123.456;
    cmd.elevation_center = 78.9;
    
    std::vector<uint8_t> encoded = cmd.Encode();
    
    // Should have message type, length, sensor_id, mode, 8 bytes azimuth, 8 bytes elevation
    EXPECT_GE(encoded.size(), 20);
}

TEST(EngageCmdTest, EncodeProducesValidMessage) {
    EngageCmd cmd;
    cmd.weapon_id = 50;
    cmd.target_id = 12;
    cmd.holdfire = false;
    
    std::vector<uint8_t> encoded = cmd.Encode();
    
    EXPECT_GT(encoded.size(), 0);
    EXPECT_EQ(encoded[0], static_cast<uint8_t>(UciMessageType::ENGAGE_COMMAND));
}

TEST(EngageCmdTest, HoldfireEncoding) {
    EngageCmd cmd;
    cmd.weapon_id = 1;
    cmd.target_id = 1;
    cmd.holdfire = true;
    
    std::vector<uint8_t> encoded = cmd.Encode();
    
    // Last byte should be 1 for holdfire=true
    EXPECT_EQ(encoded.back(), 1);
    
    cmd.holdfire = false;
    encoded = cmd.Encode();
    EXPECT_EQ(encoded.back(), 0);
}