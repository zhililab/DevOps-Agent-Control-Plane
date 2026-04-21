"use client";

import { FormEvent, useState } from "react";

import { PageCard } from "@/components/ui/PageCard";
import { StatusMessage } from "@/components/ui/StatusMessage";
import { apiClient } from "@/lib/api";
import type { UserProfile } from "@/lib/types";

export function ProfileView() {
  const [name, setName] = useState("Lizhi");
  const [role, setRole] = useState("Platform Engineer");
  const [language, setLanguage] = useState("en");
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    try {
      const created = await apiClient.createProfile({
        name,
        role,
        language,
        preferences: { timezone: "Asia/Shanghai" },
        goals: ["Improve execution consistency"],
      });
      setProfile(created);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Failed to save profile");
    }
  }

  return (
    <PageCard title="Profile" description="Store personal context and preferences.">
      <section className="result-block">
        <h3>Profile Guidance</h3>
        <p className="muted">Keep profile fields concise so generated plans and analyses stay focused.</p>
      </section>

      <form onSubmit={onSubmit}>
        <label>
          Name
          <input value={name} onChange={(event) => setName(event.target.value)} />
        </label>
        <label>
          Role
          <input value={role} onChange={(event) => setRole(event.target.value)} />
        </label>
        <label>
          Language
          <input value={language} onChange={(event) => setLanguage(event.target.value)} />
        </label>
        <button type="submit">Save Profile</button>
      </form>

      {error ? <StatusMessage message={error} tone="error" /> : null}
      {profile ? (
        <section className="reflection-section">
          <StatusMessage message={`Saved ${profile.name} (${profile.role})`} tone="success" />
          <div className="result-block">
            <p className="muted">
              Preferences are now available for future workflow templates and personalized suggestions.
            </p>
          </div>
        </section>
      ) : null}
    </PageCard>
  );
}
