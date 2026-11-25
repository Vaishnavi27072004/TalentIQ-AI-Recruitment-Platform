// Recharts wrappers. All data comes from /api/analytics/dashboard (database queries).
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, CartesianGrid, Legend, Label } from 'recharts'
import { EmptyState } from './ui'

const COLORS = ['#2563eb', '#0891b2', '#8b5cf6', '#f59e0b', '#10b981', '#ef4444']

function CategoryAxisTick({ x, y, payload }) {
  const label = String(payload.value ?? '')
  const lines = label.split(/\s+/).reduce((result, word) => {
    const last = result[result.length - 1]
    if (last && `${last} ${word}`.length <= 18) result[result.length - 1] = `${last} ${word}`
    else result.push(word)
    return result
  }, [])

  return (
    <g transform={`translate(${x},${y})`}>
      <text textAnchor="end" fill="#64748b" fontSize={10} aria-label={label}>
        <title>{label}</title>
        {lines.map((line, index) => (
          <tspan key={`${line}-${index}`} x={-8} dy={index === 0 ? -((lines.length - 1) * 6) : 12}>{line}</tspan>
        ))}
      </text>
    </g>
  )
}

export function ChartCard({ title, children }) {
  return <div className="card"><h3 className="mb-3 text-sm font-semibold text-navy-900">{title}</h3><div className="h-64">{children}</div></div>
}

const hasData = (rows, key) => rows?.some((row) => row[key] > 0)

export function SimpleBar({ rows, xKey, yKey, horizontal }) {
  if (!hasData(rows, yKey)) return <EmptyState title="No data yet" />
  return (
    <ResponsiveContainer>
      <BarChart data={rows} layout={horizontal ? 'vertical' : 'horizontal'}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        {horizontal ? <><XAxis type="number" allowDecimals={false} /><YAxis type="category" dataKey={xKey} width={160} tick={<CategoryAxisTick />} /></> : <><XAxis dataKey={xKey} tick={{ fontSize: 11 }} /><YAxis allowDecimals={false} /></>}
        <Tooltip />
        <Bar dataKey={yKey} fill="#2563eb" radius={4} />
      </BarChart>
    </ResponsiveContainer>
  )
}

export function SimplePie({ rows, nameKey, valueKey }) {
  const nonZero = rows?.filter((row) => row[valueKey] > 0) || []
  if (!nonZero.length) return <EmptyState title="No data yet" />
  const total = nonZero.reduce((sum, row) => sum + Number(row[valueKey] || 0), 0)
  return (
    <ResponsiveContainer>
      <PieChart>
        <Pie
          data={nonZero}
          dataKey={valueKey}
          nameKey={nameKey}
          innerRadius={54}
          outerRadius={82}
          paddingAngle={nonZero.length > 1 ? 3 : 0}
          label={false}
          labelLine={false}
        >
          <Label value={total} position="center" fill="#12233f" fontSize={24} fontWeight={700} pointerEvents="none" />
          {nonZero.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} stroke="none" />)}
        </Pie>
        <Tooltip /><Legend />
      </PieChart>
    </ResponsiveContainer>
  )
}
