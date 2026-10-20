// Adds a `backgroundColor` attribute to table cells + header cells so any cell
// can be filled with a color (Word-like). Applied via the table extension's
// setCellAttribute('backgroundColor', color) command; rendered as an inline style
// and parsed back from it. Schema node names: tableCell / tableHeader.
import { Extension } from '@tiptap/core'

export const CellBackground = Extension.create({
  name: 'cellBackground',

  addOptions() {
    return { types: ['tableCell', 'tableHeader'] }
  },

  addGlobalAttributes() {
    return [
      {
        types: this.options.types,
        attributes: {
          backgroundColor: {
            default: null,
            parseHTML: (element) =>
              element.style?.backgroundColor || element.getAttribute('data-background-color') || null,
            renderHTML: (attributes) => {
              if (!attributes.backgroundColor) return {}
              return {
                style: `background-color: ${attributes.backgroundColor}`,
                'data-background-color': attributes.backgroundColor,
              }
            },
          },
        },
      },
    ]
  },
})

export default CellBackground
