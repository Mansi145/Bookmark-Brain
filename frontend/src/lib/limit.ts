/**
 * Opens the Limit reached dialog from anywhere, without passing callbacks around: the layout
 * listens. Two reasons (design board LimitDialog):
 * - 'limit': an AI action (Summarise, Re-summarise, Ask) was refused because today's allowance
 *   is used up (the server answered 429);
 * - 'busy': every free AI service failed (Ask's "error" event). That doesn't use up the limit.
 */
export type LimitReason = 'limit' | 'busy'

export const limitHit = new EventTarget()

export function openLimitDialog(reason: LimitReason = 'limit') {
  limitHit.dispatchEvent(new CustomEvent<LimitReason>('hit', { detail: reason }))
}
