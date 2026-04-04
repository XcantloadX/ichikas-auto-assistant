from kotonebot import device, task, Loop, action, sleep, logging

from iaa.config.schemas import LinkAccountOptions
from iaa.consts import package_name as get_package_name
from iaa.context import conf, task_reporter
from . import R
from .common import go_home

logger = logging.getLogger(__name__)

@action('登录', screenshot_mode='manual')
def login(link_account: LinkAccountOptions):
    """执行登录流程。
    
    :param link_account: 账号引继方式，目前支持 'google' / 'google_play'
    """
    d = device.of_android()
    if link_account == 'google_play':
        logger.info('Linking with Google Play account...')
        for _ in Loop(interval=3):
            if R.Login.TextLinkFinished.find():
                logger.debug('Link finished')
                logger.info('Login finished')
                break
            if R.Login.ButtonLink.try_click():
                logger.debug('Clicked 連携')
            elif R.Login.ButtonIconLink.try_click():
                logger.debug('Clicked データ引き継ぎ')
            elif link_account == 'google_play' and R.Login.ButtonLinkByGooglePlay.try_click():
                logger.debug('Clicked GooglePlayで連携')
            elif R.Login.ButtonMenu.try_click():
                logger.debug('Clicked 右上角菜单按钮')
    elif link_account == 'google':
        logger.info('Linking with Google account...')
        for _ in Loop(interval=3):
            # 判断是否弹出 Google 登录界面
            activity = d.commands.adb_shell('dumpsys activity activities | grep ResumedActivity')
            if 'com.google.android.gms/.auth.api.credentials.assistedsignin.ui.GoogleSignInActivity' in activity:
                logger.debug('Google login screen detected')
                # 先按下箭头，再按上箭头，再按 ENTER，选择第一个账号进行登录
                d.commands.adb_shell('input keyevent 20')  # DOWN
                sleep(0.3)
                d.commands.adb_shell('input keyevent 19')  # UP
                sleep(0.3)
                d.commands.adb_shell('input keyevent 66')  # ENTER
                logger.debug('Sent key events to select Google account')
                continue

            if R.Login.TextLinkFinished.find():
                logger.debug('Link finished')
                logger.info('Login finished')
                break
            if R.Login.ButtonLink.try_click():
                logger.debug('Clicked 連携')
            elif R.Login.ButtonIconLink.try_click():
                logger.debug('Clicked データ引き継ぎ')
            elif link_account == 'google' and R.Login.ButtonLinkByGoogle.try_click():
                logger.debug('Clicked Googleで連携')
            elif R.Login.ButtonMenu.try_click():
                logger.debug('Clicked 右上角菜单按钮')

@task('启动游戏', screenshot_mode='manual')
def start_game():
    rep = task_reporter()
    d = device.of_android()
    package_name = get_package_name()
    while d.detect_orientation() != 'landscape':
        sleep(3)
    if d.current_package() != package_name:
        use_scrcpy_with_virtual_display = (
            type(d.screenshotable).__name__ == 'ScrcpyImpl'
            and conf().game.scrcpy_virtual_display
        )
        if not use_scrcpy_with_virtual_display:
            logger.info('Not at game. Launching...')
            d.launch_app(package_name)
        
        # 检查是否需要登录
        link_account = conf().game.link_account
        if link_account != 'no':
            rep.message(f'通过 {link_account} 进行引继')
            login(link_account)
        
        go_home(4)
    else:
        logger.info('Already at game.')
        go_home()
    
