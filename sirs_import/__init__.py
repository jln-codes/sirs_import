from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("sirs_import")
except PackageNotFoundError:
    __version__ = "0.0.0.dev"
