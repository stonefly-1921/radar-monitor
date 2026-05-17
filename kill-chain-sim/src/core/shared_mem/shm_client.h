#pragma once
#include "shm_types.h"
#include <string>

class ShmClient {
public:
    explicit ShmClient(const char* shm_name);
    ~ShmClient();
    
    bool Connect();
    void Disconnect();
    bool IsConnected() const { return connected_; }
    
    std::vector<TrackEntry> GetTrackUpdates();
    bool SendAllocationCommand(const AllocationResult& allocation);
    
private:
    std::string shm_name_;
    void* shm_addr_;
    bool connected_;
};