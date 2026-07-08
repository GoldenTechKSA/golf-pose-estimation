"use client";

import { Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Dropzone } from "@/components/upload/dropzone";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { uploadSwing } from "@/lib/api";
import { cn } from "@/lib/utils";

export default function UploadPage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [handedness, setHandedness] = useState<"right" | "left">("right");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const submit = async () => {
    if (!file) return;
    setSubmitting(true);
    setError(null);
    try {
      const { id } = await uploadSwing(file, handedness);
      router.push(`/analysis/${id}`);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Upload failed — is the analysis service running?",
      );
      setSubmitting(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl px-4 py-12 sm:px-6">
      <h1 className="text-2xl font-bold">Analyze a swing</h1>
      <p className="mt-1 text-secondary">
        Film from face-on or down-the-line with your full body in frame, then
        upload the clip.
      </p>

      <div className="mt-8 flex flex-col gap-6">
        <Dropzone
          file={file}
          disabled={submitting}
          onFile={(selected, validationError) => {
            setError(validationError);
            setFile(validationError ? null : selected);
          }}
        />

        <Card>
          <CardContent className="flex items-center justify-between gap-4 p-5">
            <div>
              <p className="font-medium">Which way do you swing?</p>
              <p className="text-sm text-secondary">
                Used to pick your lead arm and leg for the metrics.
              </p>
            </div>
            <div
              role="radiogroup"
              aria-label="Handedness"
              className="flex rounded-lg border border-border p-0.5"
            >
              {(["right", "left"] as const).map((side) => (
                <button
                  key={side}
                  role="radio"
                  aria-checked={handedness === side}
                  onClick={() => setHandedness(side)}
                  className={cn(
                    "rounded-md px-4 py-1.5 text-sm capitalize transition-colors",
                    handedness === side
                      ? "bg-surface-2 font-medium"
                      : "text-secondary hover:text-foreground",
                  )}
                >
                  {side}-handed
                </button>
              ))}
            </div>
          </CardContent>
        </Card>

        {error && (
          <p role="alert" className="text-sm text-[#d03b3b]">
            {error}
          </p>
        )}

        <Button size="lg" disabled={!file || submitting} onClick={submit}>
          {submitting ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              Uploading…
            </>
          ) : (
            "Start analysis"
          )}
        </Button>

        <p className="text-xs text-muted">
          Tips for best results: keep the camera steady, make sure your whole
          body (head to feet) stays in frame, and trim the clip to a single
          swing.
        </p>
      </div>
    </div>
  );
}
