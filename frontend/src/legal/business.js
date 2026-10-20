// Who runs Zinvest, for the legal pages and the footer. Set at build time
// (Vercel → Environment Variables, then redeploy); a field left empty is not
// shown, so the pages never print a made-up name or address.
//
//   VITE_LEGAL_OPERATOR  legal name of the person or company behind Zinvest
//   VITE_LEGAL_REG_NO    registration / tax number (INN, STIR …)
//   VITE_LEGAL_ADDRESS   postal address
//   VITE_LEGAL_EMAIL     contact address for privacy and support requests
const env = import.meta.env

export const BUSINESS = {
  brand: 'Zinvest',
  operator: env.VITE_LEGAL_OPERATOR || '',
  regNo: env.VITE_LEGAL_REG_NO || '',
  address: env.VITE_LEGAL_ADDRESS || '',
  email: env.VITE_LEGAL_EMAIL || '',
}

// The day the texts below were last changed (shown on every legal page).
export const LEGAL_UPDATED = '2026-10-04'

// The documents under /legal/:doc, in the order of the tabs.
export const LEGAL_DOCS = ['privacy', 'terms', 'cookies', 'refund', 'licenses']
