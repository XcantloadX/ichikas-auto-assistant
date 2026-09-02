from __future__ import annotations

import json
import logging
import threading
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtQml import QJSValue

<<<<<<< HEAD
from iaa.config.base import IaaConfig

from .config_draft import ConfigDraft
=======
from iaa.application.framework.dsl import RuntimeEngine, SnapshotState
from iaa.i18n import translate, translate_error
from ..forms.context import FormContext
from ..forms.settings_form import build_settings_form
>>>>>>> feat/en-server

if TYPE_CHECKING:
    from iaa.application.service.iaa_service import IaaService
    from iaa.application.qt.controllers.i18n_controller import I18nController

logger = logging.getLogger(__name__)


def _normalize_qt_value(value: Any) -> Any:
    """把 QML 传入的 QJSValue/QVariant 递归归一化为纯 Python 对象。"""
    if isinstance(value, QJSValue):
        return _normalize_qt_value(value.toVariant())
    if isinstance(value, list):
        return [_normalize_qt_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_normalize_qt_value(item) for item in value)
    if isinstance(value, dict):
        return {key: _normalize_qt_value(item) for key, item in value.items()}
    return value


class SettingsController(QObject):
    """设置控制器：草稿模式（kaa 风格表单）。

    设置页 QML 直写表单字段：``config`` 暴露 base+dirty 合并视图，
    ``setField``/``setListField`` 写入草稿，``save`` 归一化+校验+写盘。
    """

    configChanged = Signal()
    dirtyChanged = Signal(bool)
    operationSucceeded = Signal(str)
    operationFailed = Signal(str)
    configSwitched = Signal()
    currentProfileChanged = Signal(str)
    profilesChanged = Signal()
    emulatorInstancesReady = Signal(str, str)
    emulatorNotInstalled = Signal(str)

<<<<<<< HEAD
    def __init__(self, iaa_service: 'IaaService', parent=None) -> None:
        super().__init__(parent)
        self._iaa = iaa_service
        self._last_issues: list[dict[str, Any]] = []
        self._draft = ConfigDraft(self._base_config())

    def _base_config(self) -> dict[str, Any]:
        return self._iaa.config.conf.model_dump(mode='json')

    def _reload(self) -> None:
        """从 live 配置重建草稿（切换/新建/删除/重命名配置后调用）。"""
        self._draft = ConfigDraft(self._base_config())
        self._last_issues = []
        self.configChanged.emit()
        self.dirtyChanged.emit(False)

    # ── 表单读写 ─────────────────────────────────────────────────────────────
=======
    def __init__(self, iaa_service: 'IaaService', i18n_controller: 'I18nController', parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._iaa = iaa_service
        self._i18n = i18n_controller
        self._mumu_instances: list[dict[str, Any]] = []
        self._rebuild_form(reset_mumu_instances=True)
        self._state = SnapshotState(
            self._make_context(),
            snapshot_fn=self._snapshot_context,
            restore_fn=self._restore_context,
            stable_dump_fn=self._stable_dump_snapshot,
        )
        self._runtime: dict[str, Any] = {}
        self._recompute_runtime()

    def _default_mumu_instance_item(self) -> dict[str, Any]:
        from iaa.i18n import tstr
        return {'value': '', 'label': tstr('settings.option.mumu_instance.default')}

    def _rebuild_form(self, *, reset_mumu_instances: bool = False) -> None:
        if reset_mumu_instances:
            self._mumu_instances[:] = [self._default_mumu_instance_item()]
        self._spec, self._form_hooks = build_settings_form(
            self._mumu_instances,
            on_mumu_refresh=self._action_mumu_refresh,
            on_reset_resolution=self._action_reset_resolution,
        )
        self._engine = RuntimeEngine(self._spec)

    @staticmethod
    def _snapshot_context(context: FormContext) -> dict[str, Any]:
        return {
            'conf': context.conf.model_copy(deep=True),
        }

    @staticmethod
    def _restore_context(context: FormContext, snapshot: dict[str, Any]) -> None:
        context.conf = snapshot['conf']

    @staticmethod
    def _stable_dump_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
        conf = snapshot['conf']
        return {
            'conf': conf.model_dump(mode='json'),
        }

    def _make_context(self) -> FormContext:
        return FormContext(
            conf=self._iaa.config.conf,
            shared=self._iaa.config.shared,
        )

    def _tr(self, key: str, **kwargs: object) -> str:
        text = translate(self._iaa.config.shared.interface.language, key)
        return text.format(**kwargs) if kwargs else text

    def _sync_context_back(self) -> None:
        self._iaa.config.conf = self._state.context.conf
        self._iaa.config.shared = self._state.context.shared

    def _reload(self) -> None:
        self._rebuild_form(reset_mumu_instances=True)
        self._state.reset(self._make_context())
        self._recompute_runtime()
        self.runtimeChanged.emit()
        self.dirtyChanged.emit(self._state.dirty)

    def _recompute_runtime(self) -> None:
        language = self._i18n.language
        runtime = self._engine.build_runtime(self._state.context, language)
        runtime['dirty'] = self._state.dirty
        runtime['profileName'] = self._iaa.config.current_config_name
        self._runtime = runtime
>>>>>>> feat/en-server

    @Property('QVariantMap', notify=configChanged)
    def config(self) -> dict[str, Any]:
        """草稿视图：base + dirty 合并。"""
        return self._draft.view()

    @Slot(str, 'QVariant')
    def setField(self, path: str, value) -> None:
        """字段进草稿。path 为完整 dot path（相对 conf 根）。"""
        self._draft.set(path, _normalize_qt_value(value))
        self.configChanged.emit()
        self.dirtyChanged.emit(self._draft.is_dirty())

<<<<<<< HEAD
    @Slot(str, 'QVariantList')
    def setListField(self, path: str, value) -> None:
        """列表字段进草稿。QML 数组应走此 Slot 以触发 Qt 类型转换。"""
        self._draft.set(path, list(_normalize_qt_value(value)))
        self.configChanged.emit()
        self.dirtyChanged.emit(self._draft.is_dirty())

    @Slot(result=bool)
    def isDirty(self) -> bool:
        return self._draft.is_dirty()
=======
        for field_id, new_field in new_field_map.items():
            if old_field_map.get(field_id) != new_field:
                self.fieldUpdated.emit(field_id, json.dumps(new_field, ensure_ascii=False))

        self.dirtyChanged.emit(self._state.dirty)

    def _get_mumu_instance_id(self) -> str:
        from iaa.config.schemas import MuMuDevice
        lc = self._state.context.conf.device.lifecycle
        if isinstance(lc, MuMuDevice):
            return lc.instance_id or ''
        return ''

    def _set_mumu_instance_id(self, selected_id: str) -> None:
        from iaa.config.schemas import MuMuDevice
        lc = self._state.context.conf.device.lifecycle
        if isinstance(lc, MuMuDevice):
            lc.instance_id = selected_id or None

    def _refresh_mumu_runtime(self, preferred_id: str = '', show_notice: bool = True) -> None:
        from iaa.config.schemas import MuMuDevice
        lc = self._state.context.conf.device.lifecycle
        emulator = lc.type if isinstance(lc, MuMuDevice) else ''
        payload = json.loads(self._build_mumu_instances_payload(emulator, preferred_id))
        raw_items: list[dict[str, Any]] = payload.get('items', [])
        # Replace the placeholder default item (resolved string) with the TStr version
        # so that the label updates automatically when the language changes.
        if raw_items and str(raw_items[0].get('value', '')) == '':
            raw_items[0] = self._default_mumu_instance_item()
        self._mumu_instances[:] = raw_items or [self._default_mumu_instance_item()]

        selected_id = str(payload.get('selectedId', '') or '')
        if selected_id != self._get_mumu_instance_id():
            self._set_mumu_instance_id(selected_id)

        self._sync_context_back()
        self._recompute_runtime()
        self.runtimeChanged.emit()
        self.dirtyChanged.emit(self._state.dirty)

        if show_notice:
            if payload.get('ok'):
                self.operationSucceeded.emit(
                    str(payload.get('statusText') or self._tr('settings.status.mumu_refreshed'))
                )
            else:
                self.operationFailed.emit(
                    str(payload.get('statusText') or self._tr('settings.status.mumu_refresh_failed_plain'))
                )

    def _build_mumu_instances_payload(self, emulator: str, preferred_id: str = '') -> str:
        default_item_str = {'value': '', 'label': self._tr('settings.option.mumu_instance.default')}
        if emulator not in {'mumu', 'mumu_v5'}:
            return json.dumps(
                {
                    'ok': True,
                    'items': [default_item_str],
                    'selectedId': '',
                    'statusText': self._tr('settings.status.mumu_no_instance_needed'),
                },
                ensure_ascii=False,
            )
        try:
            from kotonebot.client.host import Mumu12Host, Mumu12V5Host

            host_cls = Mumu12Host if emulator == 'mumu' else Mumu12V5Host
            instances = host_cls.list()
            saved_id = ''
            conf = self._state.context.conf
            lc = conf.device.lifecycle
            from iaa.config.schemas import MuMuDevice
            if (
                isinstance(lc, MuMuDevice)
                and lc.type == emulator
                and lc.instance_id
            ):
                saved_id = lc.instance_id
            items = [default_item_str] + [
                {'value': str(instance.id), 'label': f'[{instance.id}] {instance.name}'}
                for instance in instances
            ]
            ids = {item['value'] for item in items}
            selected_id = ''
            if preferred_id and preferred_id in ids:
                selected_id = preferred_id
            elif saved_id and saved_id in ids:
                selected_id = saved_id
            status = self._tr('settings.status.mumu_loaded', count=len(instances))
            if not instances:
                status = self._tr('settings.status.mumu_not_found')
            elif selected_id:
                status += self._tr('settings.status.mumu_selected', selected_id=selected_id)
            return json.dumps(
                {
                    'ok': True,
                    'items': items,
                    'selectedId': selected_id,
                    'statusText': status,
                },
                ensure_ascii=False,
            )
        except Exception as exc:  # noqa: BLE001
            return json.dumps(
                {
                    'ok': False,
                    'items': [default_item_str],
                    'selectedId': '',
                    'statusText': self._tr('settings.status.mumu_refresh_failed', error=exc),
                },
                ensure_ascii=False,
            )

    @Slot(result=str)
    def getRuntime(self) -> str:
        return json.dumps(self._runtime, ensure_ascii=False)

    @Slot(result=bool)
    def isDirty(self) -> bool:
        return self._state.dirty

    @Slot(result=str)
    def currentProfileName(self) -> str:
        return self._iaa.config.current_config_name

    @Slot(result=str)
    def profilesJson(self) -> str:
        profiles = [{'value': name, 'label': name} for name in self._iaa.config.list()]
        return json.dumps({'profiles': profiles}, ensure_ascii=False)

    @Slot(str, 'QVariant')
    def setValue(self, field_id: str, value: Any) -> None:
        try:
            field = self._engine.find_field(field_id)
            if field is None:
                raise KeyError(f'Unknown field id: {field_id}')

            value = _normalize_qt_value(value)
            field.ref.set(self._state.context, value)
            if field.on_change:
                field.on_change(self._state.context, value)
            for hook in self._form_hooks:
                hook(self._state.context)

            self._sync_context_back()
            old_runtime = self._runtime
            self._recompute_runtime()
            self._emit_updates(old_runtime)
        except Exception as exc:  # noqa: BLE001
            self.operationFailed.emit(self._tr('notice.field_set_failed', error=exc))

    @Slot(str, str, str)
    def triggerAction(self, field_id: str, action: str, payload_json: str = '{}') -> None:
        _ = payload_json
        field = self._engine.find_field(field_id)
        if field is None:
            self.operationFailed.emit(self._tr('settings.error.unknown_field', field=field_id))
            return
        callback = field.actions.get(action)
        if callback is None:
            self.operationFailed.emit(self._tr('settings.error.unsupported_action', field=field_id, action=action))
            return
        try:
            callback(self._state.context)
        except Exception as exc:  # noqa: BLE001
            self.operationFailed.emit(translate_error(self._i18n.language, exc))

    def _action_mumu_refresh(self, _ctx: object) -> None:
        preferred_id = self._get_mumu_instance_id()
        self._refresh_mumu_runtime(preferred_id=preferred_id, show_notice=True)

    def _action_reset_resolution(self, _ctx: object) -> None:
        self.resetResolution()

    @Slot(result=bool)
    def save(self) -> bool:
        try:
            self._sync_context_back()
            self._iaa.config.save()
            self._state.mark_saved()
            self._recompute_runtime()
            self.runtimeChanged.emit()
            self.dirtyChanged.emit(self._state.dirty)
            self.operationSucceeded.emit(self._tr('notice.save_success'))
            return True
        except Exception as exc:  # noqa: BLE001
            self.operationFailed.emit(self._tr('notice.save_failed', error=exc))
            return False
>>>>>>> feat/en-server

    @Slot(result=bool)
    def discard(self) -> bool:
        """丢弃未保存编辑。"""
        self._draft.discard()
        self.configChanged.emit()
        self.dirtyChanged.emit(False)
        return True

<<<<<<< HEAD
    @Slot(result=bool)
    def save(self) -> bool:
        """提交草稿：归一化 → 校验 → 写盘。"""
        if not self._draft.is_dirty():
            self.operationSucceeded.emit('没有需要保存的更改')
            return True
        merged = self._normalize(self._draft.view())
        issues = self._collect_issues(merged)
        errors = [i for i in issues if i.get('severity') == 'error']
        if errors:
            self._last_issues = issues
            self.operationFailed.emit('；'.join(i['message'] for i in errors))
            return False
        try:
            candidate = IaaConfig.model_validate(merged)
        except Exception as exc:  # noqa: BLE001
            logger.warning('Settings draft validation failed: %s', exc)
            self._last_issues = [{'severity': 'error', 'field': None, 'message': f'配置结构无效：{exc}'}]
            self.operationFailed.emit(f'配置结构无效：{exc}')
            return False
        try:
            self._iaa.config.conf = candidate
            self._iaa.config.save()
        except Exception as exc:  # noqa: BLE001
            logger.exception('Failed to save settings')
            self.operationFailed.emit(f'保存失败：{exc}')
            return False
        self._draft = ConfigDraft(candidate.model_dump(mode='json'))
        self._last_issues = []
        self.configChanged.emit()
        self.dirtyChanged.emit(False)
        self.operationSucceeded.emit('保存成功')
        return True

    @Slot(result=str)
    def validateJson(self) -> str:
        """校验当前草稿（归一化后），返回 issue 列表 JSON。不提交、不写盘。"""
        try:
            merged = self._normalize(self._draft.view())
            issues = self._collect_issues(merged)
            try:
                IaaConfig.model_validate(merged)
            except Exception as exc:  # noqa: BLE001
                issues = issues + [{'severity': 'error', 'field': None, 'message': f'配置结构无效：{exc}'}]
            return json.dumps(issues, ensure_ascii=False)
        except Exception as exc:  # noqa: BLE001
            logger.exception('Failed to validate settings draft')
            return json.dumps(
                [{'severity': 'error', 'field': None, 'message': f'校验失败：{exc}'}],
                ensure_ascii=False,
            )

    # ── 归一化与校验 ─────────────────────────────────────────────────────────

    @staticmethod
    def _normalize(data: dict[str, Any]) -> dict[str, Any]:
        """对合并后的草稿 dict 做跨字段归一化（在 copy 上操作）。"""
        device = data.get('device', {})
        lifecycle = device.get('lifecycle', {})
        connection = device.get('connection', {})
        lc_type = lifecycle.get('type', 'none')
        conn_type = connection.get('type', 'usb')

        # connection 约束：mumu/avd 强制 auto，custom 强制 tcp，none 强制 usb
        if lc_type in ('mumu', 'mumu_v5', 'avd'):
            if conn_type != 'auto':
                connection['type'] = 'auto'
        elif lc_type == 'custom':
            if conn_type == 'auto':
                connection['type'] = 'tcp'
        elif lc_type == 'none':
            if conn_type == 'auto':
                connection['type'] = 'usb'

        # control_impl 约束
        impl = device.get('control_impl', 'adb')
        if impl == 'nemu_ipc' and lc_type not in ('mumu', 'mumu_v5'):
            impl = 'adb'
        elif impl == 'qemu_grpc' and lc_type != 'avd':
            impl = 'adb'
        device['control_impl'] = impl
        if impl == 'qemu_grpc':
            device['resolution_method'] = 'keep'

        # game 联动约束
        game = data.get('game', {})
        if game.get('server', 'jp') != 'jp':
            game['link_account'] = 'no'

        # 字符串 → 类型归一化
        if connection.get('type') == 'tcp':
            port = connection.get('port')
            if port is not None and not isinstance(port, bool) and not isinstance(port, int):
                text = str(port).strip()
                if text.isdigit():
                    connection['port'] = int(text)
                elif text == '':
                    connection['port'] = None

        cm = data.get('tasks', {}).get('cm', {})
        wa = cm.get('watch_ad_wait_sec')
        if not isinstance(wa, bool) and not isinstance(wa, int):
            wtext = str(wa or '').strip()
            if wtext.isdigit():
                cm['watch_ad_wait_sec'] = int(wtext)

        # nullable 字符串兜底（QML 侧已处理，此处作为安全网）
        solo = data.get('tasks', {}).get('solo_live', {})
        if solo.get('song_name') in (None, '', '保持不变'):
            solo['song_name'] = None
        if solo.get('ap_multiplier') == '保持现状':
            solo['ap_multiplier'] = None
        if lc_type in ('mumu', 'mumu_v5') and lifecycle.get('instance_id') == '':
            lifecycle['instance_id'] = None
        if lc_type == 'avd':
            if lifecycle.get('avd_name') == '':
                lifecycle['avd_name'] = None
            if lifecycle.get('sdk_path') == '':
                lifecycle['sdk_path'] = None
        if lc_type == 'custom' and lifecycle.get('start_command') is not None:
            lifecycle['start_command'] = str(lifecycle['start_command']).strip()

        return data

    @staticmethod
    def _collect_issues(data: dict[str, Any]) -> list[dict[str, Any]]:
        """收集业务校验问题（归一化后的 dict）。"""
        issues: list[dict[str, Any]] = []
        device = data.get('device', {})
        lifecycle = device.get('lifecycle', {})
        connection = device.get('connection', {})

        if connection.get('type') == 'tcp':
            port = connection.get('port')
            text = '' if port is None else str(port).strip()
            if not text:
                issues.append({'severity': 'error', 'field': 'device.connection.port', 'message': '端口不能为空'})
            elif not text.isdigit():
                issues.append({'severity': 'error', 'field': 'device.connection.port', 'message': '端口必须是数字'})

        if lifecycle.get('type') == 'custom':
            start = str(lifecycle.get('start_command') or '').strip()
            if not start:
                issues.append({'severity': 'error', 'field': 'device.lifecycle.start_command', 'message': '启动命令不能为空'})

        cm = data.get('tasks', {}).get('cm', {})
        wa = cm.get('watch_ad_wait_sec')
        wtext = '' if wa is None else str(wa).strip()
        if not wtext:
            issues.append({'severity': 'error', 'field': 'tasks.cm.watch_ad_wait_sec', 'message': 'CM 广告等待秒数不能为空'})
        elif not wtext.isdigit():
            issues.append({'severity': 'error', 'field': 'tasks.cm.watch_ad_wait_sec', 'message': 'CM 广告等待秒数必须是数字'})
        elif int(wtext) <= 0:
            issues.append({'severity': 'error', 'field': 'tasks.cm.watch_ad_wait_sec', 'message': 'CM 广告等待秒数必须大于 0'})

        return issues

    # ── 表单选项数据 ─────────────────────────────────────────────────────────

    @Slot(result=str)
    def lifecycleOptionsJson(self) -> str:
        """平台过滤后的设备类型选项。"""
        import platform as _platform

        from ..models import LIFECYCLE_TYPE_DISPLAY_MAP

        options = [
            {'value': k, 'label': v}
            for k, v in LIFECYCLE_TYPE_DISPLAY_MAP.items()
            if not (k in {'mumu', 'mumu_v5'} and _platform.system() != 'Windows')
            and not (k == 'playcover' and _platform.system() != 'Darwin')
        ]
        return json.dumps(options, ensure_ascii=False)

    @Slot(result=str)
    def connectionOptionsJson(self) -> str:
        from ..models import CONNECTION_TYPE_DISPLAY_MAP
        return json.dumps(
            [{'value': k, 'label': v} for k, v in CONNECTION_TYPE_DISPLAY_MAP.items()],
            ensure_ascii=False,
        )

    @Slot(result=str)
    def serverOptionsJson(self) -> str:
        from ..models import SERVER_DISPLAY_MAP
        return json.dumps(
            [{'value': k, 'label': v} for k, v in SERVER_DISPLAY_MAP.items()],
            ensure_ascii=False,
        )

    @Slot(result=str)
    def linkOptionsJson(self) -> str:
        from ..models import LINK_DISPLAY_MAP
        return json.dumps(
            [{'value': k, 'label': v} for k, v in LINK_DISPLAY_MAP.items()],
            ensure_ascii=False,
        )

    @Slot(result=str)
    def controlImplOptionsJson(self) -> str:
        from ..models import CONTROL_IMPL_DISPLAY_MAP
        return json.dumps(
            [{'value': k, 'label': v} for k, v in CONTROL_IMPL_DISPLAY_MAP.items()],
            ensure_ascii=False,
        )

    @Slot(result=str)
    def resolutionOptionsJson(self) -> str:
        from ..models import RESOLUTION_METHOD_DISPLAY_MAP
        return json.dumps(
            [{'value': k, 'label': v} for k, v in RESOLUTION_METHOD_DISPLAY_MAP.items()],
            ensure_ascii=False,
        )

    @Slot(result=str)
    def challengeCharactersJson(self) -> str:
        from ..models import challenge_character_groups_for_ui
        return json.dumps(challenge_character_groups_for_ui(), ensure_ascii=False)

    @Slot(result=str)
    def challengeAwardsJson(self) -> str:
        from ..models import challenge_awards_for_ui
        return json.dumps(challenge_awards_for_ui(), ensure_ascii=False)

    @Slot(result=str)
    def eventShopItemsJson(self) -> str:
        from iaa.definitions.enums import ShopItem
        return json.dumps(
            [{'value': item.value, 'label': item.display('cn')} for item in ShopItem],
            ensure_ascii=False,
        )

    # ── 设备实例枚举 ─────────────────────────────────────────────────────────

    @Slot(str)
    def listEmulatorInstancesAsync(self, emulator_type: str) -> None:
        """后台枚举模拟器实例（mumu / mumu_v5 / avd），结果经信号返回。"""

        def _run() -> None:
            try:
                options = self._enumerate_instances(emulator_type)
                self.emulatorInstancesReady.emit(
                    emulator_type,
                    json.dumps(options, ensure_ascii=False),
                )
            except Exception as exc:  # noqa: BLE001
                logger.exception('Failed to enumerate instances for %s', emulator_type)
                self.operationFailed.emit(f'刷新失败：{exc}')
                self.emulatorInstancesReady.emit(emulator_type, '[]')

        threading.Thread(target=_run, daemon=True).start()

    def _enumerate_instances(self, emulator_type: str) -> list[dict[str, Any]]:
        """返回 {value, label} 选项列表（含默认占位项）。"""
        if emulator_type in ('mumu', 'mumu_v5'):
            from kotonebot.client.host import Mumu12Host, Mumu12V5Host

            from ..models import DEFAULT_MUMU_INSTANCE_LABEL

            host_cls = Mumu12V5Host if emulator_type == 'mumu_v5' else Mumu12Host
            instances = host_cls.list()
            return [{'value': '', 'label': DEFAULT_MUMU_INSTANCE_LABEL}] + [
                {'value': str(inst.id), 'label': f'[{inst.id}] {inst.name}'}
                for inst in instances
            ]
        if emulator_type == 'avd':
            from iaa.application.service.avd import AvdHost

            sdk_path = self._draft.get('device.lifecycle.sdk_path')
            host = AvdHost(sdk_path=sdk_path)
            instances = host.list()
            return [{'value': '', 'label': '（默认第一个）'}] + [
                {'value': inst._avd_name,
                 'label': f'{inst._avd_name}{"  [运行中]" if inst.adb_serial else ""}'}
                for inst in instances
            ]
        return []

    # ── 分辨率 ───────────────────────────────────────────────────────────────
=======
    @Slot(str)
    def setLanguage(self, language: str) -> None:
        self._state.context.shared = self._iaa.config.shared
        self._recompute_runtime()
        self.runtimeChanged.emit()
        self.dirtyChanged.emit(self._state.dirty)
>>>>>>> feat/en-server

    @Slot()
    def resetResolution(self) -> None:
        device = self._iaa.scheduler.device
        if device is None:
            def on_success() -> None:
                self._do_reset_resolution()

            def on_error(exc: Exception) -> None:
                self.operationFailed.emit(self._tr('settings.status.device_connect_failed', error=exc))

            self._iaa.scheduler.connect_device(on_success=on_success, on_error=on_error)
            return
        self._do_reset_resolution()

    def _do_reset_resolution(self) -> None:
        device = self._iaa.scheduler.device
        if device is None:
            self.operationFailed.emit(self._tr('settings.status.device_not_connected'))
            return
        try:
            device.commands.adb_shell('wm size reset')
            self.operationSucceeded.emit(self._tr('settings.status.resolution_restored'))
        except Exception as exc:  # noqa: BLE001
            self.operationFailed.emit(self._tr('settings.status.resolution_restore_failed', error=exc))

    # ── 配置文件管理 ─────────────────────────────────────────────────────────

    @Slot(result=str)
    def currentProfileName(self) -> str:
        return self._iaa.config.current_config_name

    @Slot(result=str)
    def profilesJson(self) -> str:
        profiles = [{'value': name, 'label': name} for name in self._iaa.config.list()]
        return json.dumps({'profiles': profiles}, ensure_ascii=False)

    @Slot(str, result=bool)
    def switchProfile(self, name: str) -> bool:
        try:
            self._iaa.config.switch_config(name)
            self._reload()
            self.configSwitched.emit()
            self.currentProfileChanged.emit(self._iaa.config.current_config_name)
            self.operationSucceeded.emit(self._tr('settings.status.profile_switched', name=name))
            return True
        except RuntimeError as e:
            self.operationFailed.emit(translate_error(self._i18n.language, e))
            return False
        except Exception as exc:  # noqa: BLE001
            self.operationFailed.emit(self._tr('settings.status.profile_switch_failed', error=exc))
            return False

    @Slot(str, result=bool)
    def createProfile(self, name: str) -> bool:
        try:
            self._iaa.config.create(name)
            self._reload()
            self.configSwitched.emit()
            self.profilesChanged.emit()
            self.currentProfileChanged.emit(self._iaa.config.current_config_name)
            self.operationSucceeded.emit(self._tr('settings.status.profile_created', name=name))
            return True
        except Exception as exc:  # noqa: BLE001
            self.operationFailed.emit(self._tr('settings.status.profile_create_failed', error=exc))
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
            self.operationSucceeded.emit(self._tr('settings.status.profile_deleted', name=name))
            return True
        except FileNotFoundError:
            self.operationFailed.emit(self._tr('settings.status.profile_missing', name=name))
            return False
        except RuntimeError as e:
            self.operationFailed.emit(translate_error(self._i18n.language, e))
            return False
        except Exception as exc:  # noqa: BLE001
            self.operationFailed.emit(self._tr('settings.status.profile_delete_failed', error=exc))
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
            self.operationSucceeded.emit(self._tr('settings.status.profile_renamed', name=new_name))
            return True
        except FileNotFoundError:
            self.operationFailed.emit(self._tr('settings.status.profile_missing', name=old_name))
            return False
        except FileExistsError:
            self.operationFailed.emit(self._tr('settings.status.profile_exists', name=new_name))
            return False
        except Exception as exc:  # noqa: BLE001
            self.operationFailed.emit(self._tr('settings.status.profile_rename_failed', error=exc))
            return False
