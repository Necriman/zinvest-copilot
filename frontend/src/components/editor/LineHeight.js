// Custom Tiptap line-height extension. Tiptap ships no native line-height, so we
// inject a `lineHeight` global attribute onto the text block types and render it
// as an inline `line-height` style (parsed back from the DOM on load).
//
// Note the node NAMES are the schema names, not the CSS/DOM names: StarterKit's
// list item is `listItem` (camelCase), not `list_item` — the wrong name would be
// a silent no-op.
import { Extension } from '@tiptap/core'

export const LineHeight = Extension.create({
  name: 'lineHeight',

  addOptions() {
    return {
      types: ['heading', 'paragraph', 'listItem'],
      // Preset values surfaced by LineSpacingMenu.vue (kept here so the menu and
      // the schema agree on what "valid" means).
      values: ['1', '1.15', '1.5', '2'],
      defaultLineHeight: null,
    }
  },

  addGlobalAttributes() {
    return [
      {
        types: this.options.types,
        attributes: {
          lineHeight: {
            default: this.options.defaultLineHeight,
            // Read an existing inline line-height back off the element.
            parseHTML: (element) => element.style.lineHeight || this.options.defaultLineHeight,
            // Render it as an inline style so it overrides the .prose defaults.
            renderHTML: (attributes) => {
              if (!attributes.lineHeight) return {}
              return { style: `line-height: ${attributes.lineHeight}` }
            },
          },
        },
      },
    ]
  },

  addCommands() {
    return {
      // Apply a line-height to whichever text block is at the selection. Tiptap's
      // updateAttributes returns false when no node of that type is present, so we
      // `.map(...).some(...)` (NOT `.every`, which would short-circuit on the first
      // non-matching type) — the same pattern the TextAlign extension uses.
      setLineHeight:
        (value) =>
        ({ commands }) =>
          this.options.types
            .map((type) => commands.updateAttributes(type, { lineHeight: value }))
            .some((applied) => applied),

      // "Default" → clear the attribute so the .prose line-height takes over again.
      unsetLineHeight:
        () =>
        ({ commands }) =>
          this.options.types
            .map((type) => commands.updateAttributes(type, { lineHeight: null }))
            .some((applied) => applied),
    }
  },
})

export default LineHeight
