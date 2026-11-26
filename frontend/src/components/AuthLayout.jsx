import { Briefcase, CheckCircle2 } from 'lucide-react'

const FEATURES = [
  'Role-based candidate and hiring portals',
  'Resume extraction with editable profiles',
  'Transparent matching with human review',
]

function BrandMark({ compact = false }) {
  return (
    <div className={`flex items-center gap-3 ${compact ? '' : 'text-white'}`}>
      <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-600 text-white shadow-lg shadow-brand-900/20">
        <Briefcase size={19} />
      </span>
      <span className="text-xl font-bold tracking-tight">TalentIQ</span>
    </div>
  )
}

export default function AuthLayout({ title, description, children }) {
  return (
    <main className="min-h-screen bg-white lg:grid lg:grid-cols-[1.05fr_0.95fr]">
      <aside className="relative hidden min-h-screen overflow-hidden bg-navy-900 px-12 py-10 text-white lg:flex lg:flex-col lg:justify-between xl:px-16">
        <div className="pointer-events-none absolute -right-36 -top-32 h-96 w-96 rounded-full bg-brand-500/20 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-48 -left-20 h-96 w-96 rounded-full bg-cyan-400/10 blur-3xl" />
        <BrandMark />
        <div className="relative max-w-xl">
          <p className="mb-4 text-xs font-bold uppercase tracking-[0.24em] text-blue-200">Recruitment, in one place</p>
          <h2 className="text-4xl font-bold leading-tight tracking-tight xl:text-5xl">
            Find great people.<br />Make better hires.
          </h2>
          <p className="mt-5 max-w-md text-base leading-7 text-slate-300">
            A clear workspace for candidates, recruiters, and interviewers to move through every hiring step.
          </p>
          <ul className="mt-8 space-y-4">
            {FEATURES.map((feature) => (
              <li key={feature} className="flex items-center gap-3 text-sm text-slate-200">
                <CheckCircle2 size={18} className="shrink-0 text-cyan-300" />
                {feature}
              </li>
            ))}
          </ul>
        </div>
        <p className="relative text-xs text-slate-400">AI-assisted hiring, with people in control.</p>
      </aside>

      <section className="flex min-h-screen flex-col items-center justify-center bg-slate-50 px-5 py-10 sm:px-8">
        <div className="mb-8 lg:hidden"><BrandMark compact /></div>
        <div className="w-full max-w-md">
          <div className="mb-7">
            <p className="mb-2 text-xs font-bold uppercase tracking-[0.18em] text-brand-600">TalentIQ account</p>
            <h1 className="text-3xl font-bold tracking-tight text-navy-900">{title}</h1>
            <p className="mt-2 text-sm leading-6 text-slate-500">{description}</p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-[0_18px_50px_-24px_rgba(15,23,42,0.22)] sm:p-8">
            {children}
          </div>
          <p className="mt-6 text-center text-xs text-slate-400">Secure access to your recruitment workspace</p>
        </div>
      </section>
    </main>
  )
}
