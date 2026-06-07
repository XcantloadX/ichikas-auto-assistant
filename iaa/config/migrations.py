import json
import logging

from .migration import MigrationStep, MigrationContext, MigrationMessage

logger = logging.getLogger(__name__)


class ProfileV1ToV2(MigrationStep):
    """
    迁移 commit 6a34cead1637607fa526146ad78be6f47b3089ae 引入的配置变更。
    主要涉及 CustomEmulatorData 和 PhysicalAndroidData 的字段更名。
    """

    def check_needed(self, ctx: MigrationContext) -> bool:
        # 遍历所有配置文件，检查版本号
        for file in ctx.config_dir.glob('*.json'):
            if file.stem == '_shared':
                continue
            try:
                data = json.loads(file.read_text(encoding='utf-8'))
                version = data.get('version', 1)
                if version < 2:  # 目标版本是 2
                    return True
            except Exception:
                continue
        return False

    def apply(self, ctx: MigrationContext) -> None:
        for file in ctx.config_dir.glob('*.json'):
            if file.stem == '_shared':
                continue
            try:
                content = file.read_text(encoding='utf-8')
                data = json.loads(content)
                version = data.get('version', 1)

                if version >= 2:
                    continue

                changed = False
                game = data.get('game', {})
                emulator = game.get('emulator')
                emulator_data = game.get('emulator_data', {})

                if emulator == 'physical_android':
                    if 'adb_serial' in emulator_data:
                        emulator_data['device_serial'] = emulator_data.pop('adb_serial')
                        changed = True

                elif emulator == 'custom':
                    # 迁移 emulator_path -> start_command
                    emulator_data = emulator_data or {}
                    if 'emulator_path' in emulator_data:
                        path = emulator_data.pop('emulator_path')
                        args = emulator_data.pop('emulator_args', '')
                        # 合并为 start_command
                        if path:
                            emulator_data['start_command'] = f'"{path}" {args}'.strip()
                        else:
                            emulator_data['start_command'] = args.strip()
                        changed = True
                    elif 'emulator_args' in emulator_data:
                        # 只有 args 的情况
                        emulator_data['start_command'] = emulator_data.pop('emulator_args').strip()
                        changed = True

                # 升级版本号
                data['version'] = 2
                file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')

                ctx.messages.append(MigrationMessage(
                    text="自定义模拟器配置升级",
                    old_version="26.04b5 (v1)",
                    new_version="26.05b1 (v2)"
                ))
            except Exception as e:
                ctx.messages.append(MigrationMessage(
                    text=f"迁移配置 {file.name} 时出错: {e}",
                    level='warning'
                ))
                logger.exception(f"Error migrating config {file.name}")


class ProfileV2ToV3(MigrationStep):
    """
    将设备/连接/控制配置从 game.* 迁移到新的顶层 device.* 结构。

    旧结构（game.*）：
        emulator, check_emulator, emulator_data,
        control_impl, scrcpy_virtual_display, resolution_method

    新结构（device.*）：
        lifecycle: {type, ...}
        connection: {type, ...}
        control_impl, scrcpy_virtual_display, resolution_method
    """

    def check_needed(self, ctx: MigrationContext) -> bool:
        for file in ctx.config_dir.glob('*.json'):
            if file.stem == '_shared':
                continue
            try:
                data = json.loads(file.read_text(encoding='utf-8'))
                if data.get('version', 1) < 3:
                    return True
            except Exception:
                continue
        return False

    def apply(self, ctx: MigrationContext) -> None:
        for file in ctx.config_dir.glob('*.json'):
            if file.stem == '_shared':
                continue
            try:
                data = json.loads(file.read_text(encoding='utf-8'))
                if data.get('version', 1) >= 3:
                    continue

                game = data.get('game', {})
                emulator = game.pop('emulator', 'mumu_v5')
                check_emulator = game.pop('check_emulator', False)
                emulator_data = game.pop('emulator_data', None) or {}
                control_impl = game.pop('control_impl', 'nemu_ipc')
                scrcpy_virtual_display = game.pop('scrcpy_virtual_display', False)
                resolution_method = game.pop('resolution_method', 'auto')

                # ── 生命周期 ──────────────────────────────────
                if emulator in ('mumu', 'mumu_v5'):
                    lifecycle = {
                        'type': emulator,
                        'instance_id': emulator_data.get('instance_id'),
                        'check_and_start': bool(check_emulator),
                    }
                    connection = {'type': 'auto'}

                elif emulator == 'custom':
                    lifecycle = {
                        'type': 'custom',
                        'check_and_start': bool(check_emulator),
                        'start_command': emulator_data.get('start_command', ''),
                        'wait_start_command': bool(emulator_data.get('wait_start_command', False)),
                        'stop_command': emulator_data.get('stop_command', ''),
                        'running_command': emulator_data.get('running_command', ''),
                    }
                    # 连接方式：有 adb_port 且 run_adb_connect → TCP；否则 USB
                    run_adb_connect = bool(emulator_data.get('run_adb_connect', True))
                    adb_port = emulator_data.get('adb_port')
                    if run_adb_connect and adb_port is not None:
                        connection = {
                            'type': 'tcp',
                            'ip': emulator_data.get('adb_ip') or '127.0.0.1',
                            'port': adb_port,
                            'run_adb_connect': True,
                            'device_serial': emulator_data.get('device_serial', ''),
                        }
                    else:
                        connection = {
                            'type': 'usb',
                            'device_serial': emulator_data.get('device_serial', ''),
                        }

                elif emulator == 'physical_android':
                    lifecycle = {'type': 'none'}
                    connection = {
                        'type': 'usb',
                        'device_serial': emulator_data.get('device_serial', ''),
                    }

                else:
                    # 未知类型，保守处理
                    lifecycle = {'type': 'none'}
                    connection = {'type': 'usb', 'device_serial': ''}

                data['device'] = {
                    'lifecycle': lifecycle,
                    'connection': connection,
                    'control_impl': control_impl,
                    'scrcpy_virtual_display': scrcpy_virtual_display,
                    'resolution_method': resolution_method,
                }
                data['game'] = game
                data['version'] = 3

                file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
                ctx.messages.append(MigrationMessage(
                    text="设备配置结构升级（device.*）",
                    old_version="26.05 (v2)",
                    new_version="26.05 (v3)"
                ))
            except Exception as e:
                ctx.messages.append(MigrationMessage(
                    text=f"迁移配置 {file.name} 时出错: {e}",
                    level='warning'
                ))
                logger.exception(f"Error migrating config {file.name}")


class ProfileV3ToV4(MigrationStep):
    """
    将任务启用开关从 scheduler.* 下沉到各任务自己的 config 中，
    并将所有任务配置归入顶层 tasks.* 嵌套结构。

    旧结构：
        live.*  /  challenge_live.*  /  cm.*  /  event_shop.*
        scheduler.{task}_enabled

    新结构：
        tasks.solo_live.enabled / tasks.challenge_live.enabled / ...
    """

    def check_needed(self, ctx: MigrationContext) -> bool:
        for file in ctx.config_dir.glob('*.json'):
            if file.stem == '_shared':
                continue
            try:
                data = json.loads(file.read_text(encoding='utf-8'))
                if data.get('version', 1) < 4:
                    return True
            except Exception:
                continue
        return False

    def apply(self, ctx: MigrationContext) -> None:
        for file in ctx.config_dir.glob('*.json'):
            if file.stem == '_shared':
                continue
            try:
                data = json.loads(file.read_text(encoding='utf-8'))
                if data.get('version', 1) >= 4:
                    continue

                sched = data.pop('scheduler', {})
                old_live = data.pop('live', {})

                tasks: dict = {}

                tasks['start_game'] = {'enabled': sched.get('start_game_enabled', True)}

                old_live['enabled'] = sched.get('solo_live_enabled', True)
                tasks['solo_live'] = old_live

                challenge_live = data.pop('challenge_live', {})
                challenge_live['enabled'] = sched.get('challenge_live_enabled', True)
                tasks['challenge_live'] = challenge_live

                tasks['activity_story'] = {'enabled': sched.get('activity_story_enabled', False)}

                cm = data.pop('cm', {})
                cm['enabled'] = sched.get('cm_enabled', True)
                tasks['cm'] = cm

                tasks['gift'] = {'enabled': sched.get('gift_enabled', True)}
                tasks['area_convos'] = {'enabled': sched.get('area_convos_enabled', False)}

                event_shop = data.pop('event_shop', {})
                event_shop['enabled'] = sched.get('event_shop_enabled', False)
                tasks['event_shop'] = event_shop

                tasks['mission_rewards'] = {'enabled': sched.get('mission_rewards_enabled', True)}

                data['tasks'] = tasks

                dev = data.get('developer', {})
                dev['dump_sekai_home_enabled'] = sched.get('dump_sekai_home_enabled', False)
                data['developer'] = dev

                data['version'] = 4
                file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
                ctx.messages.append(MigrationMessage(
                    text="任务配置结构升级（tasks.*）",
                    old_version="26.05b2 (v3)",
                    new_version="26.06b1 (v4)"
                ))
            except Exception as e:
                ctx.messages.append(MigrationMessage(
                    text=f"迁移配置 {file.name} 时出错: {e}",
                    level='warning'
                ))
                logger.exception(f"Error migrating config {file.name}")
