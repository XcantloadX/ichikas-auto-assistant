from kotonebot import task, logging
from pathlib import Path
import cv2

from iaa.game_ui.list_view import ListView
from iaa.context import task_reporter

logger = logging.getLogger(__name__)


@task('保存 ListView Item Icon', screenshot_mode='manual')
def _dump_item(
    output_dir: str = 'logs/list_view_icons',
):
    """遍历列表并保存每个 item 的 icon 到指定目录。

    :param output_dir: 输出目录，默认 `logs/list_view_icons`
    """
    rep = task_reporter()
    logger.info('Start _dump_item, output_dir=%s', output_dir)

    list_view = ListView(scrollbar_rect=(1247, 60, 8, 650))
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    saved = 0
    try:
        for item in list_view.walk():
            icon_img = None
            # 优先从 item.image（局部裁切）获取
            if item.icon_rect is not None and item.image is not None:
                rel_x1 = item.icon_rect.x1 - item.rect.x1
                rel_y1 = item.icon_rect.y1 - item.rect.y1
                rel_x2 = rel_x1 + item.icon_rect.w
                rel_y2 = rel_y1 + item.icon_rect.h
                ih, iw = item.image.shape[:2]
                rx1 = max(0, int(rel_x1))
                ry1 = max(0, int(rel_y1))
                rx2 = min(iw, int(rel_x2))
                ry2 = min(ih, int(rel_y2))
                if rx2 > rx1 and ry2 > ry1:
                    icon_img = item.image[ry1:ry2, rx1:rx2].copy()

            if icon_img is None:
                continue

            fname = f"{saved:05d}_p{item.page_index if item.page_index is not None else 'na'}_i{item.index}.png"
            out_path = output_path / fname
            cv2.imwrite(str(out_path), icon_img)
            saved += 1

        logger.info('Saved %d icons to %s', saved, output_dir)
        rep.message(f'已保存 {saved} 个图标到 {output_dir}')
    except Exception as e:
        logger.exception('Failed to save icons: %s', e)
        rep.message(f'保存图标失败: {e}')