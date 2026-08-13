import base64
import logging

from kotonebot import device, sleep

from iaa.platform import env

from .utils import asset_path

logger = logging.getLogger(__name__)
ADB_KEYBOARD_PKG = 'com.android.adbkeyboard'
ADB_KEYBOARD_ACTIVITY = 'com.android.adbkeyboard/.AdbIME'

def _is_self_android() -> bool:
    """Android 自身设备（self_android）占位环境判断。

    Android 上 iaa 与游戏跑在同一台设备，没有 adb server，键盘注入
    走的是占位 no-op（真实实现待无障碍服务/IME 注入接入）。
    """
    return env.IS_ANDROID

def check_installed(pkg: str) -> bool:
    """检查是否安装了指定的包。
    
    .. NOTE:: Android 自身设备上没有 adb，此函数仅桌面路径使用；
        占位模式下 ``AdbKeyboardInput`` 不会调用它。"""
    d = device.of_android()
    ret = d.commands.adb_shell(f'pm list packages | grep {pkg}')
    return ret.strip() != ''

def install_apk(apk_path: str):
    """安装 APK 文件。"""
    d = device.of_android()
    d.commands.adb.install(apk_path)
    # d.commands.adb_shell(f'push {apk_path} /data/local/tmp/')
    # apk_name = os.path.basename(apk_path)
    # ret = d.commands.adb_shell(f'pm install -r /data/local/tmp/{apk_name}')
    # if 'error' in ret.lower():
    #     raise RuntimeError(f"Failed to install APK: {ret}")

class AdbKeyboardInput:
    def __init__(self) -> None:
        self._checked = False
        self._active = False
        self._ime_restore: str | None = None

    def _check(self):
        # Android 自身设备上无 adb server，键盘注入为占位 no-op，跳过安装检查。
        if _is_self_android():
            return
        # device.of_android() 的可用性校验由下方 check_installed 隐式完成。
        if not check_installed(ADB_KEYBOARD_PKG):
            install_apk(asset_path('keyboardservice-debug.apk'))
            sleep(1)
        if not check_installed(ADB_KEYBOARD_PKG):
            raise RuntimeError("Failed to install ADB Keyboard.")

    def __enter__(self):
        if self._active:
            raise RuntimeError("Nested `with` is not allowed for AdbKeyboardInput.")
        self._check()
        # Android 自身设备占位：不切换真实 IME，直接标记为激活即可。
        if _is_self_android():
            self._active = True
            return self
        c = device.of_android().commands
        get_ime = lambda: c.adb_shell('settings get secure default_input_method').strip() # noqa: E731
        self._ime_restore = get_ime()
        c.adb_shell(f'ime enable {ADB_KEYBOARD_ACTIVITY}')
        c.adb_shell(f'ime set {ADB_KEYBOARD_ACTIVITY}')
        sleep(0.7) # 等待 AdbKeyboard 启动
        self._active = True
        return self

    def __exit__(self, exc_type, exc, tb):
        if not self._active:
            return
        # Android 自身设备占位：未切换真实 IME，无需还原。
        if not _is_self_android():
            c = device.of_android().commands
            if self._ime_restore:
                c.adb_shell(f'ime set {self._ime_restore}')
                self._ime_restore = None
        self._active = False

    def send(self, text: str):
        # Android 自身设备占位：IME 注入未实现，send 为 no-op。
        if _is_self_android():
            return
        c = device.of_android().commands
        encoded_text = base64.b64encode(text.encode('utf-8')).decode('utf-8')
        c.adb_shell(f'am broadcast -a ADB_INPUT_B64 --es msg "{encoded_text}"')

    def enter(self):
        # Android 自身设备占位：IME 注入未实现，enter 为 no-op。
        if _is_self_android():
            return
        device.of_android().commands.adb_shell('input keyevent 66')

    def select_all(self):
        # Android 自身设备占位：IME 注入未实现，select_all 为 no-op。
        if _is_self_android():
            return
        device.of_android().commands.adb_shell('input keyevent 29 --longpress')

    def backspace(self):
        # Android 自身设备占位：IME 注入未实现，backspace 为 no-op。
        if _is_self_android():
            return
        device.of_android().commands.adb_shell('input keyevent 67')

    def clear(self):
        self.select_all()
        self.backspace()

    def can_input(self) -> bool | None:
        """判断当前是否处于可输入状态（聚焦于输入框）。

        :return: 布尔值表示，是否可输入。若无法判断，返回 None。
        """
        # Android 自身设备占位：无法查询输入法状态，返回 None。
        if _is_self_android():
            return None
        d = device.of_android()
        ret = d.commands.adb_shell('dumpsys input_method | grep mServedInputConnection')
        ret = ret.strip()
        if 'mServedInputConnectionWrapper=null' in ret or 'mServedInputConnection=null' in ret:
            return False
        elif ret.startswith('mServedInputConnectionWrapper=') or ret.startswith('mServedInputConnection='):
            return True
        else:
            logger.warning(f"Unexpected output from dumpsys input_method: {ret}")
            return None
