function scoreToY(value, chartHeight = 180) {
  const num = Number(value);
  const safe = Number.isFinite(num) ? Math.max(0, Math.min(100, num)) : 0;
  return chartHeight - (safe / 100) * chartHeight;
}

export function SimpleBarChart({ labels = [], series = [] }) {
  const width = 760;
  const height = 260;
  const margin = { top: 20, right: 20, bottom: 56, left: 42 };
  const plotWidth = width - margin.left - margin.right;
  const plotHeight = height - margin.top - margin.bottom;
  const groupCount = Math.max(1, labels.length);
  const seriesCount = Math.max(1, series.length);
  const groupWidth = plotWidth / groupCount;
  const innerGap = 4;
  const barWidth = Math.max(8, (groupWidth - 14 - innerGap * (seriesCount - 1)) / seriesCount);
  const colors = ["#0f766e", "#2563eb", "#b45309", "#7c3aed"];
  const yTicks = [0, 25, 50, 75, 100];

  const bars = [];
  labels.forEach((label, groupIdx) => {
    const groupStart = margin.left + groupIdx * groupWidth + 7;
    series.forEach((item, sIdx) => {
      const value = Number(item?.data?.[groupIdx] ?? 0);
      const safe = Math.max(0, Math.min(100, value));
      const barHeight = (safe / 100) * plotHeight;
      const x = groupStart + sIdx * (barWidth + innerGap);
      const y = margin.top + (plotHeight - barHeight);
      bars.push(
        <g key={`${label}-${item.label}-${sIdx}`}>
          <rect x={x} y={y} width={barWidth} height={barHeight} fill={colors[sIdx % colors.length]} rx="3">
            <title>{`${item.label}: ${safe.toFixed(1)}`}</title>
          </rect>
          <text x={x + barWidth / 2} y={Math.max(y - 4, 10)} textAnchor="middle" fontSize="9" fill="#334155">
            {safe.toFixed(0)}
          </text>
        </g>
      );
    });

    const labelText = String(label || "").length > 14 ? `${String(label).slice(0, 14)}...` : String(label);
    bars.push(
      <text
        key={`xlabel-${label}-${groupIdx}`}
        x={groupStart + ((barWidth + innerGap) * seriesCount - innerGap) / 2}
        y={height - 18}
        textAnchor="middle"
        fontSize="10"
        fill="#475569"
      >
        {labelText}
      </text>
    );
  });

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="h-56 w-full rounded-lg border border-slate-200 bg-white">
      {yTicks.map((tick) => {
        const y = margin.top + (1 - tick / 100) * plotHeight;
        return (
          <g key={`ytick-${tick}`}>
            <line x1={margin.left} y1={y} x2={width - margin.right} y2={y} stroke="#e2e8f0" strokeWidth="1" />
            <text x={margin.left - 8} y={y + 3} textAnchor="end" fontSize="9" fill="#64748b">
              {tick}
            </text>
          </g>
        );
      })}
      <line x1={margin.left} y1={margin.top} x2={margin.left} y2={height - margin.bottom} stroke="#cbd5e1" strokeWidth="1" />
      <line x1={margin.left} y1={height - margin.bottom} x2={width - margin.right} y2={height - margin.bottom} stroke="#cbd5e1" strokeWidth="1" />
      {bars}
      {series.map((item, idx) => (
        <g key={`legend-${item.label}-${idx}`}>
          <rect x={width - margin.right - 150} y={10 + idx * 14} width="9" height="9" fill={colors[idx % colors.length]} rx="2" />
          <text x={width - margin.right - 136} y={18 + idx * 14} fontSize="10" fill="#475569">
            {item.label}
          </text>
        </g>
      ))}
    </svg>
  );
}

export function SimpleScatterChart({ datasets = [] }) {
  const width = 520;
  const height = 220;
  const colors = ["#0f766e", "#2563eb", "#b45309", "#7c3aed"];
  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="h-56 w-full rounded-lg border border-slate-200 bg-white">
      <line x1="30" y1="190" x2={width - 20} y2="190" stroke="#cbd5e1" strokeWidth="1" />
      <line x1="30" y1="20" x2="30" y2="190" stroke="#cbd5e1" strokeWidth="1" />
      {datasets.map((set, idx) => {
        const point = set?.data?.[0] || {};
        const x = 30 + ((Number(point.x) || 0) / 100) * (width - 60);
        const y = scoreToY(Number(point.y) || 0, 170) + 20;
        return <circle key={`${set.label}-${idx}`} cx={x} cy={y} r="5" fill={colors[idx % colors.length]} opacity="0.88" />;
      })}
    </svg>
  );
}

export function SimpleRadarChart({ labels = [], datasets = [] }) {
  const size = 260;
  const center = size / 2;
  const radius = 90;
  const levels = [0.25, 0.5, 0.75, 1];
  const colors = ["#0f766e88", "#2563eb88", "#b4530988", "#7c3aed88"];
  const angleStep = (Math.PI * 2) / Math.max(1, labels.length);

  const toPoint = (value, idx) => {
    const ratio = (Math.max(0, Math.min(100, Number(value) || 0)) / 100) * radius;
    const angle = -Math.PI / 2 + idx * angleStep;
    const x = center + ratio * Math.cos(angle);
    const y = center + ratio * Math.sin(angle);
    return `${x},${y}`;
  };

  const rings = levels.map((level) => {
    const ringPoints = labels.map((_, idx) => {
      const angle = -Math.PI / 2 + idx * angleStep;
      const x = center + radius * level * Math.cos(angle);
      const y = center + radius * level * Math.sin(angle);
      return `${x},${y}`;
    });
    return <polygon key={`ring-${level}`} points={ringPoints.join(" ")} fill="none" stroke="#e2e8f0" strokeWidth="1" />;
  });

  return (
    <svg viewBox={`0 0 ${size} ${size}`} className="h-64 w-full rounded-lg border border-slate-200 bg-white">
      {rings}
      {datasets.map((set, idx) => {
        const points = (set.data || []).map((value, pIdx) => toPoint(value, pIdx)).join(" ");
        return <polygon key={`${set.label}-${idx}`} points={points} fill={colors[idx % colors.length]} stroke={colors[idx % colors.length].replace("88", "dd")} strokeWidth="2" />;
      })}
    </svg>
  );
}
