import logging

import cv2
from kotonebot import device, sleep

from . import R

logger = logging.getLogger(__name__)

def handle_data_download():
    """
    处理数据下载对话框。

    前置：-\n
    结束：数据下载页面

    :return: 是否处理了数据下载对话框
    """
    if R.CommonDialog.TextRecommendDownloadViaWifi.find():
        logger.debug('Data download dialog found.')
        if R.CommonDialog.ButtonDownload.click():
            logger.debug('Clicked Download button.')
            return True
    return False

def handle_notification():
    if R.Login.IconNotification.find():
        device.click(0, 0)  # 点击空白处关闭通知
        logger.debug('Notification found and closed.')
        return True
    # 台服、国服特有弹窗
    if R.Login.TextSekaiAnnouncements.find():
        logger.debug('Announcement dialog found.')
        if R.Hud.ButtonGoBack.try_click():
            logger.debug('Clicked go back button to close announcement dialog.')
            return True
    return False

def scan_area(*, step_scale: float = 0.1, max_swipes: int = -1):
    # 先重置场景，往左滑动
    SWIPE_COUNT = 4
    for _ in range(SWIPE_COUNT):
        device.swipe_scaled(x1=0.4, x2=0.7, y1=0.5, y2=0.5)
        sleep(0.2)
    
    img = device.screenshot()
    yield

    # 依次往右滑动
    x1, y1, x2, y2 = R.Map.BoxDetectSame.xyxy
    detect_img = img[y1:y2, x1:x2]
    for _ in range(1000 if max_swipes < 0 else max_swipes):
        device.swipe_scaled(x1=0.7, x2=0.7-step_scale, y1=0.5, y2=0.5)
        sleep(0.2)
        img = device.screenshot()
        new_detect_img = img[y1:y2, x1:x2]
        similarity = cv2.matchTemplate(
            detect_img,
            new_detect_img,
            cv2.TM_CCOEFF_NORMED,
        ).max()
        print(similarity)
        if similarity > 0.8:
            break
        detect_img = new_detect_img
        yield

    return
