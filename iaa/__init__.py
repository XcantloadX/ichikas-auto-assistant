try:
    from .__meta__ import __VERSION__
except ImportError:
    __VERSION__ = '(source code)'

__all__ = ['__VERSION__']