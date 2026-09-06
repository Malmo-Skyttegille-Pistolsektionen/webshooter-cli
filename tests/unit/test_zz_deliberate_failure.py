"""Throwaway: proves the Tests aggregator reports FAILURE, not skipped.

Do not merge. This file exists only for the duration of one CI run on a
scratch pull request, to observe the failure path of the `tests` job added in
#14 rather than reason about it.
"""


def test_deliberate_failure_to_exercise_the_aggregator():
    assert False, "deliberate: makes the matrix test job fail"
