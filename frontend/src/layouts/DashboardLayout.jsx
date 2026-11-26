// Sidebar + top navbar shared by all three role dashboards. Only the menu items differ.
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import {
  LayoutDashboard, Users, Upload, Briefcase, Sparkles, Search, ListChecks, CalendarClock, BarChart3,
  UserCircle, LogOut, Bell, ClipboardCheck, Menu, X,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import api, { errorMessage } from '../services/api'

const MENUS = {
  admin: [
    ['/admin', 'Dashboard', LayoutDashboard, true], ['/admin/candidates', 'Candidates', Users],
    ['/admin/upload', 'Bulk Upload', Upload], ['/admin/jobs', 'Jobs', Briefcase],
    ['/admin/matching', 'AI Matching', Sparkles], ['/admin/search', 'Semantic Search', Search],
    ['/admin/shortlists', 'Shortlists', ListChecks], ['/admin/interviews', 'Interviews', CalendarClock],
    ['/admin/analytics', 'Analytics', BarChart3],
  ],
  candidate: [
    ['/candidate', 'Dashboard', LayoutDashboard, true], ['/candidate/profile', 'My Profile & Resume', UserCircle],
    ['/candidate/jobs', 'Browse Jobs', Briefcase], ['/candidate/interviews', 'My Interviews', CalendarClock],
  ],
  interviewer: [['/interviewer', 'My Interviews', ClipboardCheck, true]],
}

const TITLES = { admin: 'Recruitment Admin', candidate: 'Candidate Portal', interviewer: 'Interviewer Portal' }

export default function DashboardLayout() {
  const { user, logout } = useAuth()
  const toast = useToast()
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)
  const [notifications, setNotifications] = useState([])
  const [notificationsOpen, setNotificationsOpen] = useState(false)
  const unread = notifications.filter((notification) => !notification.is_read).length

  useEffect(() => {
    api.get('/api/notifications').then((response) => setNotifications(response.data))
      .catch((error) => toast.error(errorMessage(error)))
  }, [toast])

  const initials = user.full_name.split(/\s+/).map((part) => part[0]).slice(0, 2).join('').toUpperCase()

  async function toggleNotifications() {
    if (!notificationsOpen) {
      try {
        const { data } = await api.get('/api/notifications')
        setNotifications(data)
      } catch (error) {
        toast.error(errorMessage(error))
      }
    }
    setNotificationsOpen((open) => !open)
  }

  async function markAllNotificationsRead() {
    try {
      await api.post('/api/notifications/read-all')
      setNotifications((current) => current.map((notification) => ({ ...notification, is_read: true })))
    } catch (error) {
      toast.error(errorMessage(error))
    }
  }

  return (
    <div className="flex min-h-screen bg-slate-50">
      {menuOpen && <button type="button" aria-label="Close navigation" className="fixed inset-0 z-20 bg-slate-950/30 backdrop-blur-[2px] md:hidden" onClick={() => setMenuOpen(false)} />}
      <aside className={`fixed inset-y-0 left-0 z-30 flex w-72 flex-col border-r border-slate-200 bg-white px-4 py-5 transition-transform md:sticky md:top-0 md:h-screen md:translate-x-0 ${menuOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="mb-9 flex items-center gap-3 px-2">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-600 text-white shadow-md shadow-brand-600/20"><Briefcase size={19} /></span>
          <div>
            <p className="text-lg font-bold tracking-tight text-navy-900">TalentIQ</p>
            <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-400">Hiring workspace</p>
          </div>
        </div>
        <p className="mb-2 px-3 text-[10px] font-bold uppercase tracking-[0.18em] text-slate-400">Workspace</p>
        <nav className="space-y-1">
          {MENUS[user.role].map(([to, label, Icon, end]) => (
            <NavLink key={to} to={to} end={end} onClick={() => setMenuOpen(false)}
              className={({ isActive }) => `group flex items-center gap-3 rounded-xl border px-3 py-2.5 text-sm font-medium transition ${isActive ? 'border-slate-200 bg-slate-100 text-navy-900 shadow-sm' : 'border-transparent text-slate-600 hover:bg-slate-50 hover:text-navy-900'}`}>
              <Icon size={18} className="shrink-0 opacity-80 group-hover:opacity-100" />{label}
            </NavLink>
          ))}
        </nav>
        <div className="mt-auto rounded-2xl bg-slate-50 p-4">
          <div className="mb-2 flex h-8 w-8 items-center justify-center rounded-lg bg-white text-brand-600 shadow-sm"><Sparkles size={16} /></div>
          <p className="text-xs font-semibold text-navy-900">A smoother hiring flow</p>
          <p className="mt-1 text-xs leading-5 text-slate-500">Keep candidate profiles, decisions, and interviews together.</p>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 flex h-[72px] items-center justify-between border-b border-slate-200/80 bg-white/95 px-4 backdrop-blur sm:px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <button type="button" className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 md:hidden" aria-label={menuOpen ? 'Close navigation' : 'Open navigation'} onClick={() => setMenuOpen(!menuOpen)}>
              {menuOpen ? <X size={20} /> : <Menu size={20} />}
            </button>
            <div>
              <p className="text-sm font-semibold text-navy-900">{TITLES[user.role]}</p>
              <p className="hidden text-xs text-slate-400 sm:block">TalentIQ recruitment workspace</p>
            </div>
          </div>
          <div className="flex items-center gap-3 sm:gap-5">
            <div className="relative">
              <button type="button" className="relative rounded-xl p-2.5 text-slate-500 transition hover:bg-slate-100 hover:text-navy-900" title={`${unread} unread notifications`}
                aria-label="Notifications" aria-expanded={notificationsOpen} onClick={toggleNotifications}>
                <Bell size={18} />
                {unread > 0 && <span className="absolute right-1 top-1 h-2 w-2 rounded-full bg-red-500 ring-2 ring-white" />}
              </button>
              {notificationsOpen && (
                <div role="dialog" aria-label="Notifications" className="absolute right-0 z-40 mt-3 w-80 max-w-[90vw] rounded-2xl border border-slate-200 bg-white p-4 text-sm shadow-xl">
                  <div className="mb-3 flex items-center justify-between">
                    <strong className="text-navy-900">Notifications <span className="ml-1 font-normal text-slate-400">{unread ? `(${unread} new)` : ''}</span></strong>
                    <button type="button" className="text-xs font-semibold text-brand-700 disabled:text-slate-400"
                      disabled={unread === 0} onClick={markAllNotificationsRead}>Mark all read</button>
                  </div>
                  <div className="max-h-80 overflow-y-auto">
                    {notifications.length ? notifications.map((notification) => (
                      <div key={notification.id} className={`border-t border-slate-100 px-2 py-3 leading-5 ${notification.is_read ? 'text-slate-500' : 'font-medium text-navy-900'}`}>
                        {notification.message}
                      </div>
                    )) : <p className="border-t border-slate-100 py-3 text-center text-slate-500">No notifications yet</p>}
                  </div>
                </div>
              )}
            </div>
            <div className="hidden items-center gap-2.5 sm:flex">
              <span className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-50 text-xs font-bold text-brand-700">{initials}</span>
              <span className="max-w-36 truncate text-sm font-medium text-slate-700">{user.full_name}</span>
            </div>
            <button className="btn-secondary !rounded-xl !px-3 !py-2 text-xs sm:text-sm" onClick={() => { logout(); navigate('/login') }}><LogOut size={15} /><span className="hidden sm:inline">Log out</span></button>
          </div>
        </header>
        <main className="flex-1 p-4 sm:p-6 lg:p-8"><Outlet /></main>
      </div>
    </div>
  )
}
