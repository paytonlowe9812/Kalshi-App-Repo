import { useState, useEffect } from 'react';
import useAppStore from '../store/useAppStore';

export function useLicense() {
  const { setLicenseValid } = useAppStore();
  const [status, setStatus] = useState({ valid: false, mode: 'paper' });

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await fetch('/api/license/status');
        const data = await res.json();
        setStatus(data);
        setLicenseValid(data.valid);
      } catch {
        /* ignore */
      }
    };
    fetchStatus();
  }, []);

  const validate = async (key) => {
    const res = await fetch('/api/license/validate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ key }),
    });
    const data = await res.json();
    if (data.valid) {
      setStatus({ valid: true, mode: 'live' });
      setLicenseValid(true);
    }
    return data;
  };

  return { ...status, validate };
}

export default useLicense;
