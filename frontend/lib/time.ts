const DEFAULT_BUSINESS_TIMEZONE = "Asia/Shanghai";

type DateTimeParts = {
  year: string;
  month: string;
  day: string;
  hour: string;
  minute: string;
  second: string;
  timeZoneName: string;
};

export function parseUtcTimestamp(value: string): Date {
  const normalized = /(?:Z|[+-]\d{2}:?\d{2})$/.test(value) ? value : `${value}Z`;
  return new Date(normalized);
}

export function formatBusinessTimestamp(value: string, timeZone = DEFAULT_BUSINESS_TIMEZONE): string {
  const date = parseUtcTimestamp(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  const formatter = new Intl.DateTimeFormat("en-GB", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hourCycle: "h23",
    timeZoneName: "shortOffset",
  });
  const parts = formatter.formatToParts(date).reduce<Partial<DateTimeParts>>((current, part) => {
    if (part.type !== "literal") {
      current[part.type as keyof DateTimeParts] = part.value;
    }
    return current;
  }, {});

  const timestamp = `${parts.year}-${parts.month}-${parts.day} · ${parts.hour}:${parts.minute}:${parts.second}`;
  const timezoneLabel = (parts.timeZoneName ?? "GMT+8").replace("GMT+08:00", "GMT+8").replace("GMT+08", "GMT+8");
  return `${timestamp} ${timezoneLabel}`;
}
