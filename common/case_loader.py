"""读取 data/cases.json，返回用例数据。"""
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_cases(filename="cases.json"):
    path = DATA_DIR / filename
    with path.open(encoding="utf-8-sig") as f:
        return json.load(f)