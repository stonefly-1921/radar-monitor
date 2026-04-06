# 雷达监控系统 - 部署说明

> 项目路径: `/root/.openclaw/agents/radarmonitornew/`
> 目标平台: Ubuntu（20.04+）
> 后端端口: 8000（代码默认）
> 内网穿透: natapp

---

## 1. 环境要求

### 1.1 基础环境

| 组件 | 要求 | 说明 |
|------|------|------|
| 操作系统 | Ubuntu 20.04+ / Debian 11+ | 其他 Linux 发行版亦可 |
| Python | 3.8+ | 建议 3.10 或更高 |
| pip | 最新版 | `python3 -m ensurepip --upgrade` |
| 网络 | 能访问 natapp 服务器 | 用于内网穿透 |

### 1.2 硬件要求

- **最低**: 1 核 CPU，512MB 内存（纯仿真，无 GPU 需求）
- **推荐**: 2 核 CPU，1GB 内存
- **网络**: 有公网 IP 或能连接 natapp 服务器

---

## 2. 项目结构

```
radarmonitornew/
├── backend/
│   ├── api.py           # FastAPI 应用入口
│   ├── simulator.py     # 仿真引擎
│   ├── models.py        # 数据模型
│   └── requirements.txt # Python 依赖
├── frontend/
│   └── index.html       # 前端单文件（PPI显示器）
├── DESIGN.md            # 设计说明
├── DEPLOY.md            # 本文档
├── API.md               # 对外接口说明
└── .gitignore
```

---

## 3. 依赖安装

### 3.1 方式一：使用 requirements.txt（推荐）

```bash
cd /root/.openclaw/agents/radarmonitornew/backend
pip install -r requirements.txt
```

### 3.2 方式二：手动安装

```bash
pip install fastapi==0.115.0 uvicorn[standard]==0.30.0 pydantic==2.9.0
```

### 3.3 验证安装

```bash
python3 -c "import fastapi, uvicorn, pydantic; print('依赖安装成功')"
```

---

## 4. 后端启动

### 4.1 直接启动（开发/调试用）

```bash
cd /root/.openclaw/agents/radarmonitornew/backend
python3 -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

参数说明：
- `--host 0.0.0.0` — 监听所有网卡（允许外部访问）
- `--port 8000` — 服务端口
- `--reload` — 开发模式，热重载（代码变更自动重启）

### 4.2 生产环境启动（后台运行）

```bash
cd /root/.openclaw/agents/radarmonitornew/backend
nohup python3 -m uvicorn api:app --host 0.0.0.0 --port 8000 > /var/log/radar.log 2>&1 &
echo $!  # 记录 PID
```

### 4.3 多进程生产模式

```bash
cd /root/.openclaw/agents/radarmonitornew/backend
nohup python3 -m uvicorn api:app --host 0.0.0.0 --port 8000 --workers 2 > /var/log/radar.log 2>&1 &
```

---

## 5. 前端访问

前端通过 FastAPI 静态文件服务托管，无需额外配置。

### 5.1 通过后端直接访问

后端已配置静态文件服务：

```
/            → frontend/index.html
/static/*    → frontend/*  （所有静态资源）
```

访问地址：
- 本机: `http://localhost:8000/`
- 局域网: `http://<本机IP>:8000/`
- natapp 穿透后: `http://<natapp分配的域名>/`

### 5.2 通过 nginx 托管（可选）

如果希望通过 nginx 反向代理或独立托管：

```nginx
server {
    listen 80;
    server_name radar.example.com;

    # 前端静态文件
    location / {
        root /root/.openclaw/agents/radarmonitornew/frontend;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # API 反向代理到后端
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

nginx 配置测试并重载：

```bash
nginx -t && systemctl reload nginx
```

---

## 6. 内网穿透（natapp）

### 6.1 安装 natapp

```bash
# 下载（Linux 64-bit）
wget https://cdn.natapp.cn/assets/natapp natapp_linux_amd64 -O /usr/local/bin/natapp
chmod +x /usr/local/bin/natapp
```

其他版本: https://natapp.cn/download

### 6.2 配置 natapp

创建配置文件 `~/.natapp.cfg`：

```ini
[common]
authtoken = <你的authtoken>       # 从 natapp.cn 注册获取
clienttoken =                    # 可选，留空
log = /var/log/natapp.log
loglevel = error                 # 日志级别: debug, info, warn, error
```

或者直接在命令行指定：

```bash
natapp -authtoken=<你的authtoken>
```

### 6.3 启动 natapp

```bash
# 前台运行（测试用）
natapp

# 后台运行
nohup natapp -config ~/.natapp.cfg > /var/log/natapp.log 2>&1 &
```

### 6.4 验证穿透

启动后，natapp 会输出分配的公网 URL：

```
[URL] http://kfc72c9d.natappfree.cc
[Tunnel] TCP://127.0.0.1:8000 -> 127.0.0.1:8000
```

访问 `http://kfc72c9d.natappfree.cc/` 即可看到雷达界面。

---

## 7. 开机自启（systemd）

### 7.1 创建 systemd Service

```bash
sudo nano /etc/systemd/system/radar.service
```

内容：

```ini
[Unit]
Description=Radar PPI Monitor Backend
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/.openclaw/agents/radarmonitornew/backend
ExecStart=/usr/bin/python3 -m uvicorn api:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
StandardOutput=append:/var/log/radar_stdout.log
StandardError=append:/var/log/radar_stderr.log

[Install]
WantedBy=multi-user.target
```

### 7.2 启用并启动

```bash
# 重载 systemd
sudo systemctl daemon-reload

# 设为开机自启
sudo systemctl enable radar

# 立即启动
sudo systemctl start radar

# 查看状态
sudo systemctl status radar
```

### 7.3 natapp 开机自启（同理）

```bash
sudo nano /etc/systemd/system/natapp.service
```

```ini
[Unit]
Description=NATAPP Tunnel
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/natapp -config /root/.natapp.cfg
Restart=always
RestartSec=5
StandardOutput=append:/var/log/natapp.log
StandardError=append:/var/log/natapp.log

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable natapp
sudo systemctl start natapp
```

---

## 8. 防火墙配置

### 8.1 ufw（Ubuntu 默认）

```bash
# 开放后端端口（内网穿透时外部已可达，仅本地测试需要）
sudo ufw allow 8000/tcp

# 如果用 nginx 托管在 80 端口
sudo ufw allow 80/tcp
```

### 8.2 检查端口监听

```bash
ss -tlnp | grep 8000
# 应看到: 0.0.0.0:8000
```

---

## 9. 快速启动脚本

创建 `/root/.openclaw/agents/radarmonitornew/start.sh`：

```bash
#!/bin/bash
set -e

PROJECT_DIR="/root/.openclaw/agents/radarmonitornew"
BACKEND_DIR="$PROJECT_DIR/backend"
LOG_DIR="/var/log"
mkdir -p "$LOG_DIR"

echo "[1/3] 启动后端服务..."
cd "$BACKEND_DIR"
nohup python3 -m uvicorn api:app --host 0.0.0.0 --port 8000 \
  >> "$LOG_DIR/radar_backend.log" 2>&1 &

BACKEND_PID=$!
echo "后端 PID: $BACKEND_PID"

sleep 2

echo "[2/3] 启动 natapp 内网穿透..."
if [ -f /root/.natapp.cfg ]; then
    nohup natapp -config /root/.natapp.cfg \
      >> "$LOG_DIR/natapp.log" 2>&1 &
    echo "natapp 已启动"
else
    echo "警告: ~/.natapp.cfg 不存在，跳过内网穿透"
fi

echo "[3/3] 完成！"
echo "后端地址: http://localhost:8000/"
echo "前端地址: http://localhost:8000/"
echo "日志: $LOG_DIR/radar_backend.log"
```

```bash
chmod +x /root/.openclaw/agents/radarmonitornew/start.sh
```

---

## 10. 故障排查

| 问题 | 排查命令 | 解决方案 |
|------|---------|---------|
| 后端无法启动 | `python3 -c "import fastapi"` | 重新安装依赖 |
| 端口被占用 | `ss -tlnp \| grep 8000` | 杀掉占用进程或改端口 |
| natapp 连接失败 | `tail /var/log/natapp.log` | 检查 authtoken 是否正确 |
| 前端无法加载 | `curl http://localhost:8000/` | 检查 frontend/index.html 是否存在 |
| 仿真不运行 | `ps aux \| grep uvicorn` | 确认进程存在，检查日志 |

### 10.1 查看实时日志

```bash
# 后端日志
tail -f /var/log/radar_backend.log

# natapp 日志
tail -f /var/log/natapp.log
```

---

## 11. 快速验证

启动后，依次验证：

```bash
# 1. 检查后端 API
curl http://localhost:8000/api/state | python3 -m json.tool

# 2. 开机
curl -X POST http://localhost:8000/api/power \
  -H "Content-Type: application/json" \
  -d '{"state": "on"}'

# 3. 切换到转动模式
curl -X POST http://localhost:8000/api/mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "spin"}'

# 4. 再次获取状态
curl http://localhost:8000/api/state | python3 -m json.tool | head -50
```

预期：power=true, mode=spin, targets 有数据。
