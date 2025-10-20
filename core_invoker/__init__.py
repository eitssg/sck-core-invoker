from .handler import handler as invoke

from importlib.metadata import version

__version__ = version("sck-core-invoker")

__all__ = ["invoke"]
