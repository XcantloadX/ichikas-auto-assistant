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
                
                if changed:
                    ctx.messages.append(MigrationMessage(
                        text="自定义模拟器配置升级",
                        old_version="26.04b5",
                        new_version="26.05b1"
                    ))
            except Exception as e:
                ctx.messages.append(MigrationMessage(
                    text=f"迁移配置 {file.name} 时出错: {e}",
                    level='warning'
                ))
                logger.exception(f"Error migrating config {file.name}")
