import type { Metadata } from "next";
import { Barlow, Space_Grotesk } from "next/font/google";
import type { ReactNode } from "react";

import { Footer } from "@/components/layout/footer";
import { Navbar } from "@/components/layout/navbar";
import { Providers } from "@/components/layout/providers";

import "./globals.css";

// Space Grotesk reads as instrumentation — the right register for measured
// numbers. Barlow carries the athletic lineage and holds up at label sizes.
const display = Space_Grotesk({
  subsets: ["latin"],
  weight: ["500", "600", "700"],
  variable: "--font-display",
  display: "swap",
});

const sans = Barlow({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-sans-face",
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "SwingLens — AI golf swing analysis",
    template: "%s · SwingLens",
  },
  description:
    "Upload a video of your golf swing and get back an annotated video, swing phase detection, biomechanical metrics, and AI coaching feedback.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${display.variable} ${sans.variable}`}
    >
      <body className="flex min-h-screen flex-col">
        <Providers>
          <Navbar />
          <main className="flex-1">{children}</main>
          <Footer />
        </Providers>
      </body>
    </html>
  );
}
