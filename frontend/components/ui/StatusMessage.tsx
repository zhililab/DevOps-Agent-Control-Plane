type StatusMessageProps = {
  message: string;
  tone?: "default" | "error" | "success";
};

export function StatusMessage({ message, tone = "default" }: StatusMessageProps) {
  return (
    <p className={`status status-${tone}`} role="status">
      {message}
    </p>
  );
}
