from __future__ import annotations

from typing import Literal

GuiLanguage = Literal['zh_CN', 'en_US']

DEFAULT_LANGUAGE: GuiLanguage = 'zh_CN'
SUPPORTED_LANGUAGES: tuple[GuiLanguage, ...] = ('zh_CN', 'en_US')

_TRANSLATIONS: dict[GuiLanguage, dict[str, str]] = {
    'zh_CN': {
        'nav.control': '控制',
        'nav.config': '配置',
        'nav.preferences': '偏好',
        'nav.logs': '日志',
        'nav.about': '关于',
        'common.save': '保存',
        'common.cancel': '取消',
        'common.ok': '确定',
        'common.close': '关闭',
        'common.create': '新建',
        'common.delete': '删除',
        'common.unsaved_changes': '有未保存改动',
        'common.do_not_save_and_continue': '不保存并继续',
        'common.save_and_continue': '保存并继续',
        'common.continue_action': '继续此操作',
        'page.settings.script_running': '脚本运行时无法修改配置',
        'log.wrap': '自动换行',
        'log.clear': '清空',
        'log.max_lines': '最多保留 {count} 行',
        'log.output': '输出',
        'about.version': '版本 v{version}',
        'about.docs': '教程文档',
        'about.qq_group': 'QQ 群',
        'modal.telemetry.title': '数据收集',
        'modal.telemetry.content': '是否允许 iaa 自动发送匿名错误报告？发送的信息仅用于改善 iaa。',
        'modal.telemetry.deny': '拒绝',
        'modal.telemetry.allow': '允许',
        'modal.migration.title': '配置升级',
        'modal.exit.title': '确认退出',
        'modal.exit.content': '当前仍在执行任务，确定要退出吗？退出将先停止任务。',
        'modal.exit.confirm': '退出',
        'modal.unsaved.title': '未保存更改',
        'modal.unsaved.content': '当前配置有未保存的更改。{action}前，请先选择处理方式。',
        'guard.close_window': '关闭窗口',
        'guard.switch_page': '切换页面',
        'guard.switch_config': '切换配置',
        'guard.switch_new_config': '切换到新配置',
        'guard.rename_current_config': '重命名当前配置',
        'guard.delete_current_config': '删除当前配置',
        'config_manager.title': '配置管理',
        'config_manager.new_placeholder': '新配置名称',
        'config_manager.rename_title': '重命名配置',
        'config_manager.rename_prompt': '请输入新名称:',
        'config_manager.delete_title': '确认删除',
        'config_manager.delete_prompt': "确定要删除配置 '{name}' 吗？此操作不可撤销。",
        'preferences.title': '设置',
        'preferences.group.interface': '界面',
        'preferences.field.language': '界面语言',
        'preferences.language.zh_CN': '简体中文',
        'preferences.language.en_US': 'English',
    },
    'en_US': {
        'nav.control': 'Control',
        'nav.config': 'Config',
        'nav.preferences': 'Preferences',
        'nav.logs': 'Logs',
        'nav.about': 'About',
        'common.save': 'Save',
        'common.cancel': 'Cancel',
        'common.ok': 'OK',
        'common.close': 'Close',
        'common.create': 'New',
        'common.delete': 'Delete',
        'common.unsaved_changes': 'Unsaved changes',
        'common.do_not_save_and_continue': 'Continue without saving',
        'common.save_and_continue': 'Save and continue',
        'common.continue_action': 'continue this action',
        'page.settings.script_running': 'Config cannot be edited while the script is running',
        'log.wrap': 'Word wrap',
        'log.clear': 'Clear',
        'log.max_lines': 'Keep up to {count} lines',
        'log.output': 'Output',
        'about.version': 'Version v{version}',
        'about.docs': 'Tutorial Docs',
        'about.qq_group': 'QQ Group',
        'modal.telemetry.title': 'Data Collection',
        'modal.telemetry.content': 'Allow iaa to send anonymous error reports automatically? The information is only used to improve iaa.',
        'modal.telemetry.deny': 'Deny',
        'modal.telemetry.allow': 'Allow',
        'modal.migration.title': 'Config Upgrade',
        'modal.exit.title': 'Confirm Exit',
        'modal.exit.content': 'Tasks are still running. Exit anyway? The app will stop the tasks first.',
        'modal.exit.confirm': 'Exit',
        'modal.unsaved.title': 'Unsaved Changes',
        'modal.unsaved.content': 'The current config has unsaved changes. Before {action}, choose how to handle them.',
        'guard.close_window': 'close the window',
        'guard.switch_page': 'switch pages',
        'guard.switch_config': 'switch config',
        'guard.switch_new_config': 'switch to the new config',
        'guard.rename_current_config': 'rename the current config',
        'guard.delete_current_config': 'delete the current config',
        'config_manager.title': 'Config Manager',
        'config_manager.new_placeholder': 'New config name',
        'config_manager.rename_title': 'Rename Config',
        'config_manager.rename_prompt': 'Enter a new name:',
        'config_manager.delete_title': 'Confirm Delete',
        'config_manager.delete_prompt': "Delete config '{name}'? This cannot be undone.",
        'preferences.title': 'Preferences',
        'preferences.group.interface': 'Interface',
        'preferences.field.language': 'Interface language',
        'preferences.language.zh_CN': 'Simplified Chinese',
        'preferences.language.en_US': 'English',
    },
}


def normalize_language(value: object) -> GuiLanguage:
    if value in ('zh', 'zh_CN', 'cn'):
        return 'zh_CN'
    if value in ('en', 'en_US'):
        return 'en_US'
    return DEFAULT_LANGUAGE


def translate(language: str, key: str) -> str:
    normalized = normalize_language(language)
    return (
        _TRANSLATIONS.get(normalized, {}).get(key)
        or _TRANSLATIONS[DEFAULT_LANGUAGE].get(key)
        or key
    )
