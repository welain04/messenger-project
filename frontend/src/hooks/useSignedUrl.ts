import { useCallback, useEffect, useRef, useState } from "react";
import type { SignedUrl } from "../api";

const REFRESH_BUFFER_MS = 30_000;

export function useSignedUrl(
  fetcher: () => Promise<SignedUrl | null>,
  enabled = true,
): { url: string | null; loading: boolean; refresh: () => void } {
  const [url, setUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const timerRef = useRef<number | null>(null);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const load = useCallback(async () => {
    if (!enabled) {
      setUrl(null);
      return;
    }
    setLoading(true);
    try {
      const signed = await fetcherRef.current();
      if (!signed) {
        setUrl(null);
        return;
      }
      setUrl(signed.url);
      if (timerRef.current) window.clearTimeout(timerRef.current);
      const expires = new Date(signed.expires_at).getTime();
      const delay = Math.max(expires - Date.now() - REFRESH_BUFFER_MS, 5_000);
      timerRef.current = window.setTimeout(() => void load(), delay);
    } catch {
      setUrl(null);
    } finally {
      setLoading(false);
    }
  }, [enabled]);

  useEffect(() => {
    void load();
    return () => {
      if (timerRef.current) window.clearTimeout(timerRef.current);
    };
  }, [load]);

  return { url, loading, refresh: () => void load() };
}
