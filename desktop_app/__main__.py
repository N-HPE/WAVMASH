from __future__ import annotations

import faulthandler
import os
import traceback

from env_loader import ensure_env_loaded
from desktop_app.app import main


PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_PATH = os.path.join(PROJECT_DIR, "desktop_app.log")

if __name__ == "__main__":
    ensure_env_loaded()
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            faulthandler.enable(file=f, all_threads=True)
    except OSError:
        pass

    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        try:
            with open(LOG_PATH, "a", encoding="utf-8") as f:
                f.write("\n--- desktop_app crash ---\n")
                f.write(traceback.format_exc())
        except OSError:
            pass
        raise

