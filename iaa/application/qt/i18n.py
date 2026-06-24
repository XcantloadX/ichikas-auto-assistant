import locale
from dataclasses import dataclass
from functools import cache
from typing import Literal

GuiLanguage = Literal['auto', 'zh_CN', 'en_US']

DEFAULT_LANGUAGE: GuiLanguage = 'auto'
SUPPORTED_LANGUAGES: tuple[GuiLanguage, ...] = ('auto', 'zh_CN', 'en_US')


@dataclass
class TStr:
    zh_CN: str
    en_US: str

    def resolve(self, language: str) -> str:
        if language == 'auto':
            language = _detect_system_language()
        return getattr(self, language, self.zh_CN)


_TRANSLATIONS: dict[str, TStr] = {
        'nav.control': TStr(
            zh_CN='控制',
            en_US='Control'
        ),
        'nav.config': TStr(
            zh_CN='配置',
            en_US='Config'
        ),
        'nav.preferences': TStr(
            zh_CN='偏好',
            en_US='Preferences'
        ),
        'nav.logs': TStr(
            zh_CN='日志',
            en_US='Logs'
        ),
        'nav.about': TStr(
            zh_CN='关于',
            en_US='About'
        ),
        'nav.help': TStr(
            zh_CN='帮助',
            en_US='Help'
        ),
        'common.save': TStr(
            zh_CN='保存',
            en_US='Save'
        ),
        'common.cancel': TStr(
            zh_CN='取消',
            en_US='Cancel'
        ),
        'common.ok': TStr(
            zh_CN='确定',
            en_US='OK'
        ),
        'common.close': TStr(
            zh_CN='关闭',
            en_US='Close'
        ),
        'common.create': TStr(
            zh_CN='新建',
            en_US='New'
        ),
        'common.delete': TStr(
            zh_CN='删除',
            en_US='Delete'
        ),
        'common.start': TStr(
            zh_CN='开始',
            en_US='Start'
        ),
        'common.unsaved_changes': TStr(
            zh_CN='有未保存改动',
            en_US='Unsaved changes'
        ),
        'common.do_not_save_and_continue': TStr(
            zh_CN='不保存并继续',
            en_US='Continue without saving'
        ),
        'common.save_and_continue': TStr(
            zh_CN='保存并继续',
            en_US='Save and continue'
        ),
        'common.continue_action': TStr(
            zh_CN='继续此操作',
            en_US='continue this action'
        ),
        'page.settings.script_running': TStr(
            zh_CN='脚本运行时无法修改配置',
            en_US='Config cannot be edited while the script is running'
        ),
        'log.wrap': TStr(
            zh_CN='自动换行',
            en_US='Word wrap'
        ),
        'log.clear': TStr(
            zh_CN='清空',
            en_US='Clear'
        ),
        'log.max_lines': TStr(
            zh_CN='最多保留 {count} 行',
            en_US='Keep up to {count} lines'
        ),
        'log.output': TStr(
            zh_CN='输出',
            en_US='Output'
        ),
        'about.version': TStr(
            zh_CN='版本 v{version}',
            en_US='Version v{version}'
        ),
        'about.tagline': TStr(
            zh_CN='我同时和六个初音未来结婚',
            en_US='I married six Hatsune Mikus at the same time'
        ),
        'about.docs': TStr(
            zh_CN='教程文档',
            en_US='Tutorial Docs'
        ),
        'about.qq_group': TStr(
            zh_CN='QQ 群',
            en_US='QQ Group'
        ),
        'scrcpy.title': TStr(
            zh_CN='Scrcpy 画面',
            en_US='Scrcpy View'
        ),
        'scrcpy.waiting_frame': TStr(
            zh_CN='等待画面...',
            en_US='Waiting for frame...'
        ),
        'scrcpy.waiting_frame_error': TStr(
            zh_CN='等待画面... {error}',
            en_US='Waiting for frame... {error}'
        ),
        'modal.telemetry.title': TStr(
            zh_CN='数据收集',
            en_US='Data Collection'
        ),
        'modal.telemetry.content': TStr(
            zh_CN='是否允许 iaa 自动发送匿名错误报告？发送的信息仅用于改善 iaa。',
            en_US='Allow iaa to send anonymous error reports automatically? The information is only used to improve iaa.'
        ),
        'modal.telemetry.deny': TStr(
            zh_CN='拒绝',
            en_US='Deny'
        ),
        'modal.telemetry.allow': TStr(
            zh_CN='允许',
            en_US='Allow'
        ),
        'modal.migration.title': TStr(
            zh_CN='配置升级',
            en_US='Config Upgrade'
        ),
        'modal.exit.title': TStr(
            zh_CN='确认退出',
            en_US='Confirm Exit'
        ),
        'modal.exit.content': TStr(
            zh_CN='当前仍在执行任务，确定要退出吗？退出将先停止任务。',
            en_US='Tasks are still running. Exit anyway? The app will stop the tasks first.'
        ),
        'modal.exit.confirm': TStr(
            zh_CN='退出',
            en_US='Exit'
        ),
        'modal.unsaved.title': TStr(
            zh_CN='未保存更改',
            en_US='Unsaved Changes'
        ),
        'modal.unsaved.content': TStr(
            zh_CN='当前配置有未保存的更改。{action}前，请先选择处理方式。',
            en_US='The current config has unsaved changes. Before {action}, choose how to handle them.'
        ),
        'guard.close_window': TStr(
            zh_CN='关闭窗口',
            en_US='close the window'
        ),
        'guard.switch_page': TStr(
            zh_CN='切换页面',
            en_US='switch pages'
        ),
        'guard.switch_config': TStr(
            zh_CN='切换配置',
            en_US='switch config'
        ),
        'guard.switch_new_config': TStr(
            zh_CN='切换到新配置',
            en_US='switch to the new config'
        ),
        'guard.rename_current_config': TStr(
            zh_CN='重命名当前配置',
            en_US='rename the current config'
        ),
        'guard.delete_current_config': TStr(
            zh_CN='删除当前配置',
            en_US='delete the current config'
        ),
        'config_manager.title': TStr(
            zh_CN='配置管理',
            en_US='Config Manager'
        ),
        'config_manager.new_placeholder': TStr(
            zh_CN='新配置名称',
            en_US='New config name'
        ),
        'config_manager.rename_title': TStr(
            zh_CN='重命名配置',
            en_US='Rename Config'
        ),
        'config_manager.rename_prompt': TStr(
            zh_CN='请输入新名称:',
            en_US='Enter a new name:'
        ),
        'config_manager.delete_title': TStr(
            zh_CN='确认删除',
            en_US='Confirm Delete'
        ),
        'config_manager.delete_prompt': TStr(
            zh_CN="确定要删除配置 '{name}' 吗？此操作不可撤销。",
            en_US="Delete config '{name}'? This cannot be undone."
        ),
        'control.main_story_confirm.title': TStr(
            zh_CN='确认开始',
            en_US='Confirm Start'
        ),
        'control.main_story_confirm.content': TStr(
            zh_CN='即将开始刷往期剧情，脚本会无限执行，需要手动停止。是否继续？',
            en_US='Main story farming will run indefinitely and must be stopped manually. Continue?'
        ),
        'control.group.run': TStr(
            zh_CN='启停',
            en_US='Run'
        ),
        'control.group.tasks': TStr(
            zh_CN='任务',
            en_US='Tasks'
        ),
        'control.start': TStr(
            zh_CN='启动',
            en_US='Start'
        ),
        'control.starting': TStr(
            zh_CN='启动中',
            en_US='Starting'
        ),
        'control.stop': TStr(
            zh_CN='停止',
            en_US='Stop'
        ),
        'control.stopping': TStr(
            zh_CN='停止中',
            en_US='Stopping'
        ),
        'control.export_report': TStr(
            zh_CN='导出报告',
            en_US='Export Report'
        ),
        'control.exporting_report': TStr(
            zh_CN='导出中...',
            en_US='Exporting...'
        ),
        'control.current_task': TStr(
            zh_CN='当前任务：{task}',
            en_US='Current task: {task}'
        ),
        'control.run_task': TStr(
            zh_CN='运行',
            en_US='Run'
        ),
        'status.ready': TStr(
            zh_CN='就绪',
            en_US='Ready'
        ),
        'status.stopped': TStr(
            zh_CN='已停止',
            en_US='Stopped'
        ),
        'progress.task_started': TStr(
            zh_CN='开始执行',
            en_US='Starting'
        ),
        'progress.task_finished': TStr(
            zh_CN='执行完成',
            en_US='Finished'
        ),
        'progress.returning_home': TStr(
            zh_CN='正在返回首页',
            en_US='Returning home'
        ),
        'progress.scanning': TStr(
            zh_CN='扫描中',
            en_US='Scanning'
        ),
        'progress.reading_story': TStr(
            zh_CN='阅读剧情',
            en_US='Reading story'
        ),
        'progress.playing_ad': TStr(
            zh_CN='播放广告',
            en_US='Playing ad'
        ),
        'progress.waiting_ad_load': TStr(
            zh_CN='等待广告载入',
            en_US='Waiting for ad to load'
        ),
        'progress.waiting_ad_end': TStr(
            zh_CN='等待广告结束',
            en_US='Waiting for ad to finish'
        ),
        'progress.reward_claimed': TStr(
            zh_CN='奖励已领取',
            en_US='Reward claimed'
        ),
        'progress.waiting_result': TStr(
            zh_CN='等待结果',
            en_US='Waiting for result'
        ),
        'progress.going_scramble_crossing': TStr(
            zh_CN='正在前往交叉路口',
            en_US='Going to Scramble Crossing'
        ),
        'progress.opening_cm': TStr(
            zh_CN='正在打开 CM 界面',
            en_US='Opening CM screen'
        ),
        'progress.scanning_list': TStr(
            zh_CN='扫描列表',
            en_US='Scanning list'
        ),
        'progress.opening_mission_rewards': TStr(
            zh_CN='前往任务奖励页面',
            en_US='Opening mission rewards'
        ),
        'progress.mission_reward': TStr(
            zh_CN='任务奖励 {value}',
            en_US='Mission rewards {value}'
        ),
        'progress.transfer_account': TStr(
            zh_CN='通过 {account} 进行引继',
            en_US='Transferring with {account}'
        ),
        'progress.preparing_auto_live': TStr(
            zh_CN='准备自动演出参数',
            en_US='Preparing auto live options'
        ),
        'progress.returning_home_before_live': TStr(
            zh_CN='返回首页准备进入演出',
            en_US='Returning home before live'
        ),
        'progress.entering_auto_live': TStr(
            zh_CN='进入自动演出流程',
            en_US='Starting auto live flow'
        ),
        'progress.setting_ap_multiplier': TStr(
            zh_CN='设置 AP 倍率',
            en_US='Setting AP multiplier'
        ),
        'progress.not_enough_ap_exiting': TStr(
            zh_CN='AP 不足，正在退出',
            en_US='Not enough AP, exiting'
        ),
        'progress.auto_team_setup': TStr(
            zh_CN='自动编队中',
            en_US='Auto team setup'
        ),
        'progress.settling_results': TStr(
            zh_CN='结算中',
            en_US='Settling results'
        ),
        'progress.entering_solo_live': TStr(
            zh_CN='进入单人演出',
            en_US='Entering solo live'
        ),
        'progress.preparing_live': TStr(
            zh_CN='准备开始演出',
            en_US='Preparing live'
        ),
        'progress.live_in_progress': TStr(
            zh_CN='演出中',
            en_US='Live in progress'
        ),
        'progress.single_loop_game_auto': TStr(
            zh_CN='开始单曲循环（游戏自动）',
            en_US='Starting single-song loop (game auto)'
        ),
        'progress.single_loop_script_auto': TStr(
            zh_CN='开始单曲循环（脚本自动）',
            en_US='Starting single-song loop (script auto)'
        ),
        'progress.single_loop_complete': TStr(
            zh_CN='单曲循环完成，返回首页',
            en_US='Single-song loop complete, returning home'
        ),
        'progress.list_loop_start': TStr(
            zh_CN='开始列表循环',
            en_US='Starting list loop'
        ),
        'progress.list_loop_complete': TStr(
            zh_CN='列表循环完成',
            en_US='List loop complete'
        ),
        'progress.entering_challenge_live': TStr(
            zh_CN='进入挑战演出',
            en_US='Entering challenge live'
        ),
        'progress.select_character': TStr(
            zh_CN='选择角色：{character}',
            en_US='Selecting character: {character}'
        ),
        'progress.starting_challenge_live': TStr(
            zh_CN='开始挑战演出',
            en_US='Starting challenge live'
        ),
        'progress.challenge_live_complete': TStr(
            zh_CN='挑战演出完成，返回首页',
            en_US='Challenge live complete, returning home'
        ),
        'progress.task_error': TStr(
            zh_CN='执行「{task}」时出错：{error}',
            en_US='Error while running {task}: {error}'
        ),
        'progress.task_interrupted': TStr(
            zh_CN='任务中断：{task}',
            en_US='Task interrupted: {task}'
        ),
        'progress.task_failed': TStr(
            zh_CN='执行失败：{task}',
            en_US='Task failed: {task}'
        ),
        'progress.unknown_error': TStr(
            zh_CN='未知错误',
            en_US='unknown error'
        ),
        'notice.tasks_completed': TStr(
            zh_CN='任务执行完成',
            en_US='Tasks completed'
        ),
        'notice.tasks_interrupted': TStr(
            zh_CN='任务已中断',
            en_US='Tasks interrupted'
        ),
        'notice.tasks_failed': TStr(
            zh_CN='任务执行失败',
            en_US='Tasks failed'
        ),
        'notice.tasks_crashed': TStr(
            zh_CN='调度器发生错误',
            en_US='Scheduler error'
        ),
        'notice.tasks_finished': TStr(
            zh_CN='任务结束',
            en_US='Tasks finished'
        ),
        'notice.save_success': TStr(
            zh_CN='保存成功',
            en_US='Saved'
        ),
        'notice.save_failed': TStr(
            zh_CN='保存失败：{error}',
            en_US='Save failed: {error}'
        ),
        'notice.field_set_failed': TStr(
            zh_CN='设置字段失败：{error}',
            en_US='Failed to set field: {error}'
        ),
        'notice.export_failed': TStr(
            zh_CN='导出失败：{error}',
            en_US='Export failed: {error}'
        ),
        'notice.report_saved': TStr(
            zh_CN='报告已保存。',
            en_US='Report saved.'
        ),
        'notice.report_save_failed': TStr(
            zh_CN='保存失败：{error}',
            en_US='Save failed: {error}'
        ),
        'notice.telemetry_effective': TStr(
            zh_CN='数据收集设置将于下次启动时生效。',
            en_US='Data collection changes will take effect after restart.'
        ),
        'notice.script_auto_warning': TStr(
            zh_CN='使用“脚本自动”时必须满足：\n1. 当前选中演出歌曲为 EASY 难度\n2. 流速为 1，特效为轻量\n3. 使用 MuMu 模拟器且控制方法选择「nemu_ipc」，或其他模拟器选择「scrcpy」\n4. 分辨率为 16:9，支持 1280x720 及其等比例缩放\n5. 使用脚本自动演出带来的一切风险与后果由使用者自行承担',
            en_US='Script auto requires:\n1. The selected live song is on EASY difficulty\n2. Note speed is 1 and effects are lightweight\n3. MuMu uses the nemu_ipc control method, or other emulators use scrcpy\n4. The resolution is 16:9, including 1280x720 and proportional scales\n5. The user accepts all risks and consequences of using script auto'
        ),
        'dialog.save_report.title': TStr(
            zh_CN='保存报告',
            en_US='Save Report'
        ),
        'dialog.save_report.filter': TStr(
            zh_CN='Zip 文件 (*.zip)',
            en_US='Zip files (*.zip)'
        ),
        'startup.config_validation_prompt': TStr(
            zh_CN='以下配置项校验失败：\n{fields}\n\n错误详情：\n{error}\n\n是否重置这些为默认值？',
            en_US='The following config fields failed validation:\n{fields}\n\nDetails:\n{error}\n\nReset these fields to defaults?'
        ),
        'startup.config_validation_aborted': TStr(
            zh_CN='配置校验失败，未重置。程序即将退出。',
            en_US='Config validation failed and was not reset. The app will exit.'
        ),
        'modal.migration.content_title': TStr(
            zh_CN='<b>配置文件已升级到 v{version}。</b>',
            en_US='<b>Config file upgraded to v{version}.</b>'
        ),
        'task.start_game': TStr(
            zh_CN='启动游戏',
            en_US='Start Game'
        ),
        'task.cm': TStr(
            zh_CN='自动 CM',
            en_US='Auto CM'
        ),
        'task.solo_live': TStr(
            zh_CN='单人演出',
            en_US='Solo Live'
        ),
        'task.challenge_live': TStr(
            zh_CN='挑战演出',
            en_US='Challenge Live'
        ),
        'task.activity_story': TStr(
            zh_CN='活动剧情',
            en_US='Event Story'
        ),
        'task.gift': TStr(
            zh_CN='领取礼物',
            en_US='Claim Gifts'
        ),
        'task.area_convos': TStr(
            zh_CN='区域对话',
            en_US='Area Convos'
        ),
        'task.event_shop': TStr(
            zh_CN='活动商店',
            en_US='Event Shop'
        ),
        'task.mission_rewards': TStr(
            zh_CN='任务奖励',
            en_US='Mission Rewards'
        ),
        'task.auto_live': TStr(
            zh_CN='自动演出',
            en_US='Auto Live'
        ),
        'task.main_story': TStr(
            zh_CN='刷主线剧情',
            en_US='Main Story'
        ),
        'task._dump_item': TStr(
            zh_CN='保存 ListView Item Icon',
            en_US='Save ListView Item Icon'
        ),
        'task._dump_sekai_home': TStr(
            zh_CN='dump 烤森',
            en_US='Dump Sekai Home'
        ),
        'auto_live.preset': TStr(
            zh_CN='预设',
            en_US='Preset'
        ),
        'auto_live.preset.clear_10': TStr(
            zh_CN='CLEAR 10 首歌',
            en_US='Clear 10 songs'
        ),
        'auto_live.preset.fc_10': TStr(
            zh_CN='FC 10 次',
            en_US='FC 10 times'
        ),
        'auto_live.preset.leader_count': TStr(
            zh_CN='队长次数',
            en_US='Leader count'
        ),
        'auto_live.preset.last': TStr(
            zh_CN='上次设定',
            en_US='Last settings'
        ),
        'auto_live.notice.no_last_preset': TStr(
            zh_CN='没有找到上次设定',
            en_US='No last settings found'
        ),
        'auto_live.count': TStr(
            zh_CN='演出次数',
            en_US='Live count'
        ),
        'auto_live.count.specify': TStr(
            zh_CN='指定次数',
            en_US='Specified count'
        ),
        'auto_live.count.placeholder': TStr(
            zh_CN='次数',
            en_US='Count'
        ),
        'auto_live.count.all': TStr(
            zh_CN='直到 AP 耗尽',
            en_US='Until AP runs out'
        ),
        'auto_live.loop_mode': TStr(
            zh_CN='循环模式',
            en_US='Loop mode'
        ),
        'auto_live.loop.single': TStr(
            zh_CN='单曲循环',
            en_US='Single song'
        ),
        'auto_live.loop.list': TStr(
            zh_CN='列表顺序',
            en_US='List order'
        ),
        'auto_live.loop.random': TStr(
            zh_CN='列表随机',
            en_US='Random list'
        ),
        'auto_live.play_mode': TStr(
            zh_CN='自动模式',
            en_US='Auto mode'
        ),
        'auto_live.play.game_auto': TStr(
            zh_CN='游戏自动',
            en_US='Game auto'
        ),
        'auto_live.play.script_auto': TStr(
            zh_CN='脚本自动',
            en_US='Script auto'
        ),
        'auto_live.ap_multiplier': TStr(
            zh_CN='AP 倍率',
            en_US='AP multiplier'
        ),
        'auto_live.ap.keep': TStr(
            zh_CN='保持现状',
            en_US='Keep current'
        ),
        'auto_live.ap.maximum': TStr(
            zh_CN='最大值',
            en_US='Maximum'
        ),
        'auto_live.song_name': TStr(
            zh_CN='歌曲名称',
            en_US='Song name'
        ),
        'auto_live.song.keep': TStr(
            zh_CN='保持不变',
            en_US='Keep unchanged'
        ),
        'auto_live.debug_display': TStr(
            zh_CN='调试显示（脚本自动）',
            en_US='Debug display (script auto)'
        ),
        'auto_live.auto_set_unit': TStr(
            zh_CN='自动编队',
            en_US='Auto team setup'
        ),
        'preferences.title': TStr(
            zh_CN='设置',
            en_US='Preferences'
        ),
        'preferences.group.telemetry': TStr(
            zh_CN='数据收集',
            en_US='Data Collection'
        ),
        'preferences.group.interface': TStr(
            zh_CN='界面',
            en_US='Interface'
        ),
        'preferences.group.notify': TStr(
            zh_CN='通知',
            en_US='Notifications'
        ),
        'preferences.group.hotkeys': TStr(
            zh_CN='快捷键',
            en_US='Hotkeys'
        ),
        'preferences.field.telemetry_sentry': TStr(
            zh_CN='自动发送匿名错误报告',
            en_US='Send anonymous error reports automatically'
        ),
        'preferences.field.language': TStr(
            zh_CN='界面语言',
            en_US='Interface language'
        ),
        'preferences.field.window_style': TStr(
            zh_CN='窗口背景样式',
            en_US='Window background style'
        ),
        'preferences.field.color_scheme': TStr(
            zh_CN='色彩方案',
            en_US='Color scheme'
        ),
        'preferences.field.theme_color': TStr(
            zh_CN='主题色',
            en_US='Theme color'
        ),
        'preferences.field.notify_system': TStr(
            zh_CN='系统通知',
            en_US='System notifications'
        ),
        'preferences.field.notify_push': TStr(
            zh_CN='推送通知',
            en_US='Push notifications'
        ),
        'preferences.field.notify_push_type': TStr(
            zh_CN='推送类型',
            en_US='Push type'
        ),
        'preferences.field.notify_custom_command': TStr(
            zh_CN='自定义命令',
            en_US='Custom command'
        ),
        'preferences.field.hotkey_start': TStr(
            zh_CN='启动脚本',
            en_US='Start script'
        ),
        'preferences.field.hotkey_stop': TStr(
            zh_CN='停止脚本',
            en_US='Stop script'
        ),
        'preferences.hotkey.placeholder.idle': TStr(
            zh_CN='点击设置',
            en_US='Click to set'
        ),
        'preferences.hotkey.placeholder.recording': TStr(
            zh_CN='按下快捷键…（按 ESC 取消）',
            en_US='Press shortcut... (Esc to cancel)'
        ),
        'preferences.hotkey.clear': TStr(
            zh_CN='清除',
            en_US='Clear'
        ),
        'preferences.language.zh_CN': TStr(
            zh_CN='简体中文',
            en_US='Simplified Chinese'
        ),
        'preferences.language.en_US': TStr(
            zh_CN='English',
            en_US='English'
        ),
        'preferences.option.auto': TStr(
            zh_CN='自动',
            en_US='Auto'
        ),
        'preferences.option.window_style.mica': TStr(
            zh_CN='Mica（仅 Win 11）',
            en_US='Mica (Win 11 only)'
        ),
        'preferences.option.window_style.blur': TStr(
            zh_CN='模糊背景',
            en_US='Blur background'
        ),
        'preferences.option.window_style.acrylic': TStr(
            zh_CN='亚克力（Win 10 1803+）',
            en_US='Acrylic (Win 10 1803+)'
        ),
        'preferences.option.window_style.solid': TStr(
            zh_CN='纯色背景',
            en_US='Solid color'
        ),
        'preferences.option.follow_system': TStr(
            zh_CN='跟随系统',
            en_US='Follow system'
        ),
        'preferences.option.color_scheme.light': TStr(
            zh_CN='浅色',
            en_US='Light'
        ),
        'preferences.option.color_scheme.dark': TStr(
            zh_CN='深色',
            en_US='Dark'
        ),
        'preferences.option.theme.blue': TStr(
            zh_CN='蓝色（#0078D4）',
            en_US='Blue (#0078D4)'
        ),
        'preferences.option.theme.red': TStr(
            zh_CN='红色（#E81123）',
            en_US='Red (#E81123)'
        ),
        'preferences.option.theme.green': TStr(
            zh_CN='绿色（#107C10）',
            en_US='Green (#107C10)'
        ),
        'preferences.option.theme.orange': TStr(
            zh_CN='橙色（#FF8C00）',
            en_US='Orange (#FF8C00)'
        ),
        'preferences.option.theme.purple': TStr(
            zh_CN='紫色（#5C2D91）',
            en_US='Purple (#5C2D91)'
        ),
        'preferences.option.theme.cyan': TStr(
            zh_CN='青色（#00B7C3）',
            en_US='Cyan (#00B7C3)'
        ),
        'preferences.option.theme.indigo': TStr(
            zh_CN='靛蓝（#6B69D6）',
            en_US='Indigo (#6B69D6)'
        ),
        'preferences.option.theme.graphite': TStr(
            zh_CN='石墨灰（#4A5459）',
            en_US='Graphite gray (#4A5459)'
        ),
        'preferences.option.notify_push.custom': TStr(
            zh_CN='自定义命令',
            en_US='Custom command'
        ),
        'preferences.option.notify_push.discord': TStr(
            zh_CN='Discord Webhook',
            en_US='Discord Webhook'
        ),
        'preferences.placeholder.notify_custom_command': TStr(
            zh_CN='任务完成后执行的命令',
            en_US='Command to run after tasks finish'
        ),
        'preferences.help.discord_webhook': TStr(
            zh_CN='如何获取 Discord Webhook URL？',
            en_US='How do I get a Discord Webhook URL?'
        ),
        'settings.title': TStr(
            zh_CN='配置',
            en_US='Config'
        ),
        'settings.group.game': TStr(
            zh_CN='游戏设置',
            en_US='Game Settings'
        ),
        'settings.group.device': TStr(
            zh_CN='设备设置',
            en_US='Device Settings'
        ),
        'settings.group.connection': TStr(
            zh_CN='连接设置',
            en_US='Connection Settings'
        ),
        'settings.group.control': TStr(
            zh_CN='控制方式',
            en_US='Control Method'
        ),
        'settings.group.live': TStr(
            zh_CN='演出设置',
            en_US='Live Settings'
        ),
        'settings.group.challenge_live': TStr(
            zh_CN='挑战演出设置',
            en_US='Challenge Live Settings'
        ),
        'settings.group.cm': TStr(
            zh_CN='CM 设置',
            en_US='CM Settings'
        ),
        'settings.group.event_shop': TStr(
            zh_CN='活动商店设置',
            en_US='Event Shop Settings'
        ),
        'settings.group.developer': TStr(
            zh_CN='开发者设置（仅供开发使用！）',
            en_US='Developer Settings'
        ),
        'settings.field.game.server': TStr(
            zh_CN='服务器',
            en_US='Server'
        ),
        'settings.field.game.link_account': TStr(
            zh_CN='引继账号',
            en_US='Transfer account'
        ),
        'settings.field.device.lifecycle_type': TStr(
            zh_CN='设备类型',
            en_US='Device type'
        ),
        'settings.field.device.mumu_instance': TStr(
            zh_CN='多开实例',
            en_US='MuMu instance'
        ),
        'settings.field.device.check_and_start': TStr(
            zh_CN='检查并启动',
            en_US='Check and start'
        ),
        'settings.field.device.custom_start_command': TStr(
            zh_CN='启动命令',
            en_US='Start command'
        ),
        'settings.field.device.custom_wait_start_command': TStr(
            zh_CN='等待启动命令退出后才继续',
            en_US='Wait for start command to exit'
        ),
        'settings.field.device.custom_stop_command': TStr(
            zh_CN='结束命令',
            en_US='Stop command'
        ),
        'settings.field.device.custom_running_command': TStr(
            zh_CN='运行检测命令',
            en_US='Running check command'
        ),
        'settings.field.device.connection_type': TStr(
            zh_CN='连接方式',
            en_US='Connection method'
        ),
        'settings.field.device.serial': TStr(
            zh_CN='设备序列号',
            en_US='Device serial'
        ),
        'settings.field.device.tcp_ip': TStr(
            zh_CN='ADB IP',
            en_US='ADB IP'
        ),
        'settings.field.device.tcp_port': TStr(
            zh_CN='ADB 端口',
            en_US='ADB port'
        ),
        'settings.field.device.tcp_run_adb_connect': TStr(
            zh_CN='执行 adb connect',
            en_US='Run adb connect'
        ),
        'settings.field.device.control_impl': TStr(
            zh_CN='控制方式',
            en_US='Control method'
        ),
        'settings.field.device.scrcpy_virtual_display': TStr(
            zh_CN='使用虚拟显示器',
            en_US='Use virtual display'
        ),
        'settings.field.device.resolution_method': TStr(
            zh_CN='分辨率设置',
            en_US='Resolution setting'
        ),
        'settings.field.live.song_name': TStr(
            zh_CN='歌曲名称',
            en_US='Song name'
        ),
        'settings.field.live.ap_multiplier': TStr(
            zh_CN='AP 倍率',
            en_US='AP multiplier'
        ),
        'settings.field.live.auto_set_unit': TStr(
            zh_CN='自动编队',
            en_US='Auto team setup'
        ),
        'settings.field.live.append_fc': TStr(
            zh_CN='追加一次 FullCombo 演出',
            en_US='Append one Full Combo live'
        ),
        'settings.field.live.append_random': TStr(
            zh_CN='追加一首随机歌曲',
            en_US='Append one random song'
        ),
        'settings.field.challenge.characters': TStr(
            zh_CN='角色',
            en_US='Character'
        ),
        'settings.field.challenge.award': TStr(
            zh_CN='奖励',
            en_US='Reward'
        ),
        'settings.field.cm.watch_ad_wait_sec': TStr(
            zh_CN='广告等待秒数',
            en_US='Ad wait seconds'
        ),
        'settings.field.developer.dump_sekai_home': TStr(
            zh_CN='dump 烤森',
            en_US='Dump Sekai Home'
        ),
        'settings.field.developer.sekai_dump_post_process': TStr(
            zh_CN='dump 烤森 - 后处理与预打标',
            en_US='Dump Sekai Home - post-process and pre-label'
        ),
        'settings.field.developer.screen_recording': TStr(
            zh_CN='自动录屏（需安装 ffmpeg）',
            en_US='Auto screen recording (requires ffmpeg)'
        ),
        'settings.help.server': TStr(
            zh_CN='广告：现招募维护者维护除日服以外的服务器适配~ 如果你有兴趣参与维护，请联系作者。<hr>维护者：<ul><li>日服：作者本人</li><li>台服：空缺</li><li>国服：空缺</li><li>国际服：空缺</li><li>韩服：空缺</li></ul>',
            en_US='Maintainers are wanted for non-JP server adaptation. Contact the author if you are interested.<hr>Maintainers:<ul><li>JP: author</li><li>TW: vacant</li><li>CN: vacant</li><li>Global / EN: vacant</li><li>KR: vacant</li></ul>'
        ),
        'settings.help.link_account': TStr(
            zh_CN='每次启动游戏的时候是否使用引继账号登录（仅限日服）',
            en_US='Whether to log in with a transfer account when starting the game. JP only.'
        ),
        'settings.help.custom_start_command': TStr(
            zh_CN='将会通过 shell 方式执行。因此编写时请注意转义等问题。<br>下面两个命令也是一样的。',
            en_US='Runs through the shell. Escape command text carefully.<br>The following two commands behave the same way.'
        ),
        'settings.help.tcp_run_adb_connect': TStr(
            zh_CN='如果需要通过「IP:端口」的形式连接设备，需要勾选。',
            en_US='Enable this when connecting to a device through IP:port.'
        ),
        'settings.help.control_impl': TStr(
            zh_CN='对于 MuMu 模拟器，推荐使用 <b>Nemu IPC</b> 方式，对于其他模拟器与物理机，推荐使用 <b>scrcpy</b> 方式',
            en_US='For MuMu, <b>Nemu IPC</b> is recommended. For other emulators and physical devices, <b>scrcpy</b> is recommended.'
        ),
        'settings.help.screen_recording': TStr(
            zh_CN='脚本启动时自动录屏，结束时自动结束。输出到 dumps/screen_records/ 目录。',
            en_US='Automatically starts recording when the script starts and stops when it ends. Output goes to dumps/screen_records/.'
        ),
        'settings.notice.nemu_ipc_tip': TStr(
            zh_CN='MuMu 模拟器选择 NemuIPC 效果最佳',
            en_US='Nemu IPC works best for MuMu emulators'
        ),
        'settings.placeholder.custom_stop_command': TStr(
            zh_CN='可选。如果为空，将会自动终止启动命令中的进程',
            en_US='Optional. When empty, processes from the start command will be stopped automatically.'
        ),
        'settings.placeholder.custom_running_command': TStr(
            zh_CN='可选。如果为空，将会使用默认的运行检测方式',
            en_US='Optional. When empty, the default running check is used.'
        ),
        'settings.placeholder.usb_serial': TStr(
            zh_CN='留空自动选择第一个 USB 设备',
            en_US='Leave empty to select the first USB device automatically'
        ),
        'settings.placeholder.tcp_device_serial': TStr(
            zh_CN='留空则默认使用 IP:端口 作为序列号',
            en_US='Leave empty to use IP:port as the serial'
        ),
        'settings.option.lifecycle.custom': TStr(
            zh_CN='自定义模拟器',
            en_US='Custom emulator'
        ),
        'settings.option.lifecycle.none': TStr(
            zh_CN='物理机 / 手动管理',
            en_US='Physical device / manual management'
        ),
        'settings.option.connection.tcp': TStr(
            zh_CN='TCP / 无线',
            en_US='TCP / wireless'
        ),
        'settings.option.server.jp': TStr(
            zh_CN='日服',
            en_US='JP'
        ),
        'settings.option.server.tw': TStr(
            zh_CN='台服',
            en_US='TW'
        ),
        'settings.option.server.cn': TStr(
            zh_CN='国服',
            en_US='CN'
        ),
        'settings.option.server.en': TStr(
            zh_CN='国际服',
            en_US='Global / EN'
        ),
        'settings.option.link.no': TStr(
            zh_CN='不引继账号',
            en_US='Do not use transfer'
        ),
        'settings.option.link.google': TStr(
            zh_CN='Google 账号',
            en_US='Google account'
        ),
        'settings.option.resolution.auto': TStr(
            zh_CN='智能决定',
            en_US='Decide automatically'
        ),
        'settings.option.resolution.keep': TStr(
            zh_CN='保持原始分辨率',
            en_US='Keep original resolution'
        ),
        'settings.option.resolution.wm_size': TStr(
            zh_CN='修改分辨率（wm size）',
            en_US='Change resolution (wm size)'
        ),
        'settings.option.mumu_instance.default': TStr(
            zh_CN='默认',
            en_US='Default'
        ),
        'settings.option.live.song.keep': TStr(
            zh_CN='保持不变',
            en_US='Keep current'
        ),
        'settings.option.live.ap.keep': TStr(
            zh_CN='保持现状',
            en_US='Keep current'
        ),
        'settings.option.live.ap.maximum': TStr(
            zh_CN='最大值',
            en_US='Maximum'
        ),
        'settings.option.event_shop.2star_event_card': TStr(
            zh_CN='★2成员',
            en_US='★2 Member'
        ),
        'settings.option.event_shop.3star_event_card': TStr(
            zh_CN='★3成员',
            en_US='★3 Member'
        ),
        'settings.option.event_shop.cover_card_voucher': TStr(
            zh_CN='歌手兑换卡',
            en_US='Cover Card Voucher'
        ),
        'settings.option.event_shop.crystal': TStr(
            zh_CN='水晶',
            en_US='Crystals'
        ),
        'settings.option.event_shop.wish_piece': TStr(
            zh_CN='心愿碎片',
            en_US='Wish Piece'
        ),
        'settings.option.event_shop.bonus_energy_drink_s': TStr(
            zh_CN='演出能量饮料（小）',
            en_US='Bonus Energy Drink (S)'
        ),
        'settings.option.event_shop.stamp_voucher': TStr(
            zh_CN='表情兑换券',
            en_US='Stamp Voucher'
        ),
        'settings.option.event_shop.practice_score_intermediate': TStr(
            zh_CN='练习乐谱（中级）',
            en_US='Practice Score (Intermediate)'
        ),
        'settings.option.event_shop.music_card': TStr(
            zh_CN='音乐卡',
            en_US='Music Card'
        ),
        'settings.option.event_shop.miracle_gem': TStr(
            zh_CN='奇迹晶石',
            en_US='Miracle Gem'
        ),
        'settings.option.event_shop.magic_cloth': TStr(
            zh_CN='魔法之布',
            en_US='Magic Cloth'
        ),
        'settings.option.event_shop.magic_thread': TStr(
            zh_CN='魔法之线',
            en_US='Magic Thread'
        ),
        'settings.option.event_shop.magical_seed': TStr(
            zh_CN='奇异种子',
            en_US='Mysterious Seed'
        ),
        'settings.option.event_shop.wish_drop': TStr(
            zh_CN='心愿之露',
            en_US='Wish Drop'
        ),
        'settings.option.event_shop.skill_up_score_intermediate': TStr(
            zh_CN='技能升级乐谱（中级）',
            en_US='Skill Up Score (Intermediate)'
        ),
        'settings.option.event_shop.coin_100000': TStr(
            zh_CN='硬币x100000',
            en_US='Coins x100000'
        ),
        'settings.option.event_shop.coin_1': TStr(
            zh_CN='硬币x1',
            en_US='Coins x1'
        ),
        'settings.action.refresh': TStr(
            zh_CN='刷新',
            en_US='Refresh'
        ),
        'settings.action.loading': TStr(
            zh_CN='获取中...',
            en_US='Loading...'
        ),
        'settings.action.reset_resolution': TStr(
            zh_CN='恢复分辨率',
            en_US='Reset Resolution'
        ),
        'settings.action.add': TStr(
            zh_CN='← 添加',
            en_US='← Add'
        ),
        'settings.action.remove': TStr(
            zh_CN='移除 →',
            en_US='Remove →'
        ),
        'settings.action.move_up': TStr(
            zh_CN='上移',
            en_US='Move Up'
        ),
        'settings.action.move_down': TStr(
            zh_CN='下移',
            en_US='Move Down'
        ),
        'settings.error.tcp_port_required': TStr(
            zh_CN='端口不能为空',
            en_US='Port is required'
        ),
        'settings.error.tcp_port_numeric': TStr(
            zh_CN='端口必须是数字',
            en_US='Port must be numeric'
        ),
        'settings.error.start_command_required': TStr(
            zh_CN='启动命令不能为空',
            en_US='Start command is required'
        ),
        'settings.error.watch_ad_wait_sec_required': TStr(
            zh_CN='CM 广告等待秒数不能为空',
            en_US='CM ad wait seconds is required'
        ),
        'settings.error.watch_ad_wait_sec_numeric': TStr(
            zh_CN='CM 广告等待秒数必须是数字',
            en_US='CM ad wait seconds must be numeric'
        ),
        'settings.error.watch_ad_wait_sec_positive': TStr(
            zh_CN='CM 广告等待秒数必须大于 0',
            en_US='CM ad wait seconds must be greater than 0'
        ),
        'settings.error.unknown_field': TStr(
            zh_CN='未知字段: {field}',
            en_US='Unknown field: {field}'
        ),
        'settings.error.unsupported_action': TStr(
            zh_CN='不支持的动作: {field}.{action}',
            en_US='Unsupported action: {field}.{action}'
        ),
        'auto_live.error.count_positive': TStr(
            zh_CN='指定次数必须为正整数。',
            en_US='Specified count must be a positive integer.'
        ),
        'auto_live.error.unknown_count_mode': TStr(
            zh_CN='未知的次数模式：{mode}',
            en_US='Unknown count mode: {mode}'
        ),
        'auto_live.error.ap_multiplier': TStr(
            zh_CN='AP 倍率必须在 0 到 10 之间，或为 maximum。',
            en_US='AP multiplier must be 0 to 10, or maximum.'
        ),
        'auto_live.error.unknown_loop_mode': TStr(
            zh_CN='未知的循环模式：{mode}',
            en_US='Unknown loop mode: {mode}'
        ),
        'settings.status.mumu_no_instance_needed': TStr(
            zh_CN='当前模拟器无需选择实例',
            en_US='Current emulator does not need an instance'
        ),
        'settings.status.mumu_refreshed': TStr(
            zh_CN='已刷新 MuMu 实例',
            en_US='MuMu instances refreshed'
        ),
        'settings.status.mumu_loaded': TStr(
            zh_CN='已载入 {count} 个实例',
            en_US='Loaded {count} instance(s)'
        ),
        'settings.status.mumu_not_found': TStr(
            zh_CN='未找到可用实例',
            en_US='No available instances found'
        ),
        'settings.status.mumu_selected': TStr(
            zh_CN='，当前选择 ID: {selected_id}',
            en_US=', selected ID: {selected_id}'
        ),
        'settings.status.mumu_refresh_failed': TStr(
            zh_CN='刷新失败：{error}',
            en_US='Refresh failed: {error}'
        ),
        'settings.status.mumu_refresh_failed_plain': TStr(
            zh_CN='刷新 MuMu 实例失败',
            en_US='Failed to refresh MuMu instances'
        ),
        'settings.status.device_connect_failed': TStr(
            zh_CN='连接失败：{error}',
            en_US='Connection failed: {error}'
        ),
        'settings.status.device_not_connected': TStr(
            zh_CN='设备尚未连接',
            en_US='Device is not connected'
        ),
        'settings.status.resolution_restored': TStr(
            zh_CN='已恢复分辨率',
            en_US='Resolution restored'
        ),
        'settings.status.resolution_restore_failed': TStr(
            zh_CN='恢复失败：{error}',
            en_US='Restore failed: {error}'
        ),
        'settings.status.profile_switched': TStr(
            zh_CN='已切换到配置: {name}',
            en_US='Switched to config: {name}'
        ),
        'settings.status.profile_created': TStr(
            zh_CN='已创建并切换到配置: {name}',
            en_US='Created and switched to config: {name}'
        ),
        'settings.status.profile_deleted': TStr(
            zh_CN='已删除配置: {name}',
            en_US='Deleted config: {name}'
        ),
        'settings.status.profile_renamed': TStr(
            zh_CN='已重命名为: {name}',
            en_US='Renamed to: {name}'
        ),
        'settings.status.profile_missing': TStr(
            zh_CN='配置不存在: {name}',
            en_US='Config does not exist: {name}'
        ),
        'settings.status.profile_exists': TStr(
            zh_CN='配置名称已存在: {name}',
            en_US='Config name already exists: {name}'
        ),
        'settings.status.profile_switch_failed': TStr(
            zh_CN='切换失败：{error}',
            en_US='Switch failed: {error}'
        ),
        'settings.status.profile_create_failed': TStr(
            zh_CN='创建失败：{error}',
            en_US='Create failed: {error}'
        ),
        'settings.status.profile_delete_failed': TStr(
            zh_CN='删除失败：{error}',
            en_US='Delete failed: {error}'
        ),
        'settings.status.profile_rename_failed': TStr(
            zh_CN='重命名失败：{error}',
            en_US='Rename failed: {error}'
        ),
}


@cache
def _detect_system_language() -> GuiLanguage:
    try:
        lang, _ = locale.getdefaultlocale()
        if lang and lang.startswith('zh'):
            return 'zh_CN'
    except Exception:
        pass
    return 'en_US'


def translate(language: str, key: str) -> str:
    if language == 'auto':
        language = _detect_system_language()
    t = _TRANSLATIONS.get(key)
    if t is not None:
        return getattr(t, language, t.zh_CN)
    return key


def tstr(key: str) -> TStr:
    """返回 key 对应的 TStr；key 不存在时返回两侧均为 key 本身的占位对象。"""
    t = _TRANSLATIONS.get(key)
    return t if t is not None else TStr(zh_CN=key, en_US=key)
