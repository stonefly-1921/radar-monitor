#include <gtest/gtest.h>
#include "shm_client.h"

TEST(TrackEntryTest, CanCreateAndAccess) {
    TrackEntry entry{};
    entry.track_id = 1;
    entry.lat = 30.0;
    entry.lon = 120.0;
    entry.altitude = 5000.0;
    entry.velocity = 300.0;
    entry.heading = 90.0;
    entry.target_type = TargetType::AIRCRAFT;
    entry.timestamp_ms = 1234567890;
    
    EXPECT_EQ(entry.track_id, 1);
    EXPECT_EQ(entry.lat, 30.0);
    EXPECT_EQ(entry.target_type, TargetType::AIRCRAFT);
}

TEST(AllocationResultTest, CanCreateAndAccess) {
    AllocationResult result{};
    result.target_id = 5;
    result.sensor_id = 2;
    result.weapon_id = 3;
    result.priority_score = 0.85;
    result.intercept_time_sec = 15.5;
    result.kill_probability = 0.8;
    
    EXPECT_EQ(result.target_id, 5);
    EXPECT_EQ(result.sensor_id, 2);
    EXPECT_EQ(result.weapon_id, 3);
    EXPECT_GT(result.priority_score, 0.8);
}

TEST(ShmClientTest, ConstructorAndConnect) {
    ShmClient client("test_shm");
    EXPECT_FALSE(client.IsConnected());
    
    bool connected = client.Connect();
    EXPECT_TRUE(connected);
    EXPECT_TRUE(client.IsConnected());
    
    client.Disconnect();
    EXPECT_FALSE(client.IsConnected());
}