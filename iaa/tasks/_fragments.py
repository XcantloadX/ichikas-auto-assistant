import cv2
from kotonebot import device, sleep

from . import R


def handle_data_download():
    """
    处理数据下载对话框。

    前置：-\n
    结束：数据下载页面

    :return: 是否处理了数据下载对话框
    """
    if R.CommonDialog.TextRecommendDownloadViaWifi.find():
        if R.CommonDialog.ButtonDownload.click():
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
        yield
        device.swipe_scaled(x1=0.7, x2=0.7-step_scale, y1=0.5, y2=0.5)
        sleep(0.2)
        img = device.screenshot()
        new_detect_img = img[y1:y2, x1:x2]
        print(cv2.matchTemplate(detect_img, new_detect_img, cv2.TM_CCOEFF_NORMED).max())
        if cv2.matchTemplate(detect_img, new_detect_img, cv2.TM_CCOEFF_NORMED).max() > 0.8:
            break
        detect_img = new_detect_img

    return
