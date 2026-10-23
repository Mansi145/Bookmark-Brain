import { Link } from 'react-router'
import Logo from '../components/Logo'
import Nebula from '../components/Nebula'
import PublicHeader from '../components/PublicHeader'
import SignInButtons from '../components/SignInButtons'
import SiteIcon from '../components/SiteIcon'

// Sign-up / landing page (design board Login.dc.html): one screen on the dark Nude texture.
// Shown for any URL while signed out, so a deep link like /connect?nonce=… continues after
// signing in.

export default function LoginPage() {
  return (
    <div className="relative flex min-h-screen flex-col overflow-hidden text-[16px] leading-[1.55] text-on-texture">
      <Nebula variant="nude" size="hero" />
      <PublicHeader />

      <main className="relative mx-auto flex w-full max-w-[1200px] flex-1 flex-wrap items-center gap-14 px-6 pt-12 pb-[72px]">
        <div className="min-w-0 flex-[999_1_480px]">
          <div className="flex items-center gap-5">
            <Logo size={150} />
            <span className="font-serif text-[40px] leading-none font-bold tracking-[-0.01em]">
              Bookmark
              <br />
              Brain
            </span>
          </div>

          <h1 className="mt-9 max-w-[620px] font-serif text-[44px] leading-[1.04] font-bold tracking-[-0.02em] sm:text-[64px]">
            Saved it? Now actually use it.
          </h1>
          <p className="mt-5 max-w-[540px] text-[19px] text-on-texture2">
            Bookmark Brain pulls the links you've saved in every browser into one feed, summarises each one, and lets
            you search and ask questions across all of them.
          </p>

          <div id="signin" className="mt-8">
            <SignInButtons />
          </div>
          <p className="mt-3.5 text-sm text-on-texture2">Free · Works with Chrome, Edge, Brave and Firefox</p>

          <Link
            to="/how-it-works"
            className="mt-7 inline-flex h-12 items-center gap-2.5 rounded-full border border-white/50 bg-white/[0.08] pr-[18px] pl-5 font-medium text-on-texture no-underline"
          >
            See how it works
            <svg aria-hidden width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M5 12h14" />
              <path d="m13 6 6 6-6 6" />
            </svg>
          </Link>
        </div>

        <ProductPreview />
      </main>

      <footer className="relative mx-auto flex w-full max-w-[1200px] flex-wrap justify-between gap-3 border-t border-white/[0.14] px-6 pt-6 pb-8 text-sm text-on-texture2">
        <span>Bookmark Brain · a personal project</span>
        <span>We only read your bookmarks' titles, links and folders, plus the public pages they point to.</span>
        <a href="https://github.com/Mansi145/Bookmark-Brain" className="text-on-texture">
          Source code
        </a>
      </footer>
    </div>
  )
}

/**
 * A mini version of the real feed: a "Today" band, one summarised row and one with the Summarise
 * button. Image-free apart from the site logos, which are bundled in public/sample-icons so the
 * landing page doesn't load anything from those sites.
 */
function ProductPreview() {
  return (
    <div aria-hidden className="relative max-w-[460px] flex-[1_1_360px] text-[#141516]">
      <div className="absolute inset-[24px_-16px_-16px_24px] rounded-[18px] bg-white/10" />
      <div className="relative overflow-hidden rounded-[18px] bg-[#FBFAF8] shadow-[0_28px_70px_rgba(0,0,0,0.35)]">
        <div className="bg-band flex items-baseline justify-between px-5 py-3 text-on-accent">
          <span className="font-serif text-lg font-bold">Today</span>
          <span className="text-[13px] text-on-accent2">2 bookmarks</span>
        </div>
        <PreviewRow icon="/sample-icons/postgresql.ico" meta="postgresql.org · Reading · 2d ago" title="Index Types" minutes={6}>
          <p className="line-clamp-2 text-sm text-[#2F3134]">
            B-tree is the default and covers equality and range queries; GIN suits arrays and full-text search.
          </p>
        </PreviewRow>
        <PreviewRow
          icon="/sample-icons/langchain.png"
          meta="docs.langchain.com · Reading/AI · just now"
          title="LangGraph: Quickstart"
          minutes={8}
          divided
        >
          <span className="mt-0.5 flex h-9 items-center gap-[7px] self-start rounded-lg border border-[#E2DFDA] px-3 text-sm font-medium">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M4 6h16" />
              <path d="M4 12h12" />
              <path d="M4 18h8" />
            </svg>
            Summarise
          </span>
        </PreviewRow>
      </div>
    </div>
  )
}

function PreviewRow(props: {
  icon: string
  meta: string
  title: string
  minutes: number
  divided?: boolean
  children: React.ReactNode
}) {
  return (
    <div className={`flex gap-4 px-5 ${props.divided ? 'border-t border-[#E2DFDA] pt-4 pb-5' : 'py-4'}`}>
      <div className="flex min-w-0 flex-1 flex-col gap-1.5">
        <div className="flex items-center gap-2 text-[13px] text-[#2F3134]">
          <SiteIcon iconUrl={props.icon} site={props.meta} light />
          {props.meta}
        </div>
        <div className="font-serif text-[21px] leading-[1.25] font-bold">{props.title}</div>
        {props.children}
      </div>
      <span className="flex-none text-[13px] whitespace-nowrap text-[#2F3134]">{props.minutes} min read</span>
    </div>
  )
}
