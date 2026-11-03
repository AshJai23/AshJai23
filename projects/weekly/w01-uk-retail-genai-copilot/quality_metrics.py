"""Transparent IR measures against source-derived silver references, not a judge LLM."""
def retrieval_metrics(relevant_ids, ranked_ids, k=3):
    relevant=set(relevant_ids)
    if not relevant:raise ValueError('A retrieval case needs at least one frozen reference')
    if len(ranked_ids)!=len(set(ranked_ids)):raise ValueError('Duplicate ranked IDs would corrupt metrics')
    top=ranked_ids[:k];hits=len(relevant.intersection(top))
    rank=next((i for i,identity in enumerate(top,1) if identity in relevant),None)
    return {'reference_count':len(relevant),'hit_at_3':bool(hits),'recall_at_3':hits/len(relevant),
            'precision_at_3':hits/k,'mrr_at_3':1/rank if rank else 0.0}

def percentile_nearest_rank(values,p):
    import math
    if not values:return None
    return sorted(values)[max(0,min(len(values)-1,math.ceil(len(values)*p)-1))]
