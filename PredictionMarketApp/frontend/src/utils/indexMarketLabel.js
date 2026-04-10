/**
 * Default short label for a sentiment index row (used in rules as {label}.YES).
 * Avoids truncating market titles to 5 chars (which produced broken names like "ETH p").
 */
export function defaultIndexLabel(ticker, title) {
  const t = (ticker || '').trim().toUpperCase();
  const series = t.split('-')[0] || '';

  const crypto = series.match(/^KX(ETH|BTC|SOL|XRP|DOGE|BNB|HYPE)(?:15M|1H|HRLY|D)?$/i);
  if (crypto) return crypto[1].toUpperCase();

  const stripped = series.replace(/^KX/i, '').replace(/(?:15M|1H|HRLY|D)$/i, '');
  if (/^[A-Z0-9]{2,12}$/i.test(stripped)) return stripped.toUpperCase();

  const tit = (title || '').trim();
  if (tit) {
    const first = tit.split(/\s+/)[0];
    if (first && /^[A-Z]{2,6}$/i.test(first.replace(/[^A-Za-z]/g, ''))) {
      return first.replace(/[^A-Za-z]/g, '').toUpperCase().slice(0, 6);
    }
    return tit.slice(0, 12).trim();
  }

  return (series || t).slice(0, 12) || 'MKT';
}
