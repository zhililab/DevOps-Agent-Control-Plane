import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";

globalThis.fetch = vi.fn(async (input: RequestInfo | URL) => {
  const url = input.toString();

  if (url.endsWith("/plans/history")) {
    return new Response(JSON.stringify({ items: [] }), { status: 200 });
  }

  if (url.endsWith("/plans/daily")) {
    return new Response(
      JSON.stringify({
        id: 1,
        plan_date: "2026-04-15",
        context: { tasks: [], meetings: [], blockers: [], priorities: [] },
        plan: {
          top_priorities: [],
          recommended_order: [],
          risks_and_reminders: [],
          next_actions: [],
          status_summary: "mock",
        },
        created_at: "2026-04-15T00:00:00Z",
      }),
      { status: 200 }
    );
  }

  if (url.endsWith("/reflections/history")) {
    return new Response(JSON.stringify({ items: [] }), { status: 200 });
  }

  if (url.endsWith("/reflections/daily")) {
    return new Response(
      JSON.stringify({
        id: 1,
        entry_date: "2026-04-16",
        input: {
          completed: [],
          unfinished: [],
          blockers: [],
          mood_or_notes: "",
        },
        summary: {
          day_summary: "mock reflection summary",
          unfinished_items: [],
          pattern_hints: [],
          tomorrow_suggestions: [],
        },
        created_at: "2026-04-16T00:00:00Z",
      }),
      { status: 200 }
    );
  }

  if (url.endsWith("/analysis/history")) {
    return new Response(JSON.stringify({ items: [] }), { status: 200 });
  }

  if (url.endsWith("/analysis/technical")) {
    return new Response(
      JSON.stringify({
        id: 1,
        analysis_date: "2026-04-16",
        input: {
          logs: "",
          errors: [],
          code_snippets: [],
          issue_description: "",
        },
        output: {
          problem_statement: "mock analysis",
          likely_causes: [],
          validation_steps: [],
          fix_options: [],
          risks: [],
          follow_up_tasks: [],
        },
        created_at: "2026-04-16T00:00:00Z",
      }),
      { status: 200 }
    );
  }

  if (url.includes("/knowledge")) {
    if (url.endsWith("/knowledge")) {
      return new Response(JSON.stringify([]), { status: 200 });
    }
    return new Response(
      JSON.stringify({
        id: 1,
        title: "mock knowledge",
        content: "mock content",
        tags: [],
        created_at: "2026-04-20T00:00:00Z",
        updated_at: "2026-04-20T00:00:00Z",
      }),
      { status: 200 }
    );
  }

  if (url.includes("/templates")) {
    if (url.endsWith("/templates")) {
      return new Response(JSON.stringify([]), { status: 200 });
    }
    return new Response(
      JSON.stringify({
        id: 1,
        name: "mock template",
        description: "mock description",
        body: "mock body",
        tags: [],
        created_at: "2026-04-20T00:00:00Z",
        updated_at: "2026-04-20T00:00:00Z",
      }),
      { status: 200 }
    );
  }

  if (url.endsWith("/tasks") || url.endsWith("/reflections")) {
    return new Response(JSON.stringify([]), { status: 200 });
  }

  return new Response(JSON.stringify({}), { status: 200 });
}) as unknown as typeof fetch;
