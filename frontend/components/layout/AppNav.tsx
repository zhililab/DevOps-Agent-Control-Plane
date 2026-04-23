"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/profile", label: "Profile" },
  { href: "/today", label: "Today" },
  { href: "/reflection", label: "Reflection" },
  { href: "/technical-analysis", label: "Technical Analysis" },
  { href: "/orchestrate", label: "Orchestrate" },
  { href: "/orchestrations", label: "Orchestrations" },
  { href: "/knowledge", label: "Knowledge" },
  { href: "/templates", label: "Templates" },
  { href: "/history", label: "History" },
];

export function AppNav() {
  const pathname = usePathname();

  return (
    <nav aria-label="Primary" className="app-nav">
      {links.map((link) => (
        <Link
          key={link.href}
          href={link.href}
          className={`nav-link ${pathname === link.href ? "nav-link-active" : ""}`}
        >
          {link.label}
        </Link>
      ))}
    </nav>
  );
}
