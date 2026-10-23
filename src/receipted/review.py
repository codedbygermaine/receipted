"""Reviewer CLI for claims the agent paused.

  python -m receipted.review list
  python -m receipted.review resolve SAMPLE-003 approve "Hot tea price agreed with the cafe"
  python -m receipted.review resolve SAMPLE-003 reject "Ask for an itemised receipt"
"""

import sys

from receipted.graph import pending_reviews, resume_review


def main(argv):
    if not argv or argv[0] == "list":
        pending = pending_reviews()
        if not pending:
            print("No claims waiting for review.")
        for p in pending:
            print(f"\n{p['claim_id']}  {p['submitter']}  amount={p['amount']}\n  why: {p['reason']}")
            for sev, typ, msg in p["issues"]:
                print(f"   [{sev:>6}] {typ}: {msg}")
        return
    if argv[0] == "resolve" and len(argv) >= 3 and argv[2] in ("approve", "reject", "needs_review"):
        note = " ".join(argv[3:])
        state = resume_review(argv[1], argv[2], note)
        print(f"{argv[1]} -> {state['decision'].upper()} ({state['decision_reason']})\n\nDRAFT:\n{state['draft']}")
        return
    print(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
