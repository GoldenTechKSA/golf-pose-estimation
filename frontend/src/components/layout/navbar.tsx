"use client";

import { Target } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { ThemeToggle } from "@/components/layout/theme-toggle";
import { cn } from "@/lib/utils";

const links = [
  { href: "/upload", label: "Analyze a swing" },
  { href: "/history", label: "History" },
];

export function Navbar() {
  const pathname = usePathname();
  return (
    <header className="glass sticky top-0 z-40 border-b border-border/70">
      <nav className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4 sm:px-6">
        <Link href="/" className="group flex items-center gap-2 font-semibold">
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-accent/12 ring-1 ring-accent/20 transition-colors group-hover:bg-accent/20">
            <Target className="h-4 w-4 text-accent" aria-hidden />
          </span>
          <span className="text-gradient">SwingLens</span>
        </Link>
        <div className="flex items-center gap-1 sm:gap-2">
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={cn(
                "rounded-lg px-3 py-1.5 text-sm transition-colors",
                pathname.startsWith(link.href)
                  ? "bg-surface-2 font-medium text-foreground"
                  : "text-secondary hover:text-foreground",
              )}
            >
              {link.label}
            </Link>
          ))}
          <ThemeToggle />
        </div>
      </nav>
    </header>
  );
}
