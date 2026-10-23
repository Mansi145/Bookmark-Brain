import { Link, NavLink } from 'react-router'
import { useMe } from '../hooks/useMe'
import Logo from './Logo'

// Top bar of the signed-out pages. Sits on the nebula texture, so text is white.

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-lg px-3.5 py-2.5 text-on-texture no-underline ${isActive ? 'bg-white/15 font-semibold' : ''}`

export default function PublicHeader() {
  // How it works is also reachable while signed in (from the app's top bar).
  const signedIn = Boolean(useMe().data)
  return (
    <header className="relative mx-auto flex w-full max-w-[1200px] flex-wrap items-center gap-x-6 gap-y-3 px-6 py-5">
      <Link to="/" className="flex items-center gap-2.5 no-underline">
        <Logo size={34} small />
        <span className="font-serif text-xl font-bold text-on-texture">Bookmark Brain</span>
      </Link>
      <nav aria-label="Main" className="ml-auto flex flex-wrap items-center gap-1">
        <NavLink to="/how-it-works" end className={linkClass}>
          How it works
        </NavLink>
        <Link to="/how-it-works#features" className="rounded-lg px-3.5 py-2.5 text-on-texture no-underline">
          Features
        </Link>
        <Link
          to={signedIn ? '/' : '/#signin'}
          className="ml-2 rounded-[10px] border border-[#8E918F] bg-[#141516] px-[18px] py-2.5 font-medium text-white no-underline"
        >
          {signedIn ? 'Open your feed' : 'Sign in'}
        </Link>
      </nav>
    </header>
  )
}
