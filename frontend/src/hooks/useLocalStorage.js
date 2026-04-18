import { useState, useEffect, useCallback } from 'react';

/**
 * Synced React state + localStorage (stringify for objects).
 * @template T
 * @param {string} key
 * @param {T} defaultValue
 */
export function useLocalStorage(key, defaultValue) {
  const [value, setValue] = useState(() => {
    try {
      const raw = localStorage.getItem(key);
      if (raw == null) return defaultValue;
      try {
        return JSON.parse(raw);
      } catch {
        return raw;
      }
    } catch {
      return defaultValue;
    }
  });

  useEffect(() => {
    try {
      if (value === undefined || value === null) {
        localStorage.removeItem(key);
        return;
      }
      const serialized = typeof value === 'string' ? value : JSON.stringify(value);
      localStorage.setItem(key, serialized);
    } catch {
      /* ignore quota / private mode */
    }
  }, [key, value]);

  const remove = useCallback(() => {
    try {
      localStorage.removeItem(key);
    } catch {
      /* ignore */
    }
    setValue(defaultValue);
  }, [key, defaultValue]);

  return [value, setValue, remove];
}
