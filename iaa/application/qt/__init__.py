__all__ = ['main']


def __getattr__(name):
    if name == 'main':
        from .index import main as _main
        return _main
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
