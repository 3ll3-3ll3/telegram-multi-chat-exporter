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
    AUTH_GUI_ONLY,
    CHAT_NOT_FOUND,
    DAEMON_UNAVAILABLE,
    EXPORT_IN_PROGRESS,
    FLOOD_WAIT,
    INVALID_ARGUMENT,
    MESSAGE_NOT_FOUND,
    NOT_AUTHORIZED,
    SESSION_BUSY,
    WRITE_FAILED,
    WRITE_OUTCOME_UNKNOWN,
    TelegramBridgeError,
)
from .logging_setup import setup_logging
from .session_lock import SessionBusyError
from .telegram_proxy import DaemonTelegramProxy

DEFAULT_FORWARD_LIMIT = 20
LARGE_FORWARD_LIMIT = 200
SAFE_SESSION_LABEL = r"%APPDATA%\TelegramMultiChatExporter\telegram.session"


class TgctlArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise TelegramBridgeError(INVALID_ARGUMENT, message)


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
        AUTH_GUI_ONLY: 3,
        CHAT_NOT_FOUND: 4,
        MESSAGE_NOT_FOUND: 4,
        AMBIGUOUS_CHAT: 5,
        FLOOD_WAIT: 6,
        WRITE_FAILED: 7,
        SESSION_BUSY: 8,
        EXPORT_IN_PROGRESS: 9,
        WRITE_OUTCOME_UNKNOWN: 10,
        DAEMON_UNAVAILABLE: 11,
    }.get(code, 1)


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


async def run_command(args: argparse.Namespace) -> dict[str, Any]:
    proxy = DaemonTelegramProxy("tgctl")

    if args.command == "status":
        return success(await proxy.status())

    if args.command == "forward":
        # Keep the client-side guard for immediate feedback; daemon validates it
        # again so future MCP/clients cannot bypass the safety boundary.
        validate_forward_batch(args.ids, args.allow_large_batch)

    if args.command == "chats" and args.chats_command == "list":
        if args.limit <= 0:
            raise TelegramBridgeError(INVALID_ARGUMENT, "limit 必须大于 0。")
        data = await proxy.ipc.request(
            "chats.list",
            {"folder": args.folder, "search": args.search, "limit": args.limit},
        )
        return success(data)

    if args.command == "messages" and args.messages_command == "search":
        rows = await proxy.search_messages(
            args.chat,
            contains=args.contains,
            since=_parse_iso(args.since),
            until=_parse_iso(args.until),
            limit=args.limit,
            case_sensitive=args.case_sensitive,
        )
        return success(rows)

    if args.command == "messages" and args.messages_command == "get":
        return success(await proxy.get_messages(args.chat, args.ids))

    if args.command == "forward":
        result = await proxy.forward_messages(
            args.source_chat,
            args.destination_chat,
            args.ids,
            dry_run=args.dry_run,
            allow_large_batch=args.allow_large_batch,
        )
        return success(result)

    if args.command == "send":
        result = await proxy.send_text_message(
            args.destination_chat,
            args.text,
            dry_run=args.dry_run,
        )
        data = _jsonable(result)
        if args.dry_run:
            # Preserve the v0.1.9 human/Codex preview contract. This is stdout
            # explicitly requested by the user, not an app.log entry.
            data["text"] = args.text
        return success(data)

    raise TelegramBridgeError(INVALID_ARGUMENT, "未知命令。")


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv == ["--tg-daemon-worker"]:
        from .daemon_main import main as daemon_main

        return daemon_main()

    setup_logging()
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
