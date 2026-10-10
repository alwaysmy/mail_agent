# mail_agent — 邮箱 agent 工具（阿里邮箱 IMAP/SMTP）

让 agent 读邮件、发邮件。两种用法：**MCP 工具**（OpenCode 等 MCP 客户端）和**命令行**。

## 一、部署

1. `cp config.template.json config.json`，填入邮箱地址和「三方客户端安全密码」
   （`config.json` 已在 `.gitignore` 中，不会被提交）。
2. 确认网页版邮箱已开启 IMAP/SMTP 权限（设置 → 邮箱设置 → POP和IMAP）并生成安全密码。
3. 装依赖：`pip install mcp`（仅 MCP 方式需要）。

## 二、服务器参数（阿里邮箱企业版）

| 协议 | 地址 | SSL 端口 | 非加密端口 |
|---|---|---|---|
| IMAP | `imap.qiye.aliyun.com` | 993 | 143 |
| SMTP | `smtp.qiye.aliyun.com` | 465 | 25 |

> 香港地区用 `imaphk.qiye.aliyun.com` / `smtphk.qiye.aliyun.com`；SMTP 80/587 未开通。
> 旧版 `mxhichina.com` 地址仍可用，新配置建议用上表地址。

## 三、MCP 用法（推荐）

`mcp_mail.py` 是一个 stdio MCP server，OpenCode 里注册到 `mcp.mail` 即可：

```json
{
  "mcp": {
    "mail": {
      "command": ["python", "/path/to/mcp_mail.py"],
      "enabled": true,
      "type": "local"
    }
  }
}
```

Agent 可直接调用三个工具：

| 工具 | 说明 |
|---|---|
| `mail.list` | 列邮件（`n` 最近 n 封 / `unread` 只看未读 / `folder` 文件夹） |
| `mail.read` | 读全文（`uid` 来自 list 结果） |
| `mail.send` | 发信（`to` / `subject` / `body`） |

> 只保留这三个工具。搜索不做成独立工具——用 `list` 拉一批邮件头，agent 在本地筛即可，
> 少注入一个工具就少一分误调用的可能。

自然语言即可触发：「列一下未读邮件」「读 UID 36 那封」「发一封给 xxx」。

## 四、命令行用法

```bat
python mailtool.py list --n 10
python mailtool.py list --unread
python mailtool.py read <uid>
python mailtool.py search 关键词          :: 本地过滤（只扫主题/发件人，--limit 控制范围）
python mailtool.py folders                :: 列出文件夹（含 modified-UTF7 原始名）
python mailtool.py send --to a@b.com --subject 标题 --body 正文
```

> CLI 比 MCP 多保留了 `search` / `folders`：命令行用不占 agent 的工具面，
> 前者在邮箱变大后翻旧邮件方便，后者用于读取非收件箱文件夹。

本地验证 MCP 是否正常：`python test_mcp.py`。

## 五、文件说明

| 文件 | 说明 |
|---|---|
| `mcp_mail.py` | MCP server（list / read / send） |
| `mailtool.py` | 同能力 CLI，含 search / folders |
| `test_mcp.py` | MCP 本地验证脚本 |
| `config.template.json` | 配置模板，复制为 `config.json` 使用 |
| `config.json` | 真实凭据，已被 `.gitignore` 排除 |
