// Lets whole nodes (images, …) carry a comment, the same way the Comment mark lets
// text carry one. Injects comment metadata as global attributes rendered as
// data-comment-* so they persist in the HTML and are found by the same
// [data-comment-id] anchoring/hover/click logic used for text comments.
import { Extension } from '@tiptap/core'

const MAP = {
  commentId: 'data-comment-id',
  commentAuthor: 'data-comment-author',
  commentDate: 'data-comment-date',
  commentText: 'data-comment-text',
  commentColor: 'data-comment-color',
}

export const Commentable = Extension.create({
  name: 'commentable',

  addOptions() {
    return { types: ['image'] }
  },

  addGlobalAttributes() {
    return [
      {
        types: this.options.types,
        attributes: Object.fromEntries(
          Object.entries(MAP).map(([attr, dataAttr]) => [
            attr,
            {
              default: null,
              parseHTML: (el) => el.getAttribute(dataAttr) || null,
              renderHTML: (a) => (a[attr] ? { [dataAttr]: a[attr] } : {}),
            },
          ]),
        ),
      },
    ]
  },
})

export default Commentable
