# AutoSign - 数据库论坛自动签到工具

<div align="center">

[![Docker Push](https://github.com/redgreat/autosign/actions/workflows/dockerpush.yml/badge.svg)](https://github.com/redgreat/autosign/actions/workflows/dockerpush.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)](https://hub.docker.com/r/redgreat/autosign)

一个基于 Python 的多平台数据库论坛自动签到工具,支持 Docker 部署和定时任务。

[功能特性](#-功能特性) • [快速开始](#-快速开始) • [配置说明](#-配置说明) • [部署方式](#-部署方式) • [支持平台](#-支持平台)

</div>

---

## ✨ 功能特性

- 🎯 **多平台支持** - 支持 Kingbase、OceanBase、PGFans、MoDB、GBase 等数据库论坛
- 👥 **多账号管理** - 每个平台支持配置多个账号同时签到
- 🔐 **安全加密** - 支持 RSA/AES 加密登录,保护账号安全
- 📱 **微信推送** - 集成 PushPlus,签到结果实时推送到微信
- ⏰ **定时执行** - 支持自定义签到时间,自动化运行
- 🐳 **Docker 部署** - 提供完整的 Docker 镜像,开箱即用
- 🔄 **CI/CD 集成** - GitHub Actions 自动构建多架构镜像
- 📊 **详细日志** - 完整的执行日志,方便排查问题
- 🏥 **健康检查** - 内置健康检查机制,确保服务稳定运行

## 🚀 快速开始

### 方式一: Docker Compose (推荐)

1. **克隆项目**
   ```bash
   git clone https://github.com/redgreat/autosign.git
   cd autosign
   ```

2. **配置文件**
   ```bash
   cp conf/config.yml.sample conf/config.yml
   vim conf/config.yml  # 编辑配置文件
   ```

3. **启动服务**
   ```bash
   docker-compose up -d
   ```

4. **查看日志**
   ```bash
   docker-compose logs -f
   ```

### 方式二: Docker 命令

```bash
# 拉取镜像
docker pull redgreat/autosign:latest

# 创建配置文件目录
mkdir -p conf logs

# 复制并编辑配置文件
cp conf/config.yml.sample conf/config.yml

# 运行容器
docker run -d \
  --name autosign \
  --restart unless-stopped \
  -v $(pwd)/conf/config.yml:/app/conf/config.yml:ro \
  -v $(pwd)/logs:/app/logs \
  -e TZ=Asia/Shanghai \
  redgreat/autosign:latest
```

### 方式三: 本地运行

```bash
# 安装依赖
pip install -r requirements.txt

# 配置文件
cp conf/config.yml.sample conf/config.yml
vim conf/config.yml

# 运行程序
python all_checkin.py
```

## ⚙️ 配置说明

### 配置文件结构

配置文件位于 `conf/config.yml`,示例如下:

```yaml
# 定时执行时间 (24小时制,格式: HH:MM)
schedule: "03:00"

# PushPlus 推送 Token (可选,用于微信通知)
push_plus_token: "your_pushplus_token"

# Kingbase 人大金仓论坛
kingbase:
  users:
    - user: "user1@example.com"
      password: "password1"
    - user: "user2@example.com"
      password: "password2"
  article_id: "da1647283d13de4bd342dd67be76c1a5"  # 回帖文章ID
  reply_count: 5  # 每日回帖次数

# OceanBase 论坛
oceanbase:
  users:
    - user: "user@example.com"
      password: "password"

# PGFans PostgreSQL 中文社区
pgfans:
  users:
    - user: "user@example.com"
      password: "password"

# MoDB 墨天轮数据库社区
modb:
  users:
    - user: "user@example.com"
      password: "password"

# GBase 南大通用论坛
gbase:
  users:
    - user: "user@example.com"
      password: "password"
```

### 配置项说明

| 配置项 | 说明 | 必填 | 默认值 |
|--------|------|------|--------|
| `schedule` | 定时执行时间 (HH:MM 格式) | 否 | `03:00` |
| `push_plus_token` | PushPlus 推送 Token | 否 | - |
| `kingbase.users` | Kingbase 账号列表 | 否 | - |
| `kingbase.article_id` | Kingbase 回帖文章 ID | 否 | - |
| `kingbase.reply_count` | Kingbase 每日回帖次数 | 否 | `5` |
| `oceanbase.users` | OceanBase 账号列表 | 否 | - |
| `pgfans.users` | PGFans 账号列表 | 否 | - |
| `modb.users` | MoDB 账号列表 | 否 | - |
| `gbase.users` | GBase 账号列表 | 否 | - |

### 获取 PushPlus Token

1. 访问 [PushPlus 官网](https://www.pushplus.plus/)
2. 微信扫码登录
3. 复制你的 Token
4. 填入配置文件的 `push_plus_token` 字段

## 🐳 部署方式

### Docker Compose 部署

`docker-compose.yml` 配置说明:

```yaml
services:
  autosign:
    image: redgreat/autosign:latest
    container_name: autosign
    restart: unless-stopped
    environment:
      - TZ=Asia/Shanghai
      - CONFIG_PATH=/app/conf/config.yml
    volumes:
      - ./logs:/app/logs
      - ./conf/config.yml:/app/conf/config.yml:ro
    healthcheck:
      test: ["CMD-SHELL", "pgrep -f 'python.*all_checkin.py' || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### GitHub Actions 自动构建

项目已配置 GitHub Actions,当推送带有 `v*` 格式的标签时,会自动:

1. 构建多架构 Docker 镜像 (amd64/arm64)
2. 推送到 Docker Hub
3. 推送到 GitHub Container Registry (ghcr.io)
4. 自动打上 `latest` 标签

**发布新版本:**

```bash
# 使用自动化脚本 (推荐)
./scripts/dockerbuild.sh        # macOS/Linux
./scripts/dockerbuild.ps1       # Windows

# 或手动创建标签
git tag v1.0.0
git push origin v1.0.0
```

## 🎯 支持平台

| 平台 | 功能 | 状态 |
|------|------|------|
| **Kingbase** (人大金仓) | 自动回帖 | ✅ 支持 |
| **OceanBase** | 自动签到 | ✅ 支持 |
| **PGFans** (PostgreSQL中文社区) | 自动签到 | ✅ 支持 |
| **MoDB** (墨天轮) | 自动签到 | ✅ 支持 |
| **GBase** (南大通用) | 自动签到 | ✅ 支持 |
| **GreatSQL** | 自动签到 | 🔄 开发中 |
| **TiDB** | 自动签到 | 🔄 开发中 |

## 📝 使用说明

### 查看运行日志

```bash
# Docker Compose
docker-compose logs -f

# Docker
docker logs -f autosign

# 本地运行
tail -f logs/autosign.log
```

### 手动触发签到

```bash
# 进入容器
docker exec -it autosign bash

# 执行签到
python all_checkin.py
```

### 修改签到时间

编辑 `conf/config.yml` 中的 `schedule` 字段,然后重启容器:

```bash
docker-compose restart
```

## 🛠️ 开发指南

### 项目结构

```
autosign/
├── all_checkin.py          # 主程序入口
├── kingbase_checkin.py     # Kingbase 签到模块
├── oceanbase_checkin.py    # OceanBase 签到模块
├── pg_checkin.py           # PGFans 签到模块
├── modb_checkin.py         # MoDB 签到模块
├── gbase_checkin.py        # GBase 签到模块
├── greatsql_checkin.py     # GreatSQL 签到模块
├── tidb_checkin.py         # TiDB 签到模块
├── requirements.txt        # Python 依赖
├── Dockerfile              # Docker 镜像构建文件
├── docker-compose.yml      # Docker Compose 配置
├── conf/
│   ├── config.yml          # 配置文件
│   └── config.yml.sample   # 配置文件示例
├── scripts/
│   ├── dockerbuild.sh      # macOS/Linux 构建脚本
│   └── dockerbuild.ps1     # Windows 构建脚本
└── .github/
    └── workflows/
        └── dockerpush.yml  # GitHub Actions 工作流
```

### 添加新平台支持

1. 创建新的签到模块文件 (如 `newplatform_checkin.py`)
2. 实现登录和签到逻辑
3. 在 `all_checkin.py` 中集成新模块
4. 更新配置文件示例

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request!

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## ⚠️ 免责声明

本工具仅供学习交流使用,请勿用于商业用途。使用本工具所产生的一切后果由使用者自行承担,与开发者无关。

## 🙏 致谢

- [PushPlus](https://www.pushplus.plus/) - 提供微信推送服务
- [ddddocr](https://github.com/sml2h3/ddddocr) - 提供验证码识别支持

## 📮 联系方式

- 项目地址: [https://github.com/redgreat/autosign](https://github.com/redgreat/autosign)
- 问题反馈: [Issues](https://github.com/redgreat/autosign/issues)

---

<div align="center">

**如果这个项目对你有帮助,请给个 ⭐️ Star 支持一下!**

Made with ❤️ by [wongcw](https://github.com/redgreat)

</div>