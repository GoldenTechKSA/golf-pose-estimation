"use client";

import { Loader2, Trash2, Upload } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { apiUrl, deleteSwing, listSwings } from "@/lib/api";
import { cn, formatDate, formatDuration } from "@/lib/utils";
import type { SwingStatus, SwingSummary } from "@/lib/types";

const STATUS_STYLES: Record<SwingStatus, string> = {
  completed: "text-good-text",
  processing: "text-accent",
  queued: "text-secondary",
  failed: "text-[#d03b3b]",
};

export default function HistoryPage() {
  const [swings, setSwings] = useState<SwingSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);

  const load = async () => {
    try {
      setSwings(await listSwings());
      setError(null);
    } catch {
      setError("Couldn't reach the analysis service.");
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const remove = async (id: string) => {
    if (!window.confirm("Delete this swing and its videos permanently?")) return;
    setDeleting(id);
    try {
      await deleteSwing(id);
      setSwings((prev) => prev?.filter((s) => s.id !== id) ?? null);
    } catch {
      setError("Couldn't delete that swing — it may still be processing.");
    } finally {
      setDeleting(null);
    }
  };

  return (
    <div className="mx-auto max-w-4xl px-4 py-12 sm:px-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Swing history</h1>
          <p className="mt-1 text-secondary">
            Every swing you&apos;ve analyzed, newest first.
          </p>
        </div>
        <Link href="/upload">
          <Button>
            <Upload className="h-4 w-4" aria-hidden />
            New analysis
          </Button>
        </Link>
      </div>

      {error && (
        <p role="alert" className="mt-6 text-sm text-[#d03b3b]">
          {error}
        </p>
      )}

      <div className="mt-8 flex flex-col gap-3">
        {swings === null &&
          Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}

        {swings?.length === 0 && (
          <Card className="p-10 text-center text-secondary">
            No swings yet — upload your first video to get started.
          </Card>
        )}

        {swings?.map((swing) => (
          <Card key={swing.id} className="flex items-center gap-4 p-3">
            <Link
              href={`/analysis/${swing.id}`}
              className="relative h-18 w-28 shrink-0 overflow-hidden rounded-lg bg-surface-2"
            >
              {swing.status === "completed" || swing.status === "processing" ? (
                // Thumbnails stream from the API service, not a Next-optimizable
                // static source — plain img semantics via unoptimized.
                <Image
                  src={apiUrl(`/api/v1/swings/${swing.id}/video/thumbnail`)}
                  alt={`Thumbnail for ${swing.original_filename}`}
                  fill
                  unoptimized
                  className="object-cover"
                />
              ) : null}
            </Link>
            <div className="min-w-0 flex-1">
              <Link
                href={`/analysis/${swing.id}`}
                className="block truncate font-medium hover:underline"
              >
                {swing.original_filename}
              </Link>
              <p className="mt-0.5 text-sm text-secondary">
                {formatDate(swing.created_at)} · {formatDuration(swing.duration)}
              </p>
              <p className={cn("mt-0.5 text-xs font-medium capitalize", STATUS_STYLES[swing.status])}>
                {swing.status === "processing"
                  ? `Processing — ${Math.round(swing.progress)}%`
                  : swing.status}
              </p>
            </div>
            <Badge className="hidden sm:inline-flex">{swing.handedness}-handed</Badge>
            <Button
              variant="danger"
              size="sm"
              aria-label={`Delete ${swing.original_filename}`}
              disabled={deleting === swing.id || swing.status === "processing"}
              onClick={() => remove(swing.id)}
            >
              {deleting === swing.id ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              ) : (
                <Trash2 className="h-4 w-4" aria-hidden />
              )}
            </Button>
          </Card>
        ))}
      </div>
    </div>
  );
}
