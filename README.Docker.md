# AutoSign - 数据库论坛自动签到工具

一个基于 Python 的多平台数据库论坛自动签到工具,支持 Kingbase、OceanBase、PGFans、MoDB、GBase 等平台。

## 快速开始

### 使用 Docker Compose (推荐)

1. 创建 `docker-compose.yml`:

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

2. 创建配置文件 `conf/config.yml`:

```yaml
schedule: "03:00"
push_plus_token: "your_token"  # 可选
kingbase:
  users:
    - user: "user@example.com"
      password: "password"
  article_id: "article_id"
  reply_count: 5
oceanbase:
  users:
    - user: "user@example.com"
      password: "password"
pgfans:
  users:
    - user: "user@example.com"
      password: "password"
modb:
  users:
    - user: "user@example.com"
      password: "password"
gbase:
  users:
    - user: "user@example.com"
      password: "password"
```

3. 启动服务:

```bash
docker-compose up -d
```

### 使用 Docker 命令

```bash
docker run -d \
  --name autosign \
  --restart unless-stopped \
  -v $(pwd)/conf/config.yml:/app/conf/config.yml:ro \
  -v $(pwd)/logs:/app/logs \
  -e TZ=Asia/Shanghai \
  redgreat/autosign:latest
```

## 支持的平台

- ✅ Kingbase (人大金仓) - 自动回帖
- ✅ OceanBase - 自动签到
- ✅ PGFans (PostgreSQL中文社区) - 自动签到
- ✅ MoDB (墨天轮) - 自动签到
- ✅ GBase (南大通用) - 自动签到

## 功能特性

- 🎯 多平台支持
- 👥 多账号管理
- 🔐 安全加密登录
- 📱 微信推送通知 (PushPlus)
- ⏰ 定时自动执行
- 📊 详细执行日志
- 🏥 健康检查机制

## 镜像标签

- `latest` - 最新稳定版本
- `vX.Y.Z` - 指定版本

## 支持的架构

- `linux/amd64`
- `linux/arm64`

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `TZ` | 时区设置 | `Asia/Shanghai` |
| `CONFIG_PATH` | 配置文件路径 | `/app/conf/config.yml` |
| `PYTHONUNBUFFERED` | Python 输出缓冲 | `1` |

## 数据卷

| 路径 | 说明 |
|------|------|
| `/app/conf/config.yml` | 配置文件 (只读) |
| `/app/logs` | 日志目录 |

## 健康检查

容器内置健康检查机制,每 30 秒检查一次进程状态。

## 查看日志

```bash
# Docker Compose
docker-compose logs -f

# Docker
docker logs -f autosign
```

## 手动执行签到

```bash
docker exec -it autosign python all_checkin.py
```

## 项目地址

- GitHub: https://github.com/redgreat/autosign
- 文档: https://github.com/redgreat/autosign/blob/main/README.md

## 许可证

MIT License - 详见 [LICENSE](https://github.com/redgreat/autosign/blob/main/LICENSE)
