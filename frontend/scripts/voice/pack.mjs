// Turns recorded lines into the voice pack the narrator plays:
// public/voice/<lang>/<line>.mp3 plus public/voice/manifest.json, which maps
// the hash of each exact text to its file (see src/voice/narrator.js).
//
//   node scripts/voice/pack.mjs <jobs.json>
//
// jobs.json maps "<lang>/<i18n key>" to the URL (or local path) of a recording,
// e.g. { "ru/mascot.praise1": "https://.../clip.mp3" }. Each clip is trimmed of
// silence, levelled to the same loudness and saved as mono 64 kbit/s MP3.
// Needs ffmpeg and ffprobe on the PATH (or FFMPEG / FFPROBE set).
import { execFileSync } from 'node:child_process'
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

import { lines } from './lines.mjs'

const FFMPEG = process.env.FFMPEG || 'ffmpeg'
const FFPROBE = process.env.FFPROBE || 'ffprobe'
const here = dirname(fileURLToPath(import.meta.url))
const out = resolve(here, '../../public/voice')
const jobs = JSON.parse(readFileSync(process.argv[2], 'utf8'))

const manifestPath = join(out, 'manifest.json')
const manifest = existsSync(manifestPath) ? JSON.parse(readFileSync(manifestPath, 'utf8')) : { clips: {} }
const wanted = lines([...new Set(Object.keys(jobs).map((k) => k.split('/')[0]))])

for (const line of wanted) {
  const source = jobs[`${line.lang}/${line.path}`]
  if (!source) { console.warn('no recording for', line.lang, line.path); continue }
  let input = source
  if (/^https?:/.test(source)) {
    const res = await fetch(source)
    if (!res.ok) throw new Error(`download failed ${res.status} ${source}`)
    input = join(tmpdir(), `zinvest-voice-${line.key}.src`)
    writeFileSync(input, Buffer.from(await res.arrayBuffer()))
  }
  const target = join(out, line.file)
  mkdirSync(dirname(target), { recursive: true })
  execFileSync(FFMPEG, ['-y', '-loglevel', 'error', '-i', input,
    '-af', 'silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.05,areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.08,areverse,loudnorm=I=-16:TP=-1.5:LRA=11',
    '-ac', '1', '-ar', '44100', '-codec:a', 'libmp3lame', '-b:a', '64k', target])
  const seconds = Number(execFileSync(FFPROBE, ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', target]).toString().trim())
  manifest.clips[line.key] = { src: `/voice/${line.file}`, lang: line.lang, line: line.path, d: Math.round(seconds * 100) / 100 }
  console.log(line.lang, line.path.padEnd(22), seconds.toFixed(2) + 's')
}

manifest.v = 1
manifest.voices = { ...manifest.voices, ru: 'Alexey (ElevenLabs via Higgsfield)', en: 'Julian (ElevenLabs via Higgsfield)' }
writeFileSync(manifestPath, JSON.stringify(manifest, null, 1) + '\n')
console.log('manifest:', Object.keys(manifest.clips).length, 'clips')
