import logging
import platform
import subprocess
import time
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def _setup_job(process: subprocess.Popen) -> object | None:
    """
    Windows: 将进程加入 Job Object 并设置 kill-on-job-close。
    父进程意外退出时 OS 自动终止 job 内的子进程。
    """
    if platform.system() != 'Windows':
        return None
    try:
        import ctypes
        from ctypes import wintypes
    except ImportError:
        return None

    JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000
    JobObjectExtendedLimitInformation = 9

    class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", wintypes.LARGE_INTEGER),
            ("PerJobUserTimeLimit", wintypes.LARGE_INTEGER),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    class IO_COUNTERS(ctypes.Structure):
        _fields_ = [
            ("ReadOperationCount", ctypes.c_uint64),
            ("WriteOperationCount", ctypes.c_uint64),
            ("OtherOperationCount", ctypes.c_uint64),
            ("ReadTransferCount", ctypes.c_uint64),
            ("WriteTransferCount", ctypes.c_uint64),
            ("OtherTransferCount", ctypes.c_uint64),
        ]

    class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
            ("IoInfo", IO_COUNTERS),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    kernel32 = ctypes.windll.kernel32
    job = kernel32.CreateJobObjectW(None, None)
    if not job:
        logger.warning('CreateJobObjectW failed, job object not created (error %d).', kernel32.GetLastError())
        return None

    info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
    info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE

    ret = kernel32.SetInformationJobObject(
        job,
        JobObjectExtendedLimitInformation,
        ctypes.byref(info),
        ctypes.sizeof(info),
    )
    if not ret:
        kernel32.CloseHandle(job)
        logger.warning('SetInformationJobObject failed (error %d), job object not configured.', kernel32.GetLastError())
        return None

    proc_handle = wintypes.HANDLE(process._handle)  # type: ignore[attr-defined]
    ret = kernel32.AssignProcessToJobObject(job, proc_handle)
    if not ret:
        kernel32.CloseHandle(job)
        logger.warning('AssignProcessToJobObject failed (error %d), job object not assigned.', kernel32.GetLastError())
        return None

    return job


class ScreenRecorder:
    def __init__(self):
        self._process: subprocess.Popen | None = None
        self._output_path: Path | None = None
        self._job_handle: object | None = None

    @property
    def running(self) -> bool:
        if self._process is None:
            return False
        return self._process.poll() is None

    def start(self) -> Path:
        records_dir = Path('dumps/screen_records')
        records_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        self._output_path = records_dir / f'{timestamp}.mkv'

        system = platform.system()
        if system == 'Windows':
            cmd = [
                'ffmpeg', '-y',
                '-f', 'gdigrab',
                '-framerate', '15',
                '-i', 'desktop',
                '-c:v', 'libx264',
                '-preset', 'ultrafast',
                '-pix_fmt', 'yuv420p',
                str(self._output_path),
            ]
        else:
            cmd = [
                'ffmpeg', '-y',
                '-f', 'x11grab',
                '-framerate', '15',
                '-i', ':0.0',
                '-c:v', 'libx264',
                '-preset', 'ultrafast',
                '-pix_fmt', 'yuv420p',
                str(self._output_path),
            ]

        logger.info('Starting screen recording: %s', self._output_path)
        logger.debug('FFmpeg command: %s', ' '.join(cmd))

        self._process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        time.sleep(1)
        if self._process.poll() is not None:
            self._process = None
            self._output_path = None
            raise RuntimeError('FFmpeg failed to start')

        self._job_handle = _setup_job(self._process)
        return self._output_path

    def stop(self) -> Path | None:
        if self._process is None:
            return None

        logger.info('Stopping screen recording...')
        try:
            self._process.terminate()
            self._process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            logger.warning('FFmpeg did not exit gracefully, killing...')
            self._process.kill()
            self._process.wait()
        except Exception as e:
            logger.warning('Error stopping FFmpeg: %s', e)

        self._close_job()
        result = self._output_path
        self._process = None
        self._output_path = None

        if result and result.exists():
            size_mb = result.stat().st_size / (1024 * 1024)
            logger.info('Screen recording saved: %s (%.1f MB)', result, size_mb)

        return result

    def _close_job(self) -> None:
        if self._job_handle is None:
            return
        try:
            import ctypes
            ctypes.windll.kernel32.CloseHandle(self._job_handle)
        except Exception as e:
            logger.warning('Error closing job handle: %s', e)
        self._job_handle = None


_recorder = ScreenRecorder()


def start_recording() -> Path | None:
    if _recorder.running:
        logger.warning('Screen recording already in progress.')
        return None
    return _recorder.start()


def stop_recording() -> Path | None:
    return _recorder.stop()
