type Props = {
  label: string;
  value: string;
  highlight?: boolean;
};

export function MetricCard({ label, value, highlight }: Props) {
  return (
    <div className="panel" style={{ borderColor: highlight ? "#7f1d1d" : undefined }}>
      <div style={{ fontSize: 12, color: "#8da0c5", marginBottom: 8 }}>{label}</div>
      <div
        style={{
          fontSize: 28,
          lineHeight: 1,
          fontWeight: 700,
          color: highlight ? "#fb7185" : "#f8fbff"
        }}
      >
        {value}
      </div>
    </div>
  );
}
