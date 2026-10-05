import { lazy, Suspense, type ReactNode } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './auth/AuthContext'
import { AppLayout } from './components/AppLayout'
import { Loading } from './components/ui'
import Landing from './pages/Landing'
import Login from './pages/auth/Login'
import Register from './pages/auth/Register'
import Verify from './pages/auth/Verify'

const CDashboard = lazy(() => import('./pages/candidate/Dashboard'))
const CProfile = lazy(() => import('./pages/candidate/Profile'))
const CTesting = lazy(() => import('./pages/candidate/Testing'))
const CRunner = lazy(() => import('./pages/candidate/TestRunner'))
const CResult = lazy(() => import('./pages/candidate/TestResult'))
const CFsp = lazy(() => import('./pages/candidate/Fsp'))
const CInvitations = lazy(() => import('./pages/candidate/Invitations'))
const CJobs = lazy(() => import('./pages/candidate/Jobs'))
const CTasks = lazy(() => import('./pages/candidate/Tasks'))
const CSettings = lazy(() => import('./pages/candidate/Settings'))
const CPrint = lazy(() => import('./pages/candidate/PrintProfile'))

const EDashboard = lazy(() => import('./pages/employer/Dashboard'))
const ECompany = lazy(() => import('./pages/employer/Company'))
const ERequirements = lazy(() => import('./pages/employer/Requirements'))
const ERequirementForm = lazy(() => import('./pages/employer/RequirementForm'))
const EMatches = lazy(() => import('./pages/employer/Matches'))
const ECandidate = lazy(() => import('./pages/employer/CandidateView'))
const EBank = lazy(() => import('./pages/employer/Bank'))
const EInvitations = lazy(() => import('./pages/employer/Invitations'))
const EApplications = lazy(() => import('./pages/employer/Applications'))
const ETasks = lazy(() => import('./pages/employer/Tasks'))

function RequireRole({ role, children }: { role: 'candidate' | 'employer'; children: ReactNode }) {
  const { user, ready } = useAuth()
  if (!ready) return <Loading />
  if (!user) return <Navigate to="/login" replace />
  if (user.role !== role) return <Navigate to={user.role === 'candidate' ? '/candidate' : '/employer'} replace />
  return <>{children}</>
}

export default function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<Loading />}>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/verify" element={<Verify />} />

          <Route path="/candidate" element={<RequireRole role="candidate"><AppLayout /></RequireRole>}>
            <Route index element={<CDashboard />} />
            <Route path="profile" element={<CProfile />} />
            <Route path="testing" element={<CTesting />} />
            <Route path="testing/:attemptId" element={<CRunner />} />
            <Route path="results/:attemptId" element={<CResult />} />
            <Route path="fsp" element={<CFsp />} />
            <Route path="invitations" element={<CInvitations />} />
            <Route path="invitations/:invId" element={<CInvitations />} />
            <Route path="jobs" element={<CJobs />} />
            <Route path="tasks" element={<CTasks />} />
            <Route path="settings" element={<CSettings />} />
            <Route path="print" element={<CPrint />} />
          </Route>

          <Route path="/employer" element={<RequireRole role="employer"><AppLayout /></RequireRole>}>
            <Route index element={<EDashboard />} />
            <Route path="company" element={<ECompany />} />
            <Route path="requirements" element={<ERequirements />} />
            <Route path="requirements/new" element={<ERequirementForm />} />
            <Route path="requirements/:jobId" element={<EMatches />} />
            <Route path="requirements/:jobId/edit" element={<ERequirementForm />} />
            <Route path="candidates" element={<EBank />} />
            <Route path="candidates/:candidateId" element={<ECandidate />} />
            <Route path="invitations" element={<EInvitations />} />
            <Route path="applications" element={<EApplications />} />
            <Route path="tasks" element={<ETasks />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  )
}
