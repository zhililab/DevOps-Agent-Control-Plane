import type { ReactNode } from "react";

type PageCardProps = {
  title: string;
  description?: string;
  children: ReactNode;
};

export function PageCard({ title, description, children }: PageCardProps) {
  return (
    <section className="card" aria-label={title}>
      <header className="card-header">
        <h2>{title}</h2>
        {description ? <p className="muted">{description}</p> : null}
      </header>
      <div className="card-body">{children}</div>
    </section>
  );
}
