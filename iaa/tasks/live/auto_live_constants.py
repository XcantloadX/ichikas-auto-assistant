AP_KEEP_UNCHANGED = '__ap_keep__'
SONG_KEEP_UNCHANGED = '__song_keep__'
LAST_PRESET_NAME = '__last_preset__'
PRESET_CLEAR_10 = '__preset_clear_10__'
PRESET_FC_10 = '__preset_fc_10__'
PRESET_LEADER_COUNT = '__preset_leader_count__'

LEGACY_AP_KEEP = frozenset({'保持现状', AP_KEEP_UNCHANGED})
LEGACY_SONG_KEEP = frozenset({'保持不变', SONG_KEEP_UNCHANGED})
LEGACY_LAST_PRESET_NAME = '上次设定'
LEGACY_PRESET_CLEAR_10 = 'CLEAR 10 首歌'
LEGACY_PRESET_FC_10 = 'FC 10 次'
LEGACY_PRESET_LEADER_COUNT = '队长次数'

# TODO: 后续引入配置迁移，删除这些旧的映射
def preset_name_matches(name: str, preset_id: str) -> bool:
    legacy = {
        PRESET_CLEAR_10: LEGACY_PRESET_CLEAR_10,
        PRESET_FC_10: LEGACY_PRESET_FC_10,
        PRESET_LEADER_COUNT: LEGACY_PRESET_LEADER_COUNT,
        LAST_PRESET_NAME: LEGACY_LAST_PRESET_NAME,
    }.get(preset_id)
    if name == preset_id:
        return True
    return legacy is not None and name == legacy