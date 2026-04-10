import React from 'react';

function fmt(n) {
  if (n == null || Number.isNaN(n)) return '--';
  return Math.round(Number(n));
}

/**
 * @param {'prices' | 'odds'} quoteMode - Kalshi-style: prices = bid/ask per side; odds = implied fair % from last/mid.
 */
export default function CoinTile({
  label,
  quoteMode,
  yesBid,
  yesAsk,
  noBid,
  noAsk,
  yesOdds,
  noOdds,
  ticker,
}) {
  const bullish = Number(yesOdds) > 50;
  const priceMode = quoteMode === 'prices';

  const box =
    'flex-shrink-0 w-[56px] md:w-[62px] h-9 md:h-[38px] py-0.5 flex flex-col items-center justify-center font-mono cursor-default select-none border leading-tight';

  return (
    <div
      className={`${box} ${
        bullish
          ? 'bg-terminal-green/30 border-terminal-green-bright/40'
          : 'bg-terminal-red/20 border-terminal-red/40'
      }`}
      title={
        priceMode
          ? `${ticker} | YES bid/ask ${fmt(yesBid)}/${fmt(yesAsk)}c NO bid/ask ${fmt(noBid)}/${fmt(noAsk)}c (order book)`
          : `${ticker} | YES ${fmt(yesOdds)}% NO ${fmt(noOdds)}% implied (last or mid; not bid/ask)`
      }
    >
      <span className="font-semibold text-terminal-amber text-[9px] truncate max-w-full px-0.5">
        {label}
      </span>
      {priceMode ? (
        <div className="flex flex-col items-center gap-0 text-[7px] leading-tight w-full px-0.5">
          <div className="text-terminal-green-text">
            Y {fmt(yesBid)}/{fmt(yesAsk)}
          </div>
          <div className="text-terminal-red-text">
            N {fmt(noBid)}/{fmt(noAsk)}
          </div>
        </div>
      ) : (
        <div className="flex gap-0.5 text-[7px] md:text-[8px] items-center justify-center w-full px-0.5">
          <span className="text-terminal-green-text">{fmt(yesOdds)}%</span>
          <span className="text-terminal-amber-dim">/</span>
          <span className="text-terminal-red-text">{fmt(noOdds)}%</span>
        </div>
      )}
    </div>
  );
}
