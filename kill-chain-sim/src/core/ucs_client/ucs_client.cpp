#include "ucs_client.h"
#include <cstring>

UcsClient::UcsClient(const char* host, uint16_t port)
    : host_(host), port_(port), socket_fd_(-1), connected_(false) {}

UcsClient::~UcsClient() {
    Disconnect();
}

bool UcsClient::Connect() {
    // Placeholder - real impl would connect TCP socket
    connected_ = true;
    return true;
}

void UcsClient::Disconnect() {
    if (socket_fd_ >= 0) {
        // closesocket(socket_fd_);
    }
    connected_ = false;
    socket_fd_ = -1;
}

bool UcsClient::SendRaw(const std::vector<uint8_t>& data) {
    if (!connected_) {
        last_error_ = "Not connected";
        return false;
    }
    // Placeholder - real impl would send to socket
    return true;
}

bool UcsClient::SendWeaponAssign(const WeaponAssignCmd& cmd) {
    return SendRaw(cmd.Encode());
}

bool UcsClient::SendSensorControl(const SensorControlCmd& cmd) {
    return SendRaw(cmd.Encode());
}

bool UcsClient::SendEngageCommand(const EngageCmd& cmd) {
    return SendRaw(cmd.Encode());
}