import { useState, useEffect } from 'react';
import useAppStore from '../store/useAppStore';

/** Bump when GET /available-variables grouping or names change (invalidates client cache). */
const CACHE_SCHEMA = 5;
const cacheByBot = new Map();
const inflightByBot = new Map();

const cacheKey = (botId) => `${botId}:${CACHE_SCHEMA}`;

export default function useBotAvailableVariables() {
  const { activeBotId } = useAppStore();
  const [groups, setGroups] = useState(() =>
    activeBotId && cacheByBot.has(cacheKey(activeBotId)) ? cacheByBot.get(cacheKey(activeBotId)) : [],
  );
  const [loading, setLoading] = useState(
    !(activeBotId && cacheByBot.has(cacheKey(activeBotId))),
  );

  useEffect(() => {
    if (!activeBotId) {
      setGroups([]);
      setLoading(false);
      return;
    }
    const key = cacheKey(activeBotId);
    if (cacheByBot.has(key)) {
      setGroups(cacheByBot.get(key));
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);

    const apply = (g) => {
      if (cancelled) return;
      setGroups(g);
      setLoading(false);
    };

    const pending = inflightByBot.get(key);
    if (pending) {
      pending.then((g) => apply(g)).catch(() => apply([]));
      return () => {
        cancelled = true;
      };
    }

    const p = fetch(`/api/bots/${activeBotId}/available-variables`)
      .then((r) => r.json())
      .then((data) => {
        const g = data.groups || [];
        cacheByBot.set(key, g);
        return g;
      })
      .catch(() => {
        cacheByBot.set(key, []);
        return [];
      })
      .finally(() => {
        inflightByBot.delete(key);
      });

    inflightByBot.set(key, p);
    p.then((g) => apply(g));

    return () => {
      cancelled = true;
    };
  }, [activeBotId]);

  const allNames = groups.flatMap((g) => (g.vars || []).map((v) => v.name).filter(Boolean));

  return { groups, loading, allNames };
}
