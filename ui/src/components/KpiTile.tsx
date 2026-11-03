interface KpiTileProps {
  label: string;
  value: string | number;
  trend?: string;
  tone?: 'default' | 'positive' | 'warning' | 'danger';
}

export default function KpiTile({ label, value, trend, tone = 'default' }: KpiTileProps) {
  return (
    <div className={`tile tile-${tone}`}>
      <div className="tile-label">{label}</div>
      <div className="tile-value">{value}</div>
      {trend && <div className="tile-trend">{trend}</div>}
    </div>
  );
}
