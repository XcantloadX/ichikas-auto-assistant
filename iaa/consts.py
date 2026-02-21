from typing import Literal

PACKAGE_NAME_JP = 'com.sega.pjsekai'
PACKAGE_NAME_CN = 'com.hermes.mk'
PACKAGE_NAME_TW = 'com.hermes.mk.asia'

PACKAGE_NAME_MAP: dict[Literal['jp', 'tw'], str] = {
    'jp': PACKAGE_NAME_JP,
    'tw': PACKAGE_NAME_TW,
}


def package_by_server(server: Literal['jp', 'tw']) -> str:
    return PACKAGE_NAME_MAP.get(server, PACKAGE_NAME_JP)

def package_name() -> str:
    """获取当前服务器的包名。

    :return: 包名。
    """
    from iaa.context import conf
    return package_by_server(conf().game.server)