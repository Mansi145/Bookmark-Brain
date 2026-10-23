import { useEffect } from 'react'
import { Link, useLocation } from 'react-router'
import Nebula from '../components/Nebula'
import PublicHeader from '../components/PublicHeader'
import SignInButtons from '../components/SignInButtons'
import SiteIcon from '../components/SiteIcon'
import { useMe } from '../hooks/useMe'

// How it works (design board HowItWorks.dc.html): texture header band, three steps, features,
// a closing call to action on the texture, footer.

const STEPS = [
  { n: '1', tint: 'bg-accent', title: 'Sign in', body: 'Use your Google or GitHub account. No new password to remember.' },
  {
    n: '2',
    tint: 'bg-accent',
    title: 'Connect your browsers',
    body: 'Add the extension to Chrome, Edge, Brave or Firefox and click Connect this browser. Your bookmarks sync on their own.',
  },
  {
    n: '3',
    tint: 'bg-accent',
    title: 'Read, search and ask',
    body: 'Your bookmarks show up as a feed with summaries. Search them, or ask questions across all of them.',
  },
]

const EXTRAS = [
  { tint: 'bg-accent', title: 'Dead link checks', body: 'Spots pages that have gone missing and points you to an archived copy.' },
  { tint: 'bg-accent2', title: 'Reading status', body: 'Mark things as read, and see how long each one takes to read.' },
  { tint: 'bg-accent', title: 'Weekly digest', body: 'A short weekly round-up of things you saved and never got back to.' },
]

export default function HowItWorksPage() {
  const signedIn = Boolean(useMe().data)
  // React Router doesn't scroll to #features on its own.
  const { hash } = useLocation()
  useEffect(() => {
    if (hash) document.getElementById(hash.slice(1))?.scrollIntoView()
  }, [hash])

  return (
    // The marketing pages are designed light-only, so they use fixed colours, not theme tokens:
    // off-white page #ECEAE7, cards #FBFAF8 with #E2DFDA borders (no pure white except logo chips).
    <div className="bg-[#ECEAE7] text-[16px] leading-[1.55] text-[#141516]">
      <section aria-labelledby="how-title" className="relative overflow-hidden text-on-texture">
        <Nebula variant="nude" size="band" />
        <PublicHeader />
        <div className="relative mx-auto max-w-[1200px] px-6 pt-10 pb-16">
          <h1 id="how-title" className="font-serif text-[40px] leading-[1.05] font-bold tracking-[-0.02em] sm:text-[56px]">
            How it works
          </h1>
          <p className="mt-3.5 max-w-[560px] text-[19px] text-on-texture2">
            Sign in, connect your browsers, then read, search and ask across everything you've saved.
          </p>
        </div>
      </section>

      <section aria-label="Steps" className="mx-auto max-w-[1200px] px-6 pt-14 pb-10">
        <ol className="grid list-none grid-cols-[repeat(auto-fit,minmax(260px,1fr))] gap-5 p-0">
          {STEPS.map((s) => (
            <li key={s.n} className="rounded-2xl border border-[#E2DFDA] bg-[#FBFAF8] p-6">
              <span aria-hidden className={`grid size-9 place-items-center rounded-full font-semibold text-on-accent ${s.tint}`}>
                {s.n}
              </span>
              <h2 className="mt-4 text-lg font-semibold">{s.title}</h2>
              <p className="mt-1.5 text-[#2F3134]">{s.body}</p>
            </li>
          ))}
        </ol>
      </section>

      <section id="features" aria-labelledby="features-title" className="mx-auto max-w-[1200px] px-6 pt-14 pb-10">
        <h2 id="features-title" className="font-serif text-[32px] font-bold tracking-[-0.015em] sm:text-[40px]">
          What it does with your bookmarks
        </h2>

        <Feature title="Summaries you can skim" body="Every saved page gets a short summary and its key points, so you remember why you saved it before you open it.">
          <div className="mb-1.5 flex items-center gap-2 text-[13px] text-[#2F3134]">
            <SiteIcon iconUrl="/sample-icons/webdev.png" site="web.dev" light />
            web.dev · 5 min read
          </div>
          <div className="font-serif text-xl font-bold">Largest Contentful Paint (LCP)</div>
          <ul className="mt-3 flex flex-col gap-1.5 pl-5 text-[#2F3134]">
            <li>Measures when the largest image or text block finishes rendering.</li>
            <li>A good score is 2.5 seconds or less.</li>
            <li>Judged at the 75th percentile of page loads.</li>
          </ul>
        </Feature>

        <Feature
          reverse
          title="Search by what it was about"
          body="Type what you remember, not the exact title. Keyword and meaning-based search work together to find it."
        >
          <div className="flex flex-col gap-3">
            <div className="flex h-11 items-center rounded-[10px] border border-[#E2DFDA] bg-[#F5F4F2] px-3.5 text-[#2F3134]">
              that article about making pages load faster
            </div>
            <div className="rounded-xl bg-accent px-3.5 py-3 text-on-accent">
              <div className="font-semibold">Largest Contentful Paint (LCP)</div>
              <div className="mt-1 flex items-center gap-2 text-[13px] text-on-accent2">
                <SiteIcon iconUrl="/sample-icons/webdev.png" site="web.dev" light />
                web.dev · matched by meaning
              </div>
            </div>
            <div className="rounded-xl bg-accent2 px-3.5 py-3 text-on-accent">
              <div className="font-semibold">Using the Fetch API</div>
              <div className="mt-1 flex items-center gap-2 text-[13px] text-on-accent2">
                <SiteIcon iconUrl="/sample-icons/mdn.png" site="developer.mozilla.org" light />
                developer.mozilla.org · matched "pages"
              </div>
            </div>
          </div>
        </Feature>

        <Feature
          title="Ask your bookmarks"
          body="Ask a question and get an answer drawn only from the pages you saved, with links to the sources it used."
        >
          <div className="flex flex-col gap-3">
            <div className="max-w-[80%] self-end rounded-[14px_14px_4px_14px] bg-[#141516] px-3.5 py-2.5 text-white">
              Which Postgres index should I use for full-text search?
            </div>
            <div className="max-w-[88%] self-start rounded-[14px_14px_14px_4px] bg-[#F5F4F2] px-3.5 py-3">
              A GIN index. Your saved docs say GIN suits values with many parts, like full-text search vectors and
              arrays.
              <div className="mt-2 flex flex-wrap gap-1.5">
                <span className="inline-flex items-center gap-1.5 rounded-md bg-accent py-[3px] pr-2 pl-1 text-xs text-on-accent">
                  <SiteIcon iconUrl="/sample-icons/postgresql.ico" site="postgresql.org" small light />
                  Index Types · postgresql.org
                </span>
              </div>
            </div>
          </div>
        </Feature>

        <ul className="mt-16 grid list-none grid-cols-[repeat(auto-fit,minmax(240px,1fr))] gap-4 p-0">
          {EXTRAS.map((x) => (
            <li key={x.title} className={`rounded-2xl p-5 text-on-accent ${x.tint}`}>
              <div className="font-semibold">{x.title}</div>
              <div className="mt-1 text-[15px] text-on-accent2">{x.body}</div>
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="cta-title" className="relative mx-6 mt-[72px] overflow-hidden rounded-[28px] text-on-texture">
        <Nebula variant="nude" size="band" />
        <div className="relative mx-auto max-w-[760px] px-6 py-[72px] text-center">
          <h2 id="cta-title" className="font-serif text-[32px] leading-[1.1] font-bold tracking-[-0.015em] sm:text-[44px]">
            Your saved links are waiting.
          </h2>
          <p className="mt-3 text-lg text-on-texture2">
            Sign in, connect a browser, and your bookmarks turn into a feed in about a minute.
          </p>
          <div className="mt-7 flex justify-center">
            {signedIn ? (
              <Link to="/" className="rounded-xl bg-white px-6 py-3.5 font-semibold text-[#141516] no-underline">
                Open your feed
              </Link>
            ) : (
              <SignInButtons />
            )}
          </div>
        </div>
      </section>

      <footer className="mx-auto flex max-w-[1200px] flex-wrap justify-between gap-3 px-6 pt-10 pb-12 text-sm text-[#2F3134]">
        <span>Bookmark Brain · a personal project</span>
        <span>We only read your bookmarks' titles, links and folders, plus the public pages they point to.</span>
        <a href="https://github.com/Mansi145/Bookmark-Brain">Source code</a>
      </footer>
    </div>
  )
}

function Feature(props: { title: string; body: string; reverse?: boolean; children: React.ReactNode }) {
  return (
    <div className={`mt-14 flex flex-wrap items-center gap-10 ${props.reverse ? 'flex-wrap-reverse flex-row-reverse' : ''}`}>
      <div className="flex-[1_1_360px]">
        <h3 className="font-serif text-[28px] font-bold">{props.title}</h3>
        <p className="mt-2.5 max-w-[460px] text-[#2F3134]">{props.body}</p>
      </div>
      <div aria-hidden className="flex-[1_1_420px] rounded-[18px] border border-[#E2DFDA] bg-[#FBFAF8] p-6">
        {props.children}
      </div>
    </div>
  )
}
