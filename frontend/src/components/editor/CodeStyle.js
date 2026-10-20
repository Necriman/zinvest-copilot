// Per-span color for inline code. Adds `color` + `backgroundColor` attributes to
// StarterKit's `code` mark, rendered as inline styles, so a snippet can be tinted
// independently (the stylesheet supplies the default pill when neither is set).
import { Extension } from '@tiptap/core'

export const CodeStyle = Extension.create({
  name: 'codeStyle',

  addOptions() {
    return { types: ['code'] }
  },

  addGlobalAttributes() {
    return [
      {
        types: this.options.types,
        attributes: {
          color: {
            default: null,
            parseHTML: (el) => el.style.color || null,
            renderHTML: (attrs) => (attrs.color ? { style: `color: ${attrs.color}` } : {}),
          },
          backgroundColor: {
            default: null,
            parseHTML: (el) => el.style.backgroundColor || null,
            renderHTML: (attrs) =>
              attrs.backgroundColor ? { style: `background-color: ${attrs.backgroundColor}` } : {},
          },
        },
      },
    ]
  },
})

export default CodeStyle
