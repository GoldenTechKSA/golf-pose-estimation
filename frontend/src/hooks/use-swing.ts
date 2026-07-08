"use client";

import { useCallback, useEffect, useState } from "react";

import { ApiError, getSwing } from "@/lib/api";
import type { SwingDetail } from "@/lib/types";

export function useSwing(id: string | null) {
  const [swing, setSwing] = useState<SwingDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const refetch = useCallback(async () => {
    if (!id) return;
    try {
      setSwing(await getSwing(id));
      setError(null);
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 404
          ? "This swing doesn't exist (it may have been deleted)."
          : "Couldn't reach the analysis service.",
      );
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    void refetch();
  }, [refetch]);

  return { swing, error, loading, refetch };
}
