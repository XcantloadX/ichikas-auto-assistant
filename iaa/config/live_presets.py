from pathlib import Path
from typing import Optional
import json

from pydantic import BaseModel, ConfigDict

from iaa.tasks.live.live import SingleLoopPlan, ListLoopPlan


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
        """保存上次自动演出设定，强制设置 name 为"上次设定" """
        self.preset_dir.mkdir(parents=True, exist_ok=True)
        # 强制使用固定名称
        preset_to_save = AutoLivePreset(
            version=preset.version,
            name="上次设定",
            plan=preset.plan,
        )
        with open(self.last_auto_file, 'w', encoding='utf-8') as f:
            json.dump(preset_to_save.model_dump(mode='json'), f, ensure_ascii=False, indent=2)
    
    def load_last_auto(self) -> Optional[AutoLivePreset]:
        """加载上次自动演出设定"""
        if not self.last_auto_file.exists():
            return None
        try:
            with open(self.last_auto_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return AutoLivePreset.model_validate(data)
        except Exception:
            return None
    
    def clear_last_auto(self) -> None:
        """清除上次设定"""
        if self.last_auto_file.exists():
            self.last_auto_file.unlink()
