from pathlib import Path
from typing import Optional
import json

from pydantic import BaseModel, ConfigDict

from iaa.tasks.live.live import SingleLoopPlan, ListLoopPlan

from iaa.tasks.live.auto_live_constants import LAST_PRESET_NAME


LIVE_PRESET_VERSION = 1


class AutoLivePreset(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    version: int = LIVE_PRESET_VERSION
    name: str
    plan: SingleLoopPlan | ListLoopPlan


class LivePresetManager:
    """演出预设管理器"""
    
    def __init__(self, preset_dir: Path | None = None):
        if preset_dir is None:
            preset_dir = Path("conf/live_presets")
        self.preset_dir = preset_dir
        self.last_auto_file = self.preset_dir / "last_auto.json"
    
    def save_last_auto(self, preset: AutoLivePreset) -> None:
        """保存上次自动演出设定，强制设置 name 为 LAST_PRESET_NAME。"""
        self.preset_dir.mkdir(parents=True, exist_ok=True)
        preset_to_save = AutoLivePreset(
            version=preset.version,
            name=LAST_PRESET_NAME,
            plan=preset.plan,
        )
        with open(self.last_auto_file, 'w', encoding='utf-8') as f:
            json.dump(preset_to_save.model_dump(mode='json'), f, ensure_ascii=False, indent=2)
    
    def load_last_auto(self) -> Optional[AutoLivePreset]:
        """加载上次自动演出设定，``name`` 归一化为 ``LAST_PRESET_NAME``。

        该文件语义上只代表"上次设定"，``name`` 仅有这一个合法值；历史版本曾把
        展示名「上次设定」强制写盘，任何非哨兵值均为旧版残留，读取时统一归一化。

        :return: 上次自动演出设定（``name`` 恒为 ``LAST_PRESET_NAME``）；文件不存在或损坏时返回 None。
        """
        if not self.last_auto_file.exists():
            return None
        try:
            with open(self.last_auto_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            preset = AutoLivePreset.model_validate(data)
        except Exception:
            return None
        if preset.name != LAST_PRESET_NAME:
            # frozen 模型，归一化需重建实例。
            preset = AutoLivePreset(version=preset.version, name=LAST_PRESET_NAME, plan=preset.plan)
        return preset
    
    def clear_last_auto(self) -> None:
        """清除上次设定"""
        if self.last_auto_file.exists():
            self.last_auto_file.unlink()
