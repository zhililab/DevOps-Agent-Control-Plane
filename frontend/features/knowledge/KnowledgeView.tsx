"use client";

import { FormEvent, useEffect, useState } from "react";

import { PageCard } from "@/components/ui/PageCard";
import { StatusMessage } from "@/components/ui/StatusMessage";
import { apiClient } from "@/lib/api";
import type { NoteEntry } from "@/lib/types";

function splitTags(raw: string): string[] {
  return raw
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export function KnowledgeView() {
  const [title, setTitle] = useState("Runner cache troubleshooting");
  const [content, setContent] = useState("When CI cache misses increase, compare cache key changes and runner image.");
  const [tagsText, setTagsText] = useState("devops,ci,cache");
  const [searchText, setSearchText] = useState("");
  const [filterTag, setFilterTag] = useState("");
  const [entries, setEntries] = useState<NoteEntry[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  async function loadEntries(q?: string, tag?: string) {
    try {
      const response = await apiClient.listKnowledgeEntries({ q, tag });
      setEntries(response);
      setError(null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Failed to load knowledge entries");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadEntries();
  }, []);

  async function onCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStatus(null);
    setError(null);

    try {
      const created = await apiClient.createKnowledgeEntry({
        title: title.trim(),
        content: content.trim(),
        tags: splitTags(tagsText),
      });
      setEntries((existing) => [created, ...existing]);
      setStatus("Knowledge entry saved.");
      setSelectedId(created.id);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Failed to save knowledge entry");
    }
  }

  async function onFilter(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsLoading(true);
    await loadEntries(searchText.trim(), filterTag.trim());
  }

  function selectEntry(entry: NoteEntry) {
    setSelectedId(entry.id);
    setTitle(entry.title);
    setContent(entry.content);
    setTagsText(entry.tags.join(", "));
    setStatus(null);
    setError(null);
  }

  async function saveSelectedEntry() {
    if (selectedId === null) return;
    setStatus(null);
    setError(null);
    try {
      const updated = await apiClient.updateKnowledgeEntry(selectedId, {
        title: title.trim(),
        content: content.trim(),
        tags: splitTags(tagsText),
      });
      setEntries((existing) => existing.map((item) => (item.id === updated.id ? updated : item)));
      setStatus("Knowledge entry updated.");
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Failed to update knowledge entry");
    }
  }

  function clearFilter() {
    setSearchText("");
    setFilterTag("");
    setIsLoading(true);
    void loadEntries();
  }

  return (
    <PageCard title="Knowledge" description="Capture durable notes and reusable knowledge entries.">
      <form onSubmit={onCreate}>
        <label>
          Title
          <input value={title} onChange={(event) => setTitle(event.target.value)} />
        </label>
        <label>
          Content
          <textarea value={content} rows={5} onChange={(event) => setContent(event.target.value)} />
        </label>
        <label>
          Tags (comma-separated)
          <input value={tagsText} onChange={(event) => setTagsText(event.target.value)} />
        </label>
        <div className="button-row">
          <button type="submit">Save Entry</button>
          <button type="button" onClick={saveSelectedEntry} disabled={selectedId === null}>
            Update Selected
          </button>
        </div>
      </form>

      <form onSubmit={onFilter} className="reflection-section">
        <h3>Search</h3>
        <label>
          Text Query
          <input value={searchText} onChange={(event) => setSearchText(event.target.value)} />
        </label>
        <label>
          Tag Filter
          <input value={filterTag} onChange={(event) => setFilterTag(event.target.value)} />
        </label>
        <div className="button-row">
          <button type="submit">Apply Filter</button>
          <button type="button" onClick={clearFilter}>
            Clear
          </button>
        </div>
      </form>

      {status ? <StatusMessage message={status} tone="success" /> : null}
      {error ? <StatusMessage message={error} tone="error" /> : null}

      <section className="reflection-section">
        <h3>Entries</h3>
        {isLoading ? <p className="muted">Loading entries...</p> : null}
        {!isLoading && entries.length === 0 ? <p className="muted">No entries found.</p> : null}
        {entries.map((entry) => (
          <article key={entry.id} className="history-plan">
            <h4>{entry.title}</h4>
            <p>{entry.content}</p>
            <p className="muted">Tags: {entry.tags.join(", ") || "none"}</p>
            <button type="button" onClick={() => selectEntry(entry)}>
              Edit
            </button>
          </article>
        ))}
      </section>
    </PageCard>
  );
}
