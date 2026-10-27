// Renders the logo SVGs into the PNG sizes browsers want for extension icons.
// WXT picks up public/icon/<size>.png automatically (toolbar, extensions page, store).
// Run after changing the logo: npm run icons
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { Resvg } from '@resvg/resvg-js'

// The small version under 64 px, where the full version's thin rules disappear; the full one at
// 128 px (extensions page, store). Design board LogoFinal / the ui-design skill.
const sizes = { 16: 'logo-small.svg', 32: 'logo-small.svg', 48: 'logo-small.svg', 128: 'logo.svg' }

mkdirSync('public/icon', { recursive: true })
for (const [size, file] of Object.entries(sizes)) {
  const svg = readFileSync(`assets/icon/${file}`, 'utf8')
  const png = new Resvg(svg, { fitTo: { mode: 'width', value: Number(size) } }).render().asPng()
  writeFileSync(`public/icon/${size}.png`, png)
  console.log(`public/icon/${size}.png  (${file})`)
}
