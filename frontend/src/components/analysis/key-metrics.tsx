import { MetricCard } from "@/components/analysis/metric-card";
import type { SwingMetrics } from "@/lib/types";

const VIEW_LABELS: Record<string, string> = {
  face_on: "face-on",
  oblique: "oblique to the target line",
  down_the_line: "down the line",
  unknown: "an unrecognized angle",
};

/**
 * Metrics split by whether this camera angle could actually measure them.
 *
 * Rotation is read from the projected width of the shoulder and hip lines. Film
 * down the line and those lines point at the lens, so the numbers survive but
 * mean nothing. Showing them beside judged metrics would launder an artifact
 * into evidence; hiding them entirely would be its own dishonesty, since the
 * projection really does produce them.
 */
export function KeyMetrics({ metrics }: { metrics: SwingMetrics }) {
  const measured = metrics.summary.filter((m) => m.value != null);
  // Tempo is the hero's headline number; a tile would say it twice.
  const shown = measured.filter((m) => m.key !== "tempo_ratio");

  const reliable = shown.filter((m) => m.reliable !== false);
  const unreliable = shown.filter((m) => m.reliable === false);
  const view = metrics.camera?.view ?? "unknown";

  return (
    <section aria-labelledby="metrics-heading" className="flex flex-col gap-3">
      <h2 id="metrics-heading" className="text-lg font-semibold">
        Key metrics
      </h2>

      <div className="grid grid-cols-2 gap-3">
        {reliable.map((entry) => (
          <MetricCard key={entry.key} metric={entry} />
        ))}
      </div>

      {unreliable.length > 0 && (
        <details className="rounded-xl border border-border bg-surface p-4">
          <summary className="cursor-pointer text-sm font-medium text-secondary hover:text-foreground">
            {unreliable.length} metric{unreliable.length === 1 ? "" : "s"} this camera
            angle can&apos;t measure
          </summary>
          <p className="mt-2 text-xs leading-relaxed text-muted">
            This swing looks like it was filmed {VIEW_LABELS[view] ?? VIEW_LABELS.unknown}.
            {" "}
            {unreliable[0].unreliable_reason} These values are what the 2D projection
            shows, not what the golfer did — they carry no verdict here. Film face-on to
            measure rotation.
          </p>
          <div className="mt-3 grid grid-cols-2 gap-3">
            {unreliable.map((entry) => (
              <MetricCard key={entry.key} metric={entry} />
            ))}
          </div>
        </details>
      )}
    </section>
  );
}
