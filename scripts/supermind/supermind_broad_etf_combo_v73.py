# 宽基ETF趋势权重策略 v73
# 相比 v72：趋势强时略提高创业板弹性，趋势弱时更集中转向沪深300防守。

from mindgo_api import *


def init(context):
    set_benchmark('000300.SH')
    set_commission(PerShare(type='stock', cost=0.0002))
    set_slippage(PriceSlippage(0.005))
    set_volume_limit(0.25, 0.50)
    context.cyb = '159915.SZ'
    context.zz500 = '510500.SH'
    context.hs300 = '510310.SH'
    context.rebalance_days = 20
    context.trade_days = 0


def before_trading(context):
    log.info('盘前准备完成。')


def is_trend_up(security):
    df = history(security, ['close'], 150, '1d', False, 'pre')
    if df is None or df.empty or len(df) < 120:
        return True

    close = df['close']
    price = close.iloc[-1]
    ma20 = close.iloc[-20:].mean()
    ma60 = close.iloc[-60:].mean()
    ma120 = close.iloc[-120:].mean()
    return price > ma120 and ma20 > ma60 * 0.99


def rebalance(context):
    cyb_up = is_trend_up(context.cyb)
    zz500_up = is_trend_up(context.zz500)

    cyb_weight = 0.50 if cyb_up else 0.15
    zz500_weight = 0.30 if zz500_up else 0.20
    hs300_weight = max(0.0, 1.0 - cyb_weight - zz500_weight)

    log.info(
        '趋势权重 cyb_up=%s zz500_up=%s weights: cyb=%.2f zz500=%.2f hs300=%.2f' %
        (cyb_up, zz500_up, cyb_weight, zz500_weight, hs300_weight)
    )
    order_target_percent(context.cyb, cyb_weight)
    order_target_percent(context.zz500, zz500_weight)
    order_target_percent(context.hs300, hs300_weight)


def handle_bar(context, bar_dict):
    if context.trade_days == 0 or context.trade_days % context.rebalance_days == 0:
        rebalance(context)
    context.trade_days += 1


def after_trading(context):
    log.info('宽基ETF趋势权重策略 v73 收盘。')
