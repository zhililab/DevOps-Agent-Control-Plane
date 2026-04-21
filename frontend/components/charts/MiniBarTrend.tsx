type TrendDatum = {
  label: string;
  value: number;
};

type MiniBarTrendProps = {
  title: string;
  subtitle: string;
  data: TrendDatum[];
  tone?: "brand" | "success";
};

export function MiniBarTrend({ title, subtitle, data, tone = "brand" }: MiniBarTrendProps) {
  const max = Math.max(1, ...data.map((item) => item.value));

  return (
    <article className="chart-card animate-enter">
      <h3>{title}</h3>
      <p className="muted">{subtitle}</p>
      <div className="mini-bars" role="img" aria-label={`${title} trend chart`}>
        {data.map((item, index) => (
          <div key={`${item.label}-${index}`} className="mini-bar-col">
            <div
              className={`mini-bar mini-bar-${tone}`}
              style={
                {
                  "--bar-height": `${Math.max(6, (item.value / max) * 100)}%`,
                  "--bar-delay": `${index * 70}ms`,
                } as CSSProperties
              }
            />
            <span className="mini-bar-label">{item.label}</span>
          </div>
        ))}
      </div>
    </article>
  );
}
import type { CSSProperties } from "react";
