import { defineConfig } from 'wxt'

// https://wxt.dev/api/config.html
export default defineConfig({
  manifest: ({ browser }) => ({
    name: 'Bookmark Brain',
    description: 'Syncs your bookmarks to Bookmark Brain for summaries and search.',
    // bookmarks: read the bookmark tree and listen for changes
    // storage:   remember the API URL, token and sync status
    // alarms:    wake the background worker for periodic/retry syncs
    permissions: ['bookmarks', 'storage', 'alarms'],
    // Lets the extension call the API directly (no CORS needed from an extension
    // with host permission). Add your own domain here if you deploy elsewhere.
    host_permissions: ['http://localhost:8000/*', 'https://*.onrender.com/*'],
    // Firefox requires an add-on id; Chrome would warn about the unknown key.
    ...(browser === 'firefox' && {
      browser_specific_settings: { gecko: { id: 'bookmark-brain@example.com' } },
    }),
  }),
})
