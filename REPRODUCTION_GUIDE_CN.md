# 🚀 OpenAI 智能眼镜项目完整复现指南

> 本指南将帮助您从零开始，在 Cursor IDE 中完整复现这个 OpenAI 智能眼镜项目。
> 
> **重要提示**：本项目仅供学习交流使用，请勿直接给视障人群使用。

---

## 📑 目录

1. [项目概述](#1-项目概述)
2. [前置准备](#2-前置准备)
3. [ESP32 硬件基础知识](#3-esp32-硬件基础知识)
4. [详细执行步骤](#4-详细执行步骤)
5. [Git 版本控制](#5-git-版本控制)
6. [常见问题解决](#6-常见问题解决)
7. [项目验证与测试](#7-项目验证与测试)

---

## 1. 项目概述

### 1.1 项目简介

这是一个面向视障人士的智能导航与辅助系统，主要功能包括：

- 🚶 **盲道导航**：实时识别盲道，提供语音引导
- 🚦 **过马路辅助**：斑马线识别、红绿灯检测
- 🔍 **物品查找**：语音指令查找物品，手部引导
- 🎙️ **语音交互**：实时语音识别和多模态对话
- 📹 **视频处理**：实时视频流、音视频同步录制

### 1.2 系统架构

```
┌─────────────────┐
│   硬件层        │  ESP32-CAM + 麦克风 + 扬声器
└────────┬────────┘
         │ WebSocket
┌────────▼────────┐
│   服务器层      │  FastAPI + Python (AI 处理)
└────────┬────────┘
         │ HTTP/WebSocket
┌────────▼────────┐
│   监控层        │  Web 浏览器实时监控
└─────────────────┘
```

### 1.3 技术栈

**服务器端**：
- Python 3.9-3.11
- FastAPI (Web 框架)
- PyTorch + YOLO (计算机视觉)
- MediaPipe (手部检测)
- 阿里云 DashScope (语音识别和对话)

**硬件端**：
- ESP32-CAM (摄像头模块)
- Arduino IDE (ESP32 编程)
- C++ (固件开发)

---

## 2. 前置准备

在开始之前，请确保您已准备好以下内容：

### 2.1 必需项（服务器开发）

#### 2.1.1 硬件要求

- [ ] **计算机**：
  - CPU: Intel i5 或以上（推荐 i7/i9）
  - 内存: 最低 8GB RAM（推荐 16GB）
  - 存储: 至少 10GB 可用空间
  
- [ ] **GPU（强烈推荐）**：
  - NVIDIA GPU（支持 CUDA 11.8+）
  - 推荐：RTX 3060 或以上
  - 显存：至少 6GB
  - 📝 **如果没有 GPU**：可以使用 CPU 运行，但速度会非常慢

#### 2.1.2 软件要求

- [ ] **操作系统**：
  - Windows 10/11（推荐）
  - Linux (Ubuntu 20.04+)
  - macOS 10.15+

- [ ] **开发环境**：
  - [ ] Cursor IDE 或 VS Code
  - [ ] Git 2.30+
  - [ ] Python 3.9-3.11（⚠️ 注意版本，不支持 3.12+）

- [ ] **GPU 驱动和 CUDA**（如果有 GPU）：
  - [ ] NVIDIA 驱动（最新版）
  - [ ] CUDA Toolkit 11.8+
  - [ ] cuDNN 8.6+

#### 2.1.3 API 密钥（必需）

- [ ] **阿里云 DashScope API Key**：
  - 用途：语音识别（ASR）和 Qwen-Omni 对话
  - 申请地址：https://dashscope.console.aliyun.com/
  - 步骤：
    1. 注册阿里云账号
    2. 开通 DashScope 服务
    3. 创建 API Key
    4. 充值（建议先充 100 元测试）

#### 2.1.4 模型文件（必需）

- [ ] 从 ModelScope 下载所需模型：
  - 模型地址：https://www.modelscope.cn/models/archifancy/AIGlasses_for_navigation
  - 需要下载的文件：
    - `yolo-seg.pt` (盲道分割, ~50MB)
    - `yoloe-11l-seg.pt` (开放词汇检测, ~80MB)
    - `shoppingbest5.pt` (物品识别, ~30MB)
    - `trafficlight.pt` (红绿灯检测, ~20MB)
    - `hand_landmarker.task` (手部检测, ~15MB)

### 2.2 可选项（硬件测试）

如果您想完整测试硬件功能，需要准备：

#### 2.2.1 ESP32 硬件

- [ ] **ESP32-CAM 开发板**（约 30-50 元）
  - 推荐型号：AI-Thinker ESP32-CAM
  - 包含 OV2640 摄像头
  
- [ ] **USB 转 TTL 串口模块**（约 10-20 元）
  - 用于烧录程序到 ESP32
  - 推荐：CP2102 或 CH340

- [ ] **其他配件**：
  - [ ] 杜邦线（公对母）若干
  - [ ] 面包板（可选）
  - [ ] Micro USB 数据线
  - [ ] 5V 电源适配器（烧录后供电）

#### 2.2.2 音频设备（可选）

- [ ] 麦克风（用于语音输入）
- [ ] 扬声器或耳机（用于语音输出）
- [ ] 如果使用 ESP32：需要 I2S 麦克风和扬声器模块

#### 2.2.3 软件工具

- [ ] **Arduino IDE 2.x**：
  - 下载地址：https://www.arduino.cc/en/software
  - 用于编译和上传 ESP32 固件

---

## 3. ESP32 硬件基础知识

### 3.1 ESP32 是什么？

**ESP32** 是一款由乐鑫科技（Espressif）开发的低成本、低功耗的微控制器芯片，内置 Wi-Fi 和蓝牙功能。

#### 主要特点：
- **双核处理器**：运行频率最高 240MHz
- **内置 Wi-Fi**：支持 802.11 b/g/n
- **内置蓝牙**：支持 BLE 4.2
- **GPIO 引脚**：可连接各种传感器和外设
- **低功耗**：支持深度睡眠模式

### 3.2 ESP32-CAM 是什么？

**ESP32-CAM** 是一个基于 ESP32 的摄像头模块开发板。

#### 组成部分：
1. **ESP32 主芯片**：负责处理和 Wi-Fi 通信
2. **OV2640 摄像头**：200 万像素摄像头
3. **SD 卡槽**：可存储照片和视频
4. **板载天线**：Wi-Fi 天线（也可外接）

#### 引脚说明：
```
VCC  - 5V 供电
GND  - 地线
U0R  - UART 接收 (RX)
U0T  - UART 发送 (TX)
GPIO - 通用输入输出引脚
```

### 3.3 ESP32 在本项目中的角色

在本项目中，ESP32-CAM 的作用是：

1. **采集视频**：通过摄像头实时拍摄
2. **采集音频**：通过麦克风录制声音（如果有）
3. **Wi-Fi 传输**：将视频和音频通过 WebSocket 发送到服务器
4. **接收音频**：接收服务器返回的语音播报
5. **IMU 数据**：发送姿态传感器数据（如果有 IMU）

### 3.4 ESP32 编程基础

#### 3.4.1 开发环境

ESP32 可以使用多种方式编程：
- **Arduino IDE**：最简单，适合初学者（本项目使用）
- **ESP-IDF**：官方框架，功能更强大
- **PlatformIO**：跨平台 IDE

#### 3.4.2 基本程序结构

```cpp
void setup() {
  // 初始化代码，只运行一次
  Serial.begin(115200);  // 初始化串口
  // 初始化 Wi-Fi、摄像头等
}

void loop() {
  // 主循环，不断重复执行
  // 采集数据、发送数据等
}
```

#### 3.4.3 本项目的 ESP32 代码

位于 `compile/compile.ino`，主要功能：
- Wi-Fi 连接
- 摄像头初始化
- WebSocket 客户端
- 视频流传输
- IMU 数据采集（ICM42688）

### 3.5 如何烧录程序到 ESP32-CAM

由于 ESP32-CAM 没有 USB 接口，需要使用 USB 转 TTL 模块：

#### 接线方式（烧录模式）：
```
USB转TTL    ESP32-CAM
------      ---------
VCC   ——>   VCC (5V)
GND   ——>   GND
TX    ——>   U0R (RX)
RX    ——>   U0T (TX)

特殊：GPIO0 连接到 GND（进入烧录模式）
```

#### 烧录步骤：
1. 按上述方式接线（GPIO0 接 GND）
2. 给 ESP32-CAM 上电
3. 打开 Arduino IDE，选择端口和开发板
4. 点击上传
5. 上传完成后，断开 GPIO0 和 GND
6. 重启 ESP32-CAM

### 3.6 常见 ESP32 问题

| 问题 | 原因 | 解决方法 |
|------|------|----------|
| 无法连接端口 | 驱动问题 | 安装 CP2102 或 CH340 驱动 |
| 上传失败 | GPIO0 未接地 | 检查 GPIO0 是否连接到 GND |
| 摄像头不工作 | 初始化失败 | 检查摄像头排线，重启设备 |
| Wi-Fi 连接失败 | 信号弱或密码错误 | 检查 Wi-Fi 配置 |

---

## 4. 详细执行步骤

现在开始正式复现项目。请按照以下步骤逐步操作，**每完成一个大步骤后，请告诉我，我会指导您进行下一步**。

### 📋 总体任务清单

- [ ] **阶段 1**：环境准备（预计 1-2 小时）
- [ ] **阶段 2**：项目下载和配置（预计 30 分钟）
- [ ] **阶段 3**：依赖安装（预计 30-60 分钟）
- [ ] **阶段 4**：模型文件准备（预计 30 分钟）
- [ ] **阶段 5**：服务器端测试（预计 30 分钟）
- [ ] **阶段 6**：ESP32 硬件配置（可选，预计 1-2 小时）
- [ ] **阶段 7**：完整系统测试（预计 30 分钟）

---

### 阶段 1：环境准备

#### 步骤 1.1：检查 Python 版本

```bash
# 打开终端或命令提示符
python --version
# 或
python3 --version
```

**要求**：Python 3.9, 3.10, 或 3.11

- ✅ 如果版本正确，继续下一步
- ❌ 如果版本不对，请安装正确版本：
  - Windows: 从 https://www.python.org/downloads/ 下载
  - macOS: `brew install python@3.11`
  - Linux: `sudo apt install python3.11`

**🔖 Git 检查点**：
```bash
git status  # 确认在正确的分支
```

#### 步骤 1.2：检查 Git 安装

```bash
git --version
```

**要求**：Git 2.30+

- ❌ 如果未安装：从 https://git-scm.com/downloads 下载安装

#### 步骤 1.3：检查 CUDA（如果有 GPU）

```bash
# Windows/Linux
nvidia-smi

# 查看 CUDA 版本
nvcc --version
```

**预期结果**：
- 能看到 GPU 信息
- CUDA 版本 11.8 或更高

- ❌ 如果没有安装：
  1. 安装 NVIDIA 驱动：https://www.nvidia.com/Download/index.aspx
  2. 安装 CUDA Toolkit：https://developer.nvidia.com/cuda-downloads

**✅ 阶段 1 完成检查**：
- [ ] Python 版本正确
- [ ] Git 已安装
- [ ] GPU 和 CUDA 可用（如果有 GPU）

**🎯 完成后请告诉我，我会指导您进入阶段 2**

---

### 阶段 2：项目下载和配置

#### 步骤 2.1：克隆项目（如果还未克隆）

```bash
# 在您想要的目录下执行
git clone https://github.com/13392903419/OpenAIglasses_for_Navigation.git
cd OpenAIglasses_for_Navigation
```

#### 步骤 2.2：查看项目结构

```bash
# 列出主要文件
ls -la
# 或 Windows
dir
```

**预期看到**：
- `app_main.py` - 主程序
- `requirements.txt` - 依赖列表
- `setup.sh` / `setup.bat` - 安装脚本
- `compile/` - ESP32 代码
- `model/` - 模型目录（可能为空）

#### 步骤 2.3：创建 Git 分支（版本控制）

```bash
# 创建您自己的开发分支
git checkout -b my-reproduction-$(date +%Y%m%d)

# 查看当前分支
git branch
```

#### 步骤 2.4：初始化目录结构

```bash
# 创建必要的目录
mkdir -p model recordings music voice

# 验证目录创建
ls -la
```

**✅ 阶段 2 完成检查**：
- [ ] 项目已克隆到本地
- [ ] 创建了开发分支
- [ ] 必要的目录已创建

**🔖 Git 提交**：
```bash
git add .
git commit -m "chore: 初始化项目目录结构"
```

**🎯 完成后请告诉我，我会指导您进入阶段 3**

---

### 阶段 3：依赖安装

#### 步骤 3.1：创建虚拟环境

**为什么需要虚拟环境？**
- 隔离项目依赖，避免冲突
- 方便管理不同项目的包版本

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 激活成功后，命令提示符前会显示 (venv)
```

#### 步骤 3.2：升级 pip

```bash
python -m pip install --upgrade pip
```

#### 步骤 3.3：安装 PyTorch（重要）

**有 GPU 的情况**：
```bash
pip install torch==2.0.1+cu118 torchvision==0.15.2+cu118 --index-url https://download.pytorch.org/whl/cu118
```

**没有 GPU 的情况**：
```bash
pip install torch==2.0.1 torchvision==0.15.2
```

**验证安装**：
```bash
python -c "import torch; print(f'PyTorch 版本: {torch.__version__}'); print(f'CUDA 可用: {torch.cuda.is_available()}')"
```

预期输出：
```
PyTorch 版本: 2.0.1+cu118
CUDA 可用: True  # 如果有 GPU
```

#### 步骤 3.4：安装其他依赖

```bash
pip install -r requirements.txt
```

**常见安装问题**：

**问题 1**：PyAudio 安装失败（Windows）
```bash
# 解决方法：从 https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio
# 下载对应的 .whl 文件，然后：
pip install PyAudio‑0.2.11‑cp311‑cp311‑win_amd64.whl
```

**问题 2**：OpenCV 无法导入（Linux）
```bash
sudo apt-get install libgl1-mesa-glx libglib2.0-0
```

#### 步骤 3.5：使用自动安装脚本（可选）

也可以直接运行提供的安装脚本：

**Linux/macOS**：
```bash
chmod +x setup.sh
./setup.sh
```

**Windows**：
```cmd
setup.bat
```

**✅ 阶段 3 完成检查**：
- [ ] 虚拟环境已创建并激活
- [ ] PyTorch 安装成功且能检测到 CUDA（如果有 GPU）
- [ ] 所有依赖安装成功，没有错误

**🔖 Git 提交**：
```bash
# 创建 .gitignore 文件
echo "venv/" >> .gitignore
echo "*.pyc" >> .gitignore
echo "__pycache__/" >> .gitignore
echo ".env" >> .gitignore
echo "recordings/" >> .gitignore

git add .gitignore
git commit -m "chore: 添加 .gitignore 文件"
```

**🎯 完成后请告诉我，我会指导您进入阶段 4**

---

### 阶段 4：模型文件准备

#### 步骤 4.1：下载模型文件

1. 访问模型仓库：https://www.modelscope.cn/models/archifancy/AIGlasses_for_navigation
2. 点击 "文件" 标签
3. 下载以下文件到本地：

| 文件名 | 大小 | 用途 |
|--------|------|------|
| `yolo-seg.pt` | ~50MB | 盲道分割 |
| `yoloe-11l-seg.pt` | ~80MB | 开放词汇检测 |
| `shoppingbest5.pt` | ~30MB | 物品识别 |
| `trafficlight.pt` | ~20MB | 红绿灯检测 |
| `hand_landmarker.task` | ~15MB | 手部检测 |

#### 步骤 4.2：放置模型文件

将下载的所有模型文件移动到项目的 `model/` 目录：

```bash
# 假设文件下载到了 ~/Downloads/
# Linux/macOS:
cp ~/Downloads/*.pt model/
cp ~/Downloads/*.task model/

# Windows (PowerShell):
Copy-Item "$env:USERPROFILE\Downloads\*.pt" model\
Copy-Item "$env:USERPROFILE\Downloads\*.task" model\
```

#### 步骤 4.3：验证模型文件

```bash
# 列出 model 目录
ls -lh model/
# 或 Windows
dir model\
```

**预期结果**：看到 5 个文件，总大小约 200MB

```bash
# 使用脚本验证（可选）
python -c "
import os
models = ['yolo-seg.pt', 'yoloe-11l-seg.pt', 'shoppingbest5.pt', 'trafficlight.pt', 'hand_landmarker.task']
for m in models:
    path = f'model/{m}'
    if os.path.exists(path):
        size = os.path.getsize(path) / 1024 / 1024
        print(f'✓ {m} ({size:.1f} MB)')
    else:
        print(f'✗ {m} (缺失)')
"
```

**✅ 阶段 4 完成检查**：
- [ ] 所有 5 个模型文件已下载
- [ ] 模型文件已放置在 `model/` 目录
- [ ] 文件大小合理（不是损坏的下载）

**🔖 Git 提交**：
```bash
# 注意：模型文件太大，不要提交到 Git
echo "model/*.pt" >> .gitignore
echo "model/*.task" >> .gitignore

# 只提交目录结构
touch model/.gitkeep
git add model/.gitkeep .gitignore
git commit -m "chore: 准备模型文件目录"
```

**🎯 完成后请告诉我，我会指导您进入阶段 5**

---

### 阶段 5：服务器端测试

#### 步骤 5.1：配置 API 密钥

创建 `.env` 文件：

```bash
# Linux/macOS
nano .env

# Windows
notepad .env
```

填入以下内容（替换为您的 API Key）：

```bash
# 阿里云 DashScope API Key
DASHSCOPE_API_KEY=sk-your-api-key-here

# 可选配置
AIGLASS_MASK_MIN_AREA=1500
AIGLASS_MASK_MORPH=3
AIGLASS_MASK_MISS_TTL=6
AIGLASS_PANEL_SCALE=0.65
TTS_INTERVAL_SEC=1.0
ENABLE_TTS=true
```

**保存文件**

#### 步骤 5.2：测试模型加载

创建测试脚本 `test_model_loading.py`：

```python
# test_model_loading.py
import torch
from ultralytics import YOLO
import os

print("=" * 50)
print("测试模型加载")
print("=" * 50)

# 测试 CUDA
print(f"\nPyTorch 版本: {torch.__version__}")
print(f"CUDA 可用: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"CUDA 版本: {torch.version.cuda}")
    print(f"GPU 设备: {torch.cuda.get_device_name(0)}")

# 测试模型
models = {
    'yolo-seg.pt': '盲道分割',
    'yoloe-11l-seg.pt': '开放词汇检测',
    'shoppingbest5.pt': '物品识别',
    'trafficlight.pt': '红绿灯检测',
}

print("\n" + "=" * 50)
print("测试 YOLO 模型加载")
print("=" * 50)

for model_file, desc in models.items():
    model_path = f'model/{model_file}'
    if os.path.exists(model_path):
        try:
            print(f"\n加载 {desc} ({model_file})...")
            model = YOLO(model_path)
            print(f"✓ {desc} 加载成功")
        except Exception as e:
            print(f"✗ {desc} 加载失败: {e}")
    else:
        print(f"✗ {model_file} 文件不存在")

# 测试 MediaPipe
print("\n" + "=" * 50)
print("测试 MediaPipe 手部检测")
print("=" * 50)

hand_model = 'model/hand_landmarker.task'
if os.path.exists(hand_model):
    try:
        import mediapipe as mp
        print(f"✓ MediaPipe 版本: {mp.__version__}")
        print(f"✓ 手部模型文件存在")
    except Exception as e:
        print(f"✗ MediaPipe 测试失败: {e}")
else:
    print(f"✗ 手部模型文件不存在")

print("\n" + "=" * 50)
print("测试完成")
print("=" * 50)
```

运行测试：

```bash
python test_model_loading.py
```

**预期输出**：所有模型都显示 "加载成功"

#### 步骤 5.3：启动服务器

```bash
# 确保虚拟环境已激活
python app_main.py
```

**预期输出**：
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8081 (Press CTRL+C to quit)
```

#### 步骤 5.4：测试 Web 界面

1. 打开浏览器
2. 访问：`http://localhost:8081`
3. 应该能看到监控界面

**预期看到**：
- 视频流显示区域（可能是黑色，因为还没有摄像头输入）
- 状态面板
- IMU 可视化区域

#### 步骤 5.5：检查日志

在服务器终端查看启动日志，确保没有错误：

```
✓ 模型加载成功
✓ WebSocket 端点已注册
✓ 音频系统已初始化
✓ 录制系统已启动
```

**停止服务器**：按 `Ctrl+C`

**✅ 阶段 5 完成检查**：
- [ ] `.env` 文件已创建，API Key 已配置
- [ ] 模型加载测试全部通过
- [ ] 服务器能成功启动
- [ ] Web 界面能正常访问

**🔖 Git 提交**：
```bash
# 不要提交 .env 文件（已在 .gitignore 中）
# 创建示例文件
cp .env .env.example
# 在 .env.example 中将实际的 API Key 替换为占位符
sed -i 's/sk-.*$/sk-your-api-key-here/g' .env.example  # Linux/macOS
# Windows 请手动编辑 .env.example

git add .env.example test_model_loading.py
git commit -m "feat: 添加服务器配置和测试脚本"
git push origin my-reproduction-$(date +%Y%m%d)  # 推送到远程
```

**🎯 完成后请告诉我：**
- 如果您有 ESP32 硬件，我会指导您进入阶段 6（ESP32 配置）
- 如果没有硬件，可以跳到阶段 7（使用电脑摄像头测试）

---

### 阶段 6：ESP32 硬件配置（可选）

**⚠️ 前提**：您需要有 ESP32-CAM 硬件和 USB 转 TTL 模块

#### 步骤 6.1：安装 Arduino IDE

1. 下载：https://www.arduino.cc/en/software
2. 安装最新版本（推荐 2.x）

#### 步骤 6.2：配置 ESP32 开发板支持

1. 打开 Arduino IDE
2. 进入 **文件 → 首选项**
3. 在 "附加开发板管理器网址" 中添加：
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
4. 点击 "确定"
5. 进入 **工具 → 开发板 → 开发板管理器**
6. 搜索 "esp32"
7. 安装 "esp32 by Espressif Systems"（版本 2.0.x）

#### 步骤 6.3：连接 ESP32-CAM

**接线图**：
```
USB转TTL    ESP32-CAM
------      ---------
VCC   →     5V
GND   →     GND
TX    →     U0R (RX)
RX    →     U0T (TX)

烧录模式：GPIO0 → GND（用杜邦线连接）
```

**接线步骤**：
1. 断开 ESP32-CAM 电源
2. 按上述方式连接线缆
3. 使用杜邦线将 GPIO0 连接到 GND
4. 将 USB 转 TTL 插入电脑

#### 步骤 6.4：配置 Arduino IDE

1. **选择开发板**：
   - 工具 → 开发板 → ESP32 Arduino → "AI Thinker ESP32-CAM"

2. **选择端口**：
   - 工具 → 端口 → 选择 COM 端口（Windows）或 /dev/ttyUSB0（Linux）

3. **配置上传速度**：
   - 工具 → 上传速度 → 115200

#### 步骤 6.5：修改 ESP32 代码

1. 打开 `compile/compile.ino`
2. 修改 Wi-Fi 配置（约在第 50-60 行）：

```cpp
const char* ssid = "你的WiFi名称";
const char* password = "你的WiFi密码";
```

3. 修改服务器地址（约在第 70-80 行）：

```cpp
const char* websocket_server_host = "192.168.1.100";  // 改为你电脑的 IP
const uint16_t websocket_server_port = 8081;
```

**如何查看电脑 IP**：
```bash
# Windows
ipconfig

# Linux/macOS
ifconfig
# 或
ip addr show
```

#### 步骤 6.6：编译和上传

1. 点击 Arduino IDE 中的 "验证"（✓）按钮，等待编译完成
2. 确认 GPIO0 已连接到 GND
3. 点击 "上传"（→）按钮
4. 等待上传完成（约 1-2 分钟）

**预期输出**：
```
Connecting....
Writing at 0x00001000... (1%)
...
Writing at 0x00100000... (100%)
Wrote 1234567 bytes...
Hard resetting via RTS pin...
```

#### 步骤 6.7：运行 ESP32

1. **断开 GPIO0 和 GND 的连接**（重要！）
2. 给 ESP32-CAM 重新上电（或按 RST 按钮）
3. 打开串口监视器（工具 → 串口监视器，波特率 115200）

**预期看到**：
```
Connecting to WiFi...
WiFi connected
IP address: 192.168.1.xxx
Connecting to WebSocket...
WebSocket connected
Camera started
```

#### 步骤 6.8：测试完整系统

1. 启动服务器：
   ```bash
   python app_main.py
   ```

2. 确保 ESP32 已连接（在服务器日志中查看）

3. 打开浏览器：`http://localhost:8081`

4. 应该能看到实时视频流

**✅ 阶段 6 完成检查**：
- [ ] Arduino IDE 已安装和配置
- [ ] ESP32 代码已修改（Wi-Fi 和服务器地址）
- [ ] 程序已成功上传到 ESP32
- [ ] ESP32 能连接到 Wi-Fi 和服务器
- [ ] Web 界面能显示 ESP32 的视频流

**🔖 Git 提交**：
```bash
git add compile/compile.ino
git commit -m "feat: 配置 ESP32 Wi-Fi 和服务器连接"
git push origin my-reproduction-$(date +%Y%m%d)
```

**🎯 完成后请告诉我，我会指导您进入阶段 7（完整系统测试）**

---

### 阶段 7：完整系统测试

#### 步骤 7.1：功能测试清单

**基础功能**：

- [ ] **视频流测试**：
  - 启动服务器
  - 打开 Web 界面
  - 确认能看到视频流
  - FPS 是否稳定（> 15 FPS）

- [ ] **语音识别测试**：
  - 对着麦克风说话
  - 检查 Web 界面是否显示识别结果

- [ ] **AI 对话测试**：
  - 说："你好"
  - 等待 AI 回复
  - 检查音频播放是否正常

**导航功能**（需要实际场景）：

- [ ] **盲道导航**：
  - 语音指令："开始导航"
  - 将摄像头对准盲道
  - 检查是否有语音引导

- [ ] **过马路辅助**：
  - 语音指令："开始过马路"
  - 将摄像头对准斑马线
  - 检查对齐引导

- [ ] **物品查找**：
  - 语音指令："帮我找一下红牛"
  - 将摄像头对准物品
  - 检查手部引导

#### 步骤 7.2：性能测试

运行性能测试脚本（创建 `test_performance.py`）：

```python
# test_performance.py
import time
import psutil
import torch

def test_performance():
    print("=" * 50)
    print("性能测试")
    print("=" * 50)
    
    # CPU 使用率
    cpu_percent = psutil.cpu_percent(interval=1)
    print(f"\nCPU 使用率: {cpu_percent}%")
    
    # 内存使用
    memory = psutil.virtual_memory()
    print(f"内存使用: {memory.percent}% ({memory.used / 1024**3:.1f} GB / {memory.total / 1024**3:.1f} GB)")
    
    # GPU 使用（如果有）
    if torch.cuda.is_available():
        print(f"\nGPU: {torch.cuda.get_device_name(0)}")
        print(f"GPU 内存使用: {torch.cuda.memory_allocated() / 1024**3:.1f} GB")
        print(f"GPU 内存缓存: {torch.cuda.memory_reserved() / 1024**3:.1f} GB")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    test_performance()
```

运行：
```bash
python test_performance.py
```

#### 步骤 7.3：记录测试结果

创建测试报告 `TEST_RESULTS.md`：

```markdown
# 测试报告

## 测试环境
- 日期：2024-XX-XX
- 操作系统：Windows 11 / Ubuntu 22.04
- Python 版本：3.11.x
- GPU：NVIDIA RTX 3060 / CPU Only

## 测试结果

### 基础功能
- [ ] 视频流：正常 / 异常
- [ ] FPS：XX fps
- [ ] 语音识别：正常 / 异常
- [ ] AI 对话：正常 / 异常

### 导航功能
- [ ] 盲道导航：正常 / 异常
- [ ] 过马路辅助：正常 / 异常
- [ ] 物品查找：正常 / 异常

### 性能指标
- CPU 使用率：XX%
- 内存使用：XX GB
- GPU 使用率：XX%（如果有）

### 问题记录
1. 问题描述...
2. 问题描述...

### 改进建议
1. 建议...
2. 建议...
```

#### 步骤 7.4：录制演示视频

1. 启动完整系统
2. 使用屏幕录制软件录制
3. 演示主要功能
4. 保存视频到 `demo/` 目录

**✅ 阶段 7 完成检查**：
- [ ] 所有基础功能测试通过
- [ ] 至少一个导航功能测试通过
- [ ] 性能测试完成
- [ ] 测试报告已创建
- [ ] （可选）演示视频已录制

**🔖 最终 Git 提交**：
```bash
git add test_performance.py TEST_RESULTS.md
git commit -m "test: 完成系统功能和性能测试"
git push origin my-reproduction-$(date +%Y%m%d)
```

**🎉 恭喜！项目复现完成！**

---

## 5. Git 版本控制

### 5.1 Git 工作流程

在整个复现过程中，建议使用以下 Git 工作流：

```bash
# 1. 创建功能分支
git checkout -b feature/your-feature-name

# 2. 进行修改

# 3. 查看修改
git status
git diff

# 4. 暂存修改
git add <file>
# 或添加所有修改
git add .

# 5. 提交修改
git commit -m "类型: 简短描述"

# 6. 推送到远程
git push origin feature/your-feature-name
```

### 5.2 提交信息规范

使用约定式提交（Conventional Commits）：

| 类型 | 说明 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat: 添加物品识别功能` |
| `fix` | 修复 Bug | `fix: 修复视频流断连问题` |
| `docs` | 文档 | `docs: 更新 README` |
| `style` | 代码格式 | `style: 格式化代码` |
| `refactor` | 重构 | `refactor: 重构导航模块` |
| `test` | 测试 | `test: 添加单元测试` |
| `chore` | 杂项 | `chore: 更新依赖` |

### 5.3 常用 Git 命令

```bash
# 查看状态
git status

# 查看历史
git log --oneline

# 创建分支
git branch <branch-name>

# 切换分支
git checkout <branch-name>

# 合并分支
git merge <branch-name>

# 拉取远程更新
git pull origin main

# 推送到远程
git push origin <branch-name>

# 撤销修改（未暂存）
git checkout -- <file>

# 撤销暂存
git reset HEAD <file>

# 查看远程仓库
git remote -v

# 添加远程仓库
git remote add origin <url>
```

### 5.4 .gitignore 配置

确保 `.gitignore` 包含以下内容：

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
ENV/

# 项目特定
.env
recordings/
model/*.pt
model/*.task
*.avi
*.wav

# IDE
.vscode/
.idea/
*.swp
*.swo

# 系统
.DS_Store
Thumbs.db
```

### 5.5 远程仓库管理

```bash
# 添加您自己的远程仓库
git remote add my-remote https://github.com/your-username/your-repo.git

# 推送到您的仓库
git push my-remote my-reproduction-$(date +%Y%m%d)

# 查看所有远程仓库
git remote -v

# 从上游拉取更新
git remote add upstream https://github.com/original-author/original-repo.git
git fetch upstream
git merge upstream/main
```

---

## 6. 常见问题解决

### 6.1 安装相关

**Q: pip 安装速度很慢**
```bash
# 使用国内镜像
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple <package>
# 或永久配置
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

**Q: PyTorch 安装失败**
```bash
# 尝试不同的 CUDA 版本
pip install torch==2.0.1+cu117 torchvision==0.15.2+cu117 --index-url https://download.pytorch.org/whl/cu117
```

**Q: 虚拟环境激活失败（Windows PowerShell）**
```powershell
# 需要先允许执行脚本
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 6.2 运行时错误

**Q: "ModuleNotFoundError: No module named 'xxx'"**
```bash
# 确保虚拟环境已激活
# 重新安装依赖
pip install -r requirements.txt
```

**Q: CUDA out of memory**
```python
# 减小批处理大小或使用 CPU
# 在代码中添加：
import torch
torch.cuda.empty_cache()
```

**Q: "Address already in use" (端口 8081 被占用)**
```bash
# Linux/macOS
lsof -i :8081
kill -9 <PID>

# Windows
netstat -ano | findstr :8081
taskkill /PID <PID> /F

# 或修改 app_main.py 中的端口
```

### 6.3 ESP32 相关

**Q: 无法找到 ESP32 端口**
- 检查驱动：安装 CP2102 或 CH340 驱动
- 检查连接：确认 USB 线缆正常
- 尝试不同的 USB 端口

**Q: 上传失败 "A fatal error occurred"**
- 确认 GPIO0 已连接到 GND
- 按住 BOOT 按钮，点击上传
- 降低上传速度（115200）

**Q: ESP32 无法连接 Wi-Fi**
- 检查 SSID 和密码是否正确
- 确认 Wi-Fi 是 2.4GHz（ESP32 不支持 5GHz）
- 检查 Wi-Fi 信号强度

**Q: 摄像头初始化失败**
- 检查摄像头排线
- 重启 ESP32
- 尝试降低分辨率

### 6.4 性能优化

**Q: FPS 太低**
- 启用 GPU 加速
- 减小视频分辨率
- 降低检测频率
- 关闭不必要的功能

**Q: 内存占用过高**
- 定期清理缓存
- 减少同时运行的模型
- 使用更小的模型

### 6.5 API 相关

**Q: "Invalid API Key"**
- 检查 `.env` 文件中的 API Key
- 确认账户有余额
- 检查 API Key 是否过期

**Q: 语音识别不工作**
- 检查麦克风权限
- 确认音频格式正确（PCM16, 16000Hz）
- 查看 DashScope 控制台日志

---

## 7. 项目验证与测试

### 7.1 单元测试

创建测试文件 `tests/test_basic.py`：

```python
import pytest
import torch
from ultralytics import YOLO

def test_pytorch():
    """测试 PyTorch 安装"""
    assert torch.__version__.startswith('2.0')
    
def test_cuda_available():
    """测试 CUDA 可用性"""
    # GPU 环境应该通过，CPU 环境会失败（正常）
    if torch.cuda.is_available():
        assert torch.cuda.device_count() > 0

def test_model_loading():
    """测试模型加载"""
    model = YOLO('model/yolo-seg.pt')
    assert model is not None
```

运行测试：
```bash
pip install pytest
pytest tests/
```

### 7.2 集成测试

创建 `tests/test_integration.py`：

```python
import asyncio
from fastapi.testclient import TestClient
from app_main import app

def test_web_interface():
    """测试 Web 界面"""
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200

def test_websocket():
    """测试 WebSocket 连接"""
    client = TestClient(app)
    with client.websocket_connect("/ws/viewer") as websocket:
        # 应该能成功连接
        assert websocket is not None
```

### 7.3 性能基准测试

创建 `tests/test_performance.py`：

```python
import time
import cv2
import numpy as np
from ultralytics import YOLO

def test_yolo_inference_speed():
    """测试 YOLO 推理速度"""
    model = YOLO('model/yolo-seg.pt')
    
    # 创建测试图像
    img = np.random.randint(0, 255, (640, 480, 3), dtype=np.uint8)
    
    # 预热
    for _ in range(10):
        _ = model(img, verbose=False)
    
    # 测试
    start = time.time()
    n_iterations = 100
    for _ in range(n_iterations):
        _ = model(img, verbose=False)
    elapsed = time.time() - start
    
    fps = n_iterations / elapsed
    print(f"FPS: {fps:.2f}")
    
    # 断言 FPS 大于某个阈值（根据硬件调整）
    assert fps > 10  # 至少 10 FPS
```

### 7.4 完整性检查脚本

创建 `check_setup.py`：

```python
#!/usr/bin/env python3
"""
完整性检查脚本
检查项目是否已正确设置
"""

import os
import sys

def check_python_version():
    """检查 Python 版本"""
    version = sys.version_info
    if version.major == 3 and 9 <= version.minor <= 11:
        print("✓ Python 版本正确:", f"{version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print("✗ Python 版本不正确:", f"{version.major}.{version.minor}.{version.micro}")
        print("  需要 Python 3.9-3.11")
        return False

def check_dependencies():
    """检查依赖安装"""
    required = [
        'torch', 'torchvision', 'ultralytics', 'fastapi',
        'opencv-python', 'mediapipe', 'dashscope'
    ]
    
    all_ok = True
    for pkg in required:
        try:
            __import__(pkg.replace('-', '_'))
            print(f"✓ {pkg}")
        except ImportError:
            print(f"✗ {pkg} (未安装)")
            all_ok = False
    
    return all_ok

def check_models():
    """检查模型文件"""
    models = [
        'model/yolo-seg.pt',
        'model/yoloe-11l-seg.pt',
        'model/shoppingbest5.pt',
        'model/trafficlight.pt',
        'model/hand_landmarker.task'
    ]
    
    all_ok = True
    for model in models:
        if os.path.exists(model):
            size = os.path.getsize(model) / 1024 / 1024
            print(f"✓ {model} ({size:.1f} MB)")
        else:
            print(f"✗ {model} (不存在)")
            all_ok = False
    
    return all_ok

def check_config():
    """检查配置文件"""
    if os.path.exists('.env'):
        print("✓ .env 配置文件存在")
        # 检查 API Key
        with open('.env', 'r') as f:
            content = f.read()
            if 'DASHSCOPE_API_KEY' in content and 'sk-' in content:
                print("  ✓ API Key 已配置")
                return True
            else:
                print("  ✗ API Key 未配置或格式错误")
                return False
    else:
        print("✗ .env 配置文件不存在")
        return False

def main():
    print("=" * 60)
    print("OpenAI 智能眼镜项目 - 环境检查")
    print("=" * 60)
    
    checks = [
        ("Python 版本", check_python_version),
        ("依赖安装", check_dependencies),
        ("模型文件", check_models),
        ("配置文件", check_config),
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\n{name}:")
        results.append(check_func())
    
    print("\n" + "=" * 60)
    if all(results):
        print("✓ 所有检查通过！可以运行项目。")
        print("\n启动命令: python app_main.py")
        return 0
    else:
        print("✗ 部分检查失败，请修复后再运行。")
        return 1

if __name__ == "__main__":
    exit(main())
```

运行完整性检查：
```bash
python check_setup.py
```

---

## 📝 附录

### A. 项目目录结构

```
OpenAIglasses_for_Navigation/
├── app_main.py                 # 主程序入口
├── requirements.txt            # Python 依赖
├── setup.sh / setup.bat       # 安装脚本
├── .env                       # 环境变量（不提交）
├── .gitignore                 # Git 忽略文件
│
├── model/                     # 模型文件目录
│   ├── yolo-seg.pt
│   ├── yoloe-11l-seg.pt
│   ├── shoppingbest5.pt
│   ├── trafficlight.pt
│   └── hand_landmarker.task
│
├── compile/                   # ESP32 固件
│   ├── compile.ino
│   ├── camera_pins.h
│   └── ICM42688.cpp/h
│
├── templates/                 # Web 模板
│   └── index.html
│
├── static/                    # 静态资源
│   ├── main.js
│   ├── vision.js
│   └── ...
│
├── music/                     # 提示音
├── voice/                     # 预录语音
├── recordings/                # 录制文件（不提交）
│
├── tests/                     # 测试文件
│   ├── test_basic.py
│   ├── test_integration.py
│   └── test_performance.py
│
└── docs/                      # 文档
    ├── README.md
    ├── REPRODUCTION_GUIDE_CN.md  # 本文件
    └── API.md
```

### B. 快速命令参考

```bash
# 环境管理
python -m venv venv                    # 创建虚拟环境
source venv/bin/activate               # 激活（Linux/macOS）
venv\Scripts\activate                  # 激活（Windows）
deactivate                             # 退出虚拟环境

# 依赖管理
pip install -r requirements.txt        # 安装依赖
pip freeze > requirements.txt          # 导出依赖
pip list                               # 列出已安装包

# Git 操作
git status                             # 查看状态
git add .                              # 添加所有修改
git commit -m "message"                # 提交
git push origin branch-name            # 推送
git pull origin main                   # 拉取

# 项目运行
python app_main.py                     # 启动服务器
python check_setup.py                  # 检查环境
pytest tests/                          # 运行测试
```

### C. 资源链接

**官方文档**：
- Python: https://docs.python.org/3/
- PyTorch: https://pytorch.org/docs/
- FastAPI: https://fastapi.tiangolo.com/
- Ultralytics YOLO: https://docs.ultralytics.com/

**教程资源**：
- ESP32 入门: https://randomnerdtutorials.com/getting-started-with-esp32/
- Arduino IDE: https://www.arduino.cc/en/Guide
- Git 教程: https://git-scm.com/book/zh/v2

**社区支持**：
- GitHub Issues: [项目 Issues 页面]
- Stack Overflow: https://stackoverflow.com/
- ESP32 论坛: https://www.esp32.com/

### D. 更新日志

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| 1.0 | 2024-02-12 | 初始版本，完整复现指南 |

---

## 📧 获取帮助

如果您在复现过程中遇到问题：

1. **查看日志**：仔细阅读错误信息
2. **搜索问题**：在 GitHub Issues 中搜索类似问题
3. **提问**：在项目 Issues 中提问，提供详细信息：
   - 操作系统和版本
   - Python 版本
   - 完整的错误信息
   - 已尝试的解决方法

---

## 🎉 总结

恭喜您完成了 OpenAI 智能眼镜项目的复现！

通过本指南，您应该已经：
- ✅ 理解了项目的整体架构
- ✅ 掌握了 ESP32 的基础知识
- ✅ 成功搭建了开发环境
- ✅ 运行了完整的系统
- ✅ 学会了使用 Git 进行版本控制

**下一步建议**：
1. 深入阅读源代码，理解各模块实现
2. 尝试修改和优化功能
3. 添加新的导航模式或检测功能
4. 参与社区贡献，提交 Pull Request

**祝您学习愉快！** 🚀
