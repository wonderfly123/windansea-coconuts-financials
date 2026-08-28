"""Shared bucket and flag string literals.

These strings are load-bearing. The Excel SUMIFS formulas, the owner-comp
aggregation, and the classification rules all match on them exactly, so a single
typo would silently zero a total. Define them once here and import everywhere.
"""

# Buckets drive every total. Every transaction lands in exactly one.
BUCKET_REVENUE = "Revenue"
BUCKET_OPERATING = "Operating Expense"
BUCKET_PAYROLL = "Payroll"
BUCKET_OWNER_PAY = "Owner Pay"
BUCKET_OWNER_DRAW = "Owner Draw"
BUCKET_EXCLUDED = "Excluded"

ALL_BUCKETS = [
    BUCKET_REVENUE,
    BUCKET_OPERATING,
    BUCKET_PAYROLL,
    BUCKET_OWNER_PAY,
    BUCKET_OWNER_DRAW,
    BUCKET_EXCLUDED,
]

# Flags mark special items so they can be eyeballed and totaled in the owner panel.
FLAG_OWNER_PAY_ADP = "Owner Pay ADP"
FLAG_HARRISON_DIRECT = "Owner Pay Direct Transfer (Harrison)"
FLAG_OWNER_CAR = "Owner Car Capital One (Jordan)"
FLAG_OWNER_DRAW_BOFA = "Owner Draw BofA Car (Jordan)"
FLAG_VENMO = "Venmo/CashApp Pay"

# Meta keys (key/value store in the DB).
META_LAST_REFRESH = "last_refresh"
META_WINDOW_START = "window_start"
META_WINDOW_END = "window_end"
META_ADP_VARIANCE = "adp_variance"
META_HARRISON_W2_GROSS = "harrison_w2_gross"
