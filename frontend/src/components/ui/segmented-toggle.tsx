"use client";

import type { KeyboardEvent, ReactNode } from "react";
import { useRef } from "react";

import { cn } from "@/lib/utils";

/**
 * A row of mutually exclusive options. Four call sites had grown their own copy
 * of this markup with slightly different ARIA; the `variant` picks the right
 * semantics rather than leaving it to each caller.
 *
 *  - `tab`     switches which view is shown (video source, chart mode)
 *  - `radio`   picks a value that will be submitted (handedness)
 *  - `pressed` toggles a setting on the current view (playback speed)
 */
type Variant = "tab" | "radio" | "pressed";
type Size = "sm" | "md" | "lg";

export interface SegmentedOption<T> {
  value: T;
  label: ReactNode;
  disabled?: boolean;
}

const SIZES: Record<Size, string> = {
  sm: "px-2 py-0.5 text-xs",
  md: "px-3 py-1 text-sm",
  lg: "px-4 py-1.5 text-sm",
};

const GROUP_ROLE: Record<Variant, string> = {
  tab: "tablist",
  radio: "radiogroup",
  pressed: "group",
};

const ITEM_ROLE: Record<Variant, string | undefined> = {
  tab: "tab",
  radio: "radio",
  pressed: undefined,
};

function selectionProps<T>(variant: Variant, selected: boolean) {
  if (variant === "tab") return { "aria-selected": selected };
  if (variant === "radio") return { "aria-checked": selected };
  return { "aria-pressed": selected };
}

export function SegmentedToggle<T extends string | number>({
  label,
  options,
  value,
  onChange,
  variant = "tab",
  size = "md",
  className,
  itemClassName,
}: {
  label: string;
  options: readonly SegmentedOption<T>[];
  value: T;
  onChange: (value: T) => void;
  variant?: Variant;
  size?: Size;
  className?: string;
  itemClassName?: string;
}) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);

  // Arrow keys move between options, which is what a tablist and a radiogroup
  // are both expected to do. Skips disabled options and wraps at the ends.
  const onKeyDown = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    const step = event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
    if (step === 0) return;
    event.preventDefault();

    let next = index;
    for (let i = 0; i < options.length; i += 1) {
      next = (next + step + options.length) % options.length;
      if (!options[next].disabled) break;
    }
    onChange(options[next].value);
    refs.current[next]?.focus();
  };

  return (
    <div
      role={GROUP_ROLE[variant]}
      aria-label={label}
      className={cn("flex rounded-lg border border-border p-0.5", className)}
    >
      {options.map((option, index) => {
        const selected = option.value === value;
        return (
          <button
            key={String(option.value)}
            ref={(el) => {
              refs.current[index] = el;
            }}
            type="button"
            role={ITEM_ROLE[variant]}
            {...selectionProps(variant, selected)}
            disabled={option.disabled}
            onClick={() => onChange(option.value)}
            onKeyDown={(event) => onKeyDown(event, index)}
            className={cn(
              "rounded-md transition-colors disabled:opacity-40",
              SIZES[size],
              selected ? "bg-surface-2 font-medium" : "text-secondary hover:text-foreground",
              itemClassName,
            )}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
