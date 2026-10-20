// Custom Tiptap spacing extension. Injects `marginTop` / `marginBottom` /
// `paddingTop` / `paddingBottom` as global attributes onto every block type and
// renders them as inline styles, so the user can dial in vertical spacing per
// block (see SpacingMenu.vue).
//
// Schema node names — NOT the DOM `data-type` values: block math is `blockMath`
// in the schema (its rendered element carries data-type="block-math").
//
// Heads-up: `image` and `blockMath` render through custom NodeViews, which do NOT
// auto-apply an attribute's renderHTML. Those two NodeViews read these attrs off
// `node.attrs` and set the styles themselves (see ResizableImage.vue and the
// BlockMath NodeView in DocumentEditor.vue). For plain toDOM nodes (paragraph,
// heading, table) the renderHTML below is what paints the style.
import { Extension } from '@tiptap/core'

// attr name → CSS property.
const SPACING_CSS = {
  marginTop: 'margin-top',
  marginBottom: 'margin-bottom',
  paddingTop: 'padding-top',
  paddingBottom: 'padding-bottom',
}

export const Spacing = Extension.create({
  name: 'spacing',

  addOptions() {
    return {
      types: ['heading', 'paragraph', 'image', 'table', 'blockMath'],
    }
  },

  addGlobalAttributes() {
    return [
      {
        types: this.options.types,
        attributes: Object.fromEntries(
          Object.keys(SPACING_CSS).map((attr) => [
            attr,
            {
              default: null,
              parseHTML: (element) => element.style?.[attr] || null,
              renderHTML: (attributes) => {
                if (!attributes[attr]) return {}
                return { style: `${SPACING_CSS[attr]}: ${attributes[attr]}` }
              },
            },
          ]),
        ),
      },
    ]
  },

  addCommands() {
    return {
      // Convenience command mirroring the per-type updateAttributes the menu uses.
      // Applies the given spacing patch to whichever block type is at the cursor.
      // `.map(...).some(...)`, not `.every` — updateAttributes returns false for
      // types absent from the selection, which would short-circuit `.every`.
      setSpacing:
        (attributes) =>
        ({ commands }) =>
          this.options.types
            .map((type) => commands.updateAttributes(type, attributes))
            .some((applied) => applied),
    }
  },
})

export default Spacing
