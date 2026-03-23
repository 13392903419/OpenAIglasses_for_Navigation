# app_main.py
# -*- coding: utf-8 -*-
import os, sys, time, json, asyncio, base64, audioop

# ---- .env（必须尽早加载：很多模块在 import 时就读取环境变量）----
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass
from typing import Any, Dict, Optional, Tuple, List, Callable, Set, Deque
from collections import deque
from dataclasses import dataclass
import re
# 在其它 import 之后加：
from qwen_extractor import extract_english_label
from navigation_master import NavigationMaster, OrchestratorResult 
# 新增：导入盲道导航器
from workflow_blindpath import BlindPathNavigator
# 新增：导入过马路导航器
from workflow_crossstreet import CrossStreetNavigator
import torch
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Body
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from starlette.websockets import WebSocketState
import uvicorn
import cv2
import numpy as np
from ultralytics import YOLO
from obstacle_detector_client import ObstacleDetectorClient

import torch  # 添加这行


import mediapipe as mp
import bridge_io
import threading
import yolomedia  # 确保和 app_main.py 同目录，文件名就是 yolomedia.py
# ---- Windows 事件循环策略 ----
if sys.platform.startswith("win"):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass

# ---- DashScope ASR 基础 ----
from dashscope import audio as dash_audio  # 若未安装，会在原项目里抛错提示

API_KEY = os.getenv("DASHSCOPE_API_KEY", "sk-a673b9ac8f7e4a139e1569a6320e2caa")
if not API_KEY:
    raise RuntimeError("未设置 DASHSCOPE_API_KEY")

MODEL        = "paraformer-realtime-v2"
SAMPLE_RATE  = 16000
AUDIO_FMT    = "pcm"
CHUNK_MS     = 20
BYTES_CHUNK  = SAMPLE_RATE * CHUNK_MS // 1000 * 2
SILENCE_20MS = bytes(BYTES_CHUNK)

# ---- 引入我们的模块 ----
from audio_stream import (
    register_stream_route,         # 挂 /stream.wav
    broadcast_pcm16_realtime,      # 实时向连接分发 16k PCM
    hard_reset_audio,              # 音频+AI 播放总闸
    BYTES_PER_20MS_16K,
    is_playing_now,
    current_ai_task,
)
from omni_client import stream_chat, OmniStreamPiece
from asr_core import (
    ASRCallback,
    set_current_recognition,
    stop_current_recognition,
)
from audio_player import initialize_audio_system, play_voice_text

# ---- 同步录制器 ----
import sync_recorder
import signal
import atexit
import subprocess

# ---- IMU UDP ----
UDP_IP   = "0.0.0.0"
UDP_PORT = int(os.getenv("UDP_PORT", "12345"))

# ---- 电脑麦克风/扬声器自动启动（开发模式，无 ESP32 时使用）----
# 设置 AUTO_PC_AUDIO=0 可禁用（例如使用 ESP32 硬件时）
AUTO_PC_AUDIO = os.getenv("AUTO_PC_AUDIO", "1") == "1"
_pc_mic_process: Optional[subprocess.Popen] = None
_pc_speaker_process: Optional[subprocess.Popen] = None

app = FastAPI()

# ====== 状态与容器 ======
app.mount("/static", StaticFiles(directory="static"), name="static")

ui_clients: Dict[int, WebSocket] = {}
current_partial: str = ""
recent_finals: List[str] = []
RECENT_MAX = 50
last_frames: Deque[Tuple[float, bytes]] = deque(maxlen=10)

camera_viewers: Set[WebSocket] = set()
esp32_camera_ws: Optional[WebSocket] = None
imu_ws_clients: Set[WebSocket] = set()
esp32_audio_ws: Optional[WebSocket] = None

# 【新增】盲道导航相关全局变量
blind_path_navigator = None
navigation_active = False

# 【新增】全局ASRCallback引用，用于在导航模式时管理唤醒词
current_asr_callback: Optional[object] = None
yolo_seg_model = None
obstacle_detector = None

# 【新增】过马路导航相关全局变量
cross_street_navigator = None
cross_street_active = False
orchestrator = None  # 新增

# 【新增】omni对话状态标志
omni_conversation_active = False  # 标记omni对话是否正在进行
omni_previous_nav_state = None  # 保存omni激活前的导航状态，用于恢复

# 【新增】地图导航目的地（语音「导航到xxx」解析后设置）
current_destination: Optional[str] = None
# 【新增】地图路线步骤与当前指引（供三级优先级播报使用）
route_steps: List[str] = []
route_path: List[Any] = []  # 路线坐标点，用于后端计算当前步骤
current_map_instruction: Optional[str] = None
last_map_instruction_ts: float = 0.0
MAP_INSTRUCTION_INTERVAL: float = 5.0  # 地图指引最小播报间隔（秒）

# 【新增】模型加载函数
def load_navigation_models():
    """加载盲道导航所需的模型"""
    global yolo_seg_model, obstacle_detector

    try:
        seg_model_path = os.getenv("BLIND_PATH_MODEL", r"D:\Blind_Navigation\OpenAIglasses_for_Navigation\model\yolo-seg.pt")
        #print(f"[NAVIGATION] 尝试加载模型: {seg_model_path}")

        if os.path.exists(seg_model_path):
            print(f"[NAVIGATION] 模型文件存在，开始加载...")
            yolo_seg_model = YOLO(seg_model_path)

            # 强制放到 GPU
            if torch.cuda.is_available():
                yolo_seg_model.to("cuda")
                print(f"[NAVIGATION] 盲道分割模型加载成功并放到GPU: {yolo_seg_model.device}")
            else:
                print("[NAVIGATION] CUDA不可用，模型仍在CPU")

            # 测试模型是否能正常运行
            try:
                test_img = np.zeros((640, 640, 3), dtype=np.uint8)
                results = yolo_seg_model.predict(
                    test_img,
                    device="cuda" if torch.cuda.is_available() else "cpu",
                    verbose=False
                )
                print(f"[NAVIGATION] 模型测试成功，支持的类别数: {len(yolo_seg_model.names) if hasattr(yolo_seg_model, 'names') else '未知'}")
                if hasattr(yolo_seg_model, 'names'):
                    print(f"[NAVIGATION] 模型类别: {yolo_seg_model.names}")
            except Exception as e:
                print(f"[NAVIGATION] 模型测试失败: {e}")
        else:
            print(f"[NAVIGATION] 错误：找不到模型文件: {seg_model_path}")
            print(f"[NAVIGATION] 当前工作目录: {os.getcwd()}")
            print(f"[NAVIGATION] 请检查文件路径是否正确")
            
        # 【修改开始】使用 ObstacleDetectorClient 替代直接的 YOLO
        obstacle_model_path = os.getenv("OBSTACLE_MODEL", r"D:\Blind_Navigation\OpenAIglasses_for_Navigation\model\yoloe-11l-seg.pt")
        print(f"[NAVIGATION] 尝试加载障碍物检测模型: {obstacle_model_path}")
        
        if os.path.exists(obstacle_model_path):
            print(f"[NAVIGATION] 障碍物检测模型文件存在，开始加载...")
            try:
                # 使用 ObstacleDetectorClient 封装的 YOLO-E
                obstacle_detector = ObstacleDetectorClient(model_path=obstacle_model_path)
                print(f"[NAVIGATION] ========== YOLO-E 障碍物检测器加载成功 ==========")
                
                # 检查模型是否成功加载
                if hasattr(obstacle_detector, 'model') and obstacle_detector.model is not None:
                    print(f"[NAVIGATION] YOLO-E 模型已初始化")
                    print(f"[NAVIGATION] 模型设备: {next(obstacle_detector.model.parameters()).device}")
                else:
                    print(f"[NAVIGATION] 警告：YOLO-E 模型初始化异常")
                
                # 检查白名单是否成功加载
                if hasattr(obstacle_detector, 'WHITELIST_CLASSES'):
                    print(f"[NAVIGATION] 白名单类别数: {len(obstacle_detector.WHITELIST_CLASSES)}")
                    print(f"[NAVIGATION] 白名单前10个类别: {', '.join(obstacle_detector.WHITELIST_CLASSES[:10])}")
                else:
                    print(f"[NAVIGATION] 警告：白名单类别未定义")
                
                # 检查文本特征是否成功预计算
                if hasattr(obstacle_detector, 'whitelist_embeddings') and obstacle_detector.whitelist_embeddings is not None:
                    print(f"[NAVIGATION] YOLO-E 文本特征已预计算")
                    print(f"[NAVIGATION] 文本特征张量形状: {obstacle_detector.whitelist_embeddings.shape if hasattr(obstacle_detector.whitelist_embeddings, 'shape') else '未知'}")
                else:
                    print(f"[NAVIGATION] 警告：YOLO-E 文本特征未预计算")
                
                # 测试障碍物检测功能
                print(f"[NAVIGATION] 开始测试 YOLO-E 检测功能...")
                try:
                    test_img = np.zeros((640, 640, 3), dtype=np.uint8)
                    # 在测试图像中画一个白色矩形，模拟一个物体
                    cv2.rectangle(test_img, (200, 200), (400, 400), (255, 255, 255), -1)
                    
                    # 测试检测（不提供 path_mask）
                    test_results = obstacle_detector.detect(test_img)
                    print(f"[NAVIGATION] YOLO-E 检测测试成功!")
                    print(f"[NAVIGATION] 测试检测结果数: {len(test_results)}")
                    
                    if len(test_results) > 0:
                        print(f"[NAVIGATION] 测试检测到的物体:")
                        for i, obj in enumerate(test_results):
                            print(f"  - 物体 {i+1}: {obj.get('name', 'unknown')}, "
                                  f"面积比例: {obj.get('area_ratio', 0):.3f}, "
                                  f"位置: ({obj.get('center_x', 0):.0f}, {obj.get('center_y', 0):.0f})")
                except Exception as e:
                    print(f"[NAVIGATION] YOLO-E 检测测试失败: {e}")
                    import traceback
                    traceback.print_exc()
                
                print(f"[NAVIGATION] ========== YOLO-E 障碍物检测器加载完成 ==========")
                
            except Exception as e:
                print(f"[NAVIGATION] 障碍物检测器加载失败: {e}")
                import traceback
                traceback.print_exc()
                obstacle_detector = None
        else:
            print(f"[NAVIGATION] 警告：找不到障碍物检测模型文件: {obstacle_model_path}")
        
    except Exception as e:
        print(f"[NAVIGATION] 模型加载失败: {e}")
        import traceback
        traceback.print_exc()

# 在程序启动时加载模型
print("[NAVIGATION] 开始加载导航模型...")
load_navigation_models()
print(f"[NAVIGATION] 模型加载完成 - yolo_seg_model: {yolo_seg_model is not None}")

RECORDING_ENABLED = os.getenv("AIGLASS_SYNC_RECORD", "0").strip() in ("1", "true", "True", "YES", "yes")

# 【新增】启动同步录制（默认关闭；开启会显著降低FPS）
if RECORDING_ENABLED:
    print("[RECORDER] 启动同步录制系统... (AIGLASS_SYNC_RECORD=1)")
    sync_recorder.start_recording()
    print("[RECORDER] 录制系统已启动，将自动保存视频和音频")
else:
    print("[RECORDER] 同步录制未启用（如需开启：设置环境变量 AIGLASS_SYNC_RECORD=1）")

# 【新增】注册退出处理器，确保Ctrl+C时保存录制文件
def cleanup_on_exit():
    """程序退出时的清理工作"""
    if not RECORDING_ENABLED:
        return
    print("\n[SYSTEM] 正在关闭录制器...")
    try:
        sync_recorder.stop_recording()
        print("[SYSTEM] 录制文件已保存")
    except Exception as e:
        print(f"[SYSTEM] 关闭录制器时出错: {e}")

def signal_handler(sig, frame):
    """处理Ctrl+C信号"""
    print("\n[SYSTEM] 收到中断信号，正在安全退出...")
    cleanup_on_exit()
    import sys
    sys.exit(0)

# 注册信号处理器
signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
signal.signal(signal.SIGTERM, signal_handler)  # 终止信号
atexit.register(cleanup_on_exit)  # 正常退出时也调用

print("[RECORDER] 已注册退出处理器 - Ctrl+C时会自动保存录制文件")



# 【新增】预加载红绿灯检测模型（避免进入WAIT_TRAFFIC_LIGHT状态时卡顿）
try:
    import trafficlight_detection
    print("[TRAFFIC_LIGHT] 开始预加载红绿灯检测模型...")
    if trafficlight_detection.init_model():
        print("[TRAFFIC_LIGHT] 红绿灯检测模型预加载成功")
        # 执行一次测试推理，完全预热模型
        try:
            test_img = np.zeros((640, 640, 3), dtype=np.uint8)
            _ = trafficlight_detection.process_single_frame(test_img)
            print("[TRAFFIC_LIGHT] 模型预热完成")
        except Exception as e:
            print(f"[TRAFFIC_LIGHT] 模型预热失败: {e}")
    else:
        print("[TRAFFIC_LIGHT] 红绿灯检测模型预加载失败")
except Exception as e:
    print(f"[TRAFFIC_LIGHT] 红绿灯模型预加载出错: {e}")

# ============== 关键：系统级"硬重置"总闸 =================
interrupt_lock = asyncio.Lock()

# ============== YOLO媒体线程管理 =================
yolomedia_thread: Optional[threading.Thread] = None
yolomedia_stop_event = threading.Event()
yolomedia_running = False
yolomedia_sending_frames = False  # 新增：标记YOLO是否已经开始发送处理后的帧

# 物品名称到YOLO类别的映射
ITEM_TO_CLASS_MAP = {
    "红牛": "Red_Bull",
    "AD钙奶": "AD_milk",
    "ad钙奶": "AD_milk",
    "钙奶": "AD_milk",
}

async def ui_broadcast_raw(msg: str):
    dead = []
    for k, ws in list(ui_clients.items()):
        try:
            await ws.send_text(msg)
        except Exception:
            dead.append(k)
    for k in dead:
        ui_clients.pop(k, None)


async def ui_broadcast_partial(text: str):
    global current_partial
    current_partial = text
    await ui_broadcast_raw("PARTIAL:" + text)

async def ui_broadcast_final(text: str):
    global current_partial, recent_finals
    current_partial = ""
    recent_finals.append(text)
    if len(recent_finals) > RECENT_MAX:
        recent_finals = recent_finals[-RECENT_MAX:]
    await ui_broadcast_raw("FINAL:" + text)
    print(f"[ASR/AI FINAL] {text}", flush=True)

async def full_system_reset(reason: str = ""):
    """
    回到刚启动后的状态：
    1) 停播 + 取消AI任务 + 切断所有/stream.wav（hard_reset_audio）
    2) 停止 ASR 实时识别流（关键）
    3) 清 UI 状态
    4) 清最近相机帧（避免把旧帧又拼进下一轮）
    5) 告知 ESP32：RESET（可选）
    """
    # 1) 音频&AI
    await hard_reset_audio(reason or "full_system_reset")

    # 2) ASR
    await stop_current_recognition()

    # 3) UI
    global current_partial, recent_finals
    current_partial = ""
    recent_finals = []

    # 4) 相机帧
    try:
        last_frames.clear()
    except Exception:
        pass

    # 5) 通知 ESP32
    try:
        if esp32_audio_ws and (esp32_audio_ws.client_state == WebSocketState.CONNECTED):
            await esp32_audio_ws.send_text("RESET")
    except Exception:
        pass

    print("[SYSTEM] full reset done.", flush=True)

# ========= 启动/停止 YOLO 媒体处理 =========
def start_yolomedia_with_target(target_name: str):
    """启动yolomedia线程，搜索指定物品"""
    global yolomedia_thread, yolomedia_stop_event, yolomedia_running, yolomedia_sending_frames
    
    # 如果已经在运行，先停止
    if yolomedia_running:
        stop_yolomedia()
    
    # 查找对应的YOLO类别
    yolo_class = ITEM_TO_CLASS_MAP.get(target_name, target_name)
    print(f"[YOLOMEDIA] Starting with target: {target_name} -> YOLO class: {yolo_class}", flush=True)
    print(f"[YOLOMEDIA] Available mappings: {ITEM_TO_CLASS_MAP}", flush=True)  # 添加这行调试
    
    yolomedia_stop_event.clear()
    yolomedia_running = True
    yolomedia_sending_frames = False  # 重置发送帧状态
    
    def _run():
        try:
            # 传递目标类别名和停止事件
            yolomedia.main(headless=True, prompt_name=yolo_class, stop_event=yolomedia_stop_event)
        except Exception as e:
            print(f"[YOLOMEDIA] worker stopped: {e}", flush=True)
        finally:
            global yolomedia_running, yolomedia_sending_frames
            yolomedia_running = False
            yolomedia_sending_frames = False
    
    yolomedia_thread = threading.Thread(target=_run, daemon=True)
    yolomedia_thread.start()
    print(f"[YOLOMEDIA] background worker started for: {yolo_class}（正在初始化，暂时显示原始画面）", flush=True)

def stop_yolomedia():
    """停止yolomedia线程"""
    global yolomedia_thread, yolomedia_stop_event, yolomedia_running, yolomedia_sending_frames
    
    if yolomedia_running:
        print("[YOLOMEDIA] Stopping worker...", flush=True)
        yolomedia_stop_event.set()
        
        # 等待线程结束（最多等5秒）
        if yolomedia_thread and yolomedia_thread.is_alive():
            yolomedia_thread.join(timeout=5.0)
        
        yolomedia_running = False
        yolomedia_sending_frames = False
        
        # 【新增】如果orchestrator在找物品模式，结束时不自动恢复（由命令控制）
        # 只清理标志位即可
        print("[YOLOMEDIA] Worker stopped, 等待状态切换.", flush=True)

# ========= 自定义的 start_ai_with_text，支持识别特殊命令 =========
async def start_ai_with_text_custom(user_text: str):
    """扩展版的AI启动函数，支持识别特殊命令"""
    global navigation_active, blind_path_navigator, cross_street_active, cross_street_navigator, orchestrator, current_asr_callback, yolomedia_running, yolomedia_stop_event, yolomedia_thread, yolomedia_sending_frames
    
    # 【修改】在导航模式和红绿灯检测模式下，只有特定词才进入omni对话
    if orchestrator:
        current_state = orchestrator.get_state()
        # 如果在导航模式或红绿灯检测模式（非CHAT模式）
        if current_state not in ["CHAT", "IDLE"]:
            # 检查是否是允许的对话触发词
            allowed_keywords = ["帮我看", "帮我看下", "帮我找", "找一下", "看看", "识别一下"]
            is_allowed_query = any(keyword in user_text for keyword in allowed_keywords)
            
            # 检查是否是导航控制命令
            nav_control_keywords = ["开始过马路", "过马路结束", "启动导航", "开始导航", "盲道导航", "停止导航", "结束导航", 
                                   "导航到", "导航去", "检测红绿灯", "看红绿灯", "停止检测", "停止红绿灯"]
            is_nav_control = any(keyword in user_text for keyword in nav_control_keywords)
            
            # 如果既不是允许的查询，也不是导航控制命令，则丢弃
            if not is_allowed_query and not is_nav_control:
                mode_name = "红绿灯检测" if current_state == "TRAFFIC_LIGHT_DETECTION" else "导航"
                print(f"[{mode_name}模式] 丢弃非对话语音: {user_text}")
                return  # 直接丢弃，不进入omni
    
    # 【修改】检查是否是过马路相关命令 - 使用orchestrator控制
    if "开始过马路" in user_text or "帮我过马路" in user_text:
        # 【新增】如果正在找物品，先停止
        if yolomedia_running:
            stop_yolomedia()
            print("[ITEM_SEARCH] 从找物品模式切换到过马路")
        
        if orchestrator:
            orchestrator.start_crossing()
            print(f"[CROSS_STREET] 过马路模式已启动，状态: {orchestrator.get_state()}")
            # 【新增】在导航模式激活系统，跳过唤醒词
            if current_asr_callback and hasattr(current_asr_callback, '_system_active'):
                current_asr_callback._system_active = True
                print(f"[AUDIO] 过马路模式已激活ASR系统，用户可直接说命令", flush=True)
            # 播放启动语音并广播到UI
            play_voice_text("过马路模式已启动。")
            await ui_broadcast_final("[系统] 过马路模式已启动，说'过马路结束'可停止")
        else:
            print("[CROSS_STREET] 警告：导航统领器未初始化！")
            play_voice_text("启动过马路模式失败，请稍后重试。")
            await ui_broadcast_final("[系统] 导航系统未就绪")
        return
    
    if "过马路结束" in user_text or "结束过马路" in user_text:
        if orchestrator:
            orchestrator.stop_navigation()
            print(f"[CROSS_STREET] 导航已停止，状态: {orchestrator.get_state()}")
            # 【新增】恢复到非导航模式时，重置唤醒词系统
            if current_asr_callback and hasattr(current_asr_callback, '_system_active'):
                from asr_core import WAKE_WORD_ENABLED
                if WAKE_WORD_ENABLED:
                    current_asr_callback._system_active = False
                    print(f"[AUDIO] 过马路已停止，ASR系统已重置", flush=True)
            # 播放停止语音并广播到UI
            play_voice_text("已停止导航。")
            await ui_broadcast_final("[系统] 过马路模式已停止，说'小慧启动'重新激活")
        else:
            await ui_broadcast_final("[系统] 导航系统未运行")
        return
    
    # 【修改】检查是否是红绿灯检测命令 - 实现与盲道导航互斥
    if "检测红绿灯" in user_text or "看红绿灯" in user_text:
        try:
            import trafficlight_detection
            
            # 切换orchestrator到红绿灯检测模式（暂停盲道导航）
            if orchestrator:
                orchestrator.start_traffic_light_detection()
                print(f"[TRAFFIC] 切换到红绿灯检测模式，状态: {orchestrator.get_state()}")
            
            # 【改进】使用主线程模式而不是独立线程，避免掉帧
            success = trafficlight_detection.init_model()  # 只初始化模型，不启动线程
            trafficlight_detection.reset_detection_state()  # 重置状态
            
            if success:
                await ui_broadcast_final("[系统] 红绿灯检测已启动")
            else:
                await ui_broadcast_final("[系统] 红绿灯模型加载失败")
        except Exception as e:
            print(f"[TRAFFIC] 启动红绿灯检测失败: {e}")
            await ui_broadcast_final(f"[系统] 启动失败: {e}")
        return
    
    if "停止检测" in user_text or "停止红绿灯" in user_text:
        try:
            # 恢复到对话模式
            if orchestrator:
                orchestrator.stop_navigation()  # 回到CHAT模式
                print(f"[TRAFFIC] 红绿灯检测停止，恢复到{orchestrator.get_state()}模式")
            
            await ui_broadcast_final("[系统] 红绿灯检测已停止")
        except Exception as e:
            print(f"[TRAFFIC] 停止红绿灯检测失败: {e}")
            await ui_broadcast_final(f"[系统] 停止失败: {e}")
        return
    
    # 【新增】解析「导航到xxx」/「请帮我导航到松江印象城」等，提取目的地
    nav_to_pattern = r"(?:请?帮我)?\s*(?:导航到|导航去|去|到)\s*(.+?)(?:。|！|？|$)"
    nav_to_match = re.search(nav_to_pattern, user_text)
    if nav_to_match:
        dest = nav_to_match.group(1).strip()
        # 过滤疑问词，避免误触发
        if dest and len(dest) >= 2 and dest not in ("什么", "哪里", "哪儿", "哪里啊"):
            global current_destination
            current_destination = dest
            if yolomedia_running:
                stop_yolomedia()
            if orchestrator:
                orchestrator.start_blind_path_navigation()
                if current_asr_callback and hasattr(current_asr_callback, '_system_active'):
                    current_asr_callback._system_active = True
                play_voice_text(f"正在为您导航到{dest}，请稍候。")
                await ui_broadcast_raw(f"NAV_DEST:{dest}")
                await ui_broadcast_final(f"[系统] 目的地已设为 {dest}，正在规划路线")
            else:
                await ui_broadcast_final("[系统] 导航系统未就绪")
            return

    # 【修改】检查是否是导航相关命令 - 使用orchestrator控制（含「启动导航」）
    if "启动导航" in user_text or "开始导航" in user_text or "盲道导航" in user_text or "帮我导航" in user_text:
        # 【新增】如果正在找物品，先停止
        if yolomedia_running:
            stop_yolomedia()
            print("[ITEM_SEARCH] 从找物品模式切换到盲道导航")
        
        if orchestrator:
            orchestrator.start_blind_path_navigation()
            print(f"[NAVIGATION] 盲道导航已启动，状态: {orchestrator.get_state()}")
            # 【新增】在导航模式激活系统，跳过唤醒词
            if current_asr_callback and hasattr(current_asr_callback, '_system_active'):
                current_asr_callback._system_active = True
                print(f"[AUDIO] 导航模式已激活ASR系统，用户可直接说停止导航", flush=True)
            play_voice_text("盲道导航已启动，说停止导航可结束。")
        else:
            print("[NAVIGATION] 警告：导航统领器未初始化！")
            await ui_broadcast_final("[系统] 导航系统未就绪")
        return
    
    if "停止导航" in user_text or "结束导航" in user_text:
        if orchestrator:
            orchestrator.stop_navigation()
            print(f"[NAVIGATION] 导航已停止，状态: {orchestrator.get_state()}")
            # 【新增】恢复到非导航模式时，重置唤醒词系统
            if current_asr_callback and hasattr(current_asr_callback, '_system_active'):
                from asr_core import WAKE_WORD_ENABLED
                if WAKE_WORD_ENABLED:
                    current_asr_callback._system_active = False
                    print(f"[AUDIO] 导航已停止，ASR系统已重置", flush=True)
            await ui_broadcast_final("[系统] 盲道导航已停止，说'小慧启动'重新激活")
        else:
            await ui_broadcast_final("[系统] 导航系统未运行")
        return

    nav_cmd_keywords = ["开始过马路", "过马路结束", "启动导航", "开始导航", "盲道导航", "停止导航", "结束导航", "立即通过", "现在通过", "继续"]
    if any(k in user_text for k in nav_cmd_keywords):
        if orchestrator:
            orchestrator.on_voice_command(user_text)
            await ui_broadcast_final("[系统] 导航模式已更新")
        else:
            await ui_broadcast_final("[系统] 导航统领器未初始化")
        return    

    # 检查是否是"帮我找/识别一下xxx"的命令
    # 扩展正则表达式，支持更多关键词
    find_pattern = r"(?:^\s*帮我)?\s*找一下\s*(.+?)(?:。|！|？|$)"
    match = re.search(find_pattern, user_text)
        
    if match:
        # 提取中文物品名称
        item_cn = match.group(1).strip()
        if item_cn:
            # 【新增】用本地映射 + Qwen 提取英文类名
            label_en, src = extract_english_label(item_cn)
            print(f"[COMMAND] Finder request: '{item_cn}' -> '{label_en}' (src={src})", flush=True)

            # 【新增】切换到找物品模式（暂停导航）
            if orchestrator:
                orchestrator.start_item_search()
                print(f"[ITEM_SEARCH] 已切换到找物品模式，状态: {orchestrator.get_state()}")
            
            # 【关键】把英文类名传给 yolomedia（它会在找不到类时自动切 YOLOE）
            start_yolomedia_with_target(label_en)

            # 给前端/语音来个确认反馈
            try:
                await ui_broadcast_final(f"[找物品] 正在寻找 {item_cn}...")
            except Exception:
                pass

            return
    
    # 检查是否是"找到了"的命令
    if "找到了" in user_text or "拿到了" in user_text:
        print("[COMMAND] Found command detected", flush=True)
        # 停止yolomedia
        stop_yolomedia()
        
        # 【新增】停止找物品模式，恢复之前的导航状态
        if orchestrator:
            orchestrator.stop_item_search(restore_nav=True)
            current_state = orchestrator.get_state()
            print(f"[ITEM_SEARCH] 找物品结束，当前状态: {current_state}")
            
            # 根据恢复的状态给出反馈
            if current_state in ["BLINDPATH_NAV", "SEEKING_CROSSWALK", "WAIT_TRAFFIC_LIGHT", "CROSSING", "SEEKING_NEXT_BLINDPATH"]:
                await ui_broadcast_final("[找物品] 已找到物品，继续导航。")
            else:
                await ui_broadcast_final("[找物品] 已找到物品。")
        else:
            await ui_broadcast_final("[找物品] 已找到物品。")
        
        return
    
    # 【修改】omni对话开始时，切换到CHAT模式
    global omni_conversation_active, omni_previous_nav_state
    
    # 【新增】在导航模式下，不进入omni对话，直接返回
    if orchestrator:
        current_state = orchestrator.get_state()
        if current_state not in ["CHAT", "IDLE"]:
            print(f"[{current_state}模式] 导航中无法进入对话模式，已忽略语音: {user_text}")
            await ui_broadcast_final(f"[{current_state}] 导航中，请说导航命令或说'停止导航'")
            return  # 【关键】不进入 start_ai_with_text，避免 hard_reset_audio
    
    omni_conversation_active = True
    
    # 保存当前导航状态并切换到CHAT模式
    if orchestrator:
        current_state = orchestrator.get_state()
        # 只有在导航模式下才需要保存和切换
        if current_state not in ["CHAT", "IDLE"]:
            omni_previous_nav_state = current_state
            orchestrator.force_state("CHAT")
            print(f"[OMNI] 对话开始，从{current_state}切换到CHAT模式")
        else:
            omni_previous_nav_state = None
            print(f"[OMNI] 对话开始（当前已在{current_state}模式）")
    
    # 如果不是特殊命令，执行原有的AI对话逻辑
    # 但如果yolomedia正在运行，暂时不处理普通对话
    if yolomedia_running:
        print("[AI] YOLO media is running, skipping normal AI response", flush=True)
        return
    
    # 原有的AI对话逻辑
    await start_ai_with_text(user_text)

# ========= Omni 播放启动 =========
async def start_ai_with_text(user_text: str):
    """硬重置后，开启新的 AI 语音输出。"""
    async def _runner():
        txt_buf: List[str] = []
        rate_state = None

        # 组装（图像+文本）
        content_list = []
        if last_frames:
            try:
                _, jpeg_bytes = last_frames[-1]
                img_b64 = base64.b64encode(jpeg_bytes).decode("ascii")
                content_list.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}
                })
            except Exception:
                pass
        content_list.append({"type": "text", "text": user_text})

        try:
            async for piece in stream_chat(content_list, voice="Cherry", audio_format="wav"):
                # 文本增量（仅 UI）
                if piece.text_delta:
                    txt_buf.append(piece.text_delta)
                    try:
                        await ui_broadcast_partial("[AI] " + "".join(txt_buf))
                    except Exception:
                        pass

                # 音频分片：Omni 返回 24k (PCM16) 的 wav audio.data（Base64）；下行需要 8k PCM16
                if piece.audio_b64:
                    try:
                        pcm24 = base64.b64decode(piece.audio_b64)
                    except Exception:
                        pcm24 = b""
                    if pcm24:
                        # 24k → 8k (使用ratecv保证音调和速度不变)
                        pcm8k, rate_state = audioop.ratecv(pcm24, 2, 1, 24000, 8000, rate_state)
                        pcm8k = audioop.mul(pcm8k, 2, 0.60)
                        if pcm8k:
                            await broadcast_pcm16_realtime(pcm8k)

        except asyncio.CancelledError:
            # 被新一轮打断
            raise
        except Exception as e:
            try:
                await ui_broadcast_final(f"[AI] 发生错误：{e}")
            except Exception:
                pass
        finally:
            # 【修改】标记omni对话结束，恢复之前的导航模式
            global omni_conversation_active, omni_previous_nav_state
            omni_conversation_active = False
            
            # 恢复之前的导航状态
            if orchestrator and omni_previous_nav_state:
                orchestrator.force_state(omni_previous_nav_state)
                print(f"[OMNI] 对话结束，恢复到{omni_previous_nav_state}模式")
                omni_previous_nav_state = None
            else:
                print(f"[OMNI] 对话结束（无需恢复导航状态）")
            
            # 自然结束时，给当前连接一个 "完结" 信号
            from audio_stream import stream_clients  # 局部导入，避免环依赖
            for sc in list(stream_clients):
                if not sc.abort_event.is_set():
                    try: sc.q.put_nowait(b"\x00"*BYTES_PER_20MS_16K)  # 一帧静音
                    except Exception: pass
                    try: sc.q.put_nowait(None)
                    except Exception: pass

            final_text = ("".join(txt_buf)).strip() or "（空响应）"
            try:
                await ui_broadcast_final("[AI] " + final_text)
            except Exception:
                pass

    # 真正启动前先硬重置，保证**绝无**旧音频残留
    await hard_reset_audio("start_ai_with_text")
    loop = asyncio.get_running_loop()
    from audio_stream import current_ai_task as _task_holder  # 读写模块内全局
    from audio_stream import __dict__ as _as_dict
    # 设置模块内的 current_ai_task
    task = loop.create_task(_runner())
    _as_dict["current_ai_task"] = task

# ---------- 页面 / 健康 ----------
@app.get("/", response_class=HTMLResponse)
def root():
    with open(os.path.join("templates", "index.html"), "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.get("/api/health", response_class=PlainTextResponse)
def health():
    return "OK"

# ---------- 地图导航 API（供前端路线规划与定位上报） ----------
@app.post("/api/navigation/route")
async def api_navigation_route(body: Dict[str, Any] = Body(default={})):
    """接收前端规划的路线步骤与路径点"""
    global route_steps, route_path
    steps = body.get("steps") or []
    route_steps = steps if isinstance(steps, list) else []
    path = body.get("path") or []
    route_path = path if isinstance(path, list) else []
    return {"ok": True, "steps_count": len(route_steps), "path_points": len(route_path)}

@app.post("/api/navigation/position")
async def api_navigation_position(body: Dict[str, Any] = Body(default={})):
    """接收前端上报的实时坐标与步骤索引，更新当前应播报的指引"""
    global current_map_instruction, route_steps
    lng = body.get("lng")
    lat = body.get("lat")
    step_index = body.get("step_index")
    if lng is not None and lat is not None and route_steps:
        idx = 0
        if step_index is not None and isinstance(step_index, int) and 0 <= step_index < len(route_steps):
            idx = step_index
        else:
            idx = _compute_step_index_from_position(lng, lat)
        current_map_instruction = route_steps[idx]
    return {"ok": True, "instruction": current_map_instruction}


def _compute_step_index_from_position(lng: float, lat: float) -> int:
    """根据坐标与 route_path 计算当前步骤索引（后端兜底）"""
    global route_path, route_steps
    if not route_path or not route_steps:
        return 0
    best_i, best_d = 0, float("inf")
    for i, p in enumerate(route_path):
        if isinstance(p, dict):
            plng, plat = p.get("lng"), p.get("lat")
        else:
            plng, plat = (p[0], p[1]) if len(p) >= 2 else (p[0], p[0])
        d = (lng - plng) ** 2 + (lat - plat) ** 2
        if d < best_d:
            best_d, best_i = d, i
    if len(route_path) == len(route_steps):
        return min(best_i, len(route_steps) - 1)
    step_len = max(1, len(route_path) // len(route_steps))
    return min(best_i // step_len, len(route_steps) - 1)

# 注册 /stream.wav
register_stream_route(app)

# ---------- WebSocket：WebUI 文本（ASR/AI 状态推送） ----------
@app.websocket("/ws_ui")
async def ws_ui(ws: WebSocket):
    await ws.accept()
    ui_clients[id(ws)] = ws
    try:
        init = {"partial": current_partial, "finals": recent_finals[-10:]}
        await ws.send_text("INIT:" + json.dumps(init, ensure_ascii=False))
        while True:
            await asyncio.sleep(60)
    except WebSocketDisconnect:
        pass
    finally:
        ui_clients.pop(id(ws), None)

# ---------- WebSocket：ESP32 音频入口（ASR 上行） ----------
@app.websocket("/ws_audio")
async def ws_audio(ws: WebSocket):
    global esp32_audio_ws, current_asr_callback, orchestrator
    esp32_audio_ws = ws
    await ws.accept()
    print("\n[AUDIO] client connected")
    recognition = None
    streaming = False
    last_ts = time.monotonic()
    keepalive_task: Optional[asyncio.Task] = None

    async def stop_rec(send_notice: Optional[str] = None):
        nonlocal recognition, streaming, keepalive_task
        if keepalive_task and not keepalive_task.done():
            keepalive_task.cancel()
            try: await keepalive_task
            except Exception: pass
        keepalive_task = None
        if recognition:
            try: recognition.stop()
            except Exception: pass
            recognition = None
        await set_current_recognition(None)
        streaming = False
        if send_notice:
            try: await ws.send_text(send_notice)
            except Exception: pass

    async def on_sdk_error(_msg: str):
        await stop_rec(send_notice="RESTART")

    async def keepalive_loop():
        nonlocal last_ts, recognition, streaming
        try:
            while streaming and recognition is not None:
                idle = time.monotonic() - last_ts
                if idle > 0.35:
                    try:
                        for _ in range(30):  # ~600ms 静音
                            recognition.send_audio_frame(SILENCE_20MS)
                        last_ts = time.monotonic()
                    except Exception:
                        await on_sdk_error("keepalive send failed")
                        return
                await asyncio.sleep(0.10)
        except asyncio.CancelledError:
            return

    try:
        while True:
            if WebSocketState and ws.client_state != WebSocketState.CONNECTED:
                break
            try:
                msg = await ws.receive()
            except WebSocketDisconnect:
                break
            except RuntimeError as e:
                if "Cannot call \"receive\"" in str(e):
                    break
                raise

            if "text" in msg and msg["text"] is not None:
                raw = (msg["text"] or "").strip()
                cmd = raw.upper()

                if cmd == "START":
                    print("[AUDIO] START received")
                    await stop_rec()
                    loop = asyncio.get_running_loop()
                    def post(coro):
                        asyncio.run_coroutine_threadsafe(coro, loop)

                    # 组装 ASR 回调（把依赖都注入）
                    cb = ASRCallback(
                        on_sdk_error=lambda s: post(on_sdk_error(s)),
                        post=post,
                        ui_broadcast_partial=ui_broadcast_partial,
                        ui_broadcast_final=ui_broadcast_final,
                        is_playing_now_fn=is_playing_now,
                        start_ai_with_text_fn=start_ai_with_text_custom,  # 使用自定义版本
                        full_system_reset_fn=full_system_reset,
                        interrupt_lock=interrupt_lock,
                        play_voice_fn=play_voice_text,
                    )
                    
                    # 【新增】保存全局引用，同时检查导航状态
                    current_asr_callback = cb
                    # 如果当前在导航模式，自动激活系统（跳过唤醒词）
                    if orchestrator and orchestrator.get_state() not in ["IDLE", "CHAT"]:
                        if hasattr(cb, '_system_active'):
                            cb._system_active = True
                            print(f"[AUDIO] 导航模式已激活，跳过唤醒词检查，状态: {orchestrator.get_state()}", flush=True)

                    recognition = dash_audio.asr.Recognition(
                        api_key=API_KEY, model=MODEL, format=AUDIO_FMT,
                        sample_rate=SAMPLE_RATE, callback=cb
                    )
                    recognition.start()
                    await set_current_recognition(recognition)
                    streaming = True
                    last_ts = time.monotonic()
                    keepalive_task = asyncio.create_task(keepalive_loop())
                    from asr_core import WAKE_WORD_ENABLED
                    if WAKE_WORD_ENABLED:
                        await ui_broadcast_partial('💤 休眠中 - 请说"小慧小慧，启动"')
                        print("[AUDIO] 唤醒词模式已启用，等待唤醒词...", flush=True)
                    else:
                        await ui_broadcast_partial("（已开始接收音频…）")
                    await ws.send_text("OK:STARTED")

                elif cmd == "STOP":
                    if recognition:
                        for _ in range(15):  # ~300ms 静音
                            try: recognition.send_audio_frame(SILENCE_20MS)
                            except Exception: break
                    await stop_rec(send_notice="OK:STOPPED")

                elif raw.startswith("PROMPT:"):
                    # 设备端主动发起一轮：同样使用“先硬重置后播放”的强语义
                    text = raw[len("PROMPT:"):].strip()
                    if text:
                        async with interrupt_lock:
                            await start_ai_with_text_custom(text) # 使用自定义的启动函数
                        await ws.send_text("OK:PROMPT_ACCEPTED")
                    else:
                        await ws.send_text("ERR:EMPTY_PROMPT")

            elif "bytes" in msg and msg["bytes"] is not None:
                if streaming and recognition:
                    try:
                        recognition.send_audio_frame(msg["bytes"])
                        last_ts = time.monotonic()
                    except Exception:
                        await on_sdk_error("send_audio_frame failed")

    except Exception as e:
        print(f"\n[WS ERROR] {e}")
    finally:
        await stop_rec()
        try:
            if WebSocketState is None or ws.client_state == WebSocketState.CONNECTED:
                await ws.close(code=1000)
        except Exception:
            pass
        if esp32_audio_ws is ws:
            esp32_audio_ws = None
        print("[WS] connection closed")

# ---------- WebSocket：ESP32 相机入口（JPEG 二进制） ----------
@app.websocket("/ws/camera")
async def ws_camera_esp(ws: WebSocket):
    global esp32_camera_ws, blind_path_navigator, cross_street_navigator, cross_street_active, navigation_active, orchestrator
    if esp32_camera_ws is not None:
        await ws.close(code=1013)
        return
    esp32_camera_ws = ws
    await ws.accept()
    print("[CAMERA] ESP32 connected")
    
    # 【新增】初始化盲道导航器
    if blind_path_navigator is None and yolo_seg_model is not None:
        blind_path_navigator = BlindPathNavigator(yolo_seg_model, obstacle_detector)
        print("[NAVIGATION] 盲道导航器已初始化")
    else:
        if blind_path_navigator is not None:
            print("[NAVIGATION] 导航器已存在，无需重新初始化")
        elif yolo_seg_model is None:
            print("[NAVIGATION] 警告：YOLO模型未加载，无法初始化导航器")
    
    # 【新增】初始化过马路导航器
    if cross_street_navigator is None:
        if yolo_seg_model:
            cross_street_navigator = CrossStreetNavigator(
                seg_model=yolo_seg_model,
                coco_model=None,  # 不使用交通灯检测
                obs_model=None    # 暂时也不用障碍物检测，让它更快
            )
            print("[CROSS_STREET] 过马路导航器已初始化（简化版 - 仅斑马线检测）")
        else:
            print("[CROSS_STREET] 错误：缺少分割模型，无法初始化过马路导航器")
            
            if not yolo_seg_model:
                print("[CROSS_STREET] - 缺少分割模型 (yolo_seg_model)")
            if not obstacle_detector:
                print("[CROSS_STREET] - 缺少障碍物检测器 (obstacle_detector)")
    
    if orchestrator is None and blind_path_navigator is not None and cross_street_navigator is not None:
        orchestrator = NavigationMaster(blind_path_navigator, cross_street_navigator)
        print("[NAV MASTER] 统领状态机已初始化（托管模式）")
    frame_counter = 0  # 添加帧计数器
    
    try:
        while True:
            msg = await ws.receive()
            if "bytes" in msg and msg["bytes"] is not None:
                data = msg["bytes"]
                frame_counter += 1
                
                # 【新增】录制原始帧
                if RECORDING_ENABLED:
                    try:
                        sync_recorder.record_frame(data)
                    except Exception as e:
                        if frame_counter % 100 == 0:  # 避免日志刷屏
                            print(f"[RECORDER] 录制帧失败: {e}")
                
                try:
                    last_frames.append((time.time(), data))
                except Exception:
                    pass
                
                # 推送到bridge_io（供yolomedia使用）
                bridge_io.push_raw_jpeg(data)
                
                # 【调试】检查导航条件
                if frame_counter % 30 == 0:  # 每30帧输出一次
                    state_dbg = orchestrator.get_state() if orchestrator else "N/A"
                    print(f"[NAVIGATION DEBUG] 帧:{frame_counter}, state={state_dbg}, yolomedia_running={yolomedia_running}")
                
                # 先尽快把原始 JPEG 推给浏览器（不做任何解码/再编码）
                # 说明：如果后续要叠加可视化（导航/红绿灯），那一帧再发“处理后的JPEG”。
                if not yolomedia_sending_frames and camera_viewers:
                    dead = []
                    for viewer_ws in list(camera_viewers):
                        try:
                            await viewer_ws.send_bytes(data)
                        except Exception:
                            dead.append(viewer_ws)
                    for d in dead:
                        camera_viewers.discard(d)

                # 【托管】交给统领状态机（找物品模式时跳过，让yolomedia接管画面）
                if orchestrator and not yolomedia_running:
                    current_state = orchestrator.get_state()

                    # 找物品模式：不做导航处理，等待yolomedia发送处理后的帧
                    if current_state == "ITEM_SEARCH":
                        continue

                    # 需要做视觉处理时才解码（避免无谓的CPU开销）
                    try:
                        arr = np.frombuffer(data, dtype=np.uint8)
                        bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                        if bgr is None or bgr.size == 0:
                            bgr = None
                    except Exception:
                        bgr = None

                    if bgr is None:
                        continue

                    out_img = bgr
                    try:
                        if current_state == "TRAFFIC_LIGHT_DETECTION":
                            import trafficlight_detection
                            result = trafficlight_detection.process_single_frame(bgr, ui_broadcast_callback=ui_broadcast_final)
                            out_img = result['vis_image'] if result.get('vis_image') is not None else bgr
                        else:
                            res = orchestrator.process_frame(bgr)

                            # 三级优先级播报：P1地图指引 > P2障碍物 > P3盲道
                            global last_map_instruction_ts
                            to_say = None
                            now_ts = time.time()
                            if current_map_instruction and current_destination and (now_ts - last_map_instruction_ts >= MAP_INSTRUCTION_INTERVAL):
                                to_say = current_map_instruction
                                last_map_instruction_ts = now_ts
                            elif res.guidance_text:
                                to_say = res.guidance_text
                            if to_say:
                                try:
                                    play_voice_text(to_say)
                                    await ui_broadcast_final(f"[导航] {to_say}")
                                except Exception:
                                    pass

                            out_img = res.annotated_image if res.annotated_image is not None else bgr
                    except Exception as e:
                        if frame_counter % 100 == 0:
                            print(f"[NAV MASTER] 处理帧时出错: {e}")

                    # 如果生成了叠加图，就把叠加图再发一次（原始帧已经发过）
                    if camera_viewers and out_img is not None and out_img is not bgr:
                        ok, enc = cv2.imencode(".jpg", out_img, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                        if ok:
                            jpeg_data = enc.tobytes()
                            dead = []
                            for viewer_ws in list(camera_viewers):
                                try:
                                    await viewer_ws.send_bytes(jpeg_data)
                                except Exception:
                                    dead.append(viewer_ws)
                            for d in dead:
                                camera_viewers.discard(d)

                    continue

                # 【回退】其他情况：已经在上面直接转发了原始 JPEG，无需再次解码/编码
                # 这里保留空分支以维持原有结构
                if False:
                    pass

            elif "type" in msg and msg["type"] in ("websocket.close", "websocket.disconnect"):
                break
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[CAMERA ERROR] {e}")
    finally:
        try:
            if WebSocketState is None or ws.client_state == WebSocketState.CONNECTED:
                await ws.close(code=1000)
        except Exception:
            pass
        esp32_camera_ws = None
        print("[CAMERA] ESP32 disconnected")
        
        # 【新增】清理导航状态
        if blind_path_navigator:
            blind_path_navigator.reset()
        if cross_street_navigator:
            cross_street_navigator.reset()
        if orchestrator:
            orchestrator.reset()
            print("[NAV MASTER] 统领器已重置")

# ---------- WebSocket：浏览器订阅相机帧 ----------
@app.websocket("/ws/viewer")
async def ws_viewer(ws: WebSocket):
    await ws.accept()
    camera_viewers.add(ws)
    print(f"[VIEWER] Browser connected. Total viewers: {len(camera_viewers)}", flush=True)
    try:
        while True:
            # 保持连接活跃
            await asyncio.sleep(60)
    except WebSocketDisconnect:
        print("[VIEWER] Browser disconnected", flush=True)
    finally:
        try: 
            camera_viewers.remove(ws)
        except Exception: 
            pass
        print(f"[VIEWER] Removed. Total viewers: {len(camera_viewers)}", flush=True)

# ---------- WebSocket：浏览器订阅 IMU ----------
@app.websocket("/ws")
async def ws_imu(ws: WebSocket):
    await ws.accept()
    imu_ws_clients.add(ws)
    try:
        while True:
            await asyncio.sleep(60)
    except WebSocketDisconnect:
        pass
    finally:
        imu_ws_clients.discard(ws)

async def imu_broadcast(msg: str):
    if not imu_ws_clients: return
    dead = []
    for ws in list(imu_ws_clients):
        try:
            await ws.send_text(msg)
        except Exception:
            dead.append(ws)
    for ws in dead:
        imu_ws_clients.discard(ws)

# ---------- 服务端 IMU 估计（原样保留） ----------
from math import atan2, hypot, pi
GRAV_BETA   = 0.98
STILL_W     = 0.4
YAW_DB      = 0.08
YAW_LEAK    = 0.2
ANG_EMA     = 0.15
AUTO_REZERO = True
USE_PROJ    = True
FREEZE_STILL= True
G     = 9.807
A_TOL = 0.08 * G
gLP = {"x":0.0, "y":0.0, "z":0.0}
gOff= {"x":0.0, "y":0.0, "z":0.0}
BIAS_ALPHA = 0.002
yaw  = 0.0
Rf = Pf = Yf = 0.0
ref = {"roll":0.0, "pitch":0.0, "yaw":0.0}
holdStart = 0.0
isStill   = False
last_ts_imu = 0.0
last_wall = 0.0
imu_store: List[Dict[str, Any]] = []

def _wrap180(a: float) -> float:
    a = a % 360.0
    if a >= 180.0: a -= 360.0
    if a < -180.0: a += 360.0
    return a

def process_imu_and_maybe_store(d: Dict[str, Any]):
    global gLP, gOff, yaw, Rf, Pf, Yf, ref, holdStart, isStill, last_ts_imu, last_wall

    t_ms = float(d.get("ts", 0.0))
    now_wall = time.monotonic()
    if t_ms <= 0.0:
        t_ms = (now_wall * 1000.0)
    if last_ts_imu <= 0.0 or t_ms <= last_ts_imu or (t_ms - last_ts_imu) > 3000.0:
        dt = 0.02
    else:
        dt = (t_ms - last_ts_imu) / 1000.0
    last_ts_imu = t_ms

    ax = float(((d.get("accel") or {}).get("x", 0.0)))
    ay = float(((d.get("accel") or {}).get("y", 0.0)))
    az = float(((d.get("accel") or {}).get("z", 0.0)))
    wx = float(((d.get("gyro")  or {}).get("x", 0.0)))
    wy = float(((d.get("gyro")  or {}).get("y", 0.0)))
    wz = float(((d.get("gyro")  or {}).get("z", 0.0)))

    gLP["x"] = GRAV_BETA * gLP["x"] + (1.0 - GRAV_BETA) * ax
    gLP["y"] = GRAV_BETA * gLP["y"] + (1.0 - GRAV_BETA) * ay
    gLP["z"] = GRAV_BETA * gLP["z"] + (1.0 - GRAV_BETA) * az
    gmag = hypot(gLP["x"], gLP["y"], gLP["z"]) or 1.0
    gHat = {"x": gLP["x"]/gmag, "y": gLP["y"]/gmag, "z": gLP["z"]/gmag}

    roll  = (atan2(az, ay)   * 180.0 / pi)
    pitch = (atan2(-ax, ay)  * 180.0 / pi)

    aNorm = hypot(ax, ay, az); wNorm = hypot(wx, wy, wz)
    nearFlat = (abs(roll) < 2.0 and abs(pitch) < 2.0)
    stillCond = (abs(aNorm - G) < A_TOL) and (wNorm < STILL_W)

    if stillCond:
        if holdStart <= 0.0: holdStart = t_ms
        if not isStill and (t_ms - holdStart) > 350.0: isStill = True
        gOff["x"] = (1.0 - BIAS_ALPHA)*gOff["x"] + BIAS_ALPHA*wx
        gOff["y"] = (1.0 - BIAS_ALPHA)*gOff["y"] + BIAS_ALPHA*wy
        gOff["z"] = (1.0 - BIAS_ALPHA)*gOff["z"] + BIAS_ALPHA*wz
    else:
        holdStart = 0.0; isStill = False

    if USE_PROJ:
        yawdot = ((wx - gOff["x"])*gHat["x"] + (wy - gOff["y"])*gHat["y"] + (wz - gOff["z"])*gHat["z"])
    else:
        yawdot = (wy - gOff["y"])

    if abs(yawdot) < YAW_DB: yawdot = 0.0
    if FREEZE_STILL and stillCond: yawdot = 0.0

    yaw = _wrap180(yaw + yawdot * dt)

    if (YAW_LEAK > 0.0) and nearFlat and stillCond and abs(yaw) > 0.0:
        step = YAW_LEAK * dt * (-1.0 if yaw > 0 else (1.0 if yaw < 0 else 0.0))
        if abs(yaw) <= abs(step): yaw = 0.0
        else: yaw += step

    global Rf, Pf, Yf, ref, last_wall
    Rf = ANG_EMA * roll  + (1.0 - ANG_EMA) * Rf
    Pf = ANG_EMA * pitch + (1.0 - ANG_EMA) * Pf
    Yf = ANG_EMA * yaw   + (1.0 - ANG_EMA) * Yf

    if AUTO_REZERO and nearFlat and (wNorm < STILL_W):
        if holdStart <= 0.0: holdStart = t_ms
        if not isStill and (t_ms - holdStart) > 350.0:
            ref.update({"roll": Rf, "pitch": Pf, "yaw": Yf})
            isStill = True

    R = _wrap180(Rf - ref["roll"])
    P = _wrap180(Pf - ref["pitch"])
    Y = _wrap180(Yf - ref["yaw"])

    now_wall = time.monotonic()
    if last_wall <= 0.0 or (now_wall - last_wall) >= 0.100:
        last_wall = now_wall
        item = {
            "ts": t_ms/1000.0,
            "angles": {"roll": R, "pitch": P, "yaw": Y},
            "accel":  {"x": ax, "y": ay, "z": az},
            "gyro":   {"x": wx, "y": wy, "z": wz},
        }
        imu_store.append(item)

# ---------- UDP 接收 IMU 并转发 ----------
class UDPProto(asyncio.DatagramProtocol):
    def connection_made(self, transport):
        print(f"[UDP] listening on {UDP_IP}:{UDP_PORT}")
    def datagram_received(self, data, addr):
        try:
            s = data.decode('utf-8', errors='ignore').strip()
            d = json.loads(s)
            if 'ts' not in d and 'timestamp_ms' in d:
                d['ts'] = d.pop('timestamp_ms')
            process_imu_and_maybe_store(d)
            asyncio.create_task(imu_broadcast(json.dumps(d)))
        except Exception:
            pass



# === 新增：注册给 bridge_io 的发送回调（把 JPEG 广播给 /ws/viewer） ===
@app.on_event("startup")
async def on_startup_register_bridge_sender():
    # 保存主线程的事件循环
    main_loop = asyncio.get_event_loop()
    
    def _sender(jpeg_bytes: bytes):
        # 注意：这个函数可能在非协程线程里被调用，需要切回主事件循环
        try:
            # 检查事件循环状态，避免在关闭时发送
            if main_loop.is_closed():
                return
            
            # 标记YOLO已经开始发送处理后的帧
            global yolomedia_sending_frames
            if not yolomedia_sending_frames:
                yolomedia_sending_frames = True
                print("[YOLOMEDIA] 开始发送处理后的帧，切换到YOLO画面", flush=True)
            
            async def _broadcast():
                if not camera_viewers:
                    return
                dead = []
                for ws in list(camera_viewers):
                    try:
                        await ws.send_bytes(jpeg_bytes)
                    except Exception as e:
                        dead.append(ws)
                for ws in dead:
                    try:
                        camera_viewers.remove(ws)
                    except Exception:
                        pass
            
            # 使用保存的主线程事件循环
            future = asyncio.run_coroutine_threadsafe(_broadcast(), main_loop)
            # 不等待结果，避免阻塞生产线程
        except Exception as e:
            # 只在非预期错误时打印日志
            if "Event loop is closed" not in str(e):
                print(f"[DEBUG] _sender error: {e}", flush=True)

    bridge_io.set_sender(_sender)

@app.on_event("startup")
async def on_startup_init_audio():
    """启动时初始化音频系统"""
    # 在后台线程中初始化，避免阻塞启动
    def _init():
        try:
            initialize_audio_system()
        except Exception as e:
            print(f"[AUDIO] 初始化失败: {e}")
    
    threading.Thread(target=_init, daemon=True).start()

@app.on_event("startup")
async def on_startup():
    loop = asyncio.get_running_loop()
    ports_to_try = [UDP_PORT] + [UDP_PORT + i for i in range(1, 6)]
    last_err = None
    for port in ports_to_try:
        try:
            await loop.create_datagram_endpoint(lambda: UDPProto(), local_addr=(UDP_IP, port))
            if port != UDP_PORT:
                print(f"[UDP] 端口 {UDP_PORT} 已被占用，已改用端口 {port}")
            break
        except OSError as e:
            last_err = e
            is_port_in_use = (
                getattr(e, 'winerror', None) == 10048 or
                getattr(e, 'errno', None) in (98, 48) or
                '10048' in str(e) or 'Address already in use' in str(e)
            )
            if is_port_in_use:
                continue
            raise
    else:
        print(f"[UDP] 端口 {ports_to_try[0]}-{ports_to_try[-1]} 均被占用，请关闭其他 app_main 实例或设置 UDP_PORT=12350")
        raise last_err

    # 自动启动电脑麦克风+扬声器（开发模式）
    if AUTO_PC_AUDIO:
        threading.Thread(target=_start_pc_audio_subprocesses, daemon=True).start()

@app.on_event("shutdown")
async def on_shutdown():
    """应用关闭时的清理工作"""
    global _pc_mic_process, _pc_speaker_process
    print("[SHUTDOWN] 开始清理资源...")
    
    # 停止电脑麦克风/扬声器子进程
    for proc, name in [(_pc_mic_process, "mic_test"), (_pc_speaker_process, "speaker_test")]:
        if proc and proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=3)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
            print(f"[SHUTDOWN] 已停止 {name}")
    _pc_mic_process = None
    _pc_speaker_process = None
    
    # 停止YOLO媒体处理
    stop_yolomedia()
    
    # 停止音频和AI任务
    await hard_reset_audio("shutdown")
    
    print("[SHUTDOWN] 资源清理完成")


def _start_pc_audio_subprocesses():
    """在后台线程中启动 mic_test 和 speaker_test，延迟几秒确保服务已就绪"""
    global _pc_mic_process, _pc_speaker_process
    if not AUTO_PC_AUDIO:
        return
    import time
    time.sleep(3)  # 等待 uvicorn 完全启动
    script_dir = os.path.dirname(os.path.abspath(__file__))
    try:
        _pc_mic_process = subprocess.Popen(
            [sys.executable, os.path.join(script_dir, "mic_test.py")],
            cwd=script_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
        )
        print("[AUDIO] 已自动启动电脑麦克风 (mic_test.py)")
    except Exception as e:
        print(f"[AUDIO] 启动 mic_test 失败: {e}")
    try:
        _pc_speaker_process = subprocess.Popen(
            [sys.executable, os.path.join(script_dir, "speaker_test.py")],
            cwd=script_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
        )
        print("[AUDIO] 已自动启动电脑扬声器 (speaker_test.py)")
    except Exception as e:
        print(f"[AUDIO] 启动 speaker_test 失败: {e}")


# --- 导出接口（可选） ---
def get_last_frames():
    return last_frames

def get_camera_ws():
    return esp32_camera_ws

if __name__ == "__main__":
    uvicorn.run(
        app, host="0.0.0.0", port=8081,
        log_level="warning", access_log=False,
        loop="asyncio", workers=1, reload=False
    )
