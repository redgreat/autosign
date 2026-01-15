# autosign

论坛自动签到系列

## 快速开始

### 配置 GitHub Secrets

在 GitHub 仓库的 Settings -> Secrets and variables -> Actions 中设置 `CONFIG` Secret：

#### 单账号配置示例

```json
{
  "PUSH_PLUS_TOKEN":  "xxxxx",
  "KINGBASE_USER":    "user@example.com",
  "KINGBASE_PWD":     "password",
  "KINGBASE_ARTICLE_ID": "da1647283d13de4bd342dd67be76c1a5",
  "KINGBASE_REPLY_CNT": 5,
  "TIDB_USER":        "tidb@example.com",
  "TIDB_PWD":         "tidbpasswd"
}
```

#### 多账号配置示例

多个账号使用 `#` 分隔，账号和密码需要一一对应：

```json
{
  "PUSH_PLUS_TOKEN":  "xxxxx",
  "KINGBASE_USER":    "user1@example.com#user2@example.com#user3@example.com",
  "KINGBASE_PWD":     "password1#password2#password3",
  "KINGBASE_ARTICLE_ID": "da1647283d13de4bd342dd67be76c1a5",
  "KINGBASE_REPLY_CNT": 5
}
```

同时可以设置以下环境变量 Secrets 支持多账号：
- `PGFANS_USER` 和 `PGFANS_PWD` - PGFans 论坛
- `MODB_USER` 和 `MODB_PWD` - MoDB 墨天轮论坛
- `GBASE_USER` 和 `GBASE_PWD` - GBase 论坛

### 详细配置说明

查看 [配置文档](./config/README.md) 了解完整的配置选项和多账号配置方法。

## 功能特性

- 🔄 自动签到/回帖
- 📱 微信推送通知（通过 PushPlus）
- 👥 支持多账号配置
- ⏰ 定时执行（GitHub Actions）
- 📊 详细的执行日志