from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DAILY_SCRIPTS_DIR = PROJECT_ROOT / ".agents" / "skills" / "daily-a-share-news-impact" / "scripts"
INDUSTRY_CHAIN_SCRIPTS_DIR = PROJECT_ROOT / ".agents" / "skills" / "industry-chain-analysis" / "scripts"

for _dir in (PROJECT_ROOT, DAILY_SCRIPTS_DIR, INDUSTRY_CHAIN_SCRIPTS_DIR):
    if str(_dir) not in sys.path:
        sys.path.insert(0, str(_dir))
