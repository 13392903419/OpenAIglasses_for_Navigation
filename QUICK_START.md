# ⚡ 快速开始指南

> 5 分钟快速了解如何启动 OpenAI 智能眼镜项目

---

## 🎯 最小化启动步骤

如果您只想快速看到效果，按照以下步骤操作：

### 1. 环境要求（5 分钟检查）

```bash
# 检查 Python 版本（需要 3.9-3.11）
python --version

# 检查 Git
git --version

# （可选）检查 GPU
nvidia-smi
```

✅ **要求**: Python 3.9-3.11，Git 已安装

### 2. 克隆项目（1 分钟）

```bash
git clone https://github.com/13392903419/OpenAIglasses_for_Navigation.git
cd OpenAIglasses_for_Navigation
```

### 3. 快速安装（5-10 分钟）

#### 方法 A：使用自动脚本（推荐）

**Linux/macOS**:
```bash
chmod +x setup.sh
./setup.sh
```

**Windows**:
```cmd
setup.bat
```

#### 方法 B：手动安装

```bash
# 1. 创建虚拟环境
python -m venv venv

# 2. 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt
```

### 4. 准备必需文件（10-15 分钟）

#### 4.1 下载模型（约 200MB）

从 ModelScope 下载模型文件：
https://www.modelscope.cn/models/archifancy/AIGlasses_for_navigation

下载后放入 `model/` 目录：
- `yolo-seg.pt`
- `yoloe-11l-seg.pt`
- `shoppingbest5.pt`
- `trafficlight.pt`
- `hand_landmarker.task`

#### 4.2 配置 API Key

创建 `.env` 文件：
```bash
DASHSCOPE_API_KEY=sk-your-api-key-here
```

获取 API Key：https://dashscope.console.aliyun.com/

### 5. 启动服务器（1 分钟）

```bash
python app_main.py
```

看到以下输出表示成功：
```
INFO:     Uvicorn running on http://0.0.0.0:8081
```

### 6. 访问 Web 界面

打开浏览器访问：
```
http://localhost:8081
```

---

## 🎮 快速测试

### 测试 1：模型加载（30 秒）

```bash
python -c "
from ultralytics import YOLO
model = YOLO('model/yolo-seg.pt')
print('✓ 模型加载成功')
"
```

### 测试 2：服务器启动（1 分钟）

```bash
python app_main.py
```

应该看到服务器启动成功，没有错误。

### 测试 3：Web 界面（30 秒）

打开 http://localhost:8081，应该能看到：
- 视频流区域
- 状态面板
- IMU 可视化

---

## ⚠️ 常见问题

### 问题 1: "No module named 'xxx'"
```bash
# 确保虚拟环境已激活
# 重新安装依赖
pip install -r requirements.txt
```

### 问题 2: 端口 8081 被占用
```bash
# 方法 1：关闭占用的进程
# Windows
netstat -ano | findstr :8081
taskkill /PID <PID> /F

# Linux/macOS
lsof -i :8081
kill -9 <PID>

# 方法 2：修改 app_main.py 中的端口号
```

### 问题 3: PyTorch 安装失败
```bash
# 有 GPU（CUDA 11.8）
pip install torch==2.0.1+cu118 torchvision==0.15.2+cu118 --index-url https://download.pytorch.org/whl/cu118

# 没有 GPU
pip install torch==2.0.1 torchvision==0.15.2
```

### 问题 4: 模型文件下载慢
- 使用国内镜像或代理
- 分批次下载
- 确保网络稳定

---

## 📚 下一步

完成快速启动后，您可以：

1. **阅读详细指南**: `REPRODUCTION_GUIDE_CN.md`
2. **ESP32 硬件配置**: 如果有 ESP32-CAM 硬件
3. **功能测试**: 测试盲道导航、物品识别等功能
4. **代码学习**: 了解系统架构和实现细节

---

## 📊 完整复现时间预估

| 任务 | 时间 | 必需 |
|------|------|------|
| 环境准备 | 1-2 小时 | ✅ |
| 项目配置 | 30 分钟 | ✅ |
| 依赖安装 | 30-60 分钟 | ✅ |
| 模型下载 | 30 分钟 | ✅ |
| 服务器测试 | 30 分钟 | ✅ |
| ESP32 配置 | 1-2 小时 | ⭕ 可选 |
| 系统测试 | 30 分钟 | ✅ |
| **总计** | **4-6 小时** | |

---

## 🆘 获取帮助

遇到问题？

1. **查看详细指南**: `REPRODUCTION_GUIDE_CN.md`
2. **使用检查清单**: `CHECKLIST.md`
3. **GitHub Issues**: 在项目页面提问
4. **查看日志**: 仔细阅读错误信息

---

## 🎯 成功标志

您成功启动了项目，如果：

- ✅ 服务器启动没有错误
- ✅ Web 界面能访问
- ✅ 能看到视频流区域（可能是黑色，等待摄像头输入）
- ✅ 没有红色错误提示

**恭喜！您已完成快速启动！** 🎉
