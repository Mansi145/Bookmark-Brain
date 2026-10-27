import SiteIcon from './SiteIcon'

// A sample front page for the public pages (design boards Login and HowItWorks): band rule,
// "Today's edition" masthead, a lead with its summary beside two briefs, one with Summarise.
// Image-free apart from the site logos, which are bundled in public/sample-icons so these
// pages don't load anything from those sites. Light colours only: the public pages are
// designed light-only. The caller draws the card around it.

// "Tue 27 Oct": today (when the page loaded), so the sample never looks out of date.
const TODAY = new Date().toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' })

export default function MiniFrontPage() {
  return (
    <div className="text-[#141516]">
      <div className="bg-band h-1 rounded-sm" />
      <div className="flex items-baseline justify-between gap-2.5 border-b border-[#141516] pt-[9px] pb-[7px]">
        <span className="text-xs text-[#2F3134]">{TODAY}</span>
        <span className="font-serif text-[22px] font-bold tracking-[-0.01em]">Today's edition</span>
        <span className="text-xs text-[#2F3134]">6 new</span>
      </div>
      <div className="mt-[3px] h-px bg-[#141516]" />

      <div className="mt-3.5 grid grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)]">
        <div className="flex flex-col gap-1.5 border-r border-[#E2DFDA] pr-3.5">
          <Source icon="/sample-icons/langchain.png" site="docs.langchain.com" detail="8 min read" />
          <span className="text-[11px] font-semibold tracking-[0.08em] text-[#2F3134] uppercase">Reading / AI</span>
          <span className="font-serif text-[22px] leading-[1.1] font-bold">LangGraph: Quickstart</span>
          <span className="line-clamp-4 text-[13.5px] leading-[1.5] text-[#2F3134]">
            A step-by-step build of a small agent: define the graph's state, add nodes for the model and its tools, then
            stream each step as it runs.
          </span>
        </div>
        <div className="flex flex-col gap-1.5 pl-3.5">
          <Source icon="/sample-icons/postgresql.ico" site="postgresql.org" detail="6 min" />
          <span className="font-serif text-[15px] leading-[1.3] font-bold">Index Types</span>
          <span className="my-1.5 h-px bg-[#E2DFDA]" />
          <Source icon="/sample-icons/webdev.png" site="web.dev" detail="5 min" />
          <span className="font-serif text-[15px] leading-[1.3] font-bold">Largest Contentful Paint (LCP)</span>
          <span className="flex h-[30px] items-center gap-1.5 self-start rounded-lg border border-[#E2DFDA] px-2.5 text-[13px] font-medium">
            <svg
              width="13"
              height="13"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
            >
              <path d="M4 6h16" />
              <path d="M4 12h12" />
              <path d="M4 18h8" />
            </svg>
            Summarise
          </span>
        </div>
      </div>
    </div>
  )
}

function Source(props: { icon: string; site: string; detail: string }) {
  return (
    <span className="flex min-w-0 items-center gap-1.5 text-xs text-[#2F3134]">
      <SiteIcon iconUrl={props.icon} site={props.site} brief light />
      <span className="truncate">
        {props.site} · {props.detail}
      </span>
    </span>
  )
}
