import type { User } from '../api/types'

/** The account's picture from Google when there is one, else the initial of the name. */
export default function Avatar({ user }: { user: User }) {
  if (user.avatar_url) return <img src={user.avatar_url} alt="" referrerPolicy="no-referrer" className="size-full" />
  return <>{(user.name ?? user.email).charAt(0).toUpperCase()}</>
}
