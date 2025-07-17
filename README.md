# autosign
论坛自动签到系列

## 功能特性

- **多账号支持**：所有脚本均支持多账号配置（使用 `#` 分隔符）
- **验证码识别**：GreatSQL 脚本集成 ddddocr 库自动识别验证码
- **随机延迟**：脚本内置 0-60 分钟随机延迟，避免同时执行
- **消息推送**：支持 PushPlus 推送签到结果
- **错误处理**：完善的异常处理和日志记录

## 支持的论坛

- **Kingbase（人大金仓）论坛**：自动回帖签到
- **TiDB 社区**：自动签到
- **OceanBase 社区**：自动签到
- **GreatSQL 论坛**：自动签到（支持验证码识别）

## 环境变量配置

### Kingbase 论坛配置
```bash
# 单账号
KINGBASE_USER=user@example.com
KINGBASE_PWD=password
KINGBASE_ARTICLE_ID=da1647283d13de4bd342dd67be76c1a5
KINGBASE_REPLY_CNT=5

# 多账号（使用#分隔）
KINGBASE_USER=user1@example.com#user2@example.com
KINGBASE_PWD=password1#password2
```

### TiDB 社区配置
```bash
# 单账号
TIDB_USER=tidb@example.com
TIDB_PWD=tidbpasswd

# 多账号（使用#分隔）
TIDB_USER=user1@example.com#user2@example.com
TIDB_PWD=password1#password2
```

### OceanBase 社区配置
```bash
# 单账号
OCEANBASE_USER=ob@example.com
OCEANBASE_PWD=obpasswd

# 多账号（使用#分隔）
OCEANBASE_USER=user1@example.com#user2@example.com
OCEANBASE_PWD=password1#password2
```

### GreatSQL 论坛配置
```bash
# 单账号
GREATSQL_USER=greatsql@example.com
GREATSQL_PWD=greatsqlpasswd

# 多账号（使用#分隔）
GREATSQL_USER=user1@example.com#user2@example.com
GREATSQL_PWD=password1#password2
```

### 消息推送配置（可选）
```bash
PUSH_PLUS_TOKEN=your_pushplus_token
```

## 依赖安装

```bash
# 基础依赖
pip install -r requirements.txt

# GreatSQL 脚本额外依赖
pip install ddddocr
```

## GitHub Secrets 配置示例

```json
{
  "PUSH_PLUS_TOKEN":  "xxxxx",
  "KINGBASE_USER":    "user@example.com",
  "KINGBASE_PWD":     "password",
  "KINGBASE_ARTICLE_ID": "da1647283d13de4bd342dd67be76c1a5",
  "KINGBASE_REPLY_CNT": 5,
  "TIDB_USER":        "tidb@example.com",
  "TIDB_PWD":         "tidbpasswd",
  "OCEANBASE_USER":   "ob@example.com",
  "OCEANBASE_PWD":    "obpasswd",
  "GREATSQL_USER":    "greatsql@example.com",
  "GREATSQL_PWD":     "greatsqlpasswd"
}```