from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from dataclasses import asdict, is_dataclass
from datetime import datetime
from typing import Any

from telethon.errors import FloodWaitError

from .bridge_errors import (
    AMBIGUOUS_CHAT,
    CHAT_NOT_FOUND,
    FLOOD_WAIT,
    INVALID_ARGUMENT,
    MESSAGE_NOT_FOUND,
    NOT_AUTHORIZED,
    SESSION_BUSY,
    WRITE_FAILED,
    TelegramBridgeError,
)
from .credentials_store import load_saved_credentials
from .logging_setup import setup_logging
from .paths import session_path
from .proxy import detect_windows_system_proxy
from .session_lock import SessionBusyError
from .telegram_service import TelegramService

DEFAULT_FORWARD_LIMIT = 20
LARGE_FORWARD_LIMIT = 200
SAFE_SESSION_LABEL = r"%APPDATA%\TelegramMultiChatExporter\telegram.session"


class TgctlArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise TelegramBridgeError(INVALID_ARGUMENT, message)


def _configure_console_streams() -> None:
    """Make the CLI contract UTF-8 even on legacy Windows code pages.

    PyInstaller console builds inherit the process' stdout/stderr text encoding.
    On machines/runners using a legacy code page (for example cp1252), emitting
    Chinese JSON error messages can otherwise raise UnicodeEncodeError *while
    handling the original error*. That secondary failure changes the native
    process exit code to 1 and breaks the documented JSON/exit-code contract.

    ``reconfigure`` is available on normal Python/PyInstaller TextIOWrapper
    streams. Test harnesses and embedded callers may replace streams with
    objects that do not provide it, so those are intentionally left untouched.
    """

    stdout_reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(stdout_reconfigure):
        stdout_reconfigure(encoding="utf-8", errors="strict")

    stderr_reconfigure = getattr(sys.stderr, "reconfigure", None)
    if callable(stderr_reconfigure):
        # Human diagnostics should never crash error handling merely because a
        # terminal cannot represent a character. UTF-8 handles normal Windows
        # terminals/pipes; backslashreplace is a final defensive fallback.
        stderr_reconfigure(encoding="utf-8", errors="backslashreplace")


def _add_json_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", help="stdout 仅输出机器可读 JSON")


def build_parser() -> argparse.ArgumentParser:
    parser = TgctlArgumentParser(prog="tgctl", description="TG Exporter local Telegram CLI bridge")
    sub = parser.add_subparsers(dest="command", required=True)

    status = sub.add_parser("status")
    _add_json_flag(status)

    chats = sub.add_parser("chats")
    chats_sub = chats.add_subparsers(dest="chats_command", required=True)
    chats_list = chats_sub.add_parser("list")
    chats_list.add_argument("--folder")
    chats_list.add_argument("--search")
    chats_list.add_argument("--limit", type=int, default=100)
    _add_json_flag(chats_list)

    messages = sub.add_parser("messages")
    messages_sub = messages.add_subparsers(dest="messages_command", required=True)
    search = messages_sub.add_parser("search")
    search.add_argument("--chat", required=True)
    search.add_argument("--contains")
    search.add_argument("--since")
    search.add_argument("--until")
    search.add_argument("--limit", type=int, default=100)
    search.add_argument("--case-sensitive", action="store_true")
    _add_json_flag(search)

    get = messages_sub.add_parser("get")
    get.add_argument("--chat", required=True)
    get.add_argument("--ids", nargs="+", type=int, required=True)
    _add_json_flag(get)

    forward = sub.add_parser("forward")
    forward.add_argument("--from", dest="source_chat", required=True)
    forward.add_argument("--to", dest="destination_chat", required=True)
    forward.add_argument("--ids", nargs="+", type=int, required=True)
    forward.add_argument("--dry-run", action="store_true")
    forward.add_argument("--allow-large-batch", action="store_true")
    _add_json_flag(forward)

    send = sub.add_parser("send")
    send.add_argument("--to", dest="destination_chat", required=True)
    send.add_argument("--text", required=True)
    send.add_argument("--dry-run", action="store_true")
    _add_json_flag(send)
    return parser


def validate_forward_batch(ids: list[int], allow_large_batch: bool) -> None:
    limit = LARGE_FORWARD_LIMIT if allow_large_batch else DEFAULT_FORWARD_LIMIT
    if len(ids) > limit:
        raise TelegramBridgeError(
            INVALID_ARGUMENT,
            f"单次 forward 最多 {limit} 条。"
            + ("" if allow_large_batch else "如确有需要，请显式加入 --allow-large-batch。"),
            {"requested_count": len(ids), "limit": limit},
        )


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise TelegramBridgeError(INVALID_ARGUMENT, f"无法解析时间：{value}") from exc
    if parsed.tzinfo is None:
        local_tz = datetime.now().astimezone().tzinfo
        parsed = parsed.replace(tzinfo=local_tz)
    return parsed


def _jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def success(data: Any) -> dict[str, Any]:
    return {"ok": True, "data": _jsonable(data)}


def failure(code: str, message: str, details: Any = None) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if details is not None:
        error["details"] = _jsonable(details)
    return {"ok": False, "error": error}


def _exit_code(code: str) -> int:
    return {
        INVALID_ARGUMENT: 2,
        NOT_AUTHORIZED: 3,
        CHAT_NOT_FOUND: 4,
        MESSAGE_NOT_FOUND: 4,
        AMBIGUOUS_CHAT: 5,
        FLOOD_WAIT: 6,
        WRITE_FAILED: 7,
        SESSION_BUSY: 8,
    }.get(code, 1)


def _chat_dict(group) -> dict[str, Any]:
    return {
        "chat_id": group.chat_id,
        "title": group.title,
        "username": group.username,
        "type": group.chat_type,
    }


def _human_print(payload: dict[str, Any]) -> None:
    if not payload.get("ok"):
        error = payload["error"]
        print(f"ERROR [{error['code']}]: {error['message']}", file=sys.stderr)
        if error.get("details") is not None:
            print(json.dumps(error["details"], ensure_ascii=False, indent=2), file=sys.stderr)
        return
    data = payload.get("data")
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                print("\t".join(str(item.get(key, "")) for key in item.keys()))
            else:
                print(item)
    elif isinstance(data, dict):
        for key, value in data.items():
            print(f"{key}: {value}")
    else:
        print(data)


def emit(payload: dict[str, Any], json_mode: bool) -> None:
    if json_mode:
        print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    else:
        _human_print(payload)


async def _connect_existing_session(*, allow_unauthorized: bool = False) -> tuple[TelegramService | None, bool]:
    creds = load_saved_credentials()
    if creds is None:
        if allow_unauthorized:
            return None, False
        raise TelegramBridgeError(
            NOT_AUTHORIZED,
            "未找到已保存的 Telegram 登录配置。请先打开 TG Exporter 完成 Telegram 登录。",
        )
    service = TelegramService(creds, session_path())
    try:
        authorized = await service.connect()
    except Exception:
        await service.close()
        raise
    if not authorized and not allow_unauthorized:
        await service.close()
        raise TelegramBridgeError(
            NOT_AUTHORIZED,
            "当前 Telegram Session 尚未登录。请先打开 TG Exporter 完成 Telegram 登录。",
        )
    return service, authorized


async def run_command(args: argparse.Namespace) -> dict[str, Any]:
    if args.command == "status":
        proxy = detect_windows_system_proxy()
        service, authorized = await _connect_existing_session(allow_unauthorized=True)
        try:
            account = await service.account_info() if service and authorized else None
            return success(
                {
                    "authorized": authorized,
                    "account": account,
                    "session": SAFE_SESSION_LABEL,
                    "proxy": proxy.safe_label if proxy else "direct",
                    "hint": None if authorized else "请先打开 TG Exporter 完成 Telegram 登录",
                }
            )
        finally:
            if service:
                await service.close()

    if args.command == "forward":
        validate_forward_batch(args.ids, args.allow_large_batch)

    service, _ = await _connect_existing_session()
    assert service is not None
    try:
        if args.command == "chats" and args.chats_command == "list":
            if args.limit <= 0:
                raise TelegramBridgeError(INVALID_ARGUMENT, "limit 必须大于 0。")
            groups = await service.list_groups()
            if args.folder:
                folder_key = args.folder.casefold()
                known_folders = {folder.title.casefold() for group in groups for folder in group.folders}
                if folder_key not in known_folders:
                    raise TelegramBridgeError(CHAT_NOT_FOUND, f"找不到 Telegram 分组「{args.folder}」。")
                groups = [g for g in groups if any(f.title.casefold() == folder_key for f in g.folders)]
            if args.search:
                needle = args.search.casefold()
                groups = [
                    g
                    for g in groups
                    if needle in g.title.casefold() or (g.username and needle in g.username.casefold())
                ]
            return success([_chat_dict(group) for group in groups[: args.limit]])

        if args.command == "messages" and args.messages_command == "search":
            rows = await service.search_messages(
                args.chat,
                contains=args.contains,
                since=_parse_iso(args.since),
                until=_parse_iso(args.until),
                limit=args.limit,
                case_sensitive=args.case_sensitive,
            )
            return success(rows)

        if args.command == "messages" and args.messages_command == "get":
            rows = await service.get_messages(args.chat, args.ids)
            return success(rows)

        if args.command == "forward":
            try:
                result = await service.forward_messages(
                    args.source_chat,
                    args.destination_chat,
                    args.ids,
                    dry_run=args.dry_run,
                )
            except (TelegramBridgeError, FloodWaitError):
                raise
            except Exception as exc:
                raise TelegramBridgeError(WRITE_FAILED, f"Telegram 转发失败：{type(exc).__name__}") from exc
            return success(result)

        if args.command == "send":
            try:
                result = await service.send_text_message(
                    args.destination_chat,
                    args.text,
                    dry_run=args.dry_run,
                )
            except (TelegramBridgeError, FloodWaitError):
                raise
            except Exception as exc:
                raise TelegramBridgeError(WRITE_FAILED, f"Telegram 发送失败：{type(exc).__name__}") from exc
            data = _jsonable(result)
            if args.dry_run:
                data["text"] = args.text
            return success(data)

        raise TelegramBridgeError(INVALID_ARGUMENT, "未知命令。")
    finally:
        await service.close()


def main(argv: list[str] | None = None) -> int:
    _configure_console_streams()
    setup_logging()
    argv = list(sys.argv[1:] if argv is None else argv)
    json_mode = "--json" in argv
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        json_mode = bool(getattr(args, "json", json_mode))
        payload = asyncio.run(run_command(args))
        emit(payload, json_mode)
        return 0
    except TelegramBridgeError as exc:
        payload = failure(exc.code, exc.message, exc.details)
        emit(payload, json_mode)
        return _exit_code(exc.code)
    except SessionBusyError as exc:
        payload = failure(SESSION_BUSY, str(exc))
        emit(payload, json_mode)
        return _exit_code(SESSION_BUSY)
    except FloodWaitError as exc:
        seconds = int(getattr(exc, "seconds", 0) or 0)
        payload = failure(
            FLOOD_WAIT,
            f"Telegram 要求等待 {seconds} 秒后再试。" if seconds else "Telegram 触发 Flood Wait。",
            {"retry_after_seconds": seconds},
        )
        emit(payload, json_mode)
        return _exit_code(FLOOD_WAIT)
    except Exception as exc:
        logging.getLogger("telegram_exporter.tgctl").exception("tgctl command failed")
        payload = failure("TELEGRAM_ERROR", f"Telegram 操作失败：{type(exc).__name__}")
        emit(payload, json_mode)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
