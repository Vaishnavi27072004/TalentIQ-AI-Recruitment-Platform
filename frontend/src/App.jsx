import { lazy, Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth, HOME_BY_ROLE } from './context/AuthContext'
import Login from './pages/Login'
import Register from './pages/Register'
import ForgotPassword from './pages/ForgotPassword'

const DashboardLayout = lazy(() => import('./layouts/DashboardLayout'))
const AdminDashboard = lazy(() => import('./pages/admin/AdminDashboard'))
const Candidates = lazy(() => import('./pages/admin/Candidates'))
const CandidateProfile = lazy(() => import('./pages/admin/CandidateProfile'))
const BulkUpload = lazy(() => import('./pages/admin/BulkUpload'))
const Jobs = lazy(() => import('./pages/admin/Jobs'))
const Matching = lazy(() => import('./pages/admin/Matching'))
const SemanticSearch = lazy(() => import('./pages/admin/SemanticSearch'))
const Shortlists = lazy(() => import('./pages/admin/Shortlists'))
const Interviews = lazy(() => import('./pages/admin/Interviews'))
const Analytics = lazy(() => import('./pages/admin/Analytics'))
const CandidateHome = lazy(() => import('./pages/candidate/CandidateHome'))
const MyProfile = lazy(() => import('./pages/candidate/MyProfile'))
const BrowseJobs = lazy(() => import('./pages/candidate/BrowseJobs'))
const MyInterviews = lazy(() => import('./pages/candidate/MyInterviews'))
const InterviewerHome = lazy(() => import('./pages/interviewer/InterviewerHome'))

// Only lets the right role in. Anyone else goes to their own home or the login page.
function RequireRole({ role, children }) {
  const { user } = useAuth()
  if (!user) return <Navigate to="/login" replace />
  if (user.role !== role) return <Navigate to={HOME_BY_ROLE[user.role]} replace />
  return children
}

function HomeRedirect() {
  const { user } = useAuth()
  return <Navigate to={user ? HOME_BY_ROLE[user.role] : '/login'} replace />
}

export default function App() {
  return (
    <Suspense fallback={<div className="p-6 text-sm text-slate-500">Loading page...</div>}>
      <Routes>
        <Route path="/" element={<HomeRedirect />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />

        <Route path="/admin" element={<RequireRole role="admin"><DashboardLayout /></RequireRole>}>
          <Route index element={<AdminDashboard />} />
          <Route path="candidates" element={<Candidates />} />
          <Route path="candidates/:id" element={<CandidateProfile />} />
          <Route path="upload" element={<BulkUpload />} />
          <Route path="jobs" element={<Jobs />} />
          <Route path="matching" element={<Matching />} />
          <Route path="search" element={<SemanticSearch />} />
          <Route path="shortlists" element={<Shortlists />} />
          <Route path="interviews" element={<Interviews />} />
          <Route path="analytics" element={<Analytics />} />
        </Route>

        <Route path="/candidate" element={<RequireRole role="candidate"><DashboardLayout /></RequireRole>}>
          <Route index element={<CandidateHome />} />
          <Route path="profile" element={<MyProfile />} />
          <Route path="jobs" element={<BrowseJobs />} />
          <Route path="interviews" element={<MyInterviews />} />
        </Route>

        <Route path="/interviewer" element={<RequireRole role="interviewer"><DashboardLayout /></RequireRole>}>
          <Route index element={<InterviewerHome />} />
        </Route>

        <Route path="*" element={<HomeRedirect />} />
      </Routes>
    </Suspense>
  )
}
