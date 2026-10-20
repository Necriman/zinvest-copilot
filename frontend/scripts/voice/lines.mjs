// The bear's recorded lines: which i18n strings get a voice clip, in which
// language, and under which file. Prints JSON; pack.mjs uses the same list.
//
//   node scripts/voice/lines.mjs [ru,en]
import { pathToFileURL } from 'node:url'

import { mascotMessages } from '../../src/i18n/mascot.js'
import { workspaceMessages } from '../../src/i18n/workspace.js'
import { normalizeSpeech, speechKey } from '../../src/voice/text.js'

export const LINE_KEYS = [
  'voice.clear',
  'mascot.praise1', 'mascot.praise2', 'mascot.praise3', 'mascot.praise4', 'mascot.praise5',
  'mascot.encourage1', 'mascot.encourage2', 'mascot.encourage3', 'mascot.encourage4',
  'bear.congratulations',
  'checkpoint.label',
  'hero.secret',
  'voice.testPassed',
  'voice.testFailed',
]

const INDEX = { en: 0, ru: 1, uz: 2 }

export function lines(langs = ['ru', 'en']) {
  const out = []
  for (const lang of langs) {
    const messages = { ...workspaceMessages(INDEX[lang]), ...mascotMessages(INDEX[lang]) }
    for (const path of LINE_KEYS) {
      const [section, key] = path.split('.')
      const text = messages[section]?.[key]
      if (!text) throw new Error(`missing ${lang} ${path}`)
      const clean = normalizeSpeech(text)
      out.push({ lang, path, text: clean, key: speechKey(clean), file: `${lang}/${path.replace('.', '-')}.mp3` })
    }
  }
  return out
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  console.log(JSON.stringify(lines((process.argv[2] || 'ru,en').split(',')), null, 1))
}
