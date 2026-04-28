import os
import shutil
import subprocess
import datetime
from pathlib import Path
from typing import TYPE_CHECKING, cast

from kotonebot import device, Loop, sleep, logging, task
if TYPE_CHECKING:
    from adbutils import AdbDevice

from . import R
from .common import go_home
from iaa.context import conf as get_conf
from ..game_ui.sekai import Camera, Joystick

logger = logging.getLogger(__name__)

RECORDING_DURATION = 90

def _build_output_path(view_name: str) -> Path:
    """生成输出文件路径，如果已存在则递增序号"""
    base_dir = Path("dumps/mysekai_home")
    base_dir.mkdir(parents=True, exist_ok=True)
    
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    index = 1
    while True:
        filename = f"{today}-{index:03d}-{view_name}.mp4"
        filepath = base_dir / filename
        if not filepath.exists():
            return filepath
        index += 1

def _convert_png_seq(path: str):
    input = Path(path)
    if not input.exists():
        raise FileNotFoundError(f"Input file {path} does not exist for post-processing")
    
    ffmpeg = shutil.which('ffmpeg')  # Ensure ffmpeg is available
    if not ffmpeg:
        logger.warning("ffmpeg not found, skipping post-processing")
        return
    
    name = str(Path(path).with_suffix('').name)
    os.makedirs('dumps/mysekai_home/dataset', exist_ok=True)
    output_path = Path('dumps/mysekai_home/dataset') / name
    # to 2fps png sequence
    args = [
        ffmpeg,
        '-i', str(input),
        '-vf', r"fps=2,select='eq(n\,0)+gt(scene\,0.03)'", # 丢弃重复帧和场景变化较小的帧
        '-vsync', 'vfr',
        f'{output_path}-frame-%03d.png'
    ]
    cmdline = ' '.join(args)
    logger.info(f"Post-processing recording with ffmpeg: {cmdline}")
    try:
        subprocess.run(args, check=True)
        logger.info(f"Post-processing complete, output saved to {output_path}")
    except subprocess.CalledProcessError:
        logger.exception("ffmpeg failed with error")
    except Exception:
        logger.exception("Unexpected error during post-processing")

    input.unlink()  # 删除原始视频文件

def _walk(j: Joystick):
    j.raw_move(-100, 100, 4)
    sleep(1)
    j.raw_move(100, 0, 4)
    sleep(1)
    j.raw_move(0, -100, 4)
    sleep(1)
    j.raw_move(-100, 0, 4)
    sleep(1)
    j.raw_move(0, 100, 4)

def _dump():
    d = device.of_android()
    d.scaler
    cam = Camera()
    j = Joystick()

    adb = cast('AdbDevice', device.of_android().commands.adb)
    _current_view = "default"

    def _start_recording(view_name: str):
        nonlocal _current_view
        _current_view = view_name
        remote_path = f"/sdcard/{view_name}.mp4"
        log_path = "/sdcard/screenrecord.log"
        if adb.sync.exists(remote_path):
            logger.debug(f"Remote file {remote_path} already exists, deleting...")
            adb.shell(f"rm {remote_path}")
        logger.info(f"Starting recording to {remote_path}...")
        
        while True:
            ret = d.commands.adb_shell(f"screenrecord {remote_path} </dev/null >{log_path} 2>&1 & echo $!")
            logger.debug(f"Screenrecord command output: {ret}")
            sleep(2)
            pid = adb.shell('pidof screenrecord').strip()
            if not pid:
                logger.error("Failed to start screen recording, no PID found")
                log = adb.shell(f"cat {log_path} 2>/dev/null || true").strip()
                logger.error(f"Screenrecord log: {log}")

                sleep(2)
                continue
            logger.debug(f"Screen recording started with PID {pid}")
            break
        return remote_path

    def _stop_recording():
        logger.info("Stopping screen recording...")
        d.commands.adb_shell("pkill -INT screenrecord")
        sleep(10)
        while True:
            pid = adb.shell('pidof screenrecord').strip()
            if not pid:
                logger.debug("Screen recording process has stopped")
                break
            logger.debug(f"Waiting for screen recording to stop, PID {pid} still running...")
            sleep(1)
        if not adb.sync.exists(f"/sdcard/{_current_view}.mp4"):
            logger.debug("Recording file not found on device, retrying...")
            raise RuntimeError("Recording file not found after stopping screenrecord")
        local_path = _build_output_path(_current_view)
        adb.sync.pull(f"/sdcard/{_current_view}.mp4", local_path.as_posix())
        logger.info(f"Saved recording to {local_path}")
        if get_conf().developer.sekai_dump_post_process:
            logger.info("Starting post-processing of the recording...")
            _convert_png_seq(local_path.as_posix())
            logger.info("Post-processing complete")
        else:
            logger.info("Post-processing disabled, keeping raw recording")
        sleep(3)

    d.commands.adb_shell("pkill -INT screenrecord")

    def _collect(view: str):
        # 1
        _start_recording(view + '-1')
        _walk(j)
        _stop_recording()

        # 2
        cam.rotate(90, 0)
        _start_recording(view + '-2')
        _walk(j)
        _stop_recording()

        # 3
        cam.rotate(90, 0)
        _start_recording(view + '-3')
        _walk(j)
        _stop_recording()

        # 4
        cam.rotate(90, 0)
        _start_recording(view + '-4')
        _walk(j)
        _stop_recording()

    try:
        # 默认视角
        # _start_recording("default")
        _collect('default')
        # _stop_recording()

        # 俯视视角
        cam.rotate(0, 99, duration_sec=5)
        # _start_recording("top_down")
        _collect('top_down')
        # _stop_recording()

        # # 正视视角
        cam.rotate(0, -99, duration_sec=5)
        # _start_recording("front")
        _collect('front')
        # _stop_recording()
    finally:
        d.commands.adb_shell("pkill -INT screenrecord")

def go_to_mysekai():
    go_home()

    for _ in Loop():
        if R.Hud.ButtonMySekai.try_click():
            logger.info('Clicked MySekai button')
            sleep(5)
        elif R.MySekai.Hud.ButtonLayout.exists():
            logger.info('Arrived at MySekai')
            return
        elif R.MySekai.DialogCrowded.Text.exists():
            logger.warning('MySekai is crowded, retrying...')
            if R.MySekai.DialogCrowded.ButtonOk.try_click():
                logger.info('Clicked OK on crowded dialog')
                sleep(2)
        

@task('')
def _dump_sekai_home():
    # go_to_mysekai()
    _dump()

    # logger.info('Dumping MySekai home screen')