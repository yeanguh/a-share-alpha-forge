# Retail VOC

Use retail VOC as a contrarian and crowding signal. Do not treat it as a direct
recommendation signal. The default interpretation is to avoid standing on the
same side as crowded retail opinion unless main capital recognition and
14-trading-day K-line/volume confirmation support that side.

## Accessible Sources

Use only public or authorized data:

- Stock forums and communities: Eastmoney Guba, Xueqiu public posts, Tonghuashun
  comments, broker app hot lists when accessible.
- Search and attention proxies: stock keyword search heat, watchlist ranking,
  discussion volume, hot-comment direction.
- Investor Q&A and disclosure channels: exchange interactive platforms,
  official investor-relations Q&A, company announcements.
- Market microstructure proxies: small-order activity when available,
  limit-up/limit-down chasing, turnover spikes with weak main capital.

If raw user-level VOC is unavailable, state that the analysis uses public VOC
proxies. Do not collect or expose personal data.

## Scoring Retail Sentiment

Score `retail_sentiment` from 0 to 5:

- `5`: extreme retail chasing or panic; comment heat is high and language is
  one-sided.
- `4`: strong retail attention, high discussion heat, and visible chasing or
  fear.
- `3`: normal attention with mixed views.
- `2`: low attention or fading participation.
- `1`: very low attention or retail abandonment.
- `0`: VOC data unavailable.

## Contrarian Interpretation

- Positive news plus very hot retail VOC but weak main capital is a crowding
  risk. Exclude from beneficiary columns unless capital recognition confirms.
- Positive news plus moderate retail VOC and strong main capital is healthier.
- Positive news plus very hot retail VOC can remain eligible when main capital
  recognition and 14-day volume both confirm the move. In that case, describe
  the heat as crowding risk instead of flipping the stock into a negative or
  pressure view.
- Negative news plus retail panic but stabilizing main capital can signal
  oversold observation, not automatic pressure inclusion.
- Negative news plus retail optimism and weak main capital is a stronger risk
  signal.
- If retail VOC and main capital conflict, follow main capital and K-line/volume
  confirmation first.
- Do not mechanically take the opposite side of every retail view. Use
  contrarian interpretation only after checking whether main capital is
  accumulating, distributing, or staying neutral.

## Scoring Impact

`retail_sentiment` measures retail crowding intensity, not recommendation
quality. The stock scoring helper converts it into `retail_voc_quality_score`:

- Balanced or mixed VOC is healthier than one-sided chasing or panic.
- Extreme retail VOC reduces the research score unless main capital and volume
  quality separately justify inclusion.
- Missing VOC data receives a neutral-low quality score and should reduce final
  confidence in the stock detail table.

## Review Calibration

The June 2026 intraday review showed that strong policy mainlines can overpower
retail crowding signals for several sessions. Apply this calibration in future
runs:

- Do not use hot retail VOC alone to downgrade a stock from a confirmed
  positive mainline.
- Require both main-capital weakness and price/volume deterioration before
  converting a hot mainline stock into a pressure candidate.
- Keep overheated but institutionally confirmed stocks in the mainline leader
  table as crowded leaders when they fail the stricter opportunity gate.
