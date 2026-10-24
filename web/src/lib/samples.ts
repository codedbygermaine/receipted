/* Six receipts a visitor can try. Each comes with a claim that exercises a different part of the checker; the
   cards deliberately do not say what the outcome will be. Each has its own submitter so the inbox doesn't fill
   with identical rows. */
import type { ClaimInput } from "./api"
export type Sample = { id: string; title: string; where: string; currency: "SGD" | "IDR"; claim: ClaimInput; credit?: string }
export const SAMPLES: Sample[] = [
  { id: "brunch", title: "Brunch for three", where: "Café, Singapore", currency: "SGD",
    claim: { submitter: "Priya T.", purpose: "Team brunch, 3 people", amount: 101.90, items: [{ name: "Eggs Benedict", qty: 1, line_total: 28 }, { name: "Brussels Salad", qty: 1, line_total: 27 }, { name: "Symmetry Breakfast", qty: 1, line_total: 30 }] } },
  { id: "pharmacy", title: "Pharmacy run", where: "Watsons, Singapore", currency: "SGD",
    claim: { submitter: "Marcus L.", purpose: "Supplies for event", amount: 20.40, items: [{ name: "Unscented Baby Wipes", qty: 1, line_total: 3.50 }, { name: "Transparent Plasters", qty: 1, line_total: 4.55 }, { name: "Actal Tablet", qty: 1, line_total: 4.80 }, { name: "Imodium Cap", qty: 1, line_total: 7.55 }] } },
  { id: "cafe", title: "Team lunch", where: "Café, Singapore", currency: "SGD",
    claim: { submitter: "Wei Lin", purpose: "Committee lunch, 4 people", amount: 130.00, items: [] } },
  { id: "cinema", title: "Cinema tickets", where: "SAFRA, Singapore", currency: "SGD",
    claim: { submitter: "Hafiz R.", purpose: "", amount: 67.50, items: [{ name: "Movie tickets", qty: 5, line_total: 67.50 }] } },
  { id: "bakery", title: "Bakery snacks", where: "Bakery, Indonesia", currency: "IDR", credit: "Receipt image from CORD v2 (CC BY 4.0)",
    claim: { submitter: "Dewi S.", purpose: "Snacks for orientation booth, 5 people", amount: 45500, items: [{ name: "Real Ganache", qty: 1, line_total: 16500 }, { name: "Egg Tart", qty: 1, line_total: 13000 }, { name: "Pizza Toast", qty: 1, line_total: 16000 }] } },
  { id: "dinner", title: "Team dinner", where: "Restaurant, Indonesia", currency: "IDR", credit: "Receipt image from CORD v2 (CC BY 4.0)",
    claim: { submitter: "Arjun K.", purpose: "Committee dinner, 4 people", amount: 250000, items: [{ name: "Sop Sui Jiao", qty: 1, line_total: 33000 }, { name: "Ha Kaou Udang", qty: 1, line_total: 28000 }, { name: "Siomay Kombinasi", qty: 2, line_total: 46000 }, { name: "Bir Bintang", qty: 2, line_total: 70000 }] } },
]
export const sampleImage = (s: Sample) => `${import.meta.env.BASE_URL}samples/${s.id}.jpg`
export const sampleThumb = (s: Sample) => `${import.meta.env.BASE_URL}samples/${s.id}_thumb.jpg`
