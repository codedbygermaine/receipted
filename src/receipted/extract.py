"""Step 1 of the pipeline: read a receipt image with a multimodal model.

The model is given the image and a schema, and must return JSON of that shape. We validate it
with Pydantic, retry once if the reply is unusable, and cache the result on disk.
"""

import base64
import io
import time
from dataclasses import dataclass, asdict
from pathlib import Path

from PIL import Image
from pydantic import ValidationError

from receipted import llm
from receipted.schemas import Receipt

PROMPT_VERSION = "v2"
MAX_EDGE = 1568  # the API downsizes anything larger, so sending more pixels only costs upload time

SYSTEM_PROMPT = """You read photos of shop and restaurant receipts and return their contents as structured data.
Most receipts are Indonesian, priced in Rupiah (IDR), which has no cents: "16.500", "16,500" and "16500.00" all mean 16500.

Rules:
- List every purchased line item in order. Include add-ons or modifiers that have their own printed price (even 0) as separate items.
- Lines with no price at all (e.g. "Less Ice", "70%", a size or note under an item) are modifiers, not items: leave them out.
- Do not include payment lines (cash, change, card) or counts of items as line items.
- For each item, copy the printed line into raw_line exactly as you see it.
- Report numbers exactly as printed on the receipt. Never compute a value that is not printed; use null instead.
- A quantity like "1Prs", "x2", "2 x" means 1, 2, 2.
- subtotal, tax, service, discount and total are the receipt's own printed summary lines, else null.
- readability: "clear" if every number is legible; "partly unclear" if you had to guess any digit; "unreadable" if the receipt cannot be read."""

USER_PROMPT = "Extract this receipt."


class ExtractionError(Exception):
    """Raised when the model could not give a usable extraction, so the pipeline can route to human review."""


@dataclass
class ExtractionResult:
    receipt: dict           # validated Receipt as a plain dict
    model: str
    prompt_version: str
    input_tokens: int
    output_tokens: int
    latency_s: float
    cost_usd: float
    attempts: int
    cached: bool


def tidy(receipt: dict) -> dict:
    """Rupiah has no cents: show 16500, not 16500.0. Applied to fresh and cached results alike."""
    def fix(v):
        return int(v) if isinstance(v, float) and v.is_integer() else v
    for it in receipt["items"]:
        for k in ("qty", "unit_price", "line_total"):
            it[k] = fix(it.get(k))
    for k in ("subtotal", "tax", "service", "discount", "total"):
        receipt[k] = fix(receipt.get(k))
    return receipt


def prepare_image(path: str | Path) -> tuple[bytes, str]:
    """Resize to the model's limit and JPEG-encode. Returns (bytes, media_type)."""
    img = Image.open(path).convert("RGB")
    img.thumbnail((MAX_EDGE, MAX_EDGE))  # keeps aspect ratio, only shrinks
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue(), "image/jpeg"


def _call(image_b64: str, media_type: str, model: str, nudge: str | None):
    """One API call. nudge is extra text added on the retry."""
    content = [
        {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_b64}},
        {"type": "text", "text": USER_PROMPT + (f"\n\n{nudge}" if nudge else "")},
    ]
    return llm.client().messages.parse(
        model=model,
        max_tokens=8000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": content}],
        output_format=Receipt,
        output_config={"effort": "medium"},
    )


def extract(image_path: str | Path, model: str = llm.DEFAULT_MODEL, use_cache: bool = True) -> ExtractionResult:
    image_bytes, media_type = prepare_image(image_path)
    key = llm.cache_key(image_bytes, PROMPT_VERSION, model, SYSTEM_PROMPT)
    if use_cache:
        hit = llm.cache_get("extract", key)
        if hit:
            hit["receipt"] = tidy(hit["receipt"])
            return ExtractionResult(**{**hit, "cached": True})

    image_b64 = base64.standard_b64encode(image_bytes).decode()
    nudge = None
    last_error = None
    total_in = total_out = 0
    start = time.perf_counter()
    for attempt in (1, 2):
        try:
            response = _call(image_b64, media_type, model, nudge)
        except ValidationError as e:  # model replied, but not in the shape we asked for
            last_error = e
            nudge = "Your previous reply did not match the required schema. Reply with valid JSON only."
            continue
        total_in += response.usage.input_tokens
        total_out += response.usage.output_tokens
        if response.stop_reason == "refusal":
            raise ExtractionError("model refused to read this image")
        if response.stop_reason == "max_tokens":
            raise ExtractionError("model output was cut off")
        receipt = response.parsed_output
        if receipt is None:
            last_error = "no parsed output"
            nudge = "Reply with valid JSON matching the schema only."
            continue
        result = ExtractionResult(
            receipt=tidy(receipt.model_dump()),
            model=model,
            prompt_version=PROMPT_VERSION,
            input_tokens=total_in,
            output_tokens=total_out,
            latency_s=round(time.perf_counter() - start, 2),
            cost_usd=round(llm.cost_usd(model, total_in, total_out), 6),
            attempts=attempt,
            cached=False,
        )
        llm.cache_put("extract", key, asdict(result))
        return result
    raise ExtractionError(f"invalid output twice: {last_error}")
