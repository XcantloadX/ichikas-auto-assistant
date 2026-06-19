from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from typing_extensions import override

from PySide6.QtCore import Signal, Slot

from ..forms.context import FormContext
from ..forms.settings_form import build_settings_form
from .form_controller import FormController

if TYPE_CHECKING:
    from iaa.application.service.iaa_service import IaaService

logger = logging.getLogger(__name__)


class SettingsController(FormController):
    configSwitched = Signal()
    currentProfileChanged = Signal(str)
    profilesChanged = Signal()

    def __init__(self, iaa_service: 'IaaService', parent=None) -> None:
        self._iaa = iaa_service
        spec, form_hooks = build_settings_form(
            on_reset_resolution=self._action_reset_resolution,
        )
        super().__init__(
            spec,
            form_hooks,
            self._make_context(),
            snapshot_fn=self._snapshot_context,
            restore_fn=self._restore_context,
            stable_dump_fn=self._stable_dump_snapshot,
            parent=parent,
        )

    # ── context 生命周期 ───────────────────────────────────────────────────────

    @staticmethod
    def _snapshot_context(context: FormContext) -> dict[str, Any]:
        return {
            'conf': context.conf.model_copy(deep=True),
            'shared': context.shared.model_copy(deep=True),
        }

    @staticmethod
    def _restore_context(context: FormContext, snapshot: dict[str, Any]) -> None:
        context.conf = snapshot['conf']
        context.shared = snapshot['shared']

    @staticmethod
    def _stable_dump_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
        return {
            'conf': snapshot['conf'].model_dump(mode='json'),
            'shared': snapshot['shared'].model_dump(mode='json'),
        }

    @override
    def _make_context(self) -> FormContext:
        return FormContext(
            conf=self._iaa.config.conf,
            shared=self._iaa.config.shared,
        )

    @override
    def _sync_context_back(self) -> None:
        self._iaa.config.conf = self._state.context.conf
        self._iaa.config.shared = self._state.context.shared

    # ── Slot ──────────────────────────────────────────────────────────────────

    @Slot(result=str)
    def currentProfileName(self) -> str:
        return self._iaa.config.current_config_name

    @Slot(result=str)
    def profilesJson(self) -> str:
        import json
        profiles = [{'value': name, 'label': name} for name in self._iaa.config.list()]
        return json.dumps({'profiles': profiles}, ensure_ascii=False)

    @Slot(result=bool)
    def save(self) -> bool:
        try:
            self._sync_context_back()
            self._iaa.config.save()
            self._state.mark_saved()
            self._recompute_runtime()
            self.runtimeChanged.emit()
            self.dirtyChanged.emit(self._state.dirty)
            self.operationSucceeded.emit('保存成功')
            return True
        except Exception as exc:  # noqa: BLE001
            self.operationFailed.emit(f'保存失败：{exc}')
            return False

    @Slot()
    def resetResolution(self) -> None:
        device = self._iaa.scheduler.device
        if device is None:
            def on_success() -> None:
                self._do_reset_resolution()

            def on_error(exc: Exception) -> None:
                self.operationFailed.emit(f'连接失败：{exc}')

            self._iaa.scheduler.connect_device(on_success=on_success, on_error=on_error)
            return
        self._do_reset_resolution()

    def _do_reset_resolution(self) -> None:
        device = self._iaa.scheduler.device
        if device is None:
            self.operationFailed.emit('设备尚未连接')
            return
        try:
            device.commands.adb_shell('wm size reset')
            self.operationSucceeded.emit('已恢复分辨率')
        except Exception as exc:  # noqa: BLE001
            self.operationFailed.emit(f'恢复失败：{exc}')

    def _action_reset_resolution(self, _ctx: object) -> None:
        self.resetResolution()

    # ── 配置文件管理 ───────────────────────────────────────────────────────────

    @Slot(str, result=bool)
    def switchProfile(self, name: str) -> bool:
        try:
            self._iaa.config.switch_config(name)
            self._reload()
            self.configSwitched.emit()
            self.currentProfileChanged.emit(self._iaa.config.current_config_name)
            self.operationSucceeded.emit(f'已切换到配置: {name}')
            return True
        except RuntimeError as e:
            self.operationFailed.emit(str(e))
            return False
        except Exception as exc:  # noqa: BLE001
            self.operationFailed.emit(f'切换失败：{exc}')
            return False

    @Slot(str, result=bool)
    def createProfile(self, name: str) -> bool:
        try:
            self._iaa.config.create(name)
            self._reload()
            self.configSwitched.emit()
            self.profilesChanged.emit()
            self.currentProfileChanged.emit(self._iaa.config.current_config_name)
            self.operationSucceeded.emit(f'已创建并切换到配置: {name}')
            return True
        except Exception as exc:  # noqa: BLE001
            self.operationFailed.emit(f'创建失败：{exc}')
            return False

    @Slot(str, result=bool)
    def deleteProfile(self, name: str) -> bool:
        try:
            deleted_current = self._iaa.config.delete(name)
            self._reload()
            self.profilesChanged.emit()
            if deleted_current:
                self.configSwitched.emit()
                self.currentProfileChanged.emit(self._iaa.config.current_config_name)
            self.operationSucceeded.emit(f'已删除配置: {name}')
            return True
        except FileNotFoundError:
            self.operationFailed.emit(f'配置不存在: {name}')
            return False
        except RuntimeError as e:
            self.operationFailed.emit(str(e))
            return False
        except Exception as exc:  # noqa: BLE001
            self.operationFailed.emit(f'删除失败：{exc}')
            return False

    @Slot(str, str, result=bool)
    def renameProfile(self, old_name: str, new_name: str) -> bool:
        try:
            renamed_current = self._iaa.config.rename(old_name, new_name)
            self._reload()
            self.profilesChanged.emit()
            if renamed_current:
                self.configSwitched.emit()
                self.currentProfileChanged.emit(self._iaa.config.current_config_name)
            self.operationSucceeded.emit(f'已重命名为: {new_name}')
            return True
        except FileNotFoundError:
            self.operationFailed.emit(f'配置不存在: {old_name}')
            return False
        except FileExistsError:
            self.operationFailed.emit(f'配置名称已存在: {new_name}')
            return False
        except Exception as exc:  # noqa: BLE001
            self.operationFailed.emit(f'重命名失败：{exc}')
            return False
