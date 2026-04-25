from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from iaa.config.shared import SharedConfig


class PreferencesMeta(BaseModel):
    pass


class PreferencesContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    shared: SharedConfig
    meta: PreferencesMeta = PreferencesMeta()
