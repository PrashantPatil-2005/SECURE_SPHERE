import { useEffect, useState } from 'react';
import { readToken, tokenExpSeconds } from '@/lib/jwt';

const POLL_MS = 5000;

export function useSessionTimeout({ warningSeconds = 60 } = {}) {
  const [now, setNow] = useState(() => Math.floor(Date.now() / 1000));
  const [exp, setExp] = useState(() => tokenExpSeconds(readToken()));

  useEffect(() => {
    const id = setInterval(() => {
      setNow(Math.floor(Date.now() / 1000));
      const e = tokenExpSeconds(readToken());
      setExp(e);
    }, POLL_MS);
    return () => clearInterval(id);
  }, []);

  const secondsLeft = exp ? exp - now : null;
  const showWarning = secondsLeft !== null && secondsLeft <= warningSeconds && secondsLeft > 0;
  const expired = secondsLeft !== null && secondsLeft <= 0;

  return { exp, secondsLeft, showWarning, expired, refreshExp: () => setExp(tokenExpSeconds(readToken())) };
}
