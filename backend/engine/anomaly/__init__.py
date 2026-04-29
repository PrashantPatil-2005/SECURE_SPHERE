"""Per-service behavioural anomaly layer (Phase 13).

Emits ``behavior_anomaly`` events into the stream when a service's
observed feature vector deviates from its rolling baseline. Designed as an
*augment* to rule-based correlation — never a replacement.
"""
