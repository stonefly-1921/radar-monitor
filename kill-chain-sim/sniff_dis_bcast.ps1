# DIS sniffer - listen on port 3225 unicast/broadcast
$ErrorActionPreference = "SilentlyContinue"
$UdpClient = New-Object System.Net.Sockets.UdpClient
$UdpClient.Client.SetSocketOption([System.Net.Sockets.SocketOptionLevel]::Socket, [System.Net.Sockets.SocketOptionName]::ReuseAddress, 1)
$UdpClient.Client.Bind([System.Net.IPEndPoint]::new([System.Net.IPAddress]::Any, 3225))
$UdpClient.Client.ReceiveTimeout = 35000

Write-Host "Listening on 0.0.0.0:3225..."
$received = 0

try {
    while ($true) {
        $data = $UdpClient.Receive([System.Net.IPEndPoint]::new([System.Net.IPAddress]::Any, 0))
        if ($data.Length -gt 2) {
            $pduType = $data[2]
            Write-Host "Type=$pduType len=$($data.Length)"
            $received++
        }
    }
} catch [System.Net.Sockets.SocketException] {
    Write-Host "Socket timeout - no more PDUs (received $received total)"
}
$UdpClient.Close()