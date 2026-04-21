import type { ReactNode } from "react";

import { AppNav } from "@/components/layout/AppNav";
import { RouteTransitionFX } from "@/components/layout/RouteTransitionFX";

import "./globals.css";

export const metadata = {
  title: "Personal Agent Assistant",
  description: "Frontend skeleton for planning, reflection, and history.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body suppressHydrationWarning>
        <div className="app-bg" />
        <RouteTransitionFX />
        <main className="container app-shell">
          <header className="app-header">
            <p className="eyebrow">PERSONAL OPERATING SYSTEM</p>
            <h1>Personal Agent Assistant</h1>
            <p className="muted">Execution, reflection, and reusable workflows.</p>
          </header>
          <AppNav />
          {children}
        </main>
      </body>
    </html>
  );
}
