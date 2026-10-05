import {
  Briefcase,
  Building2,
  ClipboardCheck,
  FileText,
  Inbox,
  LayoutDashboard,
  ListChecks,
  LogOut,
  Menu,
  Search,
  Settings,
  Sparkles,
  Trophy,
  UserRound,
  Users,
} from 'lucide-react'
import { useEffect, useState, type ReactNode } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useApi } from '../api/hooks'
import type { Invitation } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import { useI18n } from '../i18n/context'
import { LanguageSwitcher } from './LanguageSwitcher'

interface NavItem { to: string; label: string; icon: ReactNode; end?: boolean; count?: number }

export function Logo() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle cx="12" cy="4" r="2.2" fill="#fff" />
      <circle cx="4.5" cy="9.5" r="2.2" fill="#fff" />
      <circle cx="19.5" cy="9.5" r="2.2" fill="#fff" />
      <circle cx="7.5" cy="19" r="2.2" fill="#fff" />
      <circle cx="16.5" cy="19" r="2.2" fill="#fff" />
      <path d="M12 4 4.5 9.5 7.5 19h9l3-9.5L12 4Z" stroke="#fff" strokeOpacity=".6" strokeWidth="1.4" />
      <circle cx="12" cy="12" r="2.6" fill="#e9a6ff" />
    </svg>
  )
}

export function AppLayout() {
  const { user, signOut } = useAuth()
  const { t } = useI18n()
  const nav = useNavigate()
  const loc = useLocation()
  const [open, setOpen] = useState(false)
  const isCandidate = user?.role === 'candidate'
  const invs = useApi<Invitation[]>(isCandidate ? '/candidate/invitations' : null)
  const newCount = invs.data?.filter((i) => i.status === 'sent').length ?? 0

  useEffect(() => {
    setOpen(false)
    if (isCandidate) void invs.reload()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loc.pathname])

  const candidateNav: NavItem[] = [
    { to: '/candidate', label: t('nav.overview'), icon: <LayoutDashboard size={18} />, end: true },
    { to: '/candidate/profile', label: t('nav.profile'), icon: <UserRound size={18} /> },
    { to: '/candidate/testing', label: t('nav.testing'), icon: <ClipboardCheck size={18} /> },
    { to: '/candidate/fsp', label: t('nav.fsp'), icon: <Trophy size={18} /> },
    { to: '/candidate/invitations', label: t('nav.invitations'), icon: <Inbox size={18} />, count: newCount },
    { to: '/candidate/jobs', label: t('nav.jobs'), icon: <Briefcase size={18} /> },
    { to: '/candidate/tasks', label: t('nav.tasks'), icon: <ListChecks size={18} /> },
    { to: '/candidate/settings', label: t('nav.settings'), icon: <Settings size={18} /> },
  ]
  const employerNav: NavItem[] = [
    { to: '/employer', label: t('nav.overview'), icon: <LayoutDashboard size={18} />, end: true },
    { to: '/employer/requirements', label: t('nav.requirements'), icon: <Sparkles size={18} /> },
    { to: '/employer/candidates', label: t('nav.bank'), icon: <Search size={18} /> },
    { to: '/employer/invitations', label: t('nav.invitations'), icon: <Inbox size={18} /> },
    { to: '/employer/applications', label: t('nav.applications'), icon: <FileText size={18} /> },
    { to: '/employer/tasks', label: t('nav.tasks'), icon: <ListChecks size={18} /> },
    { to: '/employer/company', label: t('nav.company'), icon: <Building2 size={18} /> },
  ]
  const items = isCandidate ? candidateNav : employerNav

  return (
    <div className="app">
      <aside className={`sidebar ${open ? 'open' : ''}`}>
        <NavLink to="/" className="brand">
          <span className="brand-mark"><Logo /></span>
          <span><div className="brand-name">FSP Talent</div><div className="brand-sub">{t('nav.brandSub')}</div></span>
        </NavLink>
        <div className="nav-label">{isCandidate ? t('nav.candidateCabinet') : t('nav.employerCabinet')}</div>
        {items.map((it) => (
          <NavLink key={it.to} to={it.to} end={it.end} className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
            {it.icon}<span>{it.label}</span>{it.count ? <span className="count">{it.count}</span> : null}
          </NavLink>
        ))}
        <div className="sidebar-foot">
          <div className="row"><span className="badge light" style={{ background: 'rgba(255,255,255,.15)', color: '#fff' }}>
            {isCandidate ? <UserRound size={12} /> : <Users size={12} />}{isCandidate ? t('nav.roleCandidate') : t('nav.roleEmployer')}</span>
            <span className="right"><LanguageSwitcher tone="light" /></span></div>
          <div className="who" style={{ marginTop: 8 }}>{user?.display_name}</div>
          <div className="tiny" style={{ opacity: 0.7 }}>{user?.email}</div>
          <button className="btn light sm block" onClick={() => { signOut(); nav('/') }}><LogOut size={14} />{t('nav.signOut')}</button>
        </div>
      </aside>
      <div className="main">
        <div className="topbar">
          <button className="icon-btn" style={{ color: '#fff' }} onClick={() => setOpen(!open)} aria-label={t('nav.menu')}><Menu /></button>
          <span className="brand-name">FSP Talent</span>
          <LanguageSwitcher tone="light" />
        </div>
        <div className="content"><Outlet /></div>
      </div>
    </div>
  )
}
