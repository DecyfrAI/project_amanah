"""Persistence: every product read goes through one of these.

Repositories own SQL and return rows. They read the authenticated-safe views and
never a base table, so no endpoint can reach raw content or an author identifier
by asking a repository for more columns.
"""
