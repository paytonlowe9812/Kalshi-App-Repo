import { useState, useEffect } from 'react';

export function useBotStatus(botId) {
  const [status, setStatus] = useState(null);

  useEffect(() => {
    if (!botId) return;
    const fetchStatus = async () => {
      try {
        const res = await fetch(`/api/bots/${botId}`);
        const data = await res.json();
        setStatus(data.status);
      } catch {
        /* ignore */
      }
    };
    fetchStatus();
    const id = setInterval(fetchStatus, 2000);
    return () => clearInterval(id);
  }, [botId]);

  return status;
}

export default useBotStatus;
