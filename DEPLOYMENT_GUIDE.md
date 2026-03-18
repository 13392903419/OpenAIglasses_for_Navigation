# 🚀 快速上线部署指南（Web App 方案）

这份指南将帮助你在 **2-3 周内** 将 AI 智能盲人眼镜导航系统上线。

---

## 📋 目录
- [前置条件](#前置条件)
- [本地测试](#本地测试)
- [云服务器部署](#云服务器部署)
- [域名配置](#域名配置)
- [SSL 证书](#ssl-证书)
- [监控与维护](#监控与维护)
- [常见问题](#常见问题)

---

## 前置条件

### 必需
- ✅ Docker（已安装）
- ✅ Docker Compose（已安装）
- ✅ 云服务器账号（推荐：阿里云/AWS/DigitalOcean）
- ✅ 域名（可选，但推荐）
- ✅ API Key：
  - `DASHSCOPE_API_KEY`（阿里云 Qwen）
  - `OPENAI_API_KEY`（如果使用 OpenAI）

### 可选
- GPU 支持（推荐 NVIDIA GPU，CPU 也可以运行但速度慢）
- SSL 证书（Let's Encrypt 免费）

---

## 本地测试

### 1️⃣ 准备环境

```bash
# 进入项目目录
cd d:\Blind_Navigation\OpenAIglasses_for_Navigation

# 创建 .env 文件（配置环境变量）
cat > .env << EOF
DASHSCOPE_API_KEY=sk-your-key-here
BLIND_PATH_MODEL=model/yolo-seg.pt
OBSTACLE_MODEL=model/yoloe-11l-seg.pt
LOG_LEVEL=INFO
CUDA_VISIBLE_DEVICES=0
EOF

# 确保模型文件存在
ls -la model/
# 应该看到四个 .pt 文件和 hand_landmarker.task
```

### 2️⃣ 本地构建和运行

```bash
# 构建 Docker 镜像（第一次需要几分钟）
docker-compose build

# 启动所有服务（FastAPI + Nginx）
docker-compose up -d

# 查看日志
docker-compose logs -f blind-nav-backend

# 测试服务
curl http://localhost/api/health
```

### 3️⃣ 验证功能

访问 `http://localhost` 应该看到你的 Web 应用。

```bash
# 测试 WebSocket 连接
wscat -c ws://localhost/ws_ui

# 测试音频流
curl http://localhost/stream.wav -o test.wav

# 查看容器状态
docker-compose ps
```

### 4️⃣ 调试和日志

```bash
# 查看完整日志
docker-compose logs --tail=100

# 只看错误日志
docker-compose logs | grep ERROR

# 进入容器内部
docker exec -it blind-nav-backend bash

# 停止所有服务
docker-compose down
```

---

## 云服务器部署

### 选择推荐

| 服务 | 成本 | 优点 | 缺点 |
|------|------|------|------|
| **阿里云 ECS** | ¥40-100/月 | 中国快速，便宜 | 需要备案 |
| **AWS EC2** | $5-15/月 | 全球可用 | 网络延迟较高 |
| **Vultr** | $2.5-5/月 | 超便宜，快 | 配置较低 |
| **DigitalOcean** | $4-6/月 | 简单易用 | CPU 较弱 |

**最强烈推荐：阿里云 ECS（4GB RAM + 2核 CPU）+ GPU 加速**


### 方案 A：阿里云轻量应用服务器 Ubuntu 22.04 部署（实操版）

#### 步骤 1：远程连接服务器

1. 登录阿里云控制台，找到你的实例公网IP（如 8.218.84.138）
2. 用 SSH 工具连接（推荐 XShell、MobaXterm 或命令行）

```bash
# Linux/macOS/WSL 命令行：
ssh root@你的公网IP
# 首次登录会提示输入初始密码（可在控制台重置）
```

#### 步骤 2：基础安全设置（建议）

```bash
# 修改 root 密码
passwd
# 新建普通用户（可选）
adduser myuser
usermod -aG sudo myuser
# 禁止 root 远程登录（可选，增强安全）
# vi /etc/ssh/sshd_config  # PermitRootLogin no
# systemctl restart sshd
```

#### 步骤 3：安装 Docker & Docker Compose

```bash
# 更新系统
apt update && apt upgrade -y

# 安装 Docker
curl -fsSL https://get.docker.com | bash

# 安装 Docker Compose
apt install -y docker-compose

# 验证安装
docker --version
docker-compose --version
```

#### 步骤 4：上传/拉取项目代码

```bash
# 推荐用 scp 上传本地代码
scp -r ./OpenAIglasses_for_Navigation root@你的公网IP:~/OpenAIglasses_for_Navigation
# 或者服务器上用 git clone 拉取
# git clone https://github.com/your-repo/blind-nav.git
cd ~/OpenAIglasses_for_Navigation
```

#### 步骤 5：配置环境变量

```bash
cat > .env << EOF
DASHSCOPE_API_KEY=sk-your-key-here
BLIND_PATH_MODEL=model/yolo-seg.pt
OBSTACLE_MODEL=model/yoloe-11l-seg.pt
LOG_LEVEL=INFO
EOF
```

#### 步骤 6：启动服务

```bash
docker-compose up -d
# 查看日志
docker-compose logs -f
```

#### 步骤 7：开放端口（安全组配置）

1. 登录阿里云控制台 → 轻量应用服务器 → 网络与安全 → 防火墙规则
2. 添加入站规则：
  - 端口：80（HTTP）、443（HTTPS）、8000（API调试）
  - 协议：TCP
  - 授权对象：0.0.0.0/0

> ⚠️ 如需公网访问 80/443，域名需备案。

---

### 方案 B：AWS EC2 部署

```bash
# 1. 启动 EC2 实例（Ubuntu 22.04，t3.large）
# 2. SSH 连接
ssh -i your-key.pem ec2-user@your-server-ip

# 3-5. 同上面步骤 3-5
```

---

## 域名配置

### 购买域名

推荐：GoDaddy、Namecheap、腾讯云（国内）

这里以阿里云域名为例：

```bash
# 假设购买了 blind-nav.com
# 在 DNS 控制面板添加一条 A 记录：
# 类型：A
# 主机：blind-nav.com（或 www）
# 值：你的服务器公网 IP（如 123.45.67.89）
# TTL：600
```

等待 DNS 生效（通常 10-30 分钟）：

```bash
# 验证 DNS
nslookup blind-nav.com
# 应该看到你的服务器 IP
```

---

## SSL 证书

### 使用免费 Let's Encrypt

```bash
# 在服务器上执行
docker exec -it blind-nav-nginx /bin/sh

# 安装 certbot
apk add certbot certbot-nginx

# 申请证书
certbot certonly --standalone -d blind-nav.com

# 自动续期
certbot renew --dry-run
```

或者使用 Nginx 配置自动申请：

```bash
# 编辑 nginx.conf，取消 HTTPS 部分的注释
vim nginx.conf

# 重启 Nginx
docker-compose restart nginx
```

---

## 监控与维护

### 日志查看

```bash
# 实时查看日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f blind-nav-backend

# 查看过去 100 行
docker-compose logs --tail=100
```

### 性能监控

```bash
# 查看容器资源使用
docker stats

# 查看磁盘使用
df -h

# 查看内存使用
free -h
```

### 定期备份

```bash
# 备份录制文件
tar -czf recordings_backup_$(date +%Y%m%d).tar.gz recordings/

# 上传到 S3（可选）
aws s3 cp recordings_backup_*.tar.gz s3://your-bucket/
```

### 自动更新

在你的 CI/CD 流程中添加：

```bash
# GitHub Actions（.github/workflows/deploy.yml）
name: Deploy to Server

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Deploy
        run: |
          ssh ubuntu@your-server << 'EOF'
            cd ~/blind-nav
            git pull origin main
            docker-compose up -d --build
          EOF
```

---

## 常见问题

### Q1：如何获取 DASHSCOPE_API_KEY？

访问 [阿里云 DashScope 控制台](https://dashscope.aliyun.com)，创建 API Key。

### Q2：模型文件太大，怎么加速下载？

```bash
# 下载到本地后，上传到服务器
scp -r model/ ubuntu@your-server:~/blind-nav/

# 或使用更快的镜像源
pip install modelscope -i https://pypi.tuna.tsinghua.edu.cn/simple
modelscope download --model archifancy/AIGlasses_for_navigation --local_dir ./model
```

### Q3：如何更新应用代码？

```bash
# 方案 1：使用 Git
git pull origin main
docker-compose down
docker-compose up -d --build

# 方案 2：直接上传
scp -r ./* ubuntu@your-server:~/blind-nav/
ssh ubuntu@your-server "cd ~/blind-nav && docker-compose restart"
```

### Q4：如何处理高并发用户？

```bash
# 增加 Gunicorn worker 数量
# 编辑 docker-compose.yml，修改启动命令：
CMD ["python3", "-m", "uvicorn", "app_main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

# 使用负载均衡（可选，超级高级）
# 部署多个实例，使用 Nginx 负载均衡
```

### Q5：为什么 WebSocket 经常断连？

```bash
# 增加超时时间，编辑 nginx.conf
proxy_read_timeout 300s;
proxy_send_timeout 300s;

# 重启 Nginx
docker-compose restart nginx
```

---

## 📞 获取帮助

1. **查看日志**：`docker-compose logs -f`
2. **检查网络**：`ping your-domain.com`
3. **健康检查**：`curl http://your-server/api/health`
4. **提交 Issue**：在 GitHub 上反馈问题

---

## 成本估算

| 项目 | 费用 | 备注 |
|------|------|------|
| 云服务器（阿里云） | ¥40-100/月 | 2核 4GB + GPU |
| 域名 | ¥50-100/年 | GoDaddy/腾讯云 |
| SSL 证书 | 免费 | Let's Encrypt |
| **总计** | **¥40-100/月** | **很便宜！** |

---

## 下一步

✅ 本地测试成功？  
→ 购买云服务器  
→ 按照上面步骤部署  
→ 访问你的域名：`https://blind-nav.com`  
→ 在应用商店/GitHub 上分享你的链接  

**祝你上线顺利！🎉**
