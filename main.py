import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

# 启用清单里已有模组时，在任何 house.core 导入前重载数据（非空清单才触发）
from house.core import mods as _mods

if _mods.enabled_folders():
    from house.core import traits as _traits

    _traits.reload_data()

from house.ui.app_landscape import run


def main():
    run()


if __name__ == "__main__":
    main()
