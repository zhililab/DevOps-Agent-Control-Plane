"use client";

import { useMemo, useState } from "react";

type GraphFocus = "all" | "plan" | "reflection" | "analysis";

type NodeDef = {
  id: string;
  x: number;
  y: number;
  size: number;
  label: string;
  group: "core" | "work" | "growth";
  focus: GraphFocus[];
};

const focusOptions: Array<{ value: GraphFocus; label: string }> = [
  { value: "all", label: "All" },
  { value: "plan", label: "Plan" },
  { value: "reflection", label: "Reflection" },
  { value: "analysis", label: "Analysis" },
];

const nodes: NodeDef[] = [
  {
    id: "core",
    x: 140,
    y: 95,
    size: 14,
    label: "Core Loop",
    group: "core",
    focus: ["plan", "reflection", "analysis"],
  },
  { id: "today", x: 66, y: 58, size: 9, label: "Today", group: "work", focus: ["plan", "analysis"] },
  {
    id: "reflection",
    x: 228,
    y: 62,
    size: 10,
    label: "Reflection",
    group: "growth",
    focus: ["reflection"],
  },
  { id: "analysis", x: 250, y: 132, size: 9, label: "Analysis", group: "work", focus: ["analysis"] },
  {
    id: "knowledge",
    x: 82,
    y: 146,
    size: 10,
    label: "Knowledge",
    group: "growth",
    focus: ["reflection", "analysis"],
  },
  {
    id: "templates",
    x: 168,
    y: 32,
    size: 8,
    label: "Templates",
    group: "growth",
    focus: ["plan", "reflection"],
  },
];

const links: Array<[string, string]> = [
  ["core", "today"],
  ["core", "reflection"],
  ["core", "analysis"],
  ["core", "knowledge"],
  ["core", "templates"],
  ["today", "analysis"],
  ["reflection", "knowledge"],
];

function getNode(id: string): NodeDef {
  const node = nodes.find((item) => item.id === id);
  if (!node) {
    throw new Error(`Missing graph node: ${id}`);
  }
  return node;
}

export function KnowledgeGraphPreview() {
  const [focus, setFocus] = useState<GraphFocus>("all");
  const currentFocusIndex = focusOptions.findIndex((option) => option.value === focus);
  const activeFocusLabel = focusOptions.find((option) => option.value === focus)?.label ?? "All";

  function onFilterKeyDown(event: React.KeyboardEvent<HTMLDivElement>) {
    if (event.key !== "ArrowRight" && event.key !== "ArrowLeft" && event.key !== "Home" && event.key !== "End") {
      return;
    }
    event.preventDefault();

    if (event.key === "Home") {
      setFocus(focusOptions[0].value);
      return;
    }
    if (event.key === "End") {
      setFocus(focusOptions[focusOptions.length - 1].value);
      return;
    }

    const direction = event.key === "ArrowRight" ? 1 : -1;
    const nextIndex = (currentFocusIndex + direction + focusOptions.length) % focusOptions.length;
    setFocus(focusOptions[nextIndex].value);
  }

  const activeNodeIds = useMemo(() => {
    if (focus === "all") {
      return new Set(nodes.map((node) => node.id));
    }
    return new Set(nodes.filter((node) => node.focus.includes(focus)).map((node) => node.id));
  }, [focus]);

  return (
    <article className="chart-card graph-card animate-enter" aria-label="Knowledge graph preview">
      <header className="graph-card-header">
        <h3>Knowledge Graph</h3>
        <p className="muted">Connections between your daily execution loops.</p>
        <p className="graph-focus-hint" id="graph-focus-hint">
          Focus: {activeFocusLabel}. Use Left/Right arrows to switch.
        </p>
        <div
          className="graph-filter-row"
          role="group"
          aria-label="Graph focus filter"
          aria-describedby="graph-focus-hint"
          tabIndex={0}
          onKeyDown={onFilterKeyDown}
        >
          {focusOptions.map((option) => (
            <button
              key={option.value}
              type="button"
              className={focus === option.value ? "graph-filter-active" : ""}
              onClick={() => setFocus(option.value)}
              aria-pressed={focus === option.value}
              aria-label={`Focus ${option.label}`}
            >
              {option.label}
            </button>
          ))}
        </div>
      </header>

      <svg
        viewBox="0 0 300 180"
        role="img"
        aria-label={`Graph focused on ${activeFocusLabel}`}
      >
        {links.map(([from, to]) => {
          const source = getNode(from);
          const target = getNode(to);
          const active = activeNodeIds.has(source.id) && activeNodeIds.has(target.id);
          return (
            <line
              key={`${from}-${to}`}
              className={`graph-link ${active ? "graph-link-active" : "graph-link-dim"}`}
              x1={source.x}
              y1={source.y}
              x2={target.x}
              y2={target.y}
            />
          );
        })}

        {nodes.map((node) => (
            <g
              key={node.id}
              className={`graph-node graph-node-${node.group} ${
                activeNodeIds.has(node.id) ? "graph-node-active" : "graph-node-dim"
              }`}
              aria-hidden="true"
            >
              <circle cx={node.x} cy={node.y} r={node.size} />
            <text x={node.x} y={node.y + node.size + 12} textAnchor="middle">
              {node.label}
            </text>
          </g>
        ))}
      </svg>
    </article>
  );
}
