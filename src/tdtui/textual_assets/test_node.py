from pathlib import Path
import os


def _dir_has_py(path: Path) -> bool:
    try:
        for root, dirs, files in os.walk(path):
            if any(f.endswith(".py") for f in files):
                return True
    except PermissionError:
        return False
    return False


print(_dir_has_py("/Users/danieladayev/test-tui/tabsdata-tui/src/tdtui.egg-info"))
