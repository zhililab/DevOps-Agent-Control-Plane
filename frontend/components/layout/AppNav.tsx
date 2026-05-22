"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navGroups = [
  {
    label: "Operate",
    links: [
      { href: "/dashboard", label: "Control Dashboard" },
      { href: "/orchestrate", label: "Run Workflow" },
      { href: "/orchestrations", label: "Run History" },
    ],
  },
  {
    label: "Commercial",
    links: [{ href: "/monetization", label: "Plans & Usage" }],
  },
  {
    label: "Learn",
    links: [{ href: "/tutorial", label: "Tutorial" }],
  },
  {
    label: "Assets",
    links: [
      { href: "/knowledge", label: "Knowledge" },
      { href: "/templates", label: "Templates" },
      { href: "/history", label: "History" },
    ],
  },
  {
    label: "Personal Loops",
    links: [
      { href: "/today", label: "Today" },
      { href: "/reflection", label: "Reflection" },
      { href: "/technical-analysis", label: "Analysis" },
      { href: "/profile", label: "Profile" },
    ],
  },
];

export function AppNav() {
  const pathname = usePathname();

  return (
    <nav aria-label="Primary" className="app-nav">
      {navGroups.map((group) => (
        <section className="nav-group" aria-label={group.label} key={group.label}>
          <p className="nav-group-title">{group.label}</p>
          <div className="nav-group-links">
            {group.links.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                prefetch={false}
                className={`nav-link ${pathname === link.href ? "nav-link-active" : ""}`}
              >
                {link.label}
              </Link>
            ))}
          </div>
        </section>
      ))}
    </nav>
  );
}
