import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";

import KnowledgePage from "@/app/knowledge/page";
import TemplatesPage from "@/app/templates/page";

describe("knowledge and templates workflow", () => {
  test("creates knowledge entry and renders it", async () => {
    const fetchMock = vi.mocked(globalThis.fetch);
    fetchMock.mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = input.toString();

      if (url.includes("/knowledge") && init?.method === "POST") {
        return new Response(
          JSON.stringify({
            id: 10,
            title: "Runner cache troubleshooting",
            content: "Check cache key drift and runner image changes.",
            tags: ["devops", "ci"],
            created_at: "2026-04-20T08:00:00Z",
            updated_at: "2026-04-20T08:00:00Z",
          }),
          { status: 200 }
        );
      }

      if (url.includes("/knowledge")) {
        return new Response(JSON.stringify([]), { status: 200 });
      }

      return new Response(JSON.stringify({}), { status: 200 });
    });

    render(<KnowledgePage />);

    fireEvent.change(screen.getByLabelText("Title"), {
      target: { value: "Runner cache troubleshooting" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save Entry" }));

    await waitFor(() => {
      expect(screen.getByText("Knowledge entry saved.")).toBeInTheDocument();
    });
    expect(screen.getByText("Runner cache troubleshooting")).toBeInTheDocument();
  });

  test("edits selected knowledge entry", async () => {
    const fetchMock = vi.mocked(globalThis.fetch);
    fetchMock.mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = input.toString();

      if (url.includes("/knowledge/11") && init?.method === "PUT") {
        return new Response(
          JSON.stringify({
            id: 11,
            title: "Runner cache troubleshooting",
            content: "Updated cache policy checklist",
            tags: ["ci", "cache"],
            created_at: "2026-04-20T08:00:00Z",
            updated_at: "2026-04-20T09:00:00Z",
          }),
          { status: 200 }
        );
      }

      if (url.includes("/knowledge")) {
        return new Response(
          JSON.stringify([
            {
              id: 11,
              title: "Runner cache troubleshooting",
              content: "Initial notes",
              tags: ["ci"],
              created_at: "2026-04-20T08:00:00Z",
              updated_at: "2026-04-20T08:00:00Z",
            },
          ]),
          { status: 200 }
        );
      }

      return new Response(JSON.stringify({}), { status: 200 });
    });

    render(<KnowledgePage />);

    await waitFor(() => {
      expect(screen.getByText("Runner cache troubleshooting")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Edit" }));
    fireEvent.change(screen.getByLabelText("Content"), {
      target: { value: "Updated cache policy checklist" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Update Selected" }));

    await waitFor(() => {
      expect(screen.getByText("Knowledge entry updated.")).toBeInTheDocument();
    });
    expect(screen.getAllByText("Updated cache policy checklist").length).toBeGreaterThan(0);
  });

  test("creates and updates template", async () => {
    const fetchMock = vi.mocked(globalThis.fetch);
    fetchMock.mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = input.toString();

      if (url.includes("/templates") && init?.method === "POST") {
        return new Response(
          JSON.stringify({
            id: 21,
            name: "Incident Update Template",
            description: "Reusable update",
            body: "Context:\nImpact:",
            tags: ["incident"],
            created_at: "2026-04-20T08:00:00Z",
            updated_at: "2026-04-20T08:00:00Z",
          }),
          { status: 200 }
        );
      }

      if (url.includes("/templates/21") && init?.method === "PUT") {
        return new Response(
          JSON.stringify({
            id: 21,
            name: "Incident Update Template",
            description: "Updated format",
            body: "Context:\nImpact:",
            tags: ["incident", "summary"],
            created_at: "2026-04-20T08:00:00Z",
            updated_at: "2026-04-20T08:30:00Z",
          }),
          { status: 200 }
        );
      }

      if (url.includes("/templates")) {
        return new Response(JSON.stringify([]), { status: 200 });
      }

      return new Response(JSON.stringify({}), { status: 200 });
    });

    render(<TemplatesPage />);

    fireEvent.click(screen.getByRole("button", { name: "Save Template" }));

    await waitFor(() => {
      expect(screen.getByText("Template saved.")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Edit" }));
    fireEvent.change(screen.getByLabelText("Description"), {
      target: { value: "Updated format" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Update Selected" }));

    await waitFor(() => {
      expect(screen.getByText("Template updated.")).toBeInTheDocument();
    });
  });

  test("imports built-in templates via JSON", async () => {
    const fetchMock = vi.mocked(globalThis.fetch);
    fetchMock.mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = input.toString();

      if (url.includes("/templates/import/json") && init?.method === "POST") {
        return new Response(
          JSON.stringify({
            mode: "json",
            imported: 22,
            updated: 0,
            skipped: 0,
            total: 22,
          }),
          { status: 200 }
        );
      }

      if (url.includes("/templates")) {
        return new Response(JSON.stringify([]), { status: 200 });
      }

      return new Response(JSON.stringify({}), { status: 200 });
    });

    render(<TemplatesPage />);
    fireEvent.click(screen.getByRole("button", { name: "Import Built-in JSON" }));

    await waitFor(() => {
      expect(
        screen.getByText("Imported via JSON: imported=22, updated=0, skipped=0.")
      ).toBeInTheDocument();
    });
  });
});
