#pragma once
#include "ucs_types.h"
#include <string>
#include <vector>

class UcsClient {
public:
    UcsClient(const char* host, uint16_t port);
    ~UcsClient();
    
    bool Connect();
    void Disconnect();
    bool IsConnected() const { return connected_; }
    
    bool SendWeaponAssign(const WeaponAssignCmd& cmd);
    bool SendSensorControl(const SensorControlCmd& cmd);
    bool SendEngageCommand(const EngageCmd& cmd);
    
    std::string LastError() const { return last_error_; }
    
private:
    bool SendRaw(const std::vector<uint8_t>& data);
    
    std::string host_;
    uint16_t port_;
    int socket_fd_;
    bool connected_;
    std::string last_error_;
};