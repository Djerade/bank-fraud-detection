type Props = {
  updatedAt: string;
  source: string;
  refreshSeconds: number;
};

export function Header({ updatedAt, source, refreshSeconds }: Props) {
  const time = new Date(updatedAt).toLocaleTimeString("fr-FR");
  return (
    <div
      className="panel"
      style={{
        marginBottom: 16,
        background:
          "linear-gradient(140deg, rgba(19,31,58,.95), rgba(8,15,31,.95) 55%, rgba(31,16,34,.95))"
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
        <div>
          <div style={{ fontSize: 28, fontWeight: 700, letterSpacing: -0.3 }}>FraudShield Monitoring</div>
          <div style={{ color: "#98add6", marginTop: 6 }}>
            Dashboard Next.js professionnel avec mise a jour temps reel
          </div>
        </div>
        <div style={{ textAlign: "right", color: "#9cb1d8", fontSize: 13 }}>
          <div>Source: {source}</div>
          <div>Derniere synchro: {time}</div>
          <div>Refresh: {refreshSeconds}s</div>
        </div>
      </div>
    </div>
  );
}
