"""阿里邮箱 MCP server（stdio）——在 OpenCode 里以 mcp 形式提供邮件读写能力。

启动：python mcp_mail.py   （由 OpenCode 的 mcp.mail 配置自动拉起）
工具：list / read / send，凭据读取同目录 config.json。
说明：不做 search —— 用 list 拉一批邮件头，再由 agent 本地筛选即可，省一个工具注入。
"""
import email
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).parent))

import mailtool as mt  # noqa: E402
from mcp.server.fastmcp import FastMCP  # noqa: E402

mcp = FastMCP("mail")


@mcp.tool(
    name="list",
    description="列出邮箱中的邮件（发件人/日期/主题）。n 取最近 n 封；unread=True 只列未读。folder 为文件夹名，默认 INBOX。",
)
def mail_list(n: int = 10, unread: bool = False, folder: str = "INBOX") -> str:
    cfg = mt.load_cfg()
    conn = mt.connect_imap(cfg)
    try:
        conn.select(folder, readonly=True)
        if unread:
            status, data = conn.search(None, "UNSEEN")
        else:
            status, data = conn.search(None, "ALL")
        uids = data[0].split() if status == "OK" else []
        if not unread:
            uids = uids[-n:]
        out = []
        for uid in reversed(uids):
            status, data = conn.fetch(uid, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])")
            if status != "OK":
                continue
            msg = email.message_from_bytes(data[0][1])
            out.append(mt.format_msg(uid.decode(), msg))
        if not out:
            return "（没有邮件）"
        return "\n---\n".join(out)
    finally:
        try:
            conn.close()
        except Exception:
            pass
        conn.logout()


@mcp.tool(
    name="read",
    description="读取某封邮件全文。uid 来自 list 的结果（UID: 后面的数字）。folder 默认 INBOX。",
)
def mail_read(uid: str, folder: str = "INBOX", max_chars: int = 4000) -> str:
    cfg = mt.load_cfg()
    conn = mt.connect_imap(cfg)
    try:
        conn.select(folder, readonly=True)
        status, data = conn.fetch(uid.encode(), "(RFC822)")
        if status != "OK" or not data or data[0] is None:
            return f"未找到 UID {uid}"
        msg = email.message_from_bytes(data[0][1])
        head = mt.format_msg(uid, msg)
        body = mt.get_body(msg)[:max_chars]
        return f"{head}\n正文:\n{body}"
    finally:
        try:
            conn.close()
        except Exception:
            pass
        conn.logout()


@mcp.tool(
    name="send",
    description="发送邮件。to 为收件人地址，subject 主题，body 正文（纯文本）。发送前应向用户复述收件人与主题。",
)
def mail_send(to: str, subject: str, body: str) -> str:
    import smtplib
    from email.mime.text import MIMEText

    cfg = mt.load_cfg()
    msg = MIMEText(body, "plain", "utf-8")
    msg["From"] = cfg["email"]
    msg["To"] = to
    msg["Subject"] = subject
    server = smtplib.SMTP_SSL(cfg.get("smtp_host", "smtp.qiye.aliyun.com"), int(cfg.get("smtp_port", 465)))
    try:
        server.login(cfg["email"], cfg["password"])
        server.send_message(msg)
    finally:
        server.quit()
    return f"已发送至 {to}（主题：{subject}）"


if __name__ == "__main__":
    mcp.run()
