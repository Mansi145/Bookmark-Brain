import { Link } from 'react-router'
import Logo from './Logo'
import Nebula from './Nebula'

// A full-page state shown instead of the app (design boards ConnectStates and ErrorStates): the
// dark Nude texture, the logo, and one centred card with an icon, a title, a line and one action.

export default function StatePage(props: { icon: React.ReactNode; title: string; children: React.ReactNode }) {
  return (
    <div className="relative flex min-h-screen flex-col overflow-hidden text-on-texture">
      <Nebula variant="nude" size="hero" />
      <header className="relative mx-auto w-full max-w-[1240px] px-6 py-6">
        <Link to="/" className="inline-flex items-center gap-2.5 text-on-texture no-underline">
          <Logo size={34} small />
          <span className="font-serif text-xl font-bold">Bookmark Brain</span>
        </Link>
      </header>
      <main className="relative flex flex-1 items-center justify-center px-6 pb-24">
        <div
          role="status"
          className="flex w-full max-w-[480px] flex-col gap-3 rounded-2xl bg-surface p-7 text-ink shadow-[0_24px_60px_rgba(0,0,0,0.3)]"
        >
          <span aria-hidden className="grid size-12 place-items-center rounded-full bg-accent text-on-accent">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              {props.icon}
            </svg>
          </span>
          <h1 className="mt-1 font-serif text-2xl leading-[1.2] font-bold">{props.title}</h1>
          {props.children}
        </div>
      </main>
    </div>
  )
}

/** One line of explanation under the title. */
export function StateText({ children }: { children: React.ReactNode }) {
  return <p className="text-ink2">{children}</p>
}

/** A progress bar with no known end. */
export function SlidingBar() {
  return (
    <span aria-hidden className="block h-2 overflow-hidden rounded-full bg-skeleton">
      <span className="bg-band block h-full w-[45%] animate-slide rounded-full motion-reduce:animate-none" />
    </span>
  )
}
