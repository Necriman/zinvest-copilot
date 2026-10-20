// Blockquote accent color. StarterKit's blockquote is a plain `<blockquote>`;
// this adds a `color` global attribute to it, rendered as a CSS var
// (`--quote-color`) + a `data-quote-color` (for round-tripping). The stylesheet
// reads the var to paint the left rule and a soft background tint, so a quote can
// be blue / green / amber / red etc. without a bespoke node type.
import { Extension } from '@tiptap/core'

export const QuoteColor = Extension.create({
  name: 'quoteColor',

  addOptions() {
    return { types: ['blockquote'] }
  },

  addGlobalAttributes() {
    return [
      {
        types: this.options.types,
        attributes: {
          color: {
            default: null,
            parseHTML: (el) => el.getAttribute('data-quote-color') || null,
            renderHTML: (attrs) =>
              attrs.color
                ? { 'data-quote-color': attrs.color, style: `--quote-color: ${attrs.color}` }
                : {},
          },
        },
      },
    ]
  },

  addCommands() {
    return {
      // Wrap the selection in a blockquote (if it isn't already) and set its color.
      setBlockquoteColor:
        (color) =>
        ({ editor, chain }) => {
          const c = chain().focus()
          if (!editor.isActive('blockquote')) c.toggleBlockquote()
          return c.updateAttributes('blockquote', { color }).run()
        },
    }
  },
})

export default QuoteColor
