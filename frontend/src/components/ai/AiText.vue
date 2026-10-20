<script setup>
/**
 * An AI answer, formatted.
 *
 * The model writes light Markdown — headings, bold, lists, a quoted formula —
 * and shown raw it read as "### Why" and "**Runway**" in the middle of an
 * explanation. This renders that small subset as structure. It never builds
 * HTML: every piece of text goes through ordinary interpolation, so nothing
 * the model says can become markup on the page. Anything outside the subset
 * simply stays text.
 */
import { computed } from 'vue'

const props = defineProps({ text: { type: String, default: '' } })

// "**bold** and *aside*" -> [{ text: 'bold', bold: true }, { text: ' and ' }, { text: 'aside', em: true }]
function inline(line) {
  return line
    .split(/(\*\*[^*]+\*\*|\*[^*\s][^*]*\*)/g)
    .filter(Boolean)
    .map((part) => {
      if (part.startsWith('**') && part.endsWith('**') && part.length > 4) return { text: part.slice(2, -2), bold: true }
      if (part.startsWith('*') && part.endsWith('*') && part.length > 2) return { text: part.slice(1, -1), em: true }
      return { text: part }
    })
}

const blocks = computed(() => {
  const out = []
  let list = null
  const flush = () => {
    if (list) out.push(list)
    list = null
  }
  for (const raw of (props.text || '').split('\n')) {
    const line = raw.trimEnd()
    let m
    if (!line.trim()) {
      flush()
    } else if ((m = line.match(/^\s*#{1,6}\s+(.*)$/))) {
      flush()
      out.push({ type: 'h', parts: inline(m[1]) })
    } else if (/^\s*(-{3,}|\*{3,}|_{3,})\s*$/.test(line)) {
      flush()
      out.push({ type: 'hr' })
    } else if ((m = line.match(/^\s*>\s?(.*)$/))) {
      flush()
      out.push({ type: 'quote', parts: inline(m[1]) })
    } else if ((m = line.match(/^\s*(?:[-*•])\s+(.*)$/))) {
      if (list?.type !== 'ul') {
        flush()
        list = { type: 'ul', items: [] }
      }
      list.items.push(inline(m[1]))
    } else if ((m = line.match(/^\s*(\d+)[.)]\s+(.*)$/))) {
      if (list?.type !== 'ol') {
        flush()
        list = { type: 'ol', start: Number(m[1]), items: [] }
      }
      list.items.push(inline(m[2]))
    } else {
      flush()
      out.push({ type: 'p', parts: inline(line) })
    }
  }
  flush()
  return out
})
</script>

<template>
  <div class="ai-text">
    <template v-for="(block, i) in blocks" :key="i">
      <p v-if="block.type === 'h'" class="ai-text__h">
        <template v-for="(part, j) in block.parts" :key="j">{{ part.text }}</template>
      </p>
      <hr v-else-if="block.type === 'hr'" class="ai-text__hr" />
      <p v-else-if="block.type === 'quote'" class="ai-text__quote">
        <template v-for="(part, j) in block.parts" :key="j">
          <strong v-if="part.bold">{{ part.text }}</strong>
          <em v-else-if="part.em">{{ part.text }}</em>
          <template v-else>{{ part.text }}</template>
        </template>
      </p>
      <ul v-else-if="block.type === 'ul'" class="ai-text__ul">
        <li v-for="(item, k) in block.items" :key="k">
          <template v-for="(part, j) in item" :key="j">
            <strong v-if="part.bold">{{ part.text }}</strong>
            <em v-else-if="part.em">{{ part.text }}</em>
            <template v-else>{{ part.text }}</template>
          </template>
        </li>
      </ul>
      <ol v-else-if="block.type === 'ol'" class="ai-text__ol" :start="block.start">
        <li v-for="(item, k) in block.items" :key="k">
          <template v-for="(part, j) in item" :key="j">
            <strong v-if="part.bold">{{ part.text }}</strong>
            <em v-else-if="part.em">{{ part.text }}</em>
            <template v-else>{{ part.text }}</template>
          </template>
        </li>
      </ol>
      <p v-else class="ai-text__p">
        <template v-for="(part, j) in block.parts" :key="j">
          <strong v-if="part.bold">{{ part.text }}</strong>
          <em v-else-if="part.em">{{ part.text }}</em>
          <template v-else>{{ part.text }}</template>
        </template>
      </p>
    </template>
  </div>
</template>

<style scoped>
.ai-text > * + * {
  margin-top: 0.6rem;
}
.ai-text__h {
  margin-top: 0.95rem;
  font-weight: 700;
  color: var(--color-ink);
}
.ai-text > .ai-text__h:first-child {
  margin-top: 0;
}
.ai-text__p,
.ai-text li {
  line-height: 1.6;
}
.ai-text strong {
  font-weight: 700;
  color: var(--color-ink);
}
.ai-text em {
  font-style: italic;
  color: var(--color-ink-muted);
}
/* The quoted line is usually the formula — give it the room one deserves. */
.ai-text__quote {
  border-left: 3px solid color-mix(in oklab, var(--brand-500) 55%, transparent);
  border-radius: 0.25rem;
  background: color-mix(in oklab, var(--brand-500) 7%, transparent);
  padding: 0.45rem 0.75rem;
}
.ai-text__ul,
.ai-text__ol {
  padding-left: 1.15rem;
}
.ai-text__ul {
  list-style: disc;
}
.ai-text__ol {
  list-style: decimal;
}
.ai-text li + li {
  margin-top: 0.3rem;
}
.ai-text li::marker {
  color: var(--color-ink-muted);
}
.ai-text__hr {
  border: 0;
  border-top: 1px solid var(--color-hairline);
}
</style>
