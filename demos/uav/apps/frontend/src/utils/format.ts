export function formatPercent(value: number): string {
  return `${Math.round(value)}%`;
}

export function formatDistanceKm(value: number): string {
  return `${value.toFixed(1)} km`;
}

export function formatAltitude(value: number): string {
  return `${Math.round(value)} m`;
}

export function formatDurationMinutes(value: number): string {
  return `${Math.round(value)} min`;
}
