# 📘 ESP32 编程入门教程

> 专为没有 ESP32 基础的开发者准备的详细教程

---

## 目录

1. [ESP32 基础知识](#1-esp32-基础知识)
2. [开发环境搭建](#2-开发环境搭建)
3. [第一个 ESP32 程序](#3-第一个-esp32-程序)
4. [本项目中的 ESP32 代码详解](#4-本项目中的-esp32-代码详解)
5. [常见问题与调试](#5-常见问题与调试)
6. [本项目硬件接入实操（照做必通）](#6-本项目硬件接入实操照做必通)

---

## 1. ESP32 基础知识

### 1.1 什么是 ESP32？

**ESP32** 是一款功能强大的微控制器芯片，由中国的乐鑫科技（Espressif Systems）设计和制造。

#### 主要特点：
- **处理器**：双核 32 位处理器，最高 240 MHz
- **内存**：520 KB SRAM
- **无线连接**：
  - Wi-Fi（802.11 b/g/n）
  - 蓝牙 4.2 和 BLE
- **接口**：GPIO、I2C、SPI、UART、I2S 等
- **价格**：约 10-30 元人民币（开发板）

#### 与 Arduino 的对比：

| 特性 | Arduino Uno | ESP32 |
|------|-------------|-------|
| 处理器 | 8 位 16MHz | 双核 32 位 240MHz |
| 内存 | 2KB RAM | 520KB RAM |
| 存储 | 32KB Flash | 4MB Flash |
| Wi-Fi | ❌ | ✅ |
| 蓝牙 | ❌ | ✅ |
| 价格 | ~100 元 | ~20 元 |

### 1.2 ESP32-CAM 模块

**ESP32-CAM** 是一个带摄像头的 ESP32 开发板。

#### 组成部分：
```
┌─────────────────────────┐
│      OV2640 摄像头       │
├─────────────────────────┤
│                         │
│    ESP32 主芯片         │
│    (双核 + Wi-Fi)       │
│                         │
├─────────────────────────┤
│      SD 卡槽            │
├─────────────────────────┤
│   引脚（GPIO、电源等）   │
└─────────────────────────┘
```

#### 技术规格：
- **摄像头**：OV2640，最高 2MP（1600x1200）
- **存储**：支持 microSD 卡（最大 4GB）
- **电源**：5V 供电（通过 VCC 引脚）
- **尺寸**：约 27mm x 40mm

### 1.3 ESP32 的应用场景

ESP32 特别适合以下场景：
- 🌐 IoT（物联网）设备
- 📹 网络摄像头
- 🔊 音频流设备
- 🏠 智能家居控制
- 📡 无线传感器网络
- 🤖 机器人控制

### 1.4 ESP32 引脚说明

ESP32-CAM 常用引脚：

| 引脚 | 功能 | 说明 |
|------|------|------|
| VCC | 5V 供电 | 连接 5V 电源 |
| GND | 地线 | 连接地线 |
| U0R | UART RX | 接收数据（连接 TX） |
| U0T | UART TX | 发送数据（连接 RX） |
| GPIO0 | 烧录模式 | 接 GND 进入烧录模式 |
| GPIO1 | U0T | UART 发送 |
| GPIO3 | U0R | UART 接收 |
| GPIO12 | HSPI MISO | SPI 接口 |
| GPIO13 | HSPI MOSI | SPI 接口 |
| GPIO33 | 摄像头时钟 | 摄像头专用 |
| RST | 复位 | 重启设备 |

---

## 2. 开发环境搭建

### 2.1 安装 Arduino IDE

#### 步骤 1：下载 Arduino IDE

1. 访问：https://www.arduino.cc/en/software
2. 选择您的操作系统（Windows、macOS、Linux）
3. 下载最新版本（推荐 2.x）
4. 安装到您的电脑

#### 步骤 2：配置 ESP32 支持

1. **打开 Arduino IDE**

2. **添加开发板管理器 URL**：
   - 进入 **文件 → 首选项**（或 `Ctrl+,`）
   - 在 "附加开发板管理器网址" 中添加：
     ```
     https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
     ```
   - 如果已有其他 URL，用逗号分隔或换行添加

3. **安装 ESP32 开发板**：
   - 进入 **工具 → 开发板 → 开发板管理器**
   - 搜索 "esp32"
   - 找到 "esp32 by Espressif Systems"
   - 点击 "安装"（选择版本 2.0.x）
   - 等待安装完成（约 5-10 分钟，取决于网速）

4. **验证安装**：
   - 进入 **工具 → 开发板 → ESP32 Arduino**
   - 应该能看到很多 ESP32 开发板选项

### 2.2 安装 USB 驱动

ESP32-CAM 需要 USB 转 TTL 模块连接电脑，常见模块：
- CP2102
- CH340
- FT232RL

#### 安装 CP2102 驱动（最常见）：

**Windows**:
1. 下载：https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers
2. 运行安装程序
3. 重启电脑

**macOS**:
```bash
# 使用 Homebrew
brew install --cask silicon-labs-vcp-driver
```

**Linux** (Ubuntu/Debian):
```bash
# 通常自带驱动，如果没有：
sudo apt-get install linux-modules-extra-$(uname -r)
```

#### 安装 CH340 驱动：

**Windows**:
1. 下载：http://www.wch.cn/downloads/CH341SER_ZIP.html
2. 解压并运行 SETUP.EXE

**macOS**:
```bash
brew install --cask wch-ch34x-usb-serial-driver
```

#### 验证驱动安装：

1. 将 USB 转 TTL 插入电脑
2. **Windows**: 设备管理器中应该看到 "COM3" 或类似端口
3. **Linux/macOS**: 运行 `ls /dev/tty*`，应该看到 `/dev/ttyUSB0` 或 `/dev/cu.SLAB_USBtoUART`

### 2.3 硬件连接

#### 需要的硬件：
- ESP32-CAM 开发板
- USB 转 TTL 模块（CP2102 或 CH340）
- 杜邦线（公对母）4-5 根
- Micro USB 线（连接 USB 转 TTL 到电脑）

#### 接线图（烧录模式）：

```
┌──────────────┐           ┌─────────────┐
│  USB 转 TTL   │           │  ESP32-CAM  │
├──────────────┤           ├─────────────┤
│ VCC (5V)     │─────────→ │ VCC (5V)    │
│ GND          │─────────→ │ GND         │
│ TX           │─────────→ │ U0R (RX)    │
│ RX           │─────────→ │ U0T (TX)    │
└──────────────┘           │             │
                           │ GPIO0 ──┐   │
                           │ GND   ──┘   │
                           └─────────────┘
                           (GPIO0 接 GND 进入烧录模式)
```

#### 接线步骤：

1. **断开 ESP32-CAM 电源**（重要！）
2. 使用杜邦线连接：
   - USB 转 TTL 的 VCC → ESP32-CAM 的 VCC (5V)
   - USB 转 TTL 的 GND → ESP32-CAM 的 GND
   - USB 转 TTL 的 TX → ESP32-CAM 的 U0R (RX)
   - USB 转 TTL 的 RX → ESP32-CAM 的 U0T (TX)
3. **烧录模式**：用一根杜邦线将 GPIO0 连接到 GND
4. 将 USB 转 TTL 插入电脑

⚠️ **注意**：
- TX 连接 RX，RX 连接 TX（交叉连接）
- GPIO0 必须在上电前连接到 GND
- 确保供电是 5V，不是 3.3V

#### 接线图（正常运行模式）：

```
┌─────────────┐
│  ESP32-CAM  │
├─────────────┤
│ VCC (5V)    │←── 5V 电源（或 USB 转 TTL）
│ GND         │←── GND
│             │
│ GPIO0       │    (不接 GND！)
│             │
└─────────────┘
```

上传完程序后，**必须断开 GPIO0 和 GND 的连接**，然后重新上电。

---

## 3. 第一个 ESP32 程序

### 3.1 Blink 示例（ESP32 版的 Hello World）

创建一个让 LED 闪烁的程序。

#### 步骤 1：创建新项目

1. 打开 Arduino IDE
2. **文件 → 新建**

#### 步骤 2：选择开发板

1. **工具 → 开发板 → ESP32 Arduino → AI Thinker ESP32-CAM**

#### 步骤 3：编写代码

```cpp
// ESP32-CAM LED 闪烁程序
// 板载 LED 连接到 GPIO 33（闪光灯）

const int LED_PIN = 33;  // 板载闪光灯 LED

void setup() {
  // 初始化串口（用于调试）
  Serial.begin(115200);
  Serial.println("ESP32-CAM LED Blink");
  
  // 设置 LED 引脚为输出模式
  pinMode(LED_PIN, OUTPUT);
}

void loop() {
  // 打开 LED
  digitalWrite(LED_PIN, HIGH);
  Serial.println("LED ON");
  delay(1000);  // 延迟 1 秒
  
  // 关闭 LED
  digitalWrite(LED_PIN, LOW);
  Serial.println("LED OFF");
  delay(1000);  // 延迟 1 秒
}
```

#### 步骤 4：编译和上传

1. **连接硬件**（按照上面的接线图，GPIO0 接 GND）
2. **选择端口**：工具 → 端口 → COM3（或您看到的端口）
3. **上传速度**：工具 → Upload Speed → 115200
4. 点击 **上传**（→ 按钮）
5. 等待编译和上传完成

#### 步骤 5：查看结果

1. **断开 GPIO0 和 GND 的连接**
2. 按 ESP32-CAM 上的 RST 按钮（或重新上电）
3. ESP32-CAM 的闪光灯应该每秒闪烁一次
4. 打开 **串口监视器**（工具 → 串口监视器，波特率 115200）
5. 应该看到 "LED ON" 和 "LED OFF" 交替打印

### 3.2 Wi-Fi 连接示例

让 ESP32 连接到 Wi-Fi 网络。

```cpp
#include <WiFi.h>

// 修改为您的 Wi-Fi 信息
const char* ssid = "Your_WiFi_Name";
const char* password = "Your_WiFi_Password";

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);
  
  // 开始连接 Wi-Fi
  WiFi.begin(ssid, password);
  
  // 等待连接
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  Serial.println();
  Serial.println("WiFi connected!");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());
}

void loop() {
  // 保持连接
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("WiFi is connected");
  } else {
    Serial.println("WiFi disconnected!");
  }
  delay(5000);
}
```

**测试**：
1. 修改 `ssid` 和 `password` 为您的 Wi-Fi
2. 上传程序
3. 打开串口监视器
4. 应该看到 "WiFi connected!" 和 IP 地址

### 3.3 摄像头测试示例

测试 ESP32-CAM 的摄像头功能。

```cpp
#include "esp_camera.h"

// ESP32-CAM 摄像头引脚定义（AI-Thinker 型号）
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

void setup() {
  Serial.begin(115200);
  Serial.println("ESP32-CAM Camera Test");
  
  // 摄像头配置
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  
  // 图像质量设置
  config.frame_size = FRAMESIZE_SVGA;  // 800x600
  config.jpeg_quality = 10;
  config.fb_count = 1;
  
  // 初始化摄像头
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x", err);
    return;
  }
  
  Serial.println("Camera initialized successfully!");
  
  // 拍摄一张测试照片
  camera_fb_t * fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("Camera capture failed");
    return;
  }
  
  Serial.printf("Image captured! Size: %d bytes\n", fb->len);
  
  // 释放帧缓冲
  esp_camera_fb_return(fb);
}

void loop() {
  // 每 5 秒拍一张照片
  delay(5000);
  
  camera_fb_t * fb = esp_camera_fb_get();
  if (fb) {
    Serial.printf("Captured image: %d bytes\n", fb->len);
    esp_camera_fb_return(fb);
  } else {
    Serial.println("Capture failed");
  }
}
```

**测试**：
1. 上传程序
2. 打开串口监视器
3. 应该看到 "Camera initialized successfully!"
4. 每 5 秒看到新的图像大小信息

---

## 4. 本项目中的 ESP32 代码详解

### 4.0 重要说明：你买的板子可能和默认固件不一样

本仓库 `compile/` 目录下的固件代码，当前默认更偏向“**带摄像头 + 麦克风 + 扬声器 + IMU**”的一体化硬件（例如 XIAO ESP32S3 Sense 一类）。

你现在购买的硬件通常是 **AI‑Thinker ESP32‑CAM（OV2640）+ 烧录底板（带 Micro‑USB）**。两者的引脚/外设不同：

- `compile/compile.ino`
  - 适配：更偏向 **ESP32‑S3 + PDM/I2S + SPI IMU** 的组合
  - WebSocket：`/ws/camera`（视频）、`/ws_audio`（音频）
  - 备注：如果你是标准 ESP32‑CAM，仅靠改一个宏（例如 `CAMERA_MODEL_AI_THINKER`）通常仍然不够，代码里还有麦克风/扬声器/IMU 引脚与库依赖。

- `compile/esp32cam_ws_camera_min/esp32cam_ws_camera_min.ino`
  - 适配：**AI‑Thinker ESP32‑CAM（OV2640）**
  - 功能：只做一件事——把 JPEG 视频帧通过 WebSocket 推到服务器 `/ws/camera`
  - 适合你现在“先把画面连上项目”的阶段

### 4.1 代码结构

项目的 ESP32 代码位于 `compile/compile.ino`，主要功能：

1. **Wi-Fi 连接**：连接到本地网络
2. **WebSocket 客户端**：与服务器建立 WebSocket 连接
3. **摄像头初始化**：配置和启动 OV2640 摄像头
4. **视频流传输**：持续捕获图像并发送到服务器
5. **IMU 数据采集**：读取 ICM42688 传感器数据（如果有）

如果你使用的是常见 **ESP32‑CAM（AI‑Thinker）**，建议先使用本仓库新增的最小固件：

- `compile/esp32cam_ws_camera_min/esp32cam_ws_camera_min.ino`

### 4.2 关键代码片段解析

#### Wi-Fi 连接部分

```cpp
const char* ssid = "Your_WiFi_Name";
const char* password = "Your_WiFi_Password";

void connectWiFi() {
  Serial.print("Connecting to WiFi");
  WiFi.begin(ssid, password);
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  Serial.println("\nWiFi connected!");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());
}
```

**要修改的地方**：
- `ssid`：改为您的 Wi-Fi 名称
- `password`：改为您的 Wi-Fi 密码

#### WebSocket 连接部分

```cpp
// 服务器 IP（你的电脑局域网 IP，不要填 127.0.0.1）
static const char* SERVER_HOST = "192.168.1.100";
static const uint16_t SERVER_PORT = 8081;

// 本项目服务端接收 ESP32 摄像头的入口
static const char* CAM_WS_PATH = "/ws/camera";
```

**要修改的地方**：
- `websocket_server_host`：改为运行服务器的电脑 IP 地址

**如何查看电脑 IP**：
- Windows: `ipconfig`（查看 IPv4 地址）
- Linux/macOS: `ifconfig` 或 `ip addr show`

#### 摄像头捕获和发送

```cpp
void loop() {
  webSocket.loop();  // 处理 WebSocket 事件
  
  // 捕获图像
  camera_fb_t * fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("Camera capture failed");
    return;
  }
  
  // 通过 WebSocket 发送图像
  webSocket.sendBIN(fb->buf, fb->len);
  
  // 释放帧缓冲
  esp_camera_fb_return(fb);
  
  delay(33);  // 约 30 FPS
}
```

**性能调优**：
- 调整 `delay()` 值改变帧率
- 降低图像分辨率提高速度
- 调整 JPEG 质量平衡大小和清晰度

### 4.3 配置摄像头参数

在 `setup()` 函数中可以调整摄像头参数：

```cpp
// 分辨率选项
config.frame_size = FRAMESIZE_SVGA;  // 800x600

// 其他选项：
// FRAMESIZE_QVGA (320x240)
// FRAMESIZE_VGA (640x480)
// FRAMESIZE_SVGA (800x600)
// FRAMESIZE_XGA (1024x768)
// FRAMESIZE_SXGA (1280x1024)
// FRAMESIZE_UXGA (1600x1200)

// JPEG 质量（0-63，数字越小质量越高）
config.jpeg_quality = 10;
```

**建议**：
- 测试时使用 `FRAMESIZE_VGA` (640x480)
- JPEG 质量设置为 10-15
- 根据网络速度和性能调整

### 4.4 调试技巧

#### 串口调试

在代码中添加 `Serial.println()` 语句：

```cpp
Serial.println("Starting camera initialization...");
esp_err_t err = esp_camera_init(&config);
if (err != ESP_OK) {
  Serial.printf("Camera init failed: 0x%x\n", err);
} else {
  Serial.println("Camera init success!");
}
```

#### 查看内存使用

```cpp
void printMemoryInfo() {
  Serial.printf("Free heap: %d bytes\n", ESP.getFreeHeap());
  Serial.printf("Heap size: %d bytes\n", ESP.getHeapSize());
  Serial.printf("Used heap: %d bytes\n", ESP.getHeapSize() - ESP.getFreeHeap());
}
```

#### WebSocket 事件监听

```cpp
void webSocketEvent(WStype_t type, uint8_t * payload, size_t length) {
  switch(type) {
    case WStype_DISCONNECTED:
      Serial.println("[WS] Disconnected!");
      break;
    case WStype_CONNECTED:
      Serial.printf("[WS] Connected to: %s\n", payload);
      break;
    case WStype_TEXT:
      Serial.printf("[WS] Text: %s\n", payload);
      break;
    case WStype_BIN:
      Serial.printf("[WS] Binary length: %u\n", length);
      break;
  }
}
```

---

## 5. 常见问题与调试

### 5.1 上传问题

#### 问题：无法找到端口

**症状**：Arduino IDE 中看不到 COM 端口

**解决方法**：
1. 检查 USB 驱动是否安装（CP2102 或 CH340）
2. 尝试不同的 USB 端口
3. 检查 USB 线是否支持数据传输（不是仅充电线）
4. 在设备管理器中查看是否有黄色感叹号

#### 问题：上传失败 "A fatal error occurred: Failed to connect"

**症状**：点击上传后，一直显示 "Connecting..."

**解决方法**：
1. **最常见原因**：GPIO0 没有连接到 GND
   - 在点击上传前，确保 GPIO0 已连接到 GND
   - 或者在点击上传后，按住 BOOT 按钮（如果有）
2. 检查串口设置是否正确
3. 降低上传速度：115200
4. 尝试按住 RST 按钮，松开后立即点击上传

#### 问题：上传后程序不运行

**症状**：程序上传成功，但 ESP32 没有反应

**解决方法**：
1. **断开 GPIO0 和 GND 的连接**（这是最常见的原因！）
2. 按 RST 按钮重启
3. 重新给 ESP32 上电

### 5.2 Wi-Fi 连接问题

#### 问题：无法连接到 Wi-Fi

**症状**：串口显示一直在打印 "."，无法连接

**解决方法**：
1. 检查 SSID 和密码是否正确（区分大小写）
2. 确保 Wi-Fi 是 2.4GHz（ESP32 不支持 5GHz）
3. 检查 Wi-Fi 信号强度
4. 尝试靠近路由器
5. 检查路由器是否启用了 MAC 地址过滤

#### 问题：连接后频繁断开

**解决方法**：
1. 检查电源是否稳定（使用 5V 2A 电源）
2. 在代码中添加自动重连：
   ```cpp
   void loop() {
     if (WiFi.status() != WL_CONNECTED) {
       Serial.println("Reconnecting...");
       WiFi.reconnect();
     }
     // 其他代码...
   }
   ```

### 5.3 摄像头问题

#### 问题：摄像头初始化失败

**症状**：串口显示 "Camera init failed"

**解决方法**：
1. 检查摄像头排线是否插好
2. 确保排线方向正确（蓝色面朝向 PCB）
3. 重新上电
4. 尝试降低分辨率：
   ```cpp
   config.frame_size = FRAMESIZE_QVGA;  // 320x240
   ```
5. 检查是否有足够的电源（使用 5V 2A 电源）

#### 问题：图像质量差或有条纹

**解决方法**：
1. 调整 JPEG 质量：
   ```cpp
   config.jpeg_quality = 10;  // 降低数字提高质量
   ```
2. 检查光线是否充足
3. 清洁摄像头镜头
4. 检查摄像头排线连接

### 5.4 WebSocket 连接问题

#### 问题：无法连接到服务器

**症状**：串口显示 WebSocket 连接失败

**解决方法**：
1. 确认服务器正在运行：`python app_main.py`
2. 检查服务器 IP 地址是否正确
3. 确保 ESP32 和服务器在同一网络
4. 检查防火墙设置（允许端口 8081）
5. 使用 `ping` 测试连通性：
   ```bash
   ping 192.168.1.100  # 服务器 IP
   ```

#### 问题：ESP32 显示已连上 Wi‑Fi，但服务器没有出现 `[CAMERA] ESP32 connected`

**排查顺序（从最常见到最关键）**：
1. `SERVER_HOST` 是否填了电脑的“局域网 IPv4”（例如 `192.168.x.x`），而不是 `127.0.0.1`
2. 电脑和 ESP32 是否在同一个 2.4GHz 局域网（有些路由器会把 2.4G/5G 或访客网络隔离）
3. Windows 防火墙是否阻止了入站 8081（第一次运行时弹窗要点允许；也可临时关闭防火墙验证）
4. 服务器是否真的在监听 `0.0.0.0:8081`（控制台应看到 `Uvicorn running on http://0.0.0.0:8081`）

#### 问题：服务器出现 `[CAMERA] ESP32 connected`，但网页没有画面

**说明**：服务端 `/ws/camera` 收到的是 JPEG 二进制帧；网页端看的通常是服务端转发后的结果。

**排查**：
1. 先确认浏览器打开的是 `http://localhost:8081`
2. 观察 ESP32 串口输出是否持续运行（是否频繁重启/掉线）
3. 供电是否足够（ESP32‑CAM 很吃电；供电不足时常见现象：能连上但一开摄像头就重启）
4. 尝试把固件里的 `FRAME_SIZE` 降到 `FRAMESIZE_QVGA`、`FB_COUNT` 降到 1

### 5.5 性能优化

#### 问题：帧率太低

**解决方法**：
1. 降低分辨率：
   ```cpp
   config.frame_size = FRAMESIZE_VGA;  // 640x480
   ```
2. 提高 JPEG 质量数字（降低质量但减小大小）：
   ```cpp
   config.jpeg_quality = 15;
   ```
3. 使用更快的 Wi-Fi 网络（802.11n）
4. 靠近路由器

#### 问题：内存不足

**解决方法**：
1. 减少帧缓冲数量：
   ```cpp
   config.fb_count = 1;
   ```
2. 降低分辨率
3. 在 `loop()` 中及时释放资源

---

## 📚 进阶学习资源

### 官方文档
- ESP32 Arduino Core: https://github.com/espressif/arduino-esp32
- ESP32 技术规格: https://www.espressif.com/en/products/socs/esp32
- ESP-IDF 编程指南: https://docs.espressif.com/projects/esp-idf/

### 教程网站
- Random Nerd Tutorials: https://randomnerdtutorials.com/projects-esp32/
- Last Minute Engineers: https://lastminuteengineers.com/esp32/
- DroneBot Workshop: https://dronebotworkshop.com/esp32-intro/

### 视频教程
- YouTube 搜索 "ESP32 tutorial"
- B站搜索 "ESP32 教程"

### 社区支持
- ESP32 官方论坛: https://www.esp32.com/
- Arduino 论坛: https://forum.arduino.cc/
- Reddit r/esp32: https://reddit.com/r/esp32

---

## 📝 总结

通过本教程，您应该已经：

- ✅ 了解了 ESP32 的基本概念和特点
- ✅ 搭建了 ESP32 开发环境
- ✅ 学会了基本的 ESP32 编程
- ✅ 理解了本项目中 ESP32 代码的作用
- ✅ 掌握了常见问题的解决方法

**下一步**：
1. 运行简单的示例代码熟悉 ESP32
2. 修改本项目的 ESP32 代码适配您的环境
3. 测试完整的视频流传输功能
4. 根据需求定制功能

**祝您学习顺利！** 🚀

---

## 6. 本项目硬件接入实操（照做必通）

这一节是给“已经买好 ESP32‑CAM + 烧录底板/USB 线/杜邦线”的同学准备的：从 0 到 1 把 ESP32 画面送进本项目，并在网页里看到视频。

> 你要达成的最终现象：
> 1) 服务器控制台出现：`[CAMERA] ESP32 connected`
> 2) 浏览器打开 `http://localhost:8081`，能看到实时画面（或至少能看到帧在刷新）

### 6.1 确认你买的是“带摄像头的 ESP32‑CAM”

你买的套装里可能同时有两块板：

- **ESP32‑CAM（带 OV2640 摄像头座/排线）**：这是负责拍摄的
- **烧录底板（带 Micro‑USB/Type‑C）**：这是把 USB 转成串口、并给 ESP32‑CAM 供电/下载用的

只有“ESP32‑S 模组小开发板（带 Micro‑USB、但没有摄像头座）”是**不能直接当摄像头用**的。

### 6.2 安装驱动并确认 COM 口

1. 用 USB 线把“烧录底板 + ESP32‑CAM”连到电脑
2. 打开 Windows 设备管理器 → 端口（COM 和 LPT）
3. 正常情况下会出现一个新的 COM 口（例如 `COM5`）

如果没有 COM 口：
- 多半是缺驱动（常见 CH340 / CP210x）或 USB 线是“只充电线”

### 6.3 准备 Arduino IDE 环境

1. 安装 Arduino IDE 2.x
2. 安装 ESP32 开发板支持（建议 2.0.x 系列）
3. 安装库：打开 Arduino IDE → 库管理器，搜索并安装：
  - `ArduinoWebsockets`

### 6.4 打开并配置最小固件（推荐）

打开文件：`compile/esp32cam_ws_camera_min/esp32cam_ws_camera_min.ino`

把下面 3 个参数改成你自己的：

1. Wi‑Fi 名称和密码（必须是 2.4GHz Wi‑Fi）
2. `SERVER_HOST`：运行 `python app_main.py` 的那台电脑的“局域网 IPv4 地址”（不要填 127.0.0.1）
3. `SERVER_PORT`：默认是 `8081`（与你的 FastAPI 服务一致）

Windows 查看本机 IP：打开 PowerShell 输入：

```powershell
ipconfig
```

找到当前网卡的 “IPv4 地址”，形如 `192.168.x.x`。

### 6.5 Arduino IDE 编译/烧录设置

在 Arduino IDE 里按以下思路设置（不同版本菜单名称可能略有差异）：

1. 工具 → 开发板：选择 `AI Thinker ESP32-CAM`
2. 工具 → 端口：选择你在设备管理器里看到的 COM 口
3. 工具 → 上传速度：先用 `115200`（更稳），熟练后再调高
4. 如果有 PSRAM 选项：选择 `Enabled`

然后点击“上传”。

如果一直卡在 `Connecting...`：
- 你的底板如果有 `BOOT/IO0` 按钮：按住 BOOT 再点上传，看到开始写入后松开
- 如果没有按钮：把 ESP32‑CAM 的 `GPIO0` 临时接到 `GND`，再重试上传（上传完成后一定要断开）

### 6.6 启动服务器并验证连通

1. 在电脑上启动本项目服务：

```bash
python app_main.py
```

2. 确认控制台有类似：`Uvicorn running on http://0.0.0.0:8081`
3. 给 ESP32‑CAM 重新上电/按复位
4. 观察服务器控制台，正常会出现：`[CAMERA] ESP32 connected`

### 6.7 打开网页看画面

浏览器访问：`http://localhost:8081`

说明：
- 如果 ESP32 正常在推流，页面会开始刷新显示画面
- 如果页面黑屏但服务器已显示 connected，优先检查：Wi‑Fi 信号/供电/是否同一局域网/防火墙放行 8081

#### 6.7.1 画面很卡 / FPS 很低（例如 1 FPS）

如果已经能看到画面，但特别卡顿，最常见的原因是“电脑端每帧做了重活”（例如同步录制、解码/再编码、导航推理）。可以按下面顺序优化：

1) **确认后端没有开启同步录制**（开启录制会显著降低 FPS）
- 本项目后端支持把 ESP32 视频写入 `recordings/`（AVI/WAV），这是高开销操作。
- 现在默认关闭；如需开启再设置环境变量：
  - Windows PowerShell：`$env:AIGLASS_SYNC_RECORD="1"; python app_main.py`

2) **降低 ESP32 端的视频码率**（最有效、最稳）
打开 `compile/esp32cam_ws_camera_min/esp32cam_ws_camera_min.ino`，建议优先改成：
- `FRAME_SIZE = FRAMESIZE_QVGA`（320×240）
- `JPEG_QUALITY = 20~30`（数值越大画质越差但更省流量、更流畅）
- `TARGET_FPS = 8~12`

3) **检查 Wi‑Fi 条件**
- ESP32 只能连 2.4GHz，且 2.4G 在拥挤环境下抖动会很明显。
- 尽量靠近路由器，避免隔墙；电脑也尽量接入同一个路由器。

### 6.8（可选）要做“音频 + IMU”怎么办？

目前你买的 **ESP32‑CAM 套装**通常只覆盖“摄像头视频链路”。

如果你后续想把“麦克风上行（`/ws_audio`）+ 扬声器播放 + IMU 姿态（UDP 12345）”也完整跑起来：
- 需要额外的硬件外设（I2S 麦克风、功放/喇叭、IMU 等）
- 或者使用与 `compile/compile.ino` 目标一致的硬件平台（例如带摄像头与音频/IMU接口的 ESP32S3 方案）

