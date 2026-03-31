"""
WebSocket-based RPC + event server for the IAA web UI.

Protocol
--------
Client  -> Server  (RPC call):
  { "type": "call", "id": "<uuid>", "method": "<name>", "params": { ... } }

Server  -> Client  (RPC result):
  { "type": "result", "id": "<uuid>", "ok": true,  "data": { ... } }
  { "type": "result", "id": "<uuid>", "ok": false, "error": "<msg>" }

Server  -> Client  (push event):
  { "type": "event", "name": "<name>", "data": { ... } }
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import traceback
from typing import TYPE_CHECKING, Any

from aiohttp import web

if TYPE_CHECKING:
    from ..service.iaa_service import IaaService

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# RPC handler registry
# ──────────────────────────────────────────────────────────────────────────────

class RpcRegistry:
    def __init__(self, service: 'IaaService') -> None:
        self._service = service

    # ── config ──────────────────────────────────────────────────────────────

    async def get_config(self, _params: dict) -> dict:
        return self._service.config.conf.model_dump()

    async def save_config(self, params: dict) -> dict:
        from iaa.config.base import IaaConfig
        new_conf = IaaConfig.model_validate(params.get('config', {}))
        # Copy mutable fields back
        conf = self._service.config.conf
        conf.game = new_conf.game
        conf.live = new_conf.live
        conf.challenge_live = new_conf.challenge_live
        conf.cm = new_conf.cm
        conf.scheduler = new_conf.scheduler
        self._service.config.save()
        return {'ok': True}

    # ── scheduler ────────────────────────────────────────────────────────────

    async def start_tasks(self, _params: dict) -> dict:
        sch = self._service.scheduler
        if not sch.running and not sch.is_starting:
            sch.start_regular(run_in_thread=True)
        return {'ok': True}

    async def stop_tasks(self, _params: dict) -> dict:
        sch = self._service.scheduler
        if sch.running or sch.is_starting:
            sch.stop(block=False)
        return {'ok': True}

    async def run_single_task(self, params: dict) -> dict:
        task_id: str = params.get('task_id', '')
        sch = self._service.scheduler
        sch.run_single(task_id, run_in_thread=True)
        return {'ok': True}

    async def get_status(self, _params: dict) -> dict:
        sch = self._service.scheduler
        from iaa.context import hub as progress_hub
        snapshot_raw = progress_hub().snapshot()
        snapshot = {k: _snapshot_to_dict(v) for k, v in snapshot_raw.items()}
        return {
            'running': sch.running,
            'is_starting': sch.is_starting,
            'is_stopping': sch.is_stopping,
            'current_task_id': sch.current_task_id,
            'current_task_name': sch.current_task_name,
            'progress_snapshot': snapshot,
        }

    # ── misc ──────────────────────────────────────────────────────────────────

    async def get_version(self, _params: dict) -> dict:
        return {'version': self._service.version}

    async def get_task_registry(self, _params: dict) -> dict:
        from iaa.tasks.registry import REGULAR_TASKS, MANUAL_TASKS, name_from_id
        return {
            'regular_tasks': {k: name_from_id(k) for k in REGULAR_TASKS},
            'manual_tasks': {k: name_from_id(k) for k in MANUAL_TASKS},
        }

    async def export_report(self, _params: dict) -> dict:
        path = self._service.export_report_zip()
        return {'path': path}

    # ── dispatch ─────────────────────────────────────────────────────────────

    async def dispatch(self, method: str, params: dict) -> Any:
        handler = getattr(self, method, None)
        if handler is None:
            raise ValueError(f'Unknown RPC method: {method}')
        return await handler(params)


def _snapshot_to_dict(snap: Any) -> dict:
    from dataclasses import asdict
    try:
        return asdict(snap)
    except Exception:
        return {}


# ──────────────────────────────────────────────────────────────────────────────
# WebSocket connection handler
# ──────────────────────────────────────────────────────────────────────────────

class WsSession:
    """Manages a single WebSocket client connection."""

    def __init__(self, ws: web.WebSocketResponse, rpc: RpcRegistry, loop: asyncio.AbstractEventLoop) -> None:
        self._ws = ws
        self._rpc = rpc
        self._loop = loop
        self._unsubscribe_progress: Any = None

    # ── public ───────────────────────────────────────────────────────────────

    async def run(self) -> None:
        self._subscribe_progress()
        try:
            async for msg in self._ws:
                if msg.type == web.WSMsgType.TEXT:
                    await self._handle_message(msg.data)
                elif msg.type in (web.WSMsgType.ERROR, web.WSMsgType.CLOSE):
                    break
        finally:
            self._unsubscribe()

    # ── private ──────────────────────────────────────────────────────────────

    async def _handle_message(self, raw: str) -> None:
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning('Received invalid JSON from WebSocket client')
            return

        if msg.get('type') != 'call':
            return

        req_id = msg.get('id', '')
        method = msg.get('method', '')
        params = msg.get('params') or {}

        try:
            data = await self._rpc.dispatch(method, params)
            await self._send({'type': 'result', 'id': req_id, 'ok': True, 'data': data})
        except Exception as exc:
            logger.warning('RPC error [%s]: %s', method, exc)
            await self._send({'type': 'result', 'id': req_id, 'ok': False, 'error': str(exc)})

    def _subscribe_progress(self) -> None:
        from iaa.context import hub as progress_hub

        def _on_event(event: Any) -> None:
            payload: dict = {
                'type': 'event',
                'name': 'progress',
                'data': {
                    'run_id': event.run_id,
                    'task_id': event.task_id,
                    'task_name': event.task_name,
                    'timestamp': event.timestamp,
                    'event_type': event.type,
                    'payload': event.payload,
                },
            }
            asyncio.run_coroutine_threadsafe(self._send(payload), self._loop)

        self._unsubscribe_progress = progress_hub().subscribe(_on_event)

    def _unsubscribe(self) -> None:
        if self._unsubscribe_progress:
            try:
                self._unsubscribe_progress()
            except Exception:
                pass
            self._unsubscribe_progress = None

    async def _send(self, obj: dict) -> None:
        try:
            if not self._ws.closed:
                await self._ws.send_str(json.dumps(obj, default=str))
        except Exception as exc:
            logger.debug('WS send error: %s', exc)


# ──────────────────────────────────────────────────────────────────────────────
# aiohttp application factory
# ──────────────────────────────────────────────────────────────────────────────

def create_app(service: 'IaaService', static_dir: str | None = None) -> web.Application:
    app = web.Application()
    rpc_registry = RpcRegistry(service)

    async def ws_handler(request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        loop = asyncio.get_event_loop()
        session = WsSession(ws, rpc_registry, loop)
        await session.run()
        return ws

    app.router.add_get('/ws', ws_handler)

    # Serve the built React SPA when a static directory is provided
    if static_dir and os.path.isdir(static_dir):
        # Serve static assets (JS, CSS, images)
        app.router.add_static('/assets', os.path.join(static_dir, 'assets'), append_version=False)

        index_html = os.path.join(static_dir, 'index.html')

        async def spa_handler(request: web.Request) -> web.Response:  # noqa: ARG001
            return web.FileResponse(index_html)

        # Catch-all for SPA routing
        app.router.add_get('/', spa_handler)
        app.router.add_get('/{path_info:.*}', spa_handler)

    return app


def run_server(
    service: 'IaaService',
    host: str = '127.0.0.1',
    port: int = 18765,
    static_dir: str | None = None,
) -> None:
    """Start the aiohttp server (blocking call, runs until Ctrl-C)."""
    app = create_app(service, static_dir=static_dir)
    web.run_app(app, host=host, port=port, print=logger.info)
