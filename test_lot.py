from app.engine.signal_generator import _round_lot_quantity, _is_hk_symbol
from app.services.hk_lot_size import get_lot_size

print('=== HK lot tests ===')
for sym in ['00700.HK', '01810.HK', '00175.HK']:
    code = sym.replace('.HK','')
    lot = get_lot_size(code)
    print(f'{sym} ({code}): buy 250 => {_round_lot_quantity("buy", 250, sym)} (lot={lot})')
    print(f'{sym} ({code}): sell 350 => {_round_lot_quantity("sell", 350, sym)} (lot={lot})')

print('\n=== A-share lot tests ===')
for sym in ['600036', '300750']:
    print(f'{sym}: buy 250 => {_round_lot_quantity("buy", 250, sym)}')
    print(f'{sym}: sell 350 => {_round_lot_quantity("sell", 350, sym)}')

print('\n=== _is_hk_symbol ===')
for s in ['00700.HK', '00700.hk', '600036', '09988.HK']:
    print(f'{s}: {_is_hk_symbol(s)}')
