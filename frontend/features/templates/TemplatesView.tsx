"use client";

import { FormEvent, useEffect, useState } from "react";

import { PageCard } from "@/components/ui/PageCard";
import { StatusMessage } from "@/components/ui/StatusMessage";
import { apiClient } from "@/lib/api";
import type { PromptTemplate } from "@/lib/types";

function splitTags(raw: string): string[] {
  return raw
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export function TemplatesView() {
  const [name, setName] = useState("Incident Update Template");
  const [description, setDescription] = useState("Reusable format for concise incident updates.");
  const [body, setBody] = useState("Context:\nImpact:\nMitigation:\nNext step:");
  const [tagsText, setTagsText] = useState("incident,update");
  const [searchText, setSearchText] = useState("");
  const [filterTag, setFilterTag] = useState("");
  const [templates, setTemplates] = useState<PromptTemplate[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  async function loadTemplates(q?: string, tag?: string) {
    try {
      const response = await apiClient.listPromptTemplates({ q, tag });
      setTemplates(response);
      setError(null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Failed to load templates");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadTemplates();
  }, []);

  async function onCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStatus(null);
    setError(null);

    try {
      const created = await apiClient.createPromptTemplate({
        name: name.trim(),
        description: description.trim(),
        body: body.trim(),
        tags: splitTags(tagsText),
      });
      setTemplates((existing) => [created, ...existing]);
      setStatus("Template saved.");
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Failed to save template");
    }
  }

  async function onFilter(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsLoading(true);
    await loadTemplates(searchText.trim(), filterTag.trim());
  }

  function clearFilter() {
    setSearchText("");
    setFilterTag("");
    setIsLoading(true);
    void loadTemplates();
  }

  function selectTemplate(template: PromptTemplate) {
    setSelectedId(template.id);
    setName(template.name);
    setDescription(template.description);
    setBody(template.body);
    setTagsText(template.tags.join(", "));
    setStatus(null);
    setError(null);
  }

  async function saveSelectedTemplate() {
    if (selectedId === null) return;
    setStatus(null);
    setError(null);
    try {
      const updated = await apiClient.updatePromptTemplate(selectedId, {
        name: name.trim(),
        description: description.trim(),
        body: body.trim(),
        tags: splitTags(tagsText),
      });
      setTemplates((existing) => existing.map((item) => (item.id === updated.id ? updated : item)));
      setStatus("Template updated.");
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Failed to update template");
    }
  }

  async function importBuiltinJsonTemplates() {
    setStatus(null);
    setError(null);
    try {
      const result = await apiClient.importBuiltinPromptTemplatesJson({ upsert_by_name: true });
      setIsLoading(true);
      await loadTemplates(searchText.trim(), filterTag.trim());
      setStatus(
        `Imported via JSON: imported=${result.imported}, updated=${result.updated}, skipped=${result.skipped}.`
      );
    } catch (importError) {
      setError(importError instanceof Error ? importError.message : "Failed to import JSON templates");
    }
  }

  async function importBuiltinSqlTemplates() {
    setStatus(null);
    setError(null);
    try {
      const result = await apiClient.importBuiltinPromptTemplatesSql({ reset_existing: false });
      setIsLoading(true);
      await loadTemplates(searchText.trim(), filterTag.trim());
      setStatus(
        `Imported via SQL: imported=${result.imported}, updated=${result.updated}, skipped=${result.skipped}.`
      );
    } catch (importError) {
      setError(importError instanceof Error ? importError.message : "Failed to import SQL templates");
    }
  }

  return (
    <PageCard title="Templates" description="Create and reuse prompt templates for repeatable workflows.">
      <section className="result-block">
        <h3>Quick Import</h3>
        <p className="muted">Load the curated starter template library in one click.</p>
        <div className="button-row">
          <button type="button" onClick={importBuiltinJsonTemplates}>
            Import Built-in JSON
          </button>
          <button type="button" onClick={importBuiltinSqlTemplates}>
            Import Built-in SQL
          </button>
        </div>
      </section>

      <form onSubmit={onCreate}>
        <label>
          Name
          <input value={name} onChange={(event) => setName(event.target.value)} />
        </label>
        <label>
          Description
          <textarea value={description} rows={3} onChange={(event) => setDescription(event.target.value)} />
        </label>
        <label>
          Template Body
          <textarea value={body} rows={6} onChange={(event) => setBody(event.target.value)} />
        </label>
        <label>
          Tags (comma-separated)
          <input value={tagsText} onChange={(event) => setTagsText(event.target.value)} />
        </label>
        <div className="button-row">
          <button type="submit">Save Template</button>
          <button type="button" onClick={saveSelectedTemplate} disabled={selectedId === null}>
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
        <h3>Templates</h3>
        {isLoading ? <p className="muted">Loading templates...</p> : null}
        {!isLoading && templates.length === 0 ? <p className="muted">No templates found.</p> : null}
        {templates.map((template) => (
          <article key={template.id} className="history-plan">
            <h4>{template.name}</h4>
            <p>{template.description}</p>
            <pre>{template.body}</pre>
            <p className="muted">Tags: {template.tags.join(", ") || "none"}</p>
            <button type="button" onClick={() => selectTemplate(template)}>
              Edit
            </button>
          </article>
        ))}
      </section>
    </PageCard>
  );
}
