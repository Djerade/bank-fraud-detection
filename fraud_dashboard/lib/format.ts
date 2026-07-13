export function nf(value: number): string {
  return new Intl.NumberFormat("fr-FR").format(value);
}

export function pct(value: number, digits = 2): string {
  return `${value.toFixed(digits)} %`;
}

export function minuteLabel(v: string): string {
  return new Date(v).toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
}
