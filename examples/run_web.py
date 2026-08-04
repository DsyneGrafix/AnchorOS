"""Run the AnchorInsight AIN-104 web dashboard."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from anchorinsight_web import create_app


if __name__ == "__main__":
    app = create_app(ROOT / "data" / "anchorinsight.db")
    app.run(host="127.0.0.1", port=8080, debug=False)
