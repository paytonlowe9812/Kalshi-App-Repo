import { create } from 'zustand';

const INDEX_QUOTE_KEY = 'kalshi_index_quote_mode';

function readStoredQuoteMode() {
  try {
    const v = localStorage.getItem(INDEX_QUOTE_KEY);
    if (v === 'prices' || v === 'odds') return v;
  } catch {
    /* ignore */
  }
  return 'odds';
}

const useAppStore = create((set) => ({
  activeTab: 'bots',
  theme: 'dark',
  licenseValid: false,
  panicActive: false,
  activeIndexId: null,
  activeBotId: null,
  bulkEditIds: [],
  firstLaunch: false,
  indexQuoteMode: typeof localStorage !== 'undefined' ? readStoredQuoteMode() : 'odds',

  setActiveTab: (tab) => set({ activeTab: tab }),
  setTheme: (theme) => {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    set({ theme });
  },
  setLicenseValid: (valid) => set({ licenseValid: valid }),
  setPanicActive: (active) => set({ panicActive: active }),
  setActiveIndexId: (id) => set({ activeIndexId: id }),
  setActiveBotId: (id) => set({ activeBotId: id }),
  setBulkEditIds: (ids) => set({ bulkEditIds: ids }),
  setFirstLaunch: (val) => set({ firstLaunch: val }),
  setIndexQuoteMode: (mode) => {
    try {
      localStorage.setItem(INDEX_QUOTE_KEY, mode);
    } catch {
      /* ignore */
    }
    set({ indexQuoteMode: mode });
  },
}));

export default useAppStore;
