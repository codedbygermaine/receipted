"""Prove the API key in .env works: list models the key can see, then send "hello"."""

import os
import sys

from dotenv import load_dotenv
import anthropic

# Reads .env from the current directory and puts ANTHROPIC_API_KEY into the environment.
load_dotenv()

if not os.getenv("ANTHROPIC_API_KEY"):
    sys.exit("No ANTHROPIC_API_KEY found. Copy .env.example to .env and paste your key in.")

# The client picks up ANTHROPIC_API_KEY from the environment; we never hardcode it.
client = anthropic.Anthropic()

print("Models visible to this key:")
for m in client.models.list():
    print(f"  {m.id:<28} {m.display_name}")

response = client.messages.create(
    model="claude-haiku-5-5",
    max_tokens=100,
    messages=[{"role": "user", "content": "hello"}],
)

print("\nReply:", response.content[0].text)
print(f"Tokens: {response.usage.input_tokens} in, {response.usage.output_tokens} out")
