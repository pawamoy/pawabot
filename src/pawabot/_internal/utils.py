from xdg import XDG_CACHE_HOME, XDG_CONFIG_HOME, XDG_DATA_HOME, XDG_RUNTIME_DIR


def get_dir(xdg_dir):
    path = xdg_dir / "pawabot"
    if not path.exists():
        path.mkdir(parents=True)
    return path


def get_cache_dir():
    return get_dir(XDG_CACHE_HOME)


def get_config_dir():
    return get_dir(XDG_CONFIG_HOME)


def get_data_dir():
    return get_dir(XDG_DATA_HOME)


def get_runtime_dir():
    return get_dir(XDG_RUNTIME_DIR)
