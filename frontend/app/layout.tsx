import type { ReactNode } from "react";

import { AppNav } from "@/components/layout/AppNav";
import { ProductDemoMotion } from "@/components/layout/ProductDemoMotion";
import { RouteTransitionFX } from "@/components/layout/RouteTransitionFX";

import "./globals.css";

export const metadata = {
  title: "DevOps Agent Control Plane",
  description: "Deterministic orchestration, replayable audit trails, policy gates, and commercial workflow controls.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body suppressHydrationWarning>
        <div className="app-bg" />
        <RouteTransitionFX />
        <main className="container app-shell">
          <header className="app-header">
            <div className="brand-panel">
              <div>
                <p className="eyebrow">DEVOPS AGENT CONTROL PLANE</p>
                <div className="brand-row">
                  <img src="/logo-mark.svg" alt="DevOps Agent Control Plane logo" className="brand-logo" />
                  <h1>DevOps Agent Control Plane</h1>
                </div>
                <p className="muted">
                  Deterministic orchestration, replayable audit trails, and commercial workflow controls.
                </p>
              </div>
              <ProductDemoMotion />
            </div>
          </header>
          <AppNav />
          {children}
        </main>
      </body>
    </html>
  );
}
