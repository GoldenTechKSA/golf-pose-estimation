import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "rounded-xl border border-border bg-surface shadow-[0_1px_2px_rgba(0,0,0,0.04)]",
        className,
      )}
      {...props}
    />
  );
}

export function CardHeader({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("flex flex-col gap-1 p-5 pb-3", className)} {...props} />;
}

export function CardTitle({ className, ...props }: HTMLAttributes<HTMLHeadingElement>) {
  return <h3 className={cn("text-base font-semibold", className)} {...props} />;
}

export function CardDescription({ className, ...props }: HTMLAttributes<HTMLParagraphElement>) {
  return <p className={cn("text-sm text-secondary", className)} {...props} />;
}

/**
 * `default` sits under a CardHeader, so its top padding is already spent.
 * `standalone` is a card with no header. `compact` is for dense grids.
 * Reach for one of these rather than passing a bespoke `p-N`.
 */
type CardPadding = "default" | "standalone" | "compact";

const CARD_PADDING: Record<CardPadding, string> = {
  default: "p-5 pt-0",
  standalone: "p-5",
  compact: "p-4",
};

export function CardContent({
  className,
  padding = "default",
  ...props
}: HTMLAttributes<HTMLDivElement> & { padding?: CardPadding }) {
  return <div className={cn(CARD_PADDING[padding], className)} {...props} />;
}
