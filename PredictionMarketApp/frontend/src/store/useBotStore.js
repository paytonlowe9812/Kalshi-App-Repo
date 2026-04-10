import { create } from 'zustand';

const useBotStore = create((set) => ({
  bots: [],
  groups: [],
  ungroupedBots: [],
  loading: false,

  setBots: (bots) => set({ bots }),
  setGroups: (groups) => set({ groups }),
  setUngroupedBots: (bots) => set({ ungroupedBots: bots }),
  setLoading: (loading) => set({ loading }),

  fetchBots: async () => {
    set({ loading: true });
    try {
      const [botsRes, groupsRes] = await Promise.all([
        fetch('/api/bots'),
        fetch('/api/groups'),
      ]);
      const bots = await botsRes.json();
      const groupsData = await groupsRes.json();
      set({
        bots,
        groups: groupsData.groups || [],
        ungroupedBots: groupsData.ungrouped_bots || [],
        loading: false,
      });
    } catch {
      set({ loading: false });
    }
  },
}));

export default useBotStore;
