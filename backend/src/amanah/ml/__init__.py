"""The AI boundary: everything that talks to Gemini, and nothing that counts.

The split this package exists to enforce is the one `spec.md` section 11 draws.
Gemini classifies text and explains a bundle of already-computed facts. It never
produces a number the product publishes, never sees the database, and never gains
a tool. Deterministic aggregation lives in `amanah.metrics`, on the other side of
that line, and stays correct when this package is unavailable.
"""
