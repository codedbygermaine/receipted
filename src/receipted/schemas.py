"""Pydantic models for what the LLM must return. The API's structured-output mode is given this
schema, so the model can only reply with JSON of this exact shape; Pydantic then validates it.
"""

from typing import Literal

from pydantic import BaseModel, Field


class LineItem(BaseModel):
    name: str = Field(description="Item name as printed, cleaned of quantity and price")
    qty: float | None = Field(description="Quantity. null if not printed")
    unit_price: float | None = Field(description="Price per unit in whole currency units. null if not printed")
    line_total: float | None = Field(description="Line total as printed. null if not printed")
    raw_line: str = Field(description="The full line exactly as printed on the receipt")


class Receipt(BaseModel):
    items: list[LineItem]
    subtotal: float | None = Field(description="Subtotal as printed, else null")
    tax: float | None = Field(description="Tax (PB1, PPN, VAT, 'Pb 1', 'Tax') as printed, else null")
    service: float | None = Field(description="Service charge as printed, else null")
    discount: float | None = Field(description="Receipt-level discount as a positive number, else null")
    total: float | None = Field(description="Grand total as printed, else null")
    currency: str = Field(description="Three-letter currency code, e.g. IDR")
    readability: Literal["clear", "partly unclear", "unreadable"] = Field(
        description="clear = every number legible; partly unclear = some guessed; unreadable = cannot extract"
    )
