type TrendDatum = {
  label: string;
  value: number;
};

type MiniLineTrendProps = {
  title: string;
  subtitle: string;
  data: TrendDatum[];
  tone?: "brand" | "success";
};

function toChartPoints(data: TrendDatum[]): string {
  if (data.length <= 1) {
    return "0,28 100,28";
  }

  const max = Math.max(1, ...data.map((item) => item.value));
  return data
    .map((item, index) => {
      const x = (index / (data.length - 1)) * 100;
      const y = 30 - (item.value / max) * 24;
      return `${x},${Math.min(30, Math.max(4, y))}`;
    })
    .join(" ");
}

export function MiniLineTrend({ title, subtitle, data, tone = "brand" }: MiniLineTrendProps) {
  const points = toChartPoints(data);
  const total = data.reduce((sum, item) => sum + item.value, 0);
  const peak = Math.max(0, ...data.map((item) => item.value));
  const firstLabel = data[0]?.label ?? "";
  const midLabel = data[Math.floor((data.length - 1) / 2)]?.label ?? "";
  const lastLabel = data[data.length - 1]?.label ?? "";

  return (
    <article className="chart-card animate-enter">
      <h3>{title}</h3>
      <p className="muted">{subtitle}</p>
      <div className="mini-line-wrap" role="img" aria-label={`${title} trend chart`}>
        <svg viewBox="0 0 100 34" preserveAspectRatio="none" aria-hidden="true">
          <polyline className={`mini-line mini-line-${tone}`} points={points} />
        </svg>
      </div>
      <div className="mini-line-axis" aria-hidden="true">
        <span>{firstLabel}</span>
        <span>{midLabel}</span>
        <span>{lastLabel}</span>
      </div>
      <p className="mini-line-summary">Peak {peak} · Total {total}</p>
    </article>
  );
}
