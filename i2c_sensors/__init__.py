# """i2c_sensors package.

# Lightweight package initializer: exposes package version and lazily imports
# top-level submodules on attribute access.
# """

# from importlib import import_module
# import pkgutil
# from types import ModuleType


# # package version: try to import from a local _version module if present
# try:
#     from ._version import __version__  # type: ignore
# except Exception:
#     __version__ = "0.0.0"

# # discover top-level submodules in this package
# _submodules = sorted([name for _, name, _ in pkgutil.iter_modules(__path__)])

# __all__ = _submodules + ["__version__"]

# def __getattr__(name: str) -> ModuleType:
#     """Lazy import for top-level submodules (PEP 562)."""
#     if name in _submodules:
#         module = import_module(f"{__name__}.{name}")
#         globals()[name] = module
#         return module
#     raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

# def __dir__():
#     return sorted(list(globals().keys()) + _submodules)