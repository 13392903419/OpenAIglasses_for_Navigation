# 运行与排障经验总结（2026-02-14）

本文记录本次在 Windows + Conda 环境中启动本项目（运行 `app_main.py`）过程中出现过的错误、根因分析、修复方法，以及后续建议的“防踩坑”做法。

> 适用场景：
> - Windows 10/11
> - Conda 环境：`openaiglasses_nav_cu118`
> - 运行入口：`app_main.py`

---

## 1. 启动后“正常现象”基线

启动 `app_main.py` 后，正常会看到（顺序可能略有不同）：

- `pygame ... Hello from the pygame community...`：音频系统相关依赖初始化信息。
- `[NAVIGATION] ...`：加载盲道分割模型（YOLO 分割）并进行一次自检推理。
- `[RECORDER] ...`：初始化并开始录制（输出到 `recordings/`）。
- `[TRAFFIC_LIGHT] ...`：预加载红绿灯检测模型并预热。
- `[UDP] listening on 0.0.0.0:12345`：IMU UDP 监听开启。
- `[AUDIO] ...`：音频资源映射、预加载、压缩统计等。

只要服务最终能跑起来（后续能看到 Uvicorn 监听端口、浏览器可打开页面），就说明“主体链路”已可用；某些模块失败（例如 YOLO‑E）通常只会影响部分功能。

---

## 2. 错误与教训汇总

### 2.1 错误：无法从 GitHub 下载 `ultralytics/CLIP`（网络不可达）

**现象（典型日志）**

- `fatal: unable to access 'https://github.com/ultralytics/CLIP.git/': Failed to connect to github.com port 443 ...`
- `ERROR: Failed to build 'git+https://github.com/ultralytics/CLIP.git'`

**根因**

- 本机网络对 `github.com:443` 不可达（被墙/公司网络策略/代理未配置/证书拦截均可能导致）。
- Ultralytics 在某些路径下会尝试“自动补装” Git 依赖（以 `git+https` 形式安装），一旦网络不可达就会失败。

**影响范围**

- 会连带造成 YOLO‑E 文本提示相关功能不可用（见下一条）。

**经验教训**

- 不要依赖“运行时自动下载依赖”。受网络影响大，且会让启动变得不可控。
- 尽量把所有依赖写入 `requirements.txt` 并在启动前一次性装好。

---

### 2.2 错误：`ModuleNotFoundError: No module named 'clip'`

**现象（典型日志/堆栈）**

- `[NAVIGATION] 障碍物检测器加载失败: No module named 'clip'`
- Ultralytics 路径中出现：`from ultralytics.nn.text_model import build_text_model` → `import clip` → 报错。

**根因**

- YOLO‑E 的 `get_text_pe()` 需要 `clip` 模块。
- 原本 Ultralytics 可能会尝试从 GitHub 装 `ultralytics/CLIP`，但网络不可达导致安装失败，于是 `import clip` 失败。

**影响范围（重要）**

- YOLO‑E 相关功能不可用：
  - 障碍物检测（`ObstacleDetectorClient`）
  - 开放词汇找物（部分实现依赖 YOLO‑E text prompt）
- 但盲道分割（`yolo-seg.pt`）与红绿灯模型可能仍可正常使用。

**修复策略（本次采用）**

- 用 **PyPI 可安装** 的 `clip-anytorch` 来提供 `import clip`，避免走 GitHub：

```powershell
python -m pip install --no-cache-dir "clip-anytorch==2.6.0"
```

**经验教训**

- 在“GitHub 不可达但 PyPI 可达”的网络环境里，优先选择 PyPI 包替代 `git+https` 依赖。

---

### 2.3 错误：`ModuleNotFoundError: No module named 'pkg_resources'`

**现象**

- 安装完 `clip-anytorch` 后，执行：
  - `python -c "import clip"`
- 报错：
  - `ModuleNotFoundError: No module named 'pkg_resources'`

**根因**

- `clip-anytorch` 内部引用了 `pkg_resources`。
- `pkg_resources` 通常由 `setuptools` 提供，但在本次环境中：
  - 即使 `setuptools==82.0.0` 显示已安装，依然缺少 `pkg_resources`。

**修复策略（已验证可行）**

- 将 `setuptools` 固定到已验证包含 `pkg_resources` 的版本：

```powershell
python -m pip install --no-cache-dir --force-reinstall "setuptools==68.2.2"
python -c "import pkg_resources; print('pkg_resources ok')"
python -c "import clip; print('clip ok', clip.__file__)"
```

**经验教训**

- 解决依赖问题时，**以 `python -m pip ...` 为准**，避免 `pip` 指向别的环境。
- 对关键依赖建议“已知可用版本固定（pin）”，否则在不同机器/不同时间可能出现行为变化。

---

### 2.4 警告：FastAPI `on_event` 弃用（DeprecationWarning）

**现象**

- `DeprecationWarning: on_event is deprecated, use lifespan event handlers instead.`

**根因**

- FastAPI 新版推荐 lifespan 事件管理，旧的 `@app.on_event("startup")` / `shutdown` 标记为弃用。

**影响范围**

- 仅警告，不影响服务启动。

**经验教训**

- 可以后续再统一升级为 lifespan；不建议在排障阶段“为了消警告”进行大重构。

---

### 2.5 提示：音频映射文件缺失 `voice\黄灯.WAV`

**现象**

- `[AUDIO] 映射文件缺失: ...\voice\黄灯.WAV`

**根因**

- `voice/` 下某条映射引用了一个不存在的音频文件。

**影响范围**

- 只会影响对应提示音的播放（可能无声/回退/提示失败），不影响整体启动。

**经验教训**

- 资源文件最好做启动时完整性检查（缺失时给出可执行的修复建议：从哪里补文件/如何禁用该提示）。

---

## 3. 一次性“稳定安装”建议（避免每次启动踩坑）

### 3.1 推荐安装方式

在激活 conda 环境后，统一使用：

```powershell
python -m pip install -r requirements.txt
```

这样可确保 pip 与 python 属于同一个环境。

### 3.2 本次已沉淀到依赖文件的关键项

- `clip-anytorch==2.6.0`
- `setuptools==68.2.2`

如果你未来要更新这些版本，建议更新后立刻做两条验证：

```powershell
python -c "import pkg_resources; print('pkg_resources ok')"
python -c "import clip; print('clip ok')"
```

---

## 4. 排障思路（可复用模板）

1. **先判断是“致命错误”还是“可忽略警告”**：
   - 致命错误：异常栈导致某模块无法初始化（如 `clip` 缺失）
   - 可忽略：DeprecationWarning、单个资源缺失（不会阻塞启动）
2. **先让最核心链路跑通**：
   - 服务能启动、页面能打开、模型至少一个能跑
3. **再逐个补齐增强功能**：
   - YOLO‑E（找物/障碍物）
   - ESP32 音频/相机
   - IMU
4. **每修一次都加“验证命令”**：
   - `import` 检查
   - 简短推理自检
   - 端口健康检查

---

## 5. 本次关键命令备忘

- 安装 `clip-anytorch`：

```powershell
python -m pip install --no-cache-dir "clip-anytorch==2.6.0"
```

- 固定 `setuptools`（解决 `pkg_resources` 缺失）：

```powershell
python -m pip install --no-cache-dir --force-reinstall "setuptools==68.2.2"
```

- 验证：

```powershell
python -c "import pkg_resources; print('pkg_resources ok')"
python -c "import clip; print('clip ok', clip.__file__)"
```

---

## 6. 后续可选改进（不影响当前可用性）

- 将 FastAPI 的 `@app.on_event` 迁移到 lifespan（减少未来升级成本）。
- 对 `voice/` 资源做一次完整性扫描（列出缺失文件，或在映射里禁用缺失项）。
- 在启动时明确打印“哪些能力已启用/已降级”（例如 YOLO‑E 是否可用），减少用户猜测。
