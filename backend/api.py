"""
雷达仿真 - FastAPI 应用
"""
import os
from pathlib import Path
from typing import List

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

from simulator import get_simulator


app = FastAPI(title="Radar Monitor API")

# 确定 frontend 目录路径
BACKEND_DIR = Path(__file__).parent
FRONTEND_DIR = BACKEND_DIR.parent / "frontend"

# 挂载静态文件
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


# ========== 请求模型 ==========

class PowerRequest(BaseModel):
    state: str  # "on" or "off"

class ModeRequest(BaseModel):
    mode: str  # "spin" or "stop"

class SteerRequest(BaseModel):
    azimuth: float
    elevation: float

class SearchZoneRequest(BaseModel):
    azimuth_lo: float
    azimuth_hi: float
    elevation_lo: float
    elevation_hi: float
    range_min: float
    range_max: float

class HighlightRequest(BaseModel):
    target_ids: List[int]

class TargetCountRequest(BaseModel):
    count: int

class SearchZoneRequest(BaseModel):
    azimuth_lo: float
    azimuth_hi: float
    elevation_lo: float
    elevation_hi: float
    range_min: float
    range_max: float

class IdentifyRequest(BaseModel):
    target_id: int
    model: str

class ChatRequest(BaseModel):
    message: str


# ========== API 路由 ==========

@app.get("/api/state")
def get_state():
    """返回仿真器完整状态快照"""
    sim = get_simulator()
    return sim.get_state_snapshot()

@app.post("/api/power")
def set_power(req: PowerRequest):
    """开机/关机"""
    sim = get_simulator()
    if req.state == "on":
        sim.set_mode("spin")
        sim.set_power(True)
    else:
        sim.set_power(False)
    return {"ok": True, "power": sim.state.power}

@app.post("/api/mode")
def set_mode(req: ModeRequest):
    """设置雷达模式"""
    sim = get_simulator()
    sim.set_mode(req.mode)
    return {"ok": True, "mode": sim.state.mode}

@app.post("/api/steer")
def set_steer(req: SteerRequest):
    """设置法线指向"""
    sim = get_simulator()
    sim.set_steer(req.azimuth, req.elevation)
    return {"ok": True, "steer_azimuth_deg": sim.state.steer_azimuth_deg, "steer_elevation_deg": sim.state.steer_elevation_deg}

@app.post("/api/search_zone")
def set_search_zone(req: SearchZoneRequest):
    """设置搜索区"""
    sim = get_simulator()
    sim.set_search_zone(
        req.azimuth_lo, req.azimuth_hi,
        req.elevation_lo, req.elevation_hi,
        req.range_min, req.range_max,
    )
    return {"ok": True}

@app.post("/api/highlight")
def set_highlight(req: HighlightRequest):
    """设置高亮目标"""
    sim = get_simulator()
    sim.set_highlight(req.target_ids)
    return {"ok": True, "highlighted_ids": sim.state.highlighted_ids}

@app.post("/api/identify")
def identify_target(req: IdentifyRequest):
    """对指定目标进行识别，挂载型号（下次检测到目标时生效）"""
    sim = get_simulator()
    target = next((t for t in sim.targets if t.id == req.target_id), None)
    if not target:
        return {"ok": False, "error": "目标不存在"}
    target.pending_identification = req.model
    return {"ok": True, "target_id": req.target_id, "pending_identification": req.model}

@app.post("/api/target_count")
def set_target_count(req: TargetCountRequest):
    """设置目标数量"""
    sim = get_simulator()
    sim.set_target_count(req.count)
    return {"ok": True, "count": req.count}

@app.post("/api/tasEngage")
def tas_engage(req: dict):
    """对指定目标进行TAS跟踪
    Body: {"target_id": int, "data_rate": int}  # data_rate: 1/5/10 Hz
    """
    sim = get_simulator()
    target_id = req.get("target_id")
    data_rate = req.get("data_rate", 1)
    if target_id is None:
        return {"ok": False, "error": "缺少target_id"}
    if data_rate not in (1, 5, 10):
        return {"ok": False, "error": "data_rate必须是1/5/10"}
    ok, err = sim.tas_engage(target_id, data_rate)
    if not ok:
        return {"ok": False, "error": err}
    return {"ok": True, "target_id": target_id, "data_rate": data_rate}

@app.post("/api/tasDisengage")
def tas_disengage(req: dict):
    """取消指定目标的TAS跟踪
    Body: {"target_id": int}
    """
    sim = get_simulator()
    target_id = req.get("target_id")
    if target_id is None:
        return {"ok": False, "error": "缺少target_id"}
    ok, err = sim.tas_disengage(target_id)
    if not ok:
        return {"ok": False, "error": err}
    return {"ok": True, "target_id": target_id}

@app.post("/api/simulation/reset")
def simulation_reset():
    """重置仿真：清除所有目标的跟踪和识别状态"""
    sim = get_simulator()
    sim.reset_targets()
    return {"ok": True}


# ========== 雷达智能脑 Chat 接口 ==========

import subprocess

@app.post("/api/agent/chat")
def agent_chat(req: ChatRequest):
    """将自然语言命令转发给雷达智能脑 agent 处理"""
    import subprocess
    try:
        result = subprocess.run(
            ["python", "E:/radar-brain/run.py", req.message],
            capture_output=True,
            text=True,
            timeout=120,
            cwd="E:/radar-brain",
        )
        response_text = result.stdout.strip() if result.stdout else result.stderr.strip()
        return {"ok": True, "response": response_text}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "超时（120秒）"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/agent/skills")
def list_skills():
    """列出 radar-brain/skills/ 下的所有子目录（Skill 列表）"""
    skills_dir = BACKEND_DIR.parent / "radar-brain" / "skills"
    if not skills_dir.exists():
        return {"skills": []}
    skills = [d.name for d in skills_dir.iterdir() if d.is_dir() and not d.name.startswith("__")]
    return {"skills": sorted(skills)}


@app.get("/api/agent/config")
def get_agent_config():
    """读取 radar-brain 配置（大模型选择等）"""
    from radar_agent.config import get_config
    cfg = get_config()
    return {
        "model_provider": cfg.model_provider,
        "ollama_model": cfg.ollama.model,
        "memory_last_sync": None,
    }


@app.post("/api/agent/config")
def update_agent_config(req: dict):
    """更新 radar-brain 配置（大模型选择等）"""
    from radar_agent.config import get_config, reload_config
    cfg = get_config()
    if "model_provider" in req:
        cfg.model_provider = req["model_provider"]
    if "ollama_model" in req:
        cfg.ollama.model = req["ollama_model"]
    cfg.save()
    reload_config()
    return {"ok": True}


# ========== 前端入口 ==========

@app.get("/")
def index():
    """返回前端页面"""
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return HTMLResponse(content="<h1>Frontend not found</h1><p>Please place index.html in the frontend/ directory.</p>", status_code=404)


@app.get("/unified")
def unified():
    """返回统一界面"""
    unified_path = FRONTEND_DIR / "unified.html"
    if unified_path.exists():
        return FileResponse(str(unified_path))
    return HTMLResponse(content="<h1>unified.html not found</h1>", status_code=404)


# ========== 配置读写接口 ==========

CONFIG_FILE = Path(__file__).parent.parent / "radar-brain" / "config.yaml"

@app.get("/api/config")
def get_config():
    """读取 radar-brain/config.yaml 配置"""
    if CONFIG_FILE.exists():
        import json
        return json.loads(CONFIG_FILE.read_text())
    return {}

@app.post("/api/config/save")
def save_config(req: dict):
    """保存配置到 radar-brain/config.yaml"""
    import json
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(req, indent=2, ensure_ascii=False))
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
