"""Source adapters and the canonical collection pipeline (B-S8 onward).

`contract` is the boundary every source crosses; `configuration` is the reviewed,
versioned catalogue that decides what may run; `registry` maps a configured
source to its implementation; and `pipeline` moves work through the job queue.
Provider-specific translation lives in the subpackages and goes no further.
"""
