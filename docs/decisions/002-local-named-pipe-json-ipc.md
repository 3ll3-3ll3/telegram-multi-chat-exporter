# ADR-002 — Authenticated local Named Pipe + JSON IPC

## Status
Accepted

## Context
GUI/tgctl 需要访问唯一 daemon，但项目是 Windows 本地工具，不需要远程服务。

## Decision
使用 Windows Named Pipe / `AF_PIPE`、本地随机 auth secret、UTF-8 JSON bytes。

## Why
本地、可审计、无需开放端口，JSON 适合 CLI/Codex stable contract。

## Rejected alternatives
TCP/HTTP/Web server、pickle object transport、公开远程控制接口。

## Consequences
IPC 只承载 bounded request/response；Secret 不进 stdout/log/cursor。
