import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import config as C  # noqa: E402


@pytest.fixture(scope="session")
def raw() -> pd.DataFrame:
    """Independent source of truth: the untouched Excel sheet (not the cleaned DB)."""
    return pd.read_excel(C.RAW_XLSX, sheet_name="July")
