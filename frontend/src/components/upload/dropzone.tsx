"use client";

import { FileVideo, Upload } from "lucide-react";
import { useCallback, useRef, useState, type DragEvent } from "react";

import { cn } from "@/lib/utils";

const ACCEPTED_EXTENSIONS = [".mp4", ".mov", ".avi"];
const MAX_SIZE_MB = 200;

export function validateVideoFile(file: File): string | null {
  const name = file.name.toLowerCase();
  if (!ACCEPTED_EXTENSIONS.some((ext) => name.endsWith(ext))) {
    return `Unsupported format — use ${ACCEPTED_EXTENSIONS.join(", ")}`;
  }
  if (file.size > MAX_SIZE_MB * 1024 * 1024) {
    return `File is too large — the limit is ${MAX_SIZE_MB} MB`;
  }
  if (file.size === 0) {
    return "That file is empty";
  }
  return null;
}

export function Dropzone({
  file,
  onFile,
  disabled,
}: {
  file: File | null;
  onFile: (file: File, error: string | null) => void;
  disabled?: boolean;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  const handleFiles = useCallback(
    (files: FileList | null) => {
      const selected = files?.[0];
      if (!selected) return;
      onFile(selected, validateVideoFile(selected));
    },
    [onFile],
  );

  const onDrop = (event: DragEvent) => {
    event.preventDefault();
    setDragging(false);
    if (!disabled) handleFiles(event.dataTransfer.files);
  };

  return (
    <>
      {/* Kept outside the button — interactive content inside <button> is
          invalid HTML even when hidden. */}
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED_EXTENSIONS.join(",")}
        className="hidden"
        onChange={(e) => handleFiles(e.target.files)}
      />
      <button
        type="button"
        disabled={disabled}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        aria-label="Choose or drop a swing video"
        className={cn(
          "flex w-full cursor-pointer flex-col items-center gap-3 rounded-xl border-2 border-dashed p-10 text-center transition-all duration-300",
          dragging
            ? "scale-[1.01] border-accent bg-accent/8 shadow-elev-lg"
            : "border-border bg-surface/60 backdrop-blur hover:border-accent/50 hover:bg-surface-2/60",
          disabled && "pointer-events-none opacity-60",
        )}
      >
      {file ? (
        <>
          <FileVideo className="h-8 w-8 text-accent" aria-hidden />
          <div>
            <p className="font-medium">{file.name}</p>
            <p className="text-sm text-secondary">
              {(file.size / (1024 * 1024)).toFixed(1)} MB — click to choose a
              different video
            </p>
          </div>
        </>
      ) : (
        <>
          <Upload className="h-8 w-8 text-muted" aria-hidden />
          <div>
            <p className="font-medium">Drop your swing video here</p>
            <p className="text-sm text-secondary">
              or click to browse — {ACCEPTED_EXTENSIONS.join(" / ")}, up to{" "}
              {MAX_SIZE_MB} MB
            </p>
          </div>
        </>
      )}
      </button>
    </>
  );
}
