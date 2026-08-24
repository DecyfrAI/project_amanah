"""Everything a signed-in person can contribute: submissions, disputes, review.

The rule these modules share is ownership. A user reads their own records and
nobody else's; a reviewer reaches the same records through the review queue,
never through an owner-scoped read. Reviewer decisions append rather than
overwrite, so what the model said and what a human decided both stay readable.
"""
