"""pytest 경로 설정: src 레이아웃 패키지를 import 가능하게 한다."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
