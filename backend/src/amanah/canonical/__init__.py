"""Canonical processing: normalize, contextualize, hash, deduplicate, store.

Everything an adapter produces passes through here on its way to
`content_items`, so the rules that decide what two identical items look like are
written once. `text` never censors, `urls` never guesses, `hashing` never
approximates, and `store` never writes a row an adapter has not been through.
"""
