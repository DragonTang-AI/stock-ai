"""
hk_lot_size.py — 港股每手股数查询
"""
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# 模块加载时一次性读取
_DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "hk_lot_sizes.json"
_lot_sizes: dict[str, int] = {}

try:
    with open(_DATA_FILE) as f:
        _lot_sizes = json.load(f)
    logger.info(f"Loaded {len(_lot_sizes)} HK lot sizes from {_DATA_FILE}")
except Exception as e:
    logger.warning(f"Failed to load HK lot sizes: {e}, using empty mapping")


def get_lot_size(code: str) -> int:
    """
    获取港股每手股数。

    Args:
        code: 股票代码（5位纯数字，如 "00700"）
    
    Returns:
        每手股数，未找到时默认返回 100
    """
    # 去掉可能的后缀 .HK
    code = code.replace(".HK", "").replace(".hk", "").strip()
    return _lot_sizes.get(code, 100)


def is_hk_symbol(symbol: str) -> bool:
    """判断是否为港股（symbol 以 .HK 结尾或包含 hk 前缀）"""
    s = symbol.strip().upper()
    return s.endswith(".HK") or s.startswith("HK")
