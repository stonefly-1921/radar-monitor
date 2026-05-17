#include "shm_client.h"
#include <cstring>

ShmClient::ShmClient(const char* shm_name) 
    : shm_name_(shm_name), shm_addr_(nullptr), connected_(false) {}

ShmClient::~ShmClient() {
    Disconnect();
}

bool ShmClient::Connect() {
    // Placeholder - real impl would map shared memory
    connected_ = true;
    return true;
}

void ShmClient::Disconnect() {
    // Placeholder - real impl would unmap shared memory
    if (connected_ && shm_addr_ != nullptr) {
        // Unmap memory
    }
    connected_ = false;
    shm_addr_ = nullptr;
}

std::vector<TrackEntry> ShmClient::GetTrackUpdates() {
    return {};  // Placeholder
}

bool ShmClient::SendAllocationCommand(const AllocationResult& allocation) {
    return connected_;
}