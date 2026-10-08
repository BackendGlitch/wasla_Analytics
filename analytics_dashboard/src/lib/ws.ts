"use client";

import { useEffect, useState } from "react";
import type { LiveTick } from "./types";
import { liveWsUrl } from "./api";

/**
 * Subscribe to the live WS feed. Returns the latest tick, or null while
 * waiting / in mock mode. Reconnects with backoff; never throws.
 */
export function useLiveTick(): LiveTick | null {
  const [tick, setTick] = useState<LiveTick | null>(null);

  useEffect(() => {
    const url = liveWsUrl();
    if (!url) return;

    let socket: WebSocket | null = null;
    let retry: ReturnType<typeof setTimeout> | null = null;
    let disposed = false;

    const connect = () => {
      if (disposed) return;
      try {
        socket = new WebSocket(url);
      } catch {
        return; // WS unsupported — stay quiet
      }
      socket.onmessage = (ev: MessageEvent) => {
        try {
          setTick(JSON.parse(String(ev.data)) as LiveTick);
        } catch {
          /* ignore malformed frames */
        }
      };
      socket.onclose = () => {
        if (!disposed) retry = setTimeout(connect, 10_000);
      };
    };

    connect();
    return () => {
      disposed = true;
      if (retry) clearTimeout(retry);
      socket?.close();
    };
  }, []);

  return tick;
}
