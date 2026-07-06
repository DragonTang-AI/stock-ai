"""app/selection/prescreen.py — 轻量级因子粗筛（非LLM）"""
from datetime import date
from decimal import Decimal, InvalidOperation
from app.schemas.prescreen import PrescreenCandidate, PrescreenFactorScores

_MOMENTUM_WEIGHT = 0.6
_VOLUME_WEIGHT = 0.4
_TREND_WEIGHT = 0.0  # 预留权重（趋势因子由 4-Agent 深度分析层补充）
_DEFAULT_LIMIT = 50


def _to_decimal(value) -> Decimal | None:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _momentum_score(change_pct: float) -> float:
    """涨幅%转0-100分: 0%→50分, ±10%→100/0分"""
    return max(0.0, min(100.0, 50.0 + change_pct * 5.0))


def _volume_percentile(volume: float, all_volumes: list[float]) -> float:
    if not all_volumes or volume <= 0:
        return 0.0
    sorted_vols = sorted(all_volumes)
    rank = sorted_vols.index(volume)
    if len(sorted_vols) == 1:
        return 100.0
    return round(rank / (len(sorted_vols) - 1) * 100, 4)


def _trend_score(change_pct: float, volume: float, avg_volume: float) -> float:
    """趋势分：基于价量配合度（change_pct 与量比方向一致给高分）"""
    if avg_volume <= 0:
        return 50.0
    vol_ratio = volume / avg_volume
    direction = 1 if change_pct >= 0 else -1
    vol_score = min(vol_ratio / 2.0, 1.0)  # vol_ratio>2x给满分
    base = 50.0 + direction * 25.0
    return max(0.0, min(100.0, base + (vol_score - 0.5) * 25.0))


def run_prescreen(
    stocks: list[dict],
    *,
    market: str = "A",
    trade_date: str | None = None,
    limit: int = _DEFAULT_LIMIT,
) -> list[PrescreenCandidate]:
    """
    基于实时行情数据进行粗筛评分（4-Agent 前置步骤）。

    因子:
    - 动量(60%): 涨幅越大分数越高
    - 量比(40%): 成交量在候选池内的百分位

    Args:
        stocks: 行情字典列表（symbol/price/change_pct/volume 等）
        market: 市场代码
        trade_date: 交易日期（YYYY-MM-DD）
        limit: 返回上限
    """
    if not stocks:
        return []

    volumes = [float(s.get("volume", 0) or 0) for s in stocks]
    avg_vol = sum(volumes) / len(volumes) if volumes else 0.0
    effective_date = trade_date or ""

    scored: list[tuple[float, dict]] = []
    for s in stocks:
        change = float(s.get("change_pct") or s.get("change") or 0)
        volume = float(s.get("volume") or 0)
        mom = _momentum_score(change)
        vol_score = _volume_percentile(volume, volumes)
        composite = round(mom * _MOMENTUM_WEIGHT + vol_score * _VOLUME_WEIGHT, 4)
        scored.append((composite, s))

    scored.sort(key=lambda x: (-x[0], x[1].get("symbol", "")))
    effective_limit = max(1, min(limit, _DEFAULT_LIMIT))

    candidates: list[PrescreenCandidate] = []
    for idx, (score, s) in enumerate(scored[:effective_limit], start=1):
        change = float(s.get("change_pct") or s.get("change") or 0)
        volume = float(s.get("volume") or 0)
        price = s.get("price")
        close_str = str(price) if price is not None else "0.0"

        candidates.append(
            PrescreenCandidate(
                rank=idx,
                market=market,
                symbol=s.get("symbol", ""),
                symbol_name=s.get("name"),
                trade_date=effective_date,
                close=close_str,
                composite_score=score,
                factor_scores=PrescreenFactorScores(
                    momentum=round(_momentum_score(change), 4),
                    volume_activity=round(_volume_percentile(volume, volumes), 4),
                    trend=round(_trend_score(change, volume, avg_vol), 4),
                ),
            )
        )
    return candidates
