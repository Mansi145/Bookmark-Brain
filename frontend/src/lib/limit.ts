/**
 * Fires when an AI action (Summarise, Re-summarise, later Ask) is refused because today's
 * allowance is used up (the server answers 429). The layout listens and opens the Limit
 * reached dialog, so any button anywhere can trigger it without passing callbacks around.
 */
export const limitHit = new EventTarget()

export function openLimitDialog() {
  limitHit.dispatchEvent(new Event('hit'))
}
