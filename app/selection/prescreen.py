"""app/selection/prescreen.py — 轻量级因子粗筛（非LLM）"""
from decimal import Decimal, InvalidOperation
from app.schemas.prescreen import PrescreenCandidate, PrescreenFactorScores

_MOMENTUM_WEIGHT = 0.6
_VOLUME_WEIGHT = 0.4
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


def run_prescreen(
    stocks: list[dict],
    *,
    limit: int = _DEFAULT_LIMIT,
) -> list[PrescreenCandidate]:
    """
    基于实时行情数据进行粗筛评分。

    因子:
    - 动量(60%): 涨幅越大分数越高
    - 量比(40%): 成交量在候选池内的百分位
    """
    volumes = [s.get("volume", 0) or 0 for s in stocks]
    max_vol = max(volumes) if volumes else 1

    scored: list[tuple[float, dict]] = []
    for s in stocks:
        change = s.get("change_pct") or s.get("change") or 0
        volume = s.get("volume") or 0
        mom = _momentum_score(float(change))
        vol_score = _volume_percentile(float(volume), volumes)
        composite = round(mom * _MOMENTUM_WEIGHT + vol_score * _VOLUME_WEIGHT, 4)
        scored.append((composite, s))

    scored.sort(key=lambda x: (-x[0], x[1].get("symbol", "")))
    effective_limit = max(1, min(limit, _DEFAULT_LIMIT))

    candidates: list[PrescreenCandidate] = []
    for idx, (score, s) in enumerate(scored[:effective_limit], start=1):
        change = float(s.get("change_pct") or s.get("change") or 0)
        volume = float(s.get("volume") or 0)
        candidates.append(
            PrescreenCandidate(
                rank=idx,
                symbol=s.get("symbol", ""),
                name=s.get("name"),
                price=s.get("price"),
                change_pct=change,
                volume=volume,
                composite_score=score,
                factor_scores=PrescreenFactorScores(
                    momentum=round(_momentum_score(change), 4),
                    volume_activity=round(_volume_percentile(volume, volumes), 4),
                ),
            )
        )
    return candidates
