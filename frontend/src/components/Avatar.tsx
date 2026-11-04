import { useState } from 'react'
import type { User } from '../api/types'

/** The account's picture from Google when there is one, else (or if it won't load) the initial. */
export default function Avatar({ user }: { user: User }) {
  const [failed, setFailed] = useState(false)
  if (user.avatar_url && !failed) {
    return (
      <img
        src={user.avatar_url}
        alt=""
        referrerPolicy="no-referrer"
        onError={() => setFailed(true)}
        className="size-full"
      />
    )
  }
  return <>{(user.name ?? user.email).charAt(0).toUpperCase()}</>
}
