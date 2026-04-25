from kotonebot.errors import KotonebotError

class IaaError(KotonebotError):
    pass

class IaaFriendlyError(IaaError):
    pass

class SpecifiedSongLockedError(IaaFriendlyError):
    def __init__(self, song_name: str) -> None:
        super().__init__(f'指定歌曲「{song_name}」尚未解锁。')

class ContextNotInitializedError(IaaError):
    def __init__(self) -> None:
        super().__init__('Context not initialized. Call init() first.')