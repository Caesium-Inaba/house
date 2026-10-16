"""WebUI 启动器：uv run python webui.py [--port 8000] [--dev]"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

# 启用清单里已有模组时，在任何 house.core 导入前重载数据（非空清单才触发）
from house.core import mods as _mods

if _mods.enabled_folders():
    from house.core import traits as _traits

    _traits.reload_data()

from house.web.server import main

if __name__ == "__main__":
    main()
