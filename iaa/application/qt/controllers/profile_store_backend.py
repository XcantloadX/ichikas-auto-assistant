from __future__ import annotations

from PySide6.QtCore import QObject, Property, Signal


class ProfileStoreBackend(QObject):
    currentProfileChanged = Signal()
    profilesChanged = Signal()

    def __init__(self, settings_controller: QObject, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._settings_controller = settings_controller
        self._current_profile_name = ''
        self._profiles_json = '{"profiles":[]}'

        self._refresh_current_profile()
        self._refresh_profiles()

        self._settings_controller.currentProfileChanged.connect(self._refresh_current_profile)
        self._settings_controller.profilesChanged.connect(self._refresh_profiles)

    def _get_current_profile_name(self) -> str:
        return self._current_profile_name

    def _get_profiles_json(self) -> str:
        return self._profiles_json

    def _refresh_current_profile(self, name: str | None = None) -> None:
        next_name = name if name is not None else self._settings_controller.currentProfileName()
        if next_name == self._current_profile_name:
            return
        self._current_profile_name = next_name
        self.currentProfileChanged.emit()

    def _refresh_profiles(self) -> None:
        next_profiles_json = self._settings_controller.profilesJson()
        if next_profiles_json == self._profiles_json:
            return
        self._profiles_json = next_profiles_json
        self.profilesChanged.emit()

    currentProfileName = Property(str, _get_current_profile_name, notify=currentProfileChanged)
    profilesJson = Property(str, _get_profiles_json, notify=profilesChanged)
