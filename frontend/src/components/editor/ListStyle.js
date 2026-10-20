// List numbering / bullet styles. Tiptap's ordered + bullet lists only ever
// render a plain `<ol>` / `<ul>`; this injects a `listStyleType` global attribute
// onto both, rendered as an inline `list-style-type` so a single list can be
// decimal, a·b·c (alpha), i·ii·iii (roman), or disc/circle/square — Word-style.
//
// Node NAMES are schema names: `bulletList` / `orderedList` (camelCase), matching
// StarterKit. The values are raw CSS `list-style-type` keywords so the browser
// does the numbering for us (nested lists, continuation, everything).
import { Extension } from '@tiptap/core'

export const ListStyle = Extension.create({
  name: 'listStyle',

  addOptions() {
    return { types: ['bulletList', 'orderedList'] }
  },

  addGlobalAttributes() {
    return [
      {
        types: this.options.types,
        attributes: {
          listStyleType: {
            default: null,
            // Round-trip the chosen style off the element's inline style.
            parseHTML: (el) => el.style.listStyleType || null,
            renderHTML: (attrs) =>
              attrs.listStyleType ? { style: `list-style-type: ${attrs.listStyleType}` } : {},
          },
        },
      },
    ]
  },

  addCommands() {
    return {
      // Ensure the requested list kind is active (toggle it on if not), then stamp
      // the style onto that list node. Runs as one chain so a fresh list is created
      // and styled atomically.
      setListStyleType:
        (listType, styleType) =>
        ({ editor, chain }) => {
          const c = chain().focus()
          if (!editor.isActive(listType)) {
            if (listType === 'bulletList') c.toggleBulletList()
            else c.toggleOrderedList()
          }
          return c.updateAttributes(listType, { listStyleType: styleType }).run()
        },
    }
  },
})

export default ListStyle
