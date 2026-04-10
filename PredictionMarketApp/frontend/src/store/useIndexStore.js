import { create } from 'zustand';

const useIndexStore = create((set) => ({
  indexes: [],
  liveData: null,
  loading: false,

  setIndexes: (indexes) => set({ indexes }),
  setLiveData: (data) => set({ liveData: data }),

  fetchIndexes: async () => {
    set({ loading: true });
    try {
      const res = await fetch('/api/indexes');
      const data = await res.json();
      set({ indexes: data, loading: false });
    } catch {
      set({ loading: false });
    }
  },

  fetchLiveData: async (indexId) => {
    if (!indexId) return;
    try {
      const res = await fetch(`/api/indexes/${indexId}/live`);
      const data = await res.json();
      set({ liveData: data });
    } catch {
      /* keep stale data */
    }
  },
}));

export default useIndexStore;
