def merge_latest(reports, key, value):
    """Combine facts from reports given oldest first; for one key the newest report's fact wins.

    Returns ([(fact, source)], revisions) where a revision is recorded whenever a newer report
    gives a different value for a key an older one already had.
    """
    winners: dict = {}
    revisions = []
    for source, facts in reports:
        for fact in facts:
            k = key(fact)
            if k in winners and value(winners[k][0]) != value(fact):
                old, old_source = winners[k]
                revisions.append({"key": k, "old": value(old), "new": value(fact),
                                  "old_source": old_source, "new_source": source})
            winners[k] = (fact, source)
    return list(winners.values()), revisions
