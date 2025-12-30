from __future__ import annotations

import os
import threading
from typing import Any, Iterable

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from iaa.application.service.iaa_service import IaaService
from iaa.config.base import IaaConfig
from iaa.config.schemas import (
    ChallengeLiveAward,
    CustomEmulatorData,
    GameCharacter,
)
from iaa.tasks.registry import MANUAL_TASKS, REGULAR_TASKS, name_from_id

# 与原 Tkinter 界面保持一致的常量
SONG_OPTIONS: dict[int, str] = {
    -1: "保持不变",
    1: "Tell Your World｜Tell Your World",
    47: "メルト｜Melt",
    74: "独りんぼエンヴィー｜孑然妒火",
}

CHARACTER_GROUPS: list[tuple[str, list[GameCharacter]]] = [
    ("VIRTUAL SINGER", [
        GameCharacter.Miku, GameCharacter.Rin, GameCharacter.Len,
        GameCharacter.Luka, GameCharacter.Meiko, GameCharacter.Kaito,
    ]),
    ("Leo/need", [GameCharacter.Ichika, GameCharacter.Saki, GameCharacter.Honami, GameCharacter.Shiho]),
    ("MORE MORE JUMP!", [GameCharacter.Minori, GameCharacter.Haruka, GameCharacter.Airi, GameCharacter.Shizuku]),
    ("Vivid BAD SQUAD", [GameCharacter.Kohane, GameCharacter.An, GameCharacter.Akito, GameCharacter.Toya]),
    ("ワンダーランズ×ショウタイム", [GameCharacter.Tsukasa, GameCharacter.Emu, GameCharacter.Nene, GameCharacter.Rui]),
    ("25時、ナイトコードで。", [GameCharacter.Kanade, GameCharacter.Mafuyu, GameCharacter.Ena, GameCharacter.Mizuki]),
]

LINK_OPTIONS = [
    {"value": "no", "label": "不引继账号"},
    {"value": "google_play", "label": "Google Play"},
]
EMULATOR_OPTIONS = [
    {"value": "mumu", "label": "MuMu"},
    {"value": "custom", "label": "自定义"},
]
SERVER_OPTIONS = [
    {"value": "jp", "label": "日服"},
]
CONTROL_IMPL_OPTIONS = [
    {"value": "nemu_ipc", "label": "Nemu IPC"},
    {"value": "adb", "label": "ADB"},
    {"value": "uiautomator", "label": "UIAutomator2"},
]


service = IaaService()
_config_lock = threading.Lock()


def _serialize_config(conf: IaaConfig) -> dict[str, Any]:
    return {
        "meta": {
            "version": conf.version,
            "name": conf.name,
            "description": conf.description,
        },
        "game": {
            "server": conf.game.server,
            "link_account": conf.game.link_account,
            "emulator": conf.game.emulator,
            "control_impl": conf.game.control_impl,
            "emulator_data": conf.game.emulator_data.model_dump() if conf.game.emulator_data else None,
        },
        "live": {
            "mode": conf.live.mode,
            "song_id": conf.live.song_id,
            "count_mode": conf.live.count_mode,
            "count": conf.live.count,
            "fully_deplete": conf.live.fully_deplete,
        },
        "challenge_live": {
            "characters": [c.value for c in conf.challenge_live.characters],
            "award": conf.challenge_live.award.value,
        },
        "scheduler": conf.scheduler.model_dump(),
    }


def _parse_characters(values: Iterable[str]) -> list[GameCharacter]:
    parsed: list[GameCharacter] = []
    for raw in values:
        try:
            parsed.append(GameCharacter(raw))
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"Unknown character: {raw}") from exc
    return parsed


def _apply_config_patch(conf: IaaConfig, payload: dict[str, Any]) -> None:
    if "game" in payload:
        game = payload["game"] or {}
        for key in ("server", "link_account", "emulator", "control_impl"):
            if key in game:
                setattr(conf.game, key, game[key])
        if "emulator_data" in game:
            emu_data = game["emulator_data"]
            if emu_data is None:
                conf.game.emulator_data = None
            else:
                conf.game.emulator_data = CustomEmulatorData(
                    adb_ip=emu_data.get("adb_ip", conf.game.emulator_data.adb_ip if conf.game.emulator_data else "127.0.0.1"),
                    adb_port=int(emu_data.get("adb_port", conf.game.emulator_data.adb_port if conf.game.emulator_data else 5555)),
                )
    if "live" in payload:
        live = payload["live"] or {}
        for key in ("mode", "song_id", "count_mode", "count", "fully_deplete"):
            if key in live:
                setattr(conf.live, key, live[key])
    if "challenge_live" in payload:
        cl = payload["challenge_live"] or {}
        if "characters" in cl:
            conf.challenge_live.characters = _parse_characters(cl.get("characters", []))
        if "award" in cl:
            try:
                conf.challenge_live.award = ChallengeLiveAward(cl["award"])
            except Exception as exc:  # noqa: BLE001
                raise ValueError(f"Unknown challenge award: {cl['award']}") from exc
    if "scheduler" in payload:
        sched = payload["scheduler"] or {}
        for key in ("start_game_enabled", "solo_live_enabled", "challenge_live_enabled", "activity_story_enabled", "cm_enabled"):
            if key in sched:
                setattr(conf.scheduler, key, bool(sched[key]))


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app)

    @app.get("/api/status")
    def status() -> Any:
        sch = service.scheduler
        return jsonify({
            "running": sch.running,
            "is_starting": sch.is_starting,
            "is_stopping": sch.is_stopping,
            "current_task_id": sch.current_task_id,
            "current_task_name": sch.current_task_name,
            "available_tasks": list(REGULAR_TASKS.keys()) + list(MANUAL_TASKS.keys()),
            "scheduler": service.config.conf.scheduler.model_dump(),
        })

    @app.post("/api/scheduler/start")
    def start_scheduler() -> Any:
        sch = service.scheduler
        if sch.is_starting or sch.running:
            return jsonify({"message": "scheduler already starting or running"}), 409
        sch.start_regular(run_in_thread=True)
        return jsonify({"message": "scheduler starting"})

    @app.post("/api/scheduler/stop")
    def stop_scheduler() -> Any:
        sch = service.scheduler
        if not sch.running and not sch.is_starting:
            return jsonify({"message": "scheduler not running"}), 409
        sch.stop(block=False)
        return jsonify({"message": "stop requested"})

    @app.post("/api/tasks/<task_id>/run")
    def run_task(task_id: str) -> Any:
        tasks = {**REGULAR_TASKS, **MANUAL_TASKS}
        if task_id not in tasks:
            return jsonify({"error": "unknown task"}), 404
        sch = service.scheduler
        if sch.running or sch.is_starting or sch.is_stopping:
            return jsonify({"error": "scheduler busy"}), 409
        sch.run_single(task_id, run_in_thread=True)
        return jsonify({"message": f"task {task_id} started", "task_name": name_from_id(task_id)})

    @app.get("/api/config")
    def get_config() -> Any:
        return jsonify(_serialize_config(service.config.conf))

    @app.put("/api/config")
    def update_config() -> Any:
        payload = request.get_json(silent=True) or {}
        with _config_lock:
            try:
                _apply_config_patch(service.config.conf, payload)
                service.config.save()
            except ValueError as exc:
                return jsonify({"error": str(exc)}), 400
        return jsonify(_serialize_config(service.config.conf))

    @app.get("/api/options")
    def options() -> Any:
        return jsonify({
            "songs": [{"value": sid, "label": label} for sid, label in SONG_OPTIONS.items()],
            "characters": [
                {
                    "group": group_name,
                    "items": [{"value": ch.value, "label": ch.last_name_cn + ch.first_name_cn} for ch in chars],
                }
                for group_name, chars in CHARACTER_GROUPS
            ],
            "challenge_awards": [
                {"value": aw.value, "label": label} for aw, label in ChallengeLiveAward.display_map_cn().items()
            ],
            "links": [
                {"text": "GitHub", "url": "https://github.com/XcantloadX/ichikas-auto-assistant"},
                {"text": "Bilibili", "url": "https://space.bilibili.com/3546853903698457"},
                {"text": "教程文档", "url": "https://p.kdocs.cn/s/AGBH56RBAAAFS"},
                {"text": "QQ 群", "url": "https://qm.qq.com/q/Mu1SSfK1Gg"},
            ],
            "link_accounts": LINK_OPTIONS,
            "emulators": EMULATOR_OPTIONS,
            "servers": SERVER_OPTIONS,
            "control_impls": CONTROL_IMPL_OPTIONS,
        })

    @app.get("/api/about")
    def about() -> Any:
        logo_url = "/api/assets/marry_with_6_mikus.png"
        return jsonify({
            "version": service.version,
            "logo": logo_url if os.path.exists(service.assets.logo_path) else None,
            "links": [
                {"text": "GitHub", "url": "https://github.com/XcantloadX/ichikas-auto-assistant"},
                {"text": "Bilibili", "url": "https://space.bilibili.com/3546853903698457"},
                {"text": "教程文档", "url": "https://p.kdocs.cn/s/AGBH56RBAAAFS"},
                {"text": "QQ 群", "url": "https://qm.qq.com/q/Mu1SSfK1Gg"},
            ],
        })

    @app.get("/api/assets/<path:filename>")
    def serve_assets(filename: str) -> Any:
        assets_dir = os.path.join(service.root, "assets")
        return send_from_directory(assets_dir, filename)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000)
