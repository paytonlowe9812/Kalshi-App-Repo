import React, { useEffect, useState, useCallback } from 'react';
import MarketRow from './MarketRow';
import MarketCard from './MarketCard';
import MarketDetail from './MarketDetail';
import SavedListsSection from './SavedListsSection';
import useBotStore from '../../store/useBotStore';

export default function MarketBrowser() {
  const [markets, setMarkets] = useState([]);
  const [favorites, setFavorites] = useState([]);
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');
  const [horizon, setHorizon] = useState('');
  const [sortBy, setSortBy] = useState('volume');
  const [sortDir, setSortDir] = useState('desc');
  const [view, setView] = useState('list');
  const [selectedMarket, setSelectedMarket] = useState(null);
  const [loading, setLoading] = useState(false);
  const { fetchBots } = useBotStore();

  const fetchMarkets = useCallback(async () => {
    setLoading(true);
    const params = new URLSearchParams();
    if (search) params.set('search', search);
    if (category) params.set('category', category);
    if (horizon) params.set('horizon', horizon);
    if (sortBy) params.set('sort_by', sortBy);
    if (sortBy) params.set('sort_dir', sortDir);
    const limit = search || horizon ? 80 : 10;
    params.set('limit', String(limit));
    try {
      const res = await fetch(`/api/markets?${params}`);
      const data = await res.json();
      setMarkets(data.markets || []);
    } catch {
      setMarkets([]);
    }
    setLoading(false);
  }, [search, category, horizon, sortBy, sortDir]);

  const fetchFavorites = async () => {
    try {
      const res = await fetch('/api/markets/favorites');
      const data = await res.json();
      setFavorites(data.map((f) => f.ticker));
    } catch {
      setFavorites([]);
    }
  };

  useEffect(() => {
    fetchMarkets();
    fetchFavorites();
    fetchBots();
  }, []);

  useEffect(() => {
    const debounce = setTimeout(fetchMarkets, search ? 400 : 100);
    return () => clearTimeout(debounce);
  }, [fetchMarkets, search, category, horizon, sortBy, sortDir]);

  const toggleFavorite = async (ticker) => {
    if (favorites.includes(ticker)) {
      await fetch(`/api/markets/${ticker}/favorite`, { method: 'DELETE' });
      setFavorites((prev) => prev.filter((t) => t !== ticker));
    } else {
      await fetch(`/api/markets/${ticker}/favorite`, { method: 'POST' });
      setFavorites((prev) => [...prev, ticker]);
    }
  };

  const favMarkets = markets.filter((m) => favorites.includes(m.ticker));
  const otherMarkets = markets.filter((m) => !favorites.includes(m.ticker));
  const isBrowsing = !search;

  const horizonLabels = {
    '15m': '15M',
    hourly: 'HOURLY',
    daily: 'DAILY',
    weekly: 'WEEKLY',
    monthly: 'MONTHLY',
    annual: 'ANNUAL',
    one_time: 'ONE-TIME',
  };

  return (
    <div className="h-full flex flex-col">
      <div className="px-2 md:px-3 py-2 border-b border-terminal-border-dim space-y-2 md:space-y-0">
        <div className="flex items-center gap-1.5">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="SEARCH MARKETS..."
            className="input-field text-xs md:text-sm flex-1"
          />
          <div className="hidden md:flex border border-terminal-border-dim overflow-hidden">
            <button
              onClick={() => setView('list')}
              className={`px-2 py-1 text-xs font-mono ${view === 'list' ? 'bg-terminal-amber-faint text-terminal-amber-bright border-r border-terminal-border-dim' : 'text-terminal-amber-dim hover:bg-terminal-amber-faint border-r border-terminal-border-dim'}`}
            >
              LIST
            </button>
            <button
              onClick={() => setView('card')}
              className={`px-2 py-1 text-xs font-mono ${view === 'card' ? 'bg-terminal-amber-faint text-terminal-amber-bright' : 'text-terminal-amber-dim hover:bg-terminal-amber-faint'}`}
            >
              CARD
            </button>
          </div>
        </div>
        <div className="flex items-center gap-2 overflow-x-auto scrollbar-none">
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="input-field text-xs flex-shrink-0"
          >
            <option value="">ALL</option>
            <option value="crypto">CRYPTO</option>
            <option value="politics">POLITICS</option>
            <option value="economics">ECONOMICS</option>
            <option value="sports">SPORTS</option>
            <option value="weather">WEATHER</option>
          </select>
          <select
            value={horizon}
            onChange={(e) => setHorizon(e.target.value)}
            className="input-field text-xs flex-shrink-0 max-w-[140px]"
            title="Filter by rough time to expiry / series cadence"
          >
            <option value="">ANY HORIZON</option>
            <option value="15m">15 MIN</option>
            <option value="hourly">HOURLY</option>
            <option value="daily">DAILY</option>
            <option value="weekly">WEEKLY</option>
            <option value="monthly">MONTHLY</option>
            <option value="annual">ANNUAL</option>
            <option value="one_time">ONE-TIME</option>
          </select>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="input-field text-xs flex-shrink-0"
          >
            <option value="volume">VOLUME</option>
            <option value="close_date">EXPIRY</option>
            <option value="">NONE</option>
          </select>
          {sortBy && (
            <button
              onClick={() => setSortDir((d) => d === 'desc' ? 'asc' : 'desc')}
              className="input-field text-xs flex-shrink-0 px-2 py-1 font-mono cursor-pointer hover:bg-terminal-amber-faint"
              title={sortDir === 'desc' ? 'Descending (click to toggle)' : 'Ascending (click to toggle)'}
            >
              {sortDir === 'desc' ? 'DESC v' : 'ASC ^'}
            </button>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        <SavedListsSection />
        {loading && (
          <div className="flex items-center justify-center h-32 text-xs text-terminal-amber-dim font-mono">
            LOADING MARKETS...
          </div>
        )}

        {favMarkets.length > 0 && (
          <div>
            <div className="px-4 py-1.5 text-[10px] text-terminal-amber-bright uppercase tracking-wider bg-terminal-amber-faint border-b border-terminal-border-dim font-mono text-glow-sm">
              FAVORITES
            </div>
            {view === 'list'
              ? favMarkets.map((m) => (
                  <React.Fragment key={m.ticker}>
                    <MarketRow
                      market={m}
                      isFavorite
                      onToggleFavorite={toggleFavorite}
                      onSelect={setSelectedMarket}
                      selected={selectedMarket?.ticker === m.ticker}
                    />
                    {selectedMarket?.ticker === m.ticker && (
                      <MarketDetail market={m} onClose={() => setSelectedMarket(null)} />
                    )}
                  </React.Fragment>
                ))
              : (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 p-3">
                  {favMarkets.map((m) => (
                    <MarketCard key={m.ticker} market={m} isFavorite onToggleFavorite={toggleFavorite} onSelect={setSelectedMarket} />
                  ))}
                </div>
              )
            }
          </div>
        )}

        {isBrowsing && !loading && otherMarkets.length > 0 && (
          <div className="px-4 py-1.5 text-[10px] text-terminal-amber-dim uppercase tracking-wider border-b border-terminal-border-dim/50 bg-terminal-panel font-mono">
            {category ? `TOP ${category.toUpperCase()} MARKETS` : 'SUGGESTED MARKETS'}
            {horizon ? ` -- ${horizonLabels[horizon] || horizon.toUpperCase()}` : ''}
            {' '}
            -- BY {sortBy ? `${sortBy.toUpperCase()} ${sortDir === 'asc' ? 'ASC' : 'DESC'}` : 'DEFAULT'}
          </div>
        )}

        {view === 'list' ? (
          <>
            {!loading && otherMarkets.length === 0 && favMarkets.length === 0 && (
              <div className="text-center text-xs text-terminal-amber-dim font-mono py-12">
                NO MARKETS FOUND
              </div>
            )}
            <div className="hidden md:flex items-center gap-3 px-4 py-1.5 text-[10px] text-terminal-amber-dim uppercase tracking-wider border-b border-terminal-border-dim/50 bg-terminal-panel font-mono">
              <span className="w-4" />
              <span className="w-32">TICKER</span>
              <span className="flex-1">TITLE</span>
              <span className="w-20 text-right">EXPIRES</span>
              <span className="w-14 text-right">YES</span>
              <span className="w-14 text-right">NO</span>
              <span className="w-16 text-right">VOL</span>
            </div>
            {otherMarkets.map((m) => (
              <React.Fragment key={m.ticker}>
                <MarketRow
                  market={m}
                  isFavorite={false}
                  onToggleFavorite={toggleFavorite}
                  onSelect={setSelectedMarket}
                  selected={selectedMarket?.ticker === m.ticker}
                />
                {selectedMarket?.ticker === m.ticker && (
                  <MarketDetail market={m} onClose={() => setSelectedMarket(null)} />
                )}
              </React.Fragment>
            ))}
          </>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 p-3">
            {otherMarkets.map((m) => (
              <MarketCard
                key={m.ticker}
                market={m}
                isFavorite={false}
                onToggleFavorite={toggleFavorite}
                onSelect={setSelectedMarket}
              />
            ))}
          </div>
        )}
      </div>

      {selectedMarket && view === 'card' && (
        <MarketDetail market={selectedMarket} onClose={() => setSelectedMarket(null)} />
      )}
    </div>
  );
}
