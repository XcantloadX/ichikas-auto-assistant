from typing import Literal

PACKAGE_NAME_JP = 'com.sega.pjsekai'
PACKAGE_NAME_CN = 'com.hermes.mk'
PACKAGE_NAME_TW = 'com.hermes.mk.asia'

PACKAGE_NAME_MAP: dict[Literal['jp', 'tw', 'cn'], str] = {
    'jp': PACKAGE_NAME_JP,
    'tw': PACKAGE_NAME_TW,
    'cn': PACKAGE_NAME_CN,
}

BUNDLE_ID_JP = 'com.sega.pjsekai'
BUNDLE_ID_CN = 'com.hermes.mk'
BUNDLE_ID_TW = 'com.hermes.mk.asia'

BUNDLE_ID_MAP: dict[Literal['jp', 'tw', 'cn'], str] = {
    'jp': BUNDLE_ID_JP,
    'tw': BUNDLE_ID_TW,
    'cn': BUNDLE_ID_CN,
}


def package_by_server(server: Literal['jp', 'tw', 'cn']) -> str:
    return PACKAGE_NAME_MAP.get(server, PACKAGE_NAME_JP)

def bundle_id_by_server(server: Literal['jp', 'tw', 'cn']) -> str:
    return BUNDLE_ID_MAP.get(server, BUNDLE_ID_JP)

def package_name() -> str:
    """获取当前服务器的包名。

    :return: 包名。
    """
    from iaa.context import conf
    return package_by_server(conf().game.server)