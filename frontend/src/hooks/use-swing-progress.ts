"use client";

import { useEffect, useRef, useState } from "react";

import { getSwing, progressSocketUrl } from "@/lib/api";
import type { ProgressMessage, SwingStatus } from "@/lib/types";

const POLL_FALLBACK_MS = 2000;
const TERMINAL: SwingStatus[] = ["completed", "failed"];

/**
 * Live processing progress for a swing.
 *
 * Primary transport is the backend's WebSocket (Redis pub/sub pushed from the
 * worker). If the socket can't connect or drops before a terminal status, we
 * silently fall back to polling the REST endpoint — the UI can't tell the
 * difference.
 */
export function useSwingProgress(swingId: string | null) {
  const [progress, setProgress] = useState<ProgressMessage | null>(null);
  const done = progress != null && TERMINAL.includes(progress.status);
  const doneRef = useRef(false);
  doneRef.current = done;

  useEffect(() => {
    if (!swingId) return;
    let socket: WebSocket | null = null;
    let pollTimer: ReturnType<typeof setInterval> | null = null;
    let cancelled = false;

    const startPolling = () => {
      if (pollTimer || cancelled || doneRef.current) return;
      pollTimer = setInterval(async () => {
        try {
          const swing = await getSwing(swingId);
          setProgress({
            swing_id: swing.id,
            status: swing.status,
            stage: swing.stage,
            progress: swing.progress,
            message: swing.error ?? "",
          });
          if (TERMINAL.includes(swing.status) && pollTimer) {
            clearInterval(pollTimer);
            pollTimer = null;
          }
        } catch {
          /* transient poll failure — keep trying */
        }
      }, POLL_FALLBACK_MS);
    };

    try {
      socket = new WebSocket(progressSocketUrl(swingId));
      socket.onmessage = (event) => {
        try {
          setProgress(JSON.parse(event.data) as ProgressMessage);
        } catch {
          /* ignore malformed frame */
        }
      };
      socket.onerror = () => startPolling();
      socket.onclose = () => {
        if (!doneRef.current) startPolling();
      };
    } catch {
      startPolling();
    }

    return () => {
      cancelled = true;
      socket?.close();
      if (pollTimer) clearInterval(pollTimer);
    };
  }, [swingId]);

  return { progress, done };
}
