import { Fragment } from 'react'

// Search results come back with each matched word between these two control characters (see
// SearchResult in api/types.ts). Splitting on them, rather than rendering HTML from a web page,
// means a page's text can never inject markup.
const START = '\u0002'
const END = '\u0003'

/**
 * `text`, with the words `marked` marks as matches highlighted (board FeedSearch: accent with
 * white text). The marks are used only when they belong to the text on screen: a summary made
 * after the search shows unmarked.
 */
export default function Marked({ text, marked }: { text: string; marked?: string | null }) {
  if (!marked || marked.replaceAll(START, '').replaceAll(END, '') !== text) return text
  return marked.split(START).map((part, i) => {
    if (i === 0) return part
    const end = part.indexOf(END)
    const word = end === -1 ? part : part.slice(0, end)
    const rest = end === -1 ? '' : part.slice(end + 1)
    return (
      <Fragment key={i}>
        <mark className="rounded-[3px] bg-accent px-[3px] text-on-accent">{word}</mark>
        {rest}
      </Fragment>
    )
  })
}
