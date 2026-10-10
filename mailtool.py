"""邮箱 CLI 工具：list / read / search / send / folders
用法示例：
  python mailtool.py list --n 10
  python mailtool.py list --unread
  python mailtool.py read <uid>
  python mailtool.py search "关键词"
  python mailtool.py send --to a@b.com --subject 标题 --body 正文
  python mailtool.py folders
"""
import argparse
import email
import email.header
import email.utils
import imaplib
import json
import os
import smtplib
import sys
from email.header import decode_header, make_header
from email.message import EmailMessage
from email.mime.text import MIMEText
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

CFG_PATH = Path(__file__).with_name("config.json")


def load_cfg():
    if not CFG_PATH.exists():
        print(f"缺少配置文件 {CFG_PATH}，请先填写 config.json", file=sys.stderr)
        sys.exit(1)
    return json.loads(CFG_PATH.read_text(encoding="utf-8"))


def decode_str(s):
    if s is None:
        return ""
    try:
        return str(make_header(decode_header(s)))
    except Exception:
        return str(s)


def connect_imap(cfg):
    m = imaplib.IMAP4_SSL(cfg.get("imap_host", "imap.aliyun.com"), int(cfg.get("imap_port", 993)))
    m.login(cfg["email"], cfg["password"])
    return m


def get_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            disp = str(part.get("Content-Disposition", ""))
            if ctype == "text/plain" and "attachment" not in disp:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    try:
                        return payload.decode(charset, errors="replace")
                    except LookupError:
                        return payload.decode("utf-8", errors="replace")
        # 没有纯文本则取第一个 html 粗略转文本
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    try:
                        return payload.decode(charset, errors="replace")
                    except LookupError:
                        return payload.decode("utf-8", errors="replace")
        return ""
    payload = msg.get_payload(decode=True)
    if payload:
        charset = msg.get_content_charset() or "utf-8"
        try:
            return payload.decode(charset, errors="replace")
        except LookupError:
            return payload.decode("utf-8", errors="replace")
    return ""


def format_msg(uid, msg):
    subj = decode_str(msg.get("Subject"))
    frm = decode_str(msg.get("From"))
    date = msg.get("Date", "")
    return f"UID: {uid}\n发件人: {frm}\n日期: {date}\n主题: {subj}\n"


def cmd_list(args, cfg):
    m = connect_imap(cfg)
    try:
        m.select(args.folder, readonly=True)
        if args.unread:
            status, data = m.search(None, "UNSEEN")
        else:
            status, data = m.search(None, "ALL")
        uids = data[0].split() if status == "OK" else []
        uids = uids[-args.n:] if not args.unread else uids[: args.n]
        for uid in reversed(uids):
            status, data = m.fetch(uid, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])")
            if status != "OK":
                continue
            msg = email.message_from_bytes(data[0][1])
            print(format_msg(uid.decode(), msg))
            print("-" * 40)
    finally:
        try:
            m.close()
        except Exception:
            pass
        m.logout()


def cmd_read(args, cfg):
    m = connect_imap(cfg)
    try:
        m.select(args.folder, readonly=True)
        status, data = m.fetch(args.uid.encode(), "(RFC822)")
        if status != "OK" or not data or data[0] is None:
            print(f"未找到 UID {args.uid}")
            return
        msg = email.message_from_bytes(data[0][1])
        print(format_msg(args.uid, msg))
        print("正文:\n")
        print(get_body(msg)[: args.max_chars])
    finally:
        try:
            m.close()
        except Exception:
            pass
        m.logout()


def cmd_search(args, cfg):
    m = connect_imap(cfg)
    try:
        m.select(args.folder, readonly=True)
        status, data = m.search(None, "ALL")
        uids = data[0].split() if status == "OK" else []
        scanned = uids[-args.limit:]
        kw = args.keyword.lower()
        hits = []
        for uid in reversed(scanned):
            status, data = m.fetch(uid, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])")
            if status != "OK" or not data or data[0] is None:
                continue
            msg = email.message_from_bytes(data[0][1])
            hay = f"{decode_str(msg.get('Subject'))} {decode_str(msg.get('From'))}".lower()
            if kw in hay:
                hits.append((uid, msg))
        if not hits:
            print(f"（最近 {len(scanned)} 封邮件中没有「{args.keyword}」）")
            return
        for uid, msg in hits[: args.n]:
            print(format_msg(uid.decode(), msg))
            print("-" * 40)
    finally:
        try:
            m.close()
        except Exception:
            pass
        m.logout()


def cmd_send(args, cfg):
    msg = MIMEText(args.body, "plain", "utf-8")
    msg["From"] = cfg["email"]
    msg["To"] = args.to
    msg["Subject"] = args.subject
    s = smtplib.SMTP_SSL(cfg.get("smtp_host", "smtp.aliyun.com"), int(cfg.get("smtp_port", 465)))
    try:
        s.login(cfg["email"], cfg["password"])
        s.send_message(msg)
        print(f"已发送至 {args.to}")
    finally:
        s.quit()


def cmd_folders(args, cfg):
    m = connect_imap(cfg)
    try:
        status, data = m.list()
        for line in data or []:
            if line:
                print(line.decode(errors="replace"))
    finally:
        m.logout()


def main():
    p = argparse.ArgumentParser(description="阿里邮箱 CLI 工具")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("list")
    sp.add_argument("--n", type=int, default=10)
    sp.add_argument("--unread", action="store_true")
    sp.add_argument("--folder", default="INBOX")
    sp.set_defaults(func=cmd_list)

    sp = sub.add_parser("read")
    sp.add_argument("uid")
    sp.add_argument("--folder", default="INBOX")
    sp.add_argument("--max-chars", type=int, default=4000)
    sp.set_defaults(func=cmd_read)

    sp = sub.add_parser("search")
    sp.add_argument("keyword")
    sp.add_argument("--n", type=int, default=10)
    sp.add_argument("--limit", type=int, default=500, help="扫描最近多少封")
    sp.add_argument("--folder", default="INBOX")
    sp.set_defaults(func=cmd_search)

    sp = sub.add_parser("send")
    sp.add_argument("--to", required=True)
    sp.add_argument("--subject", required=True)
    sp.add_argument("--body", required=True)
    sp.set_defaults(func=cmd_send)

    sp = sub.add_parser("folders")
    sp.set_defaults(func=cmd_folders)

    args = p.parse_args()
    cfg = load_cfg()
    args.func(args, cfg)


if __name__ == "__main__":
    main()
