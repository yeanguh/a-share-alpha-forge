# 三日趋势承接买点策略 v20
# 目标：整体趋势上涨、有资金/量能承接、K线买点不过度追高；持有满 3 个交易日仍未上涨才卖出。
# 参考：巴菲特 alpha 的质量/估值/动量/低波动维度，以及奥肖内西/布兰德的估值不过贵、低负债思路。
# 行业偏好：优先 AI 算力链、光通信、存储芯片、PCB、半导体设备、液冷、AI 上游材料等 2025-2030 主线。
# 兼容 Supermind：get_iwencai 只在 init 中注册；辅助函数全部放在 handle_bar 前。
# 设计重点：避免候选池为空导致“策略没生效、没数”。

from mindgo_api import *


def refresh_daily_state(context):
    today = get_datetime().strftime('%Y-%m-%d')
    if context.last_refresh_date == today:
        return

    context.last_refresh_date = today
    context.market_ok = check_market_regime(context)
    update_portfolio_risk(context)

    theme_optical_pool = list(getattr(context, 'theme_optical_pool', []))
    theme_cpo_pool = list(getattr(context, 'theme_cpo_pool', []))
    theme_copper_cable_pool = list(getattr(context, 'theme_copper_cable_pool', []))
    theme_connector_pool = list(getattr(context, 'theme_connector_pool', []))
    theme_pcb_pool = list(getattr(context, 'theme_pcb_pool', []))
    theme_glass_pool = list(getattr(context, 'theme_glass_pool', []))
    theme_abf_pool = list(getattr(context, 'theme_abf_pool', []))
    theme_storage_pool = list(getattr(context, 'theme_storage_pool', []))
    theme_equip_pool = list(getattr(context, 'theme_equip_pool', []))
    theme_ai_server_pool = list(getattr(context, 'theme_ai_server_pool', []))
    theme_liquid_pool = list(getattr(context, 'theme_liquid_pool', []))
    theme_material_pool = list(getattr(context, 'theme_material_pool', []))
    theme_photoresist_pool = list(getattr(context, 'theme_photoresist_pool', []))
    theme_gas_pool = list(getattr(context, 'theme_gas_pool', []))
    theme_ccl_pool = list(getattr(context, 'theme_ccl_pool', []))
    theme_copper_pool = list(getattr(context, 'theme_copper_pool', []))
    theme_mlcc_pool = list(getattr(context, 'theme_mlcc_pool', []))
    theme_core_pool = unique_list(
        theme_optical_pool + theme_cpo_pool + theme_copper_cable_pool + theme_connector_pool +
        theme_pcb_pool + theme_glass_pool + theme_abf_pool + theme_storage_pool +
        theme_equip_pool + theme_ai_server_pool + theme_liquid_pool
    )
    theme_satellite_pool = unique_list(
        theme_material_pool + theme_photoresist_pool + theme_gas_pool +
        theme_ccl_pool + theme_copper_pool + theme_mlcc_pool
    )
    theme_pool = unique_list(theme_core_pool + theme_satellite_pool)
    fund_pool = list(getattr(context, 'fund_pool', []))
    quality_pool = list(getattr(context, 'quality_pool', []))
    broad_pool = list(getattr(context, 'broad_pool', []))
    context.theme_core_candidates = filter_allowed_stocks(unique_list(theme_core_pool))
    context.theme_satellite_candidates = filter_allowed_stocks(unique_list(theme_satellite_pool))
    context.theme_candidates = filter_allowed_stocks(unique_list(context.theme_core_candidates + context.theme_satellite_candidates))
    if len(context.theme_core_candidates) >= context.min_core_theme_pool:
        context.pool = filter_allowed_stocks(unique_list(context.theme_core_candidates + context.theme_satellite_candidates + fund_pool))
    else:
        context.pool = filter_allowed_stocks(unique_list(context.theme_candidates + fund_pool + quality_pool + broad_pool))

    if theme_pool:
        source = 'theme_pool+fallback'
    elif fund_pool:
        source = 'fund_pool+fallback'
    elif quality_pool:
        source = 'quality_pool+fallback'
    elif broad_pool:
        source = 'broad_pool+fallback'
    else:
        source = 'empty_pool'

    log.info(
        'daily state date=%s phase=%s market_ok=%s exposure=%.2f risk_off=%s reduce=%s force_clear=%s cooldown=%s dd=%.2f%% gdd=%.2f%% source=%s pool=%s theme=%s core=%s sat=%s opt=%s cpo=%s cable=%s conn=%s pcb=%s glass=%s abf=%s storage=%s equip=%s ai_server=%s liquid=%s mat=%s photo=%s gas=%s ccl=%s copper=%s mlcc=%s fund=%s quality=%s broad=%s' %
        (
            today, context.market_phase, context.market_ok, context.market_exposure, context.risk_off,
            context.reduce_exposure, context.force_clear, context.cooldown_days,
            context.current_drawdown * 100, context.global_drawdown * 100, source, len(context.pool),
            len(theme_pool), len(context.theme_core_candidates), len(context.theme_satellite_candidates),
            len(theme_optical_pool), len(theme_cpo_pool), len(theme_copper_cable_pool), len(theme_connector_pool),
            len(theme_pcb_pool), len(theme_glass_pool), len(theme_abf_pool), len(theme_storage_pool),
            len(theme_equip_pool), len(theme_ai_server_pool), len(theme_liquid_pool), len(theme_material_pool),
            len(theme_photoresist_pool), len(theme_gas_pool), len(theme_ccl_pool), len(theme_copper_pool),
            len(theme_mlcc_pool), len(fund_pool), len(quality_pool), len(broad_pool)
        )
    )


def unique_list(items):
    result = []
    seen = {}
    for item in items:
        if item is None:
            continue
        if item in seen:
            continue
        seen[item] = True
        result.append(item)
    return result


def filter_allowed_stocks(items):
    result = []
    for stock in items:
        if is_allowed_market(stock):
            result.append(stock)
    return result


def is_allowed_market(stock):
    if stock is None:
        return False
    code = str(stock)
    if code.endswith('.BJ'):
        return False
    if code.startswith('688') or code.startswith('689'):
        return False
    if code.startswith('8') or code.startswith('4'):
        return False
    return code.endswith('.SH') or code.endswith('.SZ')


def check_market_regime(context):
    hs300 = history('000300.SH', ['close', 'volume'], 80, '1d', False, 'pre')
    if hs300 is None or hs300.empty or len(hs300) < 60:
        log.info('沪深300数据不足，不做大盘硬拦截。')
        context.market_exposure = context.neutral_exposure
        return True

    zz500 = history('000905.SH', ['close'], 80, '1d', False, 'pre')
    cyb = history('399006.SZ', ['close'], 80, '1d', False, 'pre')
    close = hs300['close']
    volume = hs300['volume']
    ma10 = close.iloc[-10:].mean()
    ma20 = close.iloc[-20:].mean()
    ma60 = close.iloc[-60:].mean()
    high20 = close.iloc[-20:].max()
    ret1 = close.iloc[-1] / close.iloc[-2] - 1
    ret5 = close.iloc[-1] / close.iloc[-5] - 1
    vol5 = volume.iloc[-5:].mean()
    vol20 = volume.iloc[-20:].mean()

    hs_trend = close.iloc[-1] > ma20 * 0.99 and ma20 >= ma60 * 0.985
    hs_risk = ret1 > -0.025 and close.iloc[-1] > high20 * 0.90
    volume_ok = vol5 >= vol20 * 0.70
    context.market_panic = ret1 <= -0.030 or close.iloc[-1] < ma60 * 0.95
    context.market_retreat = (
        ret5 <= -0.045 or
        (close.iloc[-1] < ma20 * 0.985 and ret1 < -0.008) or
        close.iloc[-1] < high20 * 0.925
    )

    zz_trend = True
    zz_risk = True
    if zz500 is not None and (not zz500.empty) and len(zz500) >= 60:
        zz_close = zz500['close']
        zz_ma20 = zz_close.iloc[-20:].mean()
        zz_ma60 = zz_close.iloc[-60:].mean()
        zz_ret1 = zz_close.iloc[-1] / zz_close.iloc[-2] - 1
        zz_trend = zz_close.iloc[-1] > zz_ma20 * 0.985 and zz_ma20 >= zz_ma60 * 0.96
        zz_risk = zz_ret1 > -0.030 and zz_close.iloc[-1] > zz_ma60 * 0.95

    cyb_trend = True
    cyb_risk = True
    if cyb is not None and (not cyb.empty) and len(cyb) >= 60:
        cyb_close = cyb['close']
        cyb_ma20 = cyb_close.iloc[-20:].mean()
        cyb_ma60 = cyb_close.iloc[-60:].mean()
        cyb_ret1 = cyb_close.iloc[-1] / cyb_close.iloc[-2] - 1
        cyb_trend = cyb_close.iloc[-1] > cyb_ma20 * 0.985 and cyb_ma20 >= cyb_ma60 * 0.96
        cyb_risk = cyb_ret1 > -0.035 and cyb_close.iloc[-1] > cyb_ma60 * 0.94

    trend_count = 0
    if hs_trend and hs_risk:
        trend_count += 1
    if zz_trend and zz_risk:
        trend_count += 1
    if cyb_trend and cyb_risk:
        trend_count += 1

    strong = trend_count >= 3 and volume_ok
    neutral = trend_count >= 2 and ret1 > -0.030
    context.market_panic = context.market_panic or trend_count == 0

    if strong:
        context.market_phase = 'strong'
        context.market_exposure = context.normal_exposure
    elif neutral:
        context.market_phase = 'neutral'
        context.market_exposure = context.neutral_exposure
    else:
        context.market_phase = 'weak'
        context.market_exposure = context.defensive_exposure

    if context.market_retreat:
        context.market_phase = 'retreat'
        context.market_exposure = min(context.market_exposure, context.protect_exposure)

    log.info(
        'market strong=%s neutral=%s retreat=%s panic=%s trends=%s hs=%s zz=%s cyb=%s volume=%s ret1=%.4f ret5=%.4f exposure=%.2f' %
        (
            strong, neutral, context.market_retreat, context.market_panic, trend_count, hs_trend and hs_risk,
            zz_trend and zz_risk, cyb_trend and cyb_risk, volume_ok, ret1,
            ret5, context.market_exposure
        )
    )
    return not context.market_panic


def get_portfolio_value(context):
    value = getattr(context.portfolio, 'total_value', 0)
    if value and value > 0:
        return value

    stock_account = context.portfolio.stock_account
    value = getattr(stock_account, 'total_value', 0)
    if value and value > 0:
        return value

    value = getattr(stock_account, 'total_asset', 0)
    if value and value > 0:
        return value

    cash = getattr(stock_account, 'available_cash', 0)
    market_value = getattr(stock_account, 'market_value', 0)
    value = cash + market_value
    if value and value > 0:
        return value
    return 0


def update_portfolio_risk(context):
    today = get_datetime().strftime('%Y-%m-%d')
    if context.last_risk_date == today:
        return
    context.last_risk_date = today
    context.force_clear = False
    context.reduce_exposure = False

    if context.cooldown_days > 0:
        context.cooldown_days -= 1

    value = get_portfolio_value(context)
    if value <= 0:
        context.risk_off = False
        return

    if context.initial_equity <= 0:
        context.initial_equity = value

    if context.equity_peak <= 0 or value > context.equity_peak:
        context.equity_peak = value
    if context.global_equity_peak <= 0 or value > context.global_equity_peak:
        context.global_equity_peak = value

    drawdown = value / context.equity_peak - 1
    global_drawdown = value / context.global_equity_peak - 1
    context.current_drawdown = drawdown
    context.global_drawdown = global_drawdown
    context.risk_off = context.cooldown_days > 0 or drawdown <= context.soft_drawdown
    protect_profit = context.equity_peak >= context.initial_equity * (1 + context.profit_protect_start)
    global_protect_profit = context.global_equity_peak >= context.initial_equity * (1 + context.global_profit_protect_start)
    soft_line = context.profit_drawdown if protect_profit else context.soft_drawdown
    hard_line = context.profit_hard_drawdown if protect_profit else context.hard_drawdown

    if global_protect_profit and global_drawdown <= context.global_profit_hard_drawdown:
        context.cooldown_days = max(context.cooldown_days, context.cooldown_after_hard_drawdown)
        context.risk_off = True
        context.force_clear = True
        log.info('全局利润回撤 %.2f%% 触发硬保护，清仓并冷却 %s 天。' % (global_drawdown * 100, context.cooldown_days))
        clear_all_positions(context)
        context.equity_peak = value
        context.global_equity_peak = value
    elif global_protect_profit and global_drawdown <= context.global_profit_drawdown:
        context.cooldown_days = max(context.cooldown_days, context.cooldown_after_soft_drawdown)
        context.risk_off = True
        context.reduce_exposure = True
        log.info('全局利润回撤 %.2f%% 触发软保护，降到保护仓位，次日重新按市场状态评估。' % (global_drawdown * 100))
        reduce_positions_to_exposure(context, context.protect_exposure)
        context.equity_peak = value
        context.global_equity_peak = value
    elif drawdown <= hard_line:
        context.cooldown_days = max(context.cooldown_days, context.cooldown_after_hard_drawdown)
        context.risk_off = True
        context.force_clear = True
        log.info('组合回撤 %.2f%% 触发硬风控，清仓并冷却 %s 天。' % (drawdown * 100, context.cooldown_days))
        clear_all_positions(context)
        context.equity_peak = value
    elif drawdown <= soft_line:
        context.cooldown_days = max(context.cooldown_days, context.cooldown_after_soft_drawdown)
        context.risk_off = True
        context.reduce_exposure = True
        log.info('组合回撤 %.2f%% 触发软风控，降到保护仓位并暂停新开仓。' % (drawdown * 100))
        reduce_positions_to_exposure(context, context.protect_exposure)
        context.equity_peak = value


def clear_all_positions(context):
    positions = list(context.portfolio.stock_account.positions.keys())
    for stock in positions:
        record_trade_result(context, stock)
        order_target(stock, 0)
        context.hold_days.pop(stock, None)
        context.hold_day_dates.pop(stock, None)
        context.entry_price.pop(stock, None)
        context.highest_price.pop(stock, None)


def reduce_positions_to_exposure(context, target_exposure):
    positions = list(context.portfolio.stock_account.positions.keys())
    if not positions:
        return

    weight = min(target_exposure / max(len(positions), 1), context.max_single_weight)
    for stock in positions:
        order_target_percent(stock, weight)


def rebalance_existing_positions(context):
    positions = list(context.portfolio.stock_account.positions.keys())
    if not positions:
        return

    target_weight = min(context.market_exposure / context.hold_count, context.max_single_weight)
    for index, stock in enumerate(positions):
        if index >= context.hold_count:
            record_trade_result(context, stock)
            order_target(stock, 0)
            context.hold_days.pop(stock, None)
            context.hold_day_dates.pop(stock, None)
            context.entry_price.pop(stock, None)
            context.highest_price.pop(stock, None)
        else:
            order_target_percent(stock, target_weight)


def select_candidates(context):
    scored = []
    checked = 0
    scan_pool = context.pool
    if context.market_retreat and context.allow_theme_buy_in_retreat:
        scan_pool = unique_list(context.theme_core_candidates + context.theme_satellite_candidates)

    for stock in scan_pool:
        if checked >= context.max_check_count:
            break
        checked += 1
        if stock in list(context.portfolio.stock_account.positions.keys()):
            continue
        is_core_theme = stock in context.theme_core_candidates
        score = trend_support_score(stock, is_core_theme)
        if score is not None:
            if is_core_theme:
                score += context.theme_core_bonus
            elif stock in context.theme_satellite_candidates:
                score += context.theme_satellite_bonus
            scored.append((score, stock))

    scored.sort(reverse=True)
    log.info('checked=%s passed=%s' % (checked, len(scored)))
    return diversify_candidates(scored, context.hold_count)


def diversify_candidates(scored, max_count):
    result = []
    bucket_count = {}
    for score, stock in scored:
        bucket = stock_bucket(stock)
        if bucket_count.get(bucket, 0) >= 2:
            continue
        result.append(stock)
        bucket_count[bucket] = bucket_count.get(bucket, 0) + 1
        if len(result) >= max_count:
            break

    if len(result) < max_count:
        for score, stock in scored:
            if stock in result:
                continue
            result.append(stock)
            if len(result) >= max_count:
                break
    return result


def stock_bucket(stock):
    if stock.startswith('300') or stock.startswith('301'):
        return 'GEM'
    if stock.startswith('002') or stock.startswith('003'):
        return 'SME'
    if stock.startswith('60') or stock.startswith('000'):
        return 'MAIN'
    return 'OTHER'


def trend_support_score(stock, is_core_theme=False):
    df = history(stock, ['open', 'close', 'high', 'low', 'volume'], 80, '1d', False, 'pre')
    if df is None or df.empty or len(df) < 60:
        return None

    close = df['close']
    open_ = df['open']
    high = df['high']
    low = df['low']
    volume = df['volume']

    price = close.iloc[-1]
    prev_close = close.iloc[-2]
    day_ret = price / prev_close - 1
    ma5 = close.iloc[-5:].mean()
    ma10 = close.iloc[-10:].mean()
    ma20 = close.iloc[-20:].mean()
    ma60 = close.iloc[-60:].mean()
    high20 = high.iloc[-20:].max()
    low5 = low.iloc[-5:].min()
    vol5 = volume.iloc[-5:].mean()
    vol20 = volume.iloc[-20:].mean()
    vol_ratio = vol5 / max(vol20, 1)
    avg_range20 = ((high.iloc[-20:] - low.iloc[-20:]) / close.iloc[-20:]).mean()
    momentum20 = price / close.iloc[-20] - 1

    today_range = max(high.iloc[-1] - low.iloc[-1], 0.01)
    close_position = (price - low.iloc[-1]) / today_range
    upper_shadow = (high.iloc[-1] - price) / today_range
    lower_shadow = (min(open_.iloc[-1], price) - low.iloc[-1]) / today_range
    gap = open_.iloc[-1] / prev_close - 1

    trend_ok = price > ma20 and ma10 > ma20 * 0.995 and ma20 > ma60 * 0.985
    support_ok = low.iloc[-1] <= ma10 * 1.045 or low5 <= ma10 * 1.055 or price <= ma10 * 1.055
    breakout_ok = (
        is_core_theme and price >= high20 * 0.965 and price <= ma10 * 1.105 and
        price >= ma5 * 0.995 and close_position >= 0.56 and 0.85 <= vol_ratio <= 3.50
    )
    not_overheat = price <= ma20 * (1.28 if is_core_theme else 1.20) and price <= high20 * 1.025
    recover_ok = price >= ma5 * 0.99 and close_position >= 0.50
    kline_ok = upper_shadow <= 0.52 and lower_shadow >= 0.01
    volume_ok = 0.55 <= vol_ratio <= 3.20
    ret_ok = -0.035 <= day_ret <= 0.080
    gap_ok = -0.030 <= gap <= 0.055
    momentum_ok = 0.00 <= momentum20 <= (0.68 if is_core_theme else 0.55)
    low_vol_ok = avg_range20 <= (0.125 if is_core_theme else 0.110)

    if not (trend_ok and (support_ok or breakout_ok) and not_overheat and recover_ok):
        return None
    if not (kline_ok and volume_ok and ret_ok and gap_ok and momentum_ok and low_vol_ok):
        return None

    trend_score = price / ma20 - 1
    support_score = max(0, 1 - abs(price / ma10 - 1) * (5 if is_core_theme else 8))
    breakout_score = 0.35 if breakout_ok else 0
    kline_score = close_position + lower_shadow - upper_shadow
    volume_score = 1 - min(abs(vol_ratio - 1.15), 1.5) / 1.5
    momentum_score = max(0, min(momentum20, 0.30)) * 1.35
    low_vol_score = max(0, 0.095 - avg_range20)
    heat_penalty = max(day_ret - 0.045, 0) * 4 + max(momentum20 - (0.32 if is_core_theme else 0.20), 0) * 2
    return trend_score + support_score + breakout_score + kline_score + volume_score + momentum_score + low_vol_score - heat_penalty


def sell_positions(context):
    positions = list(context.portfolio.stock_account.positions.keys())
    for stock in positions:
        sync_entry_price(context, stock)
        update_hold_days(context, stock)
        if should_exit(context, stock):
            record_trade_result(context, stock)
            log.info('卖出 %s' % stock)
            order_target(stock, 0)
            context.hold_days.pop(stock, None)
            context.hold_day_dates.pop(stock, None)
            context.entry_price.pop(stock, None)
            context.highest_price.pop(stock, None)


def update_hold_days(context, stock):
    today = get_datetime().strftime('%Y-%m-%d')
    if context.hold_day_dates.get(stock) == today:
        return
    context.hold_day_dates[stock] = today
    context.hold_days[stock] = context.hold_days.get(stock, 0) + 1


def should_exit(context, stock):
    positions = context.portfolio.stock_account.positions
    if stock not in positions:
        return False

    df = history(stock, ['close', 'low', 'volume'], 30, '1d', False, 'pre')
    if df is None or df.empty or len(df) < 20:
        return False

    close = df['close']
    low = df['low']
    volume = df['volume']
    price = close.iloc[-1]
    context.highest_price[stock] = max(context.highest_price.get(stock, price), price)
    high_since_entry = context.highest_price[stock]
    ma5 = close.iloc[-5:].mean()
    ma10 = close.iloc[-10:].mean()
    ma20 = close.iloc[-20:].mean()
    vol5 = volume.iloc[-5:].mean()
    vol20 = volume.iloc[-20:].mean()

    entry = context.entry_price.get(stock)
    if entry is None or entry <= 0:
        pos = positions[stock]
        entry = getattr(pos, 'cost_basis', 0)
    if entry is None or entry <= 0:
        return False

    ret = price / entry - 1
    hold_days = context.hold_days.get(stock, 0)
    no_rise_after_3_days = hold_days >= context.max_hold_days and ret <= context.no_rise_exit_ret
    no_follow_through = hold_days >= 2 and ret <= context.confirm_exit_ret and price < ma10
    weak_two_days = hold_days >= 3 and ret <= context.two_day_exit_ret and price < ma20
    stop_loss = ret <= context.stop_loss
    take_profit = ret >= context.take_profit
    trailing_stop = ret >= context.trailing_start_ret and price <= high_since_entry * (1 - context.trailing_drop)
    break_even_stop = high_since_entry >= entry * (1 + context.break_even_start_ret) and price <= entry * (1 + context.break_even_keep_ret)
    profit_trend_break = ret >= context.profit_trend_start_ret and price < ma10 and context.market_phase == 'retreat'
    support_break = price < ma10 * 0.975 or low.iloc[-1] < ma20 * 0.97
    volume_break = price < ma5 and vol5 > vol20 * 1.50

    return (
        no_follow_through or weak_two_days or no_rise_after_3_days or stop_loss or
        take_profit or trailing_stop or break_even_stop or profit_trend_break or
        support_break or volume_break
    )


def sync_entry_price(context, stock):
    if stock in context.entry_price:
        return
    positions = context.portfolio.stock_account.positions
    if stock not in positions:
        return
    pos = positions[stock]
    cost = getattr(pos, 'cost_basis', 0)
    if cost > 0:
        context.entry_price[stock] = cost


def record_trade_result(context, stock):
    entry = context.entry_price.get(stock)
    if entry is None or entry <= 0:
        return
    df = history(stock, ['close'], 1, '1d', False, 'pre')
    if df is None or df.empty:
        return

    ret = df['close'].iloc[-1] / entry - 1
    context.trade_count += 1
    context.total_ret += ret
    if ret > 0:
        context.win_count += 1

    win_rate = context.win_count * 1.0 / context.trade_count
    avg_ret = context.total_ret * 1.0 / context.trade_count
    log.info(
        '交易统计 stock=%s ret=%.4f trades=%s win_rate=%.2f avg_ret=%.4f' %
        (stock, ret, context.trade_count, win_rate, avg_ret)
    )


def init(context):
    set_benchmark('000300.SH')
    set_commission(PerShare(type='stock', cost=0.0002))
    set_slippage(PriceSlippage(0.005))
    set_volume_limit(0.25, 0.50)

    context.hold_count = 5
    context.max_single_weight = 0.18
    context.normal_exposure = 0.92
    context.neutral_exposure = 0.60
    context.defensive_exposure = 0.20
    context.protect_exposure = 0.30
    context.retreat_theme_exposure = 0.36
    context.max_hold_days = 3
    context.no_rise_exit_ret = 0.0
    context.max_check_count = 160
    context.stop_loss = -0.035
    context.confirm_exit_ret = -0.018
    context.two_day_exit_ret = -0.006
    context.break_even_start_ret = 0.070
    context.break_even_keep_ret = 0.010
    context.profit_trend_start_ret = 0.030
    context.take_profit = 0.180
    context.trailing_start_ret = 0.100
    context.trailing_drop = 0.060
    context.soft_drawdown = -0.090
    context.hard_drawdown = -0.130
    context.profit_protect_start = 0.080
    context.profit_drawdown = -0.075
    context.profit_hard_drawdown = -0.120
    context.global_profit_protect_start = 0.100
    context.global_profit_drawdown = -0.080
    context.global_profit_hard_drawdown = -0.115
    context.cooldown_after_soft_drawdown = 1
    context.cooldown_after_hard_drawdown = 3
    context.allow_theme_buy_in_retreat = True
    context.min_core_theme_pool = 30
    context.theme_core_bonus = 0.90
    context.theme_satellite_bonus = 0.25
    context.hold_days = {}
    context.hold_day_dates = {}
    context.entry_price = {}
    context.highest_price = {}
    context.market_ok = False
    context.market_phase = 'weak'
    context.market_panic = False
    context.market_retreat = False
    context.market_exposure = 0.0
    context.risk_off = False
    context.force_clear = False
    context.reduce_exposure = False
    context.cooldown_days = 0
    context.initial_equity = 0.0
    context.equity_peak = 0.0
    context.global_equity_peak = 0.0
    context.current_drawdown = 0.0
    context.global_drawdown = 0.0
    context.pool = []
    context.theme_core_candidates = []
    context.theme_satellite_candidates = []
    context.theme_candidates = []
    context.trade_count = 0
    context.win_count = 0
    context.total_ret = 0.0
    context.last_refresh_date = ''
    context.last_buy_date = ''
    context.last_risk_date = ''

    context.theme_base_filter = (
        '非ST；非停牌；上市时间超过120天；'
        '成交额大于1亿元；换手率大于1%且小于15%；'
        '收盘价高于20日均线；20日均线大于60日均线；'
        '近20日涨幅大于-5%且小于45%；近5日涨幅小于15%；'
        '按近3日主力净流入从高到低排序'
    )

    get_iwencai('光模块概念股；' + context.theme_base_filter, 'theme_optical_pool')
    get_iwencai('CPO概念股；' + context.theme_base_filter, 'theme_cpo_pool')
    get_iwencai('高速铜缆概念股；' + context.theme_base_filter, 'theme_copper_cable_pool')
    get_iwencai('连接器概念股；' + context.theme_base_filter, 'theme_connector_pool')
    get_iwencai('PCB概念股；' + context.theme_base_filter, 'theme_pcb_pool')
    get_iwencai('玻璃基板概念股；' + context.theme_base_filter, 'theme_glass_pool')
    get_iwencai('ABF载板概念股；' + context.theme_base_filter, 'theme_abf_pool')
    get_iwencai('存储芯片概念股；' + context.theme_base_filter, 'theme_storage_pool')
    get_iwencai('半导体设备概念股；' + context.theme_base_filter, 'theme_equip_pool')
    get_iwencai('AI服务器概念股；' + context.theme_base_filter, 'theme_ai_server_pool')
    get_iwencai('液冷服务器概念股；' + context.theme_base_filter, 'theme_liquid_pool')
    get_iwencai('半导体材料概念股；' + context.theme_base_filter, 'theme_material_pool')
    get_iwencai('光刻胶概念股；' + context.theme_base_filter, 'theme_photoresist_pool')
    get_iwencai('电子特气概念股；' + context.theme_base_filter, 'theme_gas_pool')
    get_iwencai('覆铜板概念股；' + context.theme_base_filter, 'theme_ccl_pool')
    get_iwencai('铜箔概念股；' + context.theme_base_filter, 'theme_copper_pool')
    get_iwencai('MLCC概念股；' + context.theme_base_filter, 'theme_mlcc_pool')

    context.fund_query = (
        '非ST；非停牌；非科创板；非北交所；上市时间超过120天；'
        '近3日主力净流入为正；成交额大于1亿元；'
        '收盘价高于20日均线；近20日涨幅大于-3%且小于30%；'
        '近5日涨幅小于12%；换手率大于1%且小于12%；'
        '按近3日主力净流入从高到低排序'
    )
    get_iwencai(context.fund_query, 'fund_pool')

    context.quality_query = (
        '非ST；非停牌；非科创板；非北交所；上市时间超过120天；'
        '市盈率TTM大于0且小于35；市净率大于0且小于4；'
        '资产负债率小于80%；ROE大于6%；'
        '近20日涨幅大于-3%且小于28%；近5日涨幅小于10%；'
        '收盘价高于20日均线；成交额大于1亿元；'
        '按ROE从高到低排序'
    )
    get_iwencai(context.quality_query, 'quality_pool')

    context.broad_query = (
        '非ST；非停牌；非科创板；非北交所；上市时间超过120天；'
        '成交额大于1亿元；换手率大于1%且小于12%；'
        '收盘价高于20日均线；20日均线大于60日均线；'
        '近20日涨幅大于-3%且小于30%；近5日涨幅小于12%；'
        '按近20日涨幅从高到低排序'
    )
    get_iwencai(context.broad_query, 'broad_pool')


def before_trading(context):
    log.info('盘前准备完成。')


def handle_bar(context, bar_dict):
    refresh_daily_state(context)
    sell_positions(context)

    today = get_datetime().strftime('%Y-%m-%d')
    if context.last_buy_date == today:
        return

    if context.risk_off:
        if context.force_clear:
            log.info('处于硬风控/冷却期，清仓防守，今日不新开仓。')
            clear_all_positions(context)
        else:
            log.info('处于软风控/冷却期，降到保护仓位，今日不新开仓。')
            reduce_positions_to_exposure(context, context.protect_exposure)
        context.last_buy_date = today
        return

    if context.market_retreat:
        if context.allow_theme_buy_in_retreat and context.theme_candidates:
            context.market_exposure = min(context.market_exposure, context.retreat_theme_exposure)
            log.info('市场进入退潮保护，仅允许主线候选小仓位试错，目标仓位 %.2f。' % context.market_exposure)
            reduce_positions_to_exposure(context, context.protect_exposure)
        else:
            log.info('市场进入退潮保护，降到保护仓位，今日不新开仓。')
            reduce_positions_to_exposure(context, context.protect_exposure)
            context.last_buy_date = today
            return

    if not context.market_ok:
        if context.market_panic:
            log.info('大盘出现极端风险，清仓防守，今日不新开仓。')
            clear_all_positions(context)
            context.last_buy_date = today
            return
        else:
            log.info('大盘环境偏弱，使用防守仓位小额试错。')
            reduce_positions_to_exposure(context, context.defensive_exposure)

    rebalance_existing_positions(context)
    current_positions = list(context.portfolio.stock_account.positions.keys())
    available_slots = context.hold_count - len(current_positions)
    if available_slots <= 0:
        log.info('持仓数量已达到上限，今日不新开仓。')
        context.last_buy_date = today
        return

    target = select_candidates(context)[:available_slots]
    if not target:
        log.info('无合适趋势承接买点，今日不买。')
        context.last_buy_date = today
        return

    weight = min(context.market_exposure / context.hold_count, context.max_single_weight)
    for stock in target:
        is_core_entry = stock in context.theme_core_candidates
        log.info('买入趋势承接候选 %s 权重 %.2f core=%s' % (stock, weight, is_core_entry))
        order_target_percent(stock, weight)
        context.hold_days[stock] = 0
        context.hold_day_dates[stock] = today
        context.highest_price.pop(stock, None)
        context.entry_price.pop(stock, None)
    context.last_buy_date = today


def after_trading(context):
    if context.trade_count > 0:
        win_rate = context.win_count * 1.0 / context.trade_count
        avg_ret = context.total_ret * 1.0 / context.trade_count
        log.info(
            '累计统计 trades=%s win_rate=%.2f avg_ret=%.4f total_ret=%.4f' %
            (context.trade_count, win_rate, avg_ret, context.total_ret)
        )
    log.info('三日趋势承接买点策略收盘。')
