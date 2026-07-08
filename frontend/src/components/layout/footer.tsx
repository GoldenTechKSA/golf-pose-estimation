export function Footer() {
  return (
    <footer className="border-t border-border py-6">
      <div className="mx-auto flex max-w-6xl flex-col gap-1 px-4 text-xs text-muted sm:px-6">
        <p>
          SwingLens analyzes swings from single-camera video. Angles are 2D
          projections — a coaching aid, not a 3D motion-capture replacement.
        </p>
        <p>Built with YOLO pose estimation, FastAPI, Next.js, and the Claude API.</p>
      </div>
    </footer>
  );
}
