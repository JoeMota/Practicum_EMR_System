export const DAY_MS = 24 * 60 * 60 * 1000;

export function since(iso: string, now: number) {
  const mins = Math.max(0, Math.round((now - new Date(iso).getTime()) / 60000));
  if (mins < 60) return `${mins} min`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs} h`;
  const days = Math.round(hrs / 24);
  return `${days} day${days === 1 ? "" : "s"}`;
}

export const patientName = (p: { lastName: string; firstName: string }) => `${p.lastName}, ${p.firstName}`;
