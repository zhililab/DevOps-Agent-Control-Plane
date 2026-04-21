"use client";

import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";

const TRANSITION_MS = 820;

export function RouteTransitionFX() {
  const pathname = usePathname();
  const [active, setActive] = useState(false);
  const isFirstRender = useRef(true);
  const timeoutRef = useRef<number | null>(null);

  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false;
      return;
    }

    setActive(true);
    if (timeoutRef.current !== null) {
      window.clearTimeout(timeoutRef.current);
    }
    timeoutRef.current = window.setTimeout(() => {
      setActive(false);
      timeoutRef.current = null;
    }, TRANSITION_MS);
  }, [pathname]);

  useEffect(() => {
    return () => {
      if (timeoutRef.current !== null) {
        window.clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  return (
    <div
      aria-hidden="true"
      className={`route-transition ${active ? "route-transition-active" : ""}`}
    >
      <div className="route-transition-grid" />
      <div className="route-transition-sweep" />
      <div className="route-transition-glow" />
    </div>
  );
}
