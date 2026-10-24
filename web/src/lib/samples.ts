/* Six receipts a visitor can try, all photographed by the author in Singapore. Each comes with a claim that
   exercises a different rule; two are honest, two end up with an approver, two can't be paid. The cards don't
   say which, and the form says the claim is a sample. */
import type { ClaimInput } from "./api"
export type Sample = { id: string; title: string; where: string; currency: "SGD" | "IDR"; claim: ClaimInput; credit?: string }
export const SAMPLES: Sample[] = [
  { id: "brunch", title: "Team brunch", where: "Café, Singapore", currency: "SGD",
    claim: { submitter: "", purpose: "Team brunch, 3 people", amount: 101.90, items: [{ name: "Eggs Benedict", qty: 1, line_total: 28 }, { name: "Brussels Salad", qty: 1, line_total: 27 }, { name: "Symmetry Breakfast", qty: 1, line_total: 30 }] } },
  { id: "stationery", title: "Notebook", where: "Stationery shop, Singapore", currency: "SGD",
    claim: { submitter: "", purpose: "Notebook for meeting notes", amount: 18.00, items: [] } },
  { id: "client-lunch", title: "Client lunch", where: "Café, Singapore", currency: "SGD",
    claim: { submitter: "", purpose: "Client lunch, 2 people", amount: 104.72, items: [] } },
  { id: "pharmacy", title: "Pharmacy run", where: "Watsons, Singapore", currency: "SGD",
    claim: { submitter: "", purpose: "Supplies for an event", amount: 20.40, items: [{ name: "Unscented Baby Wipes", qty: 1, line_total: 3.50 }, { name: "Transparent Plasters", qty: 1, line_total: 4.55 }, { name: "Actal Tablet", qty: 1, line_total: 4.80 }, { name: "Imodium Cap", qty: 1, line_total: 7.55 }] } },
  { id: "clothing", title: "Event outfit", where: "Clothing shop, Singapore", currency: "SGD",
    claim: { submitter: "", purpose: "Outfit for the launch event", amount: 59.00, items: [] } },
  { id: "cafe", title: "Team lunch", where: "Korean restaurant, Singapore", currency: "SGD",
    claim: { submitter: "", purpose: "Team lunch, 2 people", amount: 45.00, items: [] } },
]
export const sampleImage = (s: Sample) => `${import.meta.env.BASE_URL}samples/${s.id}.jpg`
export const sampleThumb = (s: Sample) => `${import.meta.env.BASE_URL}samples/${s.id}_thumb.jpg`
