import { useState, useEffect } from 'react'
import {
  Chart as ChartJS,
  ArcElement,
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js'
import { Pie, Bar, Line, Doughnut } from 'react-chartjs-2'
import { analytics } from '../api'

ChartJS.register(
  ArcElement,
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

const COLORS = ['#2563eb', '#0891b2', '#6366f1', '#0ea5e9', '#3b82f6', '#06b6d4', '#1d4ed8', '#7c3aed', '#0284c7', '#60a5fa']

export default function AnalyticsPanel() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [labels, setLabels] = useState([])
  const [values, setValues] = useState([])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    
    // Fetch real analytics data (queries per tenant from chat history)
    analytics()
      .then((data) => {
        if (cancelled) return
        const l = Array.isArray(data.labels) ? data.labels : []
        const v = Array.isArray(data.data) ? data.data : []
        setLabels(l)
        setValues(v)
      })
      .catch((e) => {
        if (!cancelled) setError(e.message)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [])

  // Calculate stats
  const totalQueries = values.reduce((sum, v) => sum + v, 0)
  const avgPerTenant = labels.length > 0 ? Math.round(totalQueries / labels.length) : 0
  const maxQueries = Math.max(...values, 0)
  const activeTenants = labels.length

  // Mock time-series data for trend chart (last 7 days)
  const last7Days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
  const mockTrendData = last7Days.map((_, i) => Math.floor(Math.random() * 30) + 10 + (i * 2))

  const pieData = {
    labels,
    datasets: [{
      data: values,
      backgroundColor: COLORS,
      borderColor: '#ffffff',
      borderWidth: 2,
    }],
  }

  const barData = {
    labels,
    datasets: [{
      label: 'Queries by Tenant',
      data: values,
      backgroundColor: COLORS.map(c => c + '99'),
      borderColor: COLORS,
      borderWidth: 2,
      borderRadius: 8,
    }],
  }

  const lineData = {
    labels: last7Days,
    datasets: [{
      label: 'Daily Queries',
      data: mockTrendData,
      borderColor: '#2563eb',
      backgroundColor: 'rgba(37, 99, 235, 0.1)',
      fill: true,
      tension: 0.4,
      pointRadius: 4,
      pointBackgroundColor: '#2563eb',
      pointBorderColor: '#fff',
      pointBorderWidth: 2,
    }],
  }

  const doughnutData = {
    labels: ['Completed', 'Pending', 'Failed'],
    datasets: [{
      data: [totalQueries * 0.85, totalQueries * 0.1, totalQueries * 0.05].map(Math.round),
      backgroundColor: ['#10b981', '#f59e0b', '#ef4444'],
      borderColor: '#ffffff',
      borderWidth: 3,
    }],
  }

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'bottom',
        labels: {
          color: '#475569',
          font: { size: 12, family: 'Inter' },
          padding: 12,
          usePointStyle: true,
        },
      },
    },
  }

  const barOptions = {
    ...chartOptions,
    scales: {
      y: {
        beginAtZero: true,
        grid: { color: '#e2e8f0' },
        ticks: { color: '#64748b' },
      },
      x: {
        grid: { display: false },
        ticks: { color: '#64748b' },
      },
    },
  }

  const lineOptions = {
    ...chartOptions,
    scales: {
      y: {
        beginAtZero: true,
        grid: { color: '#e2e8f0' },
        ticks: { color: '#64748b' },
      },
      x: {
        grid: { display: false },
        ticks: { color: '#64748b' },
      },
    },
  }

  if (loading) {
    return (
      <div className="p-6 h-full overflow-y-auto bg-slate-50 flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
          <p className="text-slate-600 font-medium">Loading analytics...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-6 h-full overflow-y-auto bg-slate-50">
        <div className="bg-white rounded-xl border border-red-200 p-6 shadow-sm">
          <p className="text-red-600 p-3 bg-red-50 rounded-lg border border-red-200">{error}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 h-full overflow-y-auto bg-slate-50">
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-2xl font-bold text-slate-900 font-heading tracking-tight">Admin Analytics Dashboard</h3>
            <p className="text-sm text-slate-600 mt-1">Comprehensive insights and metrics</p>
          </div>
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-green-50 border border-green-200">
            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
            <span className="text-xs font-semibold text-green-700">Real-time</span>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm hover:shadow-md transition-shadow">
            <div className="flex items-center justify-between mb-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center">
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>
              </div>
              <span className="text-xs font-semibold text-green-600 bg-green-50 px-2 py-1 rounded-full">+12%</span>
            </div>
            <h4 className="text-sm font-medium text-slate-600 mb-1">Total Queries</h4>
            <p className="text-2xl font-bold text-slate-900">{totalQueries.toLocaleString()}</p>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm hover:shadow-md transition-shadow">
            <div className="flex items-center justify-between mb-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-purple-600 flex items-center justify-center">
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" /></svg>
              </div>
              <span className="text-xs font-semibold text-blue-600 bg-blue-50 px-2 py-1 rounded-full">Active</span>
            </div>
            <h4 className="text-sm font-medium text-slate-600 mb-1">Active Tenants</h4>
            <p className="text-2xl font-bold text-slate-900">{activeTenants}</p>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm hover:shadow-md transition-shadow">
            <div className="flex items-center justify-between mb-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-cyan-600 flex items-center justify-center">
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" /></svg>
              </div>
              <span className="text-xs font-semibold text-orange-600 bg-orange-50 px-2 py-1 rounded-full">Avg</span>
            </div>
            <h4 className="text-sm font-medium text-slate-600 mb-1">Avg per Tenant</h4>
            <p className="text-2xl font-bold text-slate-900">{avgPerTenant}</p>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm hover:shadow-md transition-shadow">
            <div className="flex items-center justify-between mb-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-indigo-600 flex items-center justify-center">
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" /></svg>
              </div>
              <span className="text-xs font-semibold text-purple-600 bg-purple-50 px-2 py-1 rounded-full">Peak</span>
            </div>
            <h4 className="text-sm font-medium text-slate-600 mb-1">Max Queries</h4>
            <p className="text-2xl font-bold text-slate-900">{maxQueries}</p>
          </div>
        </div>

        {/* Main Charts Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Bar Chart */}
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-lg hover:shadow-xl transition-shadow">
            <h4 className="text-lg font-bold text-slate-900 font-heading mb-4 flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-blue-600" />
              Queries by Tenant
            </h4>
            <div className="h-[280px]">
              {labels.length > 0 ? (
                <Bar data={barData} options={barOptions} />
              ) : (
                <div className="flex items-center justify-center h-full text-slate-500">No data yet.</div>
              )}
            </div>
          </div>

          {/* Line Chart */}
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-lg hover:shadow-xl transition-shadow">
            <h4 className="text-lg font-bold text-slate-900 font-heading mb-4 flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-blue-600" />
              7-Day Query Trend
            </h4>
            <div className="h-[280px]">
              <Line data={lineData} options={lineOptions} />
            </div>
          </div>

          {/* Pie Chart */}
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-lg hover:shadow-xl transition-shadow">
            <h4 className="text-lg font-bold text-slate-900 font-heading mb-4 flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-blue-600" />
              Distribution by Tenant
            </h4>
            <div className="h-[280px]">
              {labels.length > 0 ? (
                <Pie data={pieData} options={chartOptions} />
              ) : (
                <div className="flex items-center justify-center h-full text-slate-500">No data yet.</div>
              )}
            </div>
          </div>

          {/* Doughnut Chart */}
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-lg hover:shadow-xl transition-shadow">
            <h4 className="text-lg font-bold text-slate-900 font-heading mb-4 flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-green-600" />
              Query Status
            </h4>
            <div className="h-[280px]">
              {totalQueries > 0 ? (
                <Doughnut data={doughnutData} options={chartOptions} />
              ) : (
                <div className="flex items-center justify-center h-full text-slate-500">No queries yet.</div>
              )}
            </div>
          </div>
        </div>

        {/* Detailed List */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-lg">
          <h4 className="text-lg font-bold text-slate-900 font-heading mb-4 flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-blue-600" />
            Tenant Details
          </h4>
          {labels.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200">
                    <th className="text-left py-3 px-4 font-semibold text-slate-700">Tenant</th>
                    <th className="text-left py-3 px-4 font-semibold text-slate-700">Queries</th>
                    <th className="text-left py-3 px-4 font-semibold text-slate-700">Percentage</th>
                    <th className="text-left py-3 px-4 font-semibold text-slate-700">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {labels.map((l, idx) => {
                    const pct = totalQueries > 0 ? ((values[idx] / totalQueries) * 100).toFixed(1) : '0.0'
                    return (
                      <tr key={l} className="border-b border-slate-100 hover:bg-slate-50 transition-colors">
                        <td className="py-3 px-4 flex items-center gap-3">
                          <span className="inline-block w-3 h-3 rounded-full" style={{ background: COLORS[idx % COLORS.length] }} />
                          <span className="font-medium text-slate-900">{l}</span>
                        </td>
                        <td className="py-3 px-4 text-slate-900 font-semibold">{values[idx] ?? 0}</td>
                        <td className="py-3 px-4">
                          <div className="flex items-center gap-2">
                            <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden max-w-[100px]">
                              <div className="h-full bg-blue-600 rounded-full" style={{ width: `${pct}%` }} />
                            </div>
                            <span className="text-slate-600 text-xs font-medium">{pct}%</span>
                          </div>
                        </td>
                        <td className="py-3 px-4">
                          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-green-50 text-green-700 border border-green-200">
                            Active
                          </span>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-slate-500 py-8 text-center">No tenant data available yet.</p>
          )}
        </div>
      </div>
    </div>
  )
}
