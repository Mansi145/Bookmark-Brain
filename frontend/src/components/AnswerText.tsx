import type { ReactNode } from 'react'

// An Ask answer (design board Ask): the model writes plain text with a little Markdown, so
// paragraphs, "- " / "* " / "1. " lists, **bold** and `code` are shown as such, and each
// [bookmark:ID] becomes a numbered citation chip on `accent` that opens the bookmark's detail
// panel. Everything is built as React elements, never HTML from the model, so a page's text can't
// inject markup.
//
// While the answer is still being written, `numbers` is empty: citations arrive at the end, so
// they're left out until then (with any half-written one at the very end), and a blinking caret
// follows the text.

const LIST_ITEM = /^\s*(?:[-*•]|\d+[.)])\s+(.*)$/
const INLINE = /(\*\*[^*]+\*\*|`[^`]+`|\[bookmark:\s*\d+\s*\])/g
const CITATION = /^\[bookmark:\s*(\d+)\s*\]$/

export default function AnswerText(props: {
  text: string
  numbers: Map<number, number> // bookmark id -> its source number (empty while writing)
  onOpen: (bookmarkId: number) => void
  writing?: boolean
}) {
  const text = props.writing ? props.text.replace(/\[[a-z]*:?\s*\d*$/, '') : props.text
  const blocks = toBlocks(text)
  const inline = (line: string) => renderInline(line, props.numbers, props.onOpen)
  const caret = props.writing && (
    <span
      aria-hidden
      className="ml-0.5 inline-block h-[1.05em] w-0.5 animate-blink bg-ink align-[-0.15em] motion-reduce:animate-none"
    />
  )

  return (
    <>
      {blocks.map((block, i) => {
        const last = i === blocks.length - 1
        const gap = i > 0 ? 'mt-2.5' : ''
        if (block.kind === 'p') {
          return (
            <p key={i} className={`m-0 ${gap}`}>
              {inline(block.lines.join(' '))}
              {last && caret}
            </p>
          )
        }
        const List = block.kind === 'ol' ? 'ol' : 'ul'
        return (
          <List
            key={i}
            className={`m-0 flex flex-col gap-1.5 pl-5 ${block.kind === 'ol' ? 'list-decimal' : 'list-disc'} ${gap}`}
          >
            {block.lines.map((line, j) => (
              <li key={j}>
                {inline(line)}
                {last && j === block.lines.length - 1 && caret}
              </li>
            ))}
          </List>
        )
      })}
      {blocks.length === 0 && caret}
    </>
  )
}

type Block = { kind: 'p' | 'ul' | 'ol'; lines: string[] }

/** Lines into paragraphs and lists: a blank line ends a block, list items gather into a list. */
function toBlocks(text: string): Block[] {
  const blocks: Block[] = []
  for (const line of text.split('\n')) {
    if (!line.trim()) {
      blocks.push({ kind: 'p', lines: [] }) // a break; empty ones are dropped below
      continue
    }
    const item = line.match(LIST_ITEM)
    const kind = item ? (/^\s*\d/.test(line) ? 'ol' : 'ul') : 'p'
    const current = blocks.at(-1)
    if (current && current.kind === kind && current.lines.length) current.lines.push(item ? item[1] : line.trim())
    else blocks.push({ kind, lines: [item ? item[1] : line.trim()] })
  }
  return blocks.filter((block) => block.lines.length)
}

function renderInline(line: string, numbers: Map<number, number>, onOpen: (id: number) => void): ReactNode[] {
  return line.split(INLINE).map((part, i) => {
    const citation = part.match(CITATION)
    if (citation) {
      const id = Number(citation[1])
      const n = numbers.get(id)
      return n ? <Chip key={i} n={n} onClick={() => onOpen(id)} /> : null
    }
    if (part.startsWith('**') && part.endsWith('**') && part.length > 4) {
      return <strong key={i}>{part.slice(2, -2)}</strong>
    }
    if (part.startsWith('`') && part.endsWith('`') && part.length > 2) {
      return (
        <code key={i} className="font-mono text-[0.92em]">
          {part.slice(1, -1)}
        </code>
      )
    }
    return part
  })
}

/** A numbered citation: opens that source's detail panel. */
export function Chip({ n, onClick }: { n: number; onClick: () => void }) {
  return (
    <button
      type="button"
      aria-label={`Source ${n}: open its details`}
      onClick={onClick}
      className="mx-0.5 inline-grid h-[18px] min-w-[18px] cursor-pointer place-items-center rounded-[5px] border-0 bg-accent px-1 align-[2px] text-[11px] leading-none font-semibold text-on-accent"
    >
      {n}
    </button>
  )
}
