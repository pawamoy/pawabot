from pathlib import Path

from platformdirs import PlatformDirs

_dirs = PlatformDirs("pawabot", "pawamoy")


def get_cache_dir() -> Path:
    path = _dirs.user_cache_path
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_config_dir() -> Path:
    path = _dirs.user_config_path
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_data_dir() -> Path:
    path = _dirs.user_data_path
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_runtime_dir() -> Path:
    path = _dirs.user_runtime_path
    path.mkdir(parents=True, exist_ok=True)
    return path
