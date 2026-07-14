"use client";

import {
  Activity,
  BrainCircuit,
  Clapperboard,
  LineChart,
  Timer,
  Upload,
} from "lucide-react";
import { motion } from "motion/react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { PHASE_LABELS, PHASE_ORDER, phaseColor } from "@/lib/phases";

const features = [
  {
    icon: Clapperboard,
    title: "Annotated video",
    body: "Your swing rendered back with a full-body skeleton overlay, phase banner, and a phase-colored timeline.",
  },
  {
    icon: Timer,
    title: "Swing phase detection",
    body: "The seven canonical phases — address through finish — segmented automatically from your body's motion.",
  },
  {
    icon: Activity,
    title: "Biomechanical metrics",
    body: "Tempo, X-Factor, kinematic sequence, early extension, head stability, and more — computed per frame.",
  },
  {
    icon: BrainCircuit,
    title: "AI coaching",
    body: "Claude reads your numbers like a teaching pro: what you do well, what to fix, and the drill for each.",
  },
];

const steps = [
  { icon: Upload, title: "Upload", body: "Any .mp4, .mov, or .avi of a full swing." },
  { icon: Activity, title: "Analyze", body: "Pose estimation runs frame by frame with live progress." },
  { icon: LineChart, title: "Improve", body: "Explore phases, metrics, charts, and coaching feedback." },
];

export default function LandingPage() {
  return (
    <div className="mx-auto max-w-6xl px-4 sm:px-6">
      <section className="flex flex-col items-center gap-6 py-20 text-center sm:py-28">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="flex flex-col items-center gap-6"
        >
          <div className="flex flex-wrap items-center justify-center gap-1.5">
            {PHASE_ORDER.map((phase) => (
              <span
                key={phase}
                className="glass flex items-center gap-1.5 rounded-full border border-border/70 px-2.5 py-1 text-xs text-secondary"
              >
                <span
                  className="h-2 w-2 rounded-full"
                  style={{
                    background: phaseColor(phase),
                    boxShadow: `0 0 8px ${phaseColor(phase)}`,
                  }}
                  aria-hidden
                />
                {PHASE_LABELS[phase]}
              </span>
            ))}
          </div>
          <h1 className="max-w-3xl text-4xl font-bold tracking-tight sm:text-6xl">
            See your golf swing{" "}
            <span className="text-gradient">the way a coach does.</span>
          </h1>
          <p className="max-w-2xl text-lg text-secondary">
            Upload one video. SwingLens tracks your body frame by frame, detects
            every phase of your swing, measures the biomechanics that matter,
            and turns the numbers into coaching you can practice.
          </p>
          <div className="flex gap-3">
            <Link href="/upload">
              <Button size="lg">
                <Upload className="h-4 w-4" aria-hidden />
                Analyze my swing
              </Button>
            </Link>
            <Link href="/history">
              <Button size="lg" variant="secondary">
                View past swings
              </Button>
            </Link>
          </div>
        </motion.div>
      </section>

      <section className="grid gap-4 pb-16 sm:grid-cols-2 lg:grid-cols-4">
        {features.map((feature, i) => (
          <motion.div
            key={feature.title}
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-40px" }}
            transition={{ duration: 0.4, delay: i * 0.06 }}
          >
            <Card interactive className="h-full">
              <CardContent padding="standalone" className="flex h-full flex-col gap-3">
                <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-accent/20 to-accent-2/20 ring-1 ring-accent/15">
                  <feature.icon className="h-5 w-5 text-accent" aria-hidden />
                </span>
                <h3 className="font-semibold">{feature.title}</h3>
                <p className="text-sm text-secondary">{feature.body}</p>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </section>

      <section className="border-t border-border py-16">
        <h2 className="text-center text-2xl font-semibold">How it works</h2>
        <div className="mx-auto mt-8 grid max-w-3xl gap-6 sm:grid-cols-3">
          {steps.map((step, i) => (
            <div key={step.title} className="flex flex-col items-center gap-2 text-center">
              <div className="flex h-11 w-11 items-center justify-center rounded-full bg-gradient-to-br from-accent/15 to-accent-2/15 ring-1 ring-accent/15">
                <step.icon className="h-5 w-5 text-accent" aria-hidden />
              </div>
              <h3 className="font-medium">
                {i + 1}. {step.title}
              </h3>
              <p className="text-sm text-secondary">{step.body}</p>
            </div>
          ))}
        </div>
        <p className="mx-auto mt-10 max-w-xl text-center text-xs text-muted">
          Honest by design: SwingLens works from single-camera 2D video, so
          rotation metrics are projected angles — great for tracking your own
          progress, not a substitute for 3D motion capture.
        </p>
      </section>
    </div>
  );
}
