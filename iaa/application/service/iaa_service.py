import os
import sys
import zipfile
import logging
import tempfile
import traceback
from datetime import datetime
from functools import cached_property

import cv2

from .config_service import ConfigService
from .assets_service import AssetsService
from .scheduler import SchedulerService
from .help_service import HelpService

class IaaService:
    def __init__(self, config_name: str | None = None):
        # 首先配置日志
        self.__configure_logging()
        
        self.config = ConfigService(self, config_name=config_name)
        self.assets = AssetsService(self)
        self.scheduler = SchedulerService(self)
        self.help = HelpService(self)

    def __configure_logging(self) -> None:
        """配置日志：控制台 DEBUG + 文件 logs/YYYY-MM-DD-hh-mm-ss.log。只配置一次。"""
        root_logger = logging.getLogger()
        
        # 如果已经配置过了就跳过（避免重复配置）
        if root_logger.handlers:
            return
            
        root_logger.setLevel(logging.INFO)
        logging.getLogger("kotonebot").setLevel(logging.DEBUG)
        logging.getLogger("iaa").setLevel(logging.DEBUG)

        # 控制台输出
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        console_handler.setFormatter(console_formatter)

        # 文件输出
        logs_dir = os.path.join(self.root, 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        log_file_path = os.path.join(logs_dir, f'{timestamp}.log')
        file_handler = logging.FileHandler(log_file_path, mode='w', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(console_formatter)

        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler)

        logger = logging.getLogger(__name__)
        logger.debug("Logging configured. File: %s", log_file_path)

    @cached_property
    def root(self) -> str:
        """软件根目录。"""
        # 判断是否为打包运行
        if not os.path.basename(sys.executable).startswith('python'):
            return os.path.dirname(sys.executable)
        else:
            # 源码运行
            return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

    @cached_property
    def version(self) -> str:
        """
        软件版本号。
        若获取失败，返回 'Unknown'。
        """
        try:
            from iaa import __VERSION__  # type: ignore
            if isinstance(__VERSION__, str) and __VERSION__:
                return __VERSION__
        except Exception:
            pass
        return 'Unknown'

    def export_report_zip(self) -> str:
        """
        生成报告 zip，包含 {root}/logs 与 {root}/conf。
        返回生成的临时 zip 文件的绝对路径。
        """
        root_dir = self.root
        logs_dir = os.path.join(root_dir, 'logs')
        conf_dir = os.path.join(root_dir, 'conf')

        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        filename = f"iaa_report_{timestamp}.zip"

        # 在临时目录中创建 zip，避免权限问题
        tmp_dir = tempfile.gettempdir()
        zip_path = os.path.join(tmp_dir, filename)

        def _zipdir(path: str, arc_prefix: str, zf: zipfile.ZipFile) -> None:
            if not os.path.exists(path):
                return
            for folder_name, _, filenames in os.walk(path):
                for fn in filenames:
                    full_path = os.path.join(folder_name, fn)
                    # 归档路径：以 arc_prefix 开头，保持相对目录结构
                    rel_path = os.path.relpath(full_path, path)
                    arcname = os.path.join(arc_prefix, rel_path)
                    try:
                        zf.write(full_path, arcname)
                    except Exception:
                        # 某些文件可能在占用或权限问题，跳过
                        pass

        with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
            _zipdir(logs_dir, 'logs', zf)
            _zipdir(conf_dir, 'conf', zf)
            try:
                img_data = self.scheduler.capture_screenshot()
                img_file = cv2.imencode('.png', img_data)[1].tobytes()
                zf.writestr('screenshot.png', img_file)
            except Exception:
                tb = traceback.format_exc()
                zf.writestr('screenshot_error.txt', tb)

        return zip_path
