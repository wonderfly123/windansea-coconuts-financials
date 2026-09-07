"""Constants for the runway dashboard.

Everything here was either transcribed from Windansea_Roles_Responsibilities.docx
or confirmed by Jordan on 2026-08-28. See docs/superpowers/specs/2026-08-28-
runway-dashboard-design.md for the reasoning behind each rule.
"""

# Window -------------------------------------------------------------------
WINDOW_START = "2026-05-01"
WINDOW_END = "2026-08-28"
RAW_CUTOVER = "2026-06-19"  # DB rows before this date, raw Ramp pulls from it on
MONTHS = ["2026-05", "2026-06", "2026-07", "2026-08"]
MONTH_WEIGHTS = {"2026-05": 1.0, "2026-06": 1.0, "2026-07": 1.0, "2026-08": 28 / 31}
MONTH_LABELS = {"2026-05": "May", "2026-06": "Jun", "2026-07": "Jul", "2026-08": "Aug (to 28th)"}

# Sections -----------------------------------------------------------------
EXCLUDED = "excluded"
REVENUE = "revenue"
SALES_TAX = "sales_tax"
COGS = "cogs"
OVERHEAD = "overhead"
PEOPLE_NONCORE = "people_noncore"
PEOPLE_CORE = "people_core"
SECTIONS = [EXCLUDED, REVENUE, SALES_TAX, COGS, OVERHEAD, PEOPLE_NONCORE, PEOPLE_CORE]

# Non core sub labels
SUB_ADP_HOURLY = "adp_hourly"
SUB_VENMO = "venmo"
SUB_CONTRACTOR = "contractor"

# Core people ----------------------------------------------------------------
# plan_total is the doc's fully loaded monthly cost (gross + 25% payroll tax
# where applicable). Harrison = $2,000 payroll (+$500 tax) + $4,000 draw.
CORE_PEOPLE = [
    {"key": "harrison", "role": "Owner, sales and shared CEO", "person": "Harrison Goldfarb",
     "status": "filled", "plan_gross": 6000, "plan_total": 6500, "adp_name": "Goldfarb, Harrison L"},
    {"key": "trent", "role": "GM San Diego / Ops Manager", "person": "Trent Livolsi",
     "status": "filled", "plan_gross": 7300, "plan_total": 9125, "adp_name": "Livolsi, Trent"},
    {"key": "juniper", "role": "Executive Assistant", "person": "Juniper Judd",
     "status": "filled", "plan_gross": 1200, "plan_total": 1200, "adp_name": "Judd, Juniper"},
    {"key": "jordan", "role": "Systems and strategic advisor", "person": "Jordan Millhausen",
     "status": "filled", "plan_gross": 2700, "plan_total": 2700, "adp_name": None},
    {"key": "tim", "role": "Bookkeeping (Kosmos Accounting)", "person": "Tim Kosmos",
     "status": "filled", "plan_gross": 400, "plan_total": 400, "adp_name": None},
    {"key": "ops_mgr", "role": "Assistant Ops Manager", "person": "Not hired",
     "status": "not hired", "plan_gross": 4500, "plan_total": 5625, "adp_name": None},
    {"key": "edy", "role": "Social media", "person": "Edy, not hired",
     "status": "not hired", "plan_gross": 3250, "plan_total": 3250, "adp_name": None},
]
PLAN_TOTAL = 28800  # doc's $28,400 plus Tim Kosmos bookkeeping $400
ADP_CORE_NAMES = {p["adp_name"]: p["key"] for p in CORE_PEOPLE if p["adp_name"]}

# Bank counterparties that are core people pay (checked as substrings, lower case)
HARRISON_DIRECT = ["8371", "jpmorgan chase", "chase credit crd", "amex epayment"]
JORDAN_DIRECT = ["4201", "capital one auto"]
TIM_DIRECT = ["kosmos"]
SPLIT_BOFA = {"2026-06-01": {"amount": 3400.0, "jordan": 2000.0, "harrison": 1400.0}}

# Merchant lists (lower case substrings) ---------------------------------------
COGS_MERCHANTS = [
    "sun hing", "coy's produce", "coys produce", "alibaba", "manila oriental",
    "vien dong", "ematik", "packola", "uline", "imprintnow", "gearheart", "wrap caviar",
    "amazon",  # event supplies, split across events (Jordan, Sep 7 2026)
]
NONCORE_CONTRACTORS = ["indico thread", "nathan zini", "josh escalante"]
VENMO_LIKE = ["venmo", "tremendous", "apple cash"]
SALES_TAX_NAMES = ["ca dept tax", "cdtfa"]
ADP_DEBITS = ["adp wage pay", "adp tax", "adp pay-by-pay", "adp payroll"]
ADP_FEES = ["adp payroll fees", "adp fees"]
EXCLUDED_INFLOWS = ["the bitter herb", "bitter herb", "estimated taxes", "mercury",
                    "socal 4813", "ramp", "savings interest", "io cashback", "jpmorgan chase"]
EXCLUDED_OUTFLOWS = ["checking account", "mercury", "socal", "ramp - checking", "estimated taxes"]
REVENUE_NAMES = ["currency cloud"]
FIXED_OVERHEAD_SUBS = {"saas / software", "software", "insurance", "taxes and tax preparation", "adp fees",
                       "marketing & advertising", "advertising", "utilities", "clubs and memberships", "fees"}
FIXED_OVERHEAD_LABELS = ["extra space storage", "pipedrive", "anthropic", "linkedin"]
UNKNOWN_CATEGORIES = {"", "other", "uncategorized", "general merchandise", "bill pay", "withdrawal"}

# Roles appendix (from the doc) --------------------------------------------------
ROLES = [
    ("1. Revenue / Growth", [
        ("Event activation sales: pipeline ownership, proposals, closing", "Harrison", "filled"),
        ("Wholesale account growth: new hotel and restaurant accounts", "Harrison", "filled"),
        ("Partnerships and business development", "Harrison", "filled"),
        ("Pricing strategy across packages, markets, client tiers", "Harrison", "filled"),
    ]),
    ("2. Account Management", [
        ("Wholesale account servicing: relationship, reorders, issues", "No owner", "no owner"),
        ("Event client servicing: pre event, on site, follow up", "Trent", "filled"),
    ]),
    ("3. Event Operations", [
        ("Event planning and coordination: staffing, logistics, timeline", "Trent", "filled"),
        ("On site execution: day of management, setup and breakdown", "Ops Manager (new hire)", "not hired"),
        ("Delivery and fulfillment: wholesale delivery routes", "Ops Manager (new hire)", "not hired"),
        ("Prep and production: coconut prep, stamping, inventory prep", "Ops Manager (new hire)", "not hired"),
    ]),
    ("4. Supply Chain / Procurement", [
        ("Primary and backup supplier sourcing", "No owner", "no owner"),
        ("Vendor relationship management and contract terms", "No owner", "no owner"),
        ("Purchase order accuracy and tracking", "No owner", "no owner"),
        ("Inventory and cost control", "No owner", "no owner"),
    ]),
    ("5. Finance & Accounting", [
        ("Invoicing: issuing and tracking", "Executive Assistant (Juniper)", "filled"),
        ("Accounts receivable and collections", "No owner", "no owner"),
        ("Reconciliation: payment platform vs bank, ongoing", "No owner", "no owner"),
        ("Payroll administration", "Executive Assistant (Juniper)", "filled"),
        ("Financial reporting: P&L by channel, margin by event", "No owner", "no owner"),
        ("Bookkeeping", "Tim Kosmos", "filled"),
        ("Tax and entity compliance", "Tim Kosmos (filings), owner side unassigned", "filled"),
    ]),
    ("6. People / HR", [
        ("Recruiting and onboarding", "Trent", "filled"),
        ("Employment compliance: workers comp, classification, contracts", "No owner", "no owner"),
        ("Performance management and incentive structuring", "Trent", "filled"),
    ]),
    ("7. Marketing / Brand", [
        ("Social media management", "Edy (not hired)", "not hired"),
        ("Content and creative production", "Edy (not hired)", "not hired"),
        ("Pitch and concept development for prospects", "No owner", "no owner"),
        ("Brand consistency across channels", "No owner", "no owner"),
    ]),
    ("8. Systems / Operations Infrastructure", [
        ("Operations tracking software (ClickUp), actively used", "Jordan", "filled"),
        ("Internal tooling for error reduction (POs, vendor accuracy)", "Jordan", "filled"),
        ("Data and reporting infrastructure connecting sales, ops, finance", "Jordan", "filled"),
    ]),
    ("9. Executive / Strategic Leadership", [
        ("Channel and resource prioritization, event vs wholesale", "Harrison (Jordan advises)", "filled"),
        ("New venture evaluation", "Harrison (Jordan advises)", "filled"),
        ("Final decision authority on hiring, capital, direction", "Harrison", "filled"),
        ("Cross functional coordination", "Harrison", "filled"),
    ]),
]

# Compensation table from the doc, verbatim values
PLAN_COMP = [
    ("Harrison (payroll portion)", 2000, 500, 2500),
    ("Trent", 7300, 1825, 9125),
    ("Ops Manager", 4500, 1125, 5625),
    ("Harrison (owner's draw)", 4000, 0, 4000),
    ("Executive Assistant", 1200, 0, 1200),
    ("Jordan", 2700, 0, 2700),
    ("Edy", 3250, 0, 3250),
    ("Tim Kosmos, bookkeeping (added Aug 2026)", 400, 0, 400),
]

# Projection defaults not derivable from data
PROJECTION_KNOBS = {
    "hire_month": "2026-10",
    "season_months": [5, 6, 7, 8, 9],
    "new_accounts_per_month": 3,
    "value_per_account": 1500,
    "events_multiplier": 1.0,
    "tail_factors": {"2026-09": 0.7, "2026-10": 0.45, "2026-11": 0.2, "2026-12": 0.15},
    "one_offs": [],
    "tax_pct": 0.35,          # income tax set aside on cumulative profit (S corp pass through, owners pay it)
    "owner_draws": 6700,      # Harrison $4,000 + Jordan $2,700 draws inside the core plan, not deductible
}
PRESETS = {
    "status_quo": {"new_accounts_per_month": 0, "events_multiplier": 1.0},
    "plan": {"new_accounts_per_month": 3, "events_multiplier": 1.25},
    "aggressive": {"new_accounts_per_month": 5, "events_multiplier": 1.5},
}


# Go to market (Jordan, Aug 28 2026) ---------------------------------------------
GTM = [
    {"lane": "Wholesale", "owner": "Harrison", "cls": "sea",
     "what": "Hotels, resorts, pool bars and restaurants that stock branded coconuts on a standing order.",
     "how": "Outbound. Harrison opens the account, sets pricing and reorder cadence.",
     "season": "Pays May to Sep. Accounts go quiet after summer and restart in spring, so every account signed in April is worth five months, one signed in August is worth two.",
     "examples": ["Pelican Hill", "Ritz Carlton Laguna", "Omni San Diego", "Evans Hotels", "Torrey Pines Lodge", "Walkabout", "Coy's Produce"],
     "lever": "The new accounts per month and value per account knobs in the Dashboard runway."},
    {"lane": "Big hitters: tech conferences and brand activations", "owner": "Harrison", "cls": "husk",
     "what": "Large one off activations: conferences, launches, corporate brand moments. Five figure tickets, the only revenue that shows up in winter.",
     "how": "Outbound and partnerships. Harrison owns the pipeline, proposals and close. These are the deals that decide whether the team makes it through January.",
     "season": "Year round, lumpy. Vegas conference season and Q4 corporate events are the winter opportunity.",
     "examples": ["Currency Cloud ($67k)", "dbt Summit", "AWS re:Invent (Glow)", "Vanta SF", "Datafold", "Macy's", "Resorts World Las Vegas"],
     "lever": "One off deals in the Dashboard runway, typed in by month."},
    {"lane": "Inbound events: weddings, birthdays, corporate", "owner": "Trent", "cls": "muted",
     "what": "Middle of the pack events that come to us: weddings, birthday parties, company parties, real estate and community events.",
     "how": "Inbound. Leads come from social media, paid ads and referrals from past events. Trent quotes, books, staffs and runs them end to end.",
     "season": "Follows the San Diego event calendar, strongest April to October.",
     "examples": ["Michael Kang wedding", "Citreno corporate event", "Clark Sandcastle", "real estate events", "AI on the Lot", "Foodbeast"],
     "lever": "The events multiplier from ads and organic in the Dashboard runway."},
]


# Operating rules tab (Jordan, Sep 6 2026) -------------------------------------------
ONE_OFF_AUG = 67226.0  # Currency Cloud, Aug 5 2026, treated as a one off
OWNER_KEYS = ("harrison", "jordan")  # margins use plan pay for these, actuals for everyone else
RULE_TARGETS = {"product_pct": 0.18, "staff_pct": 0.14, "discretionary_cap": 2500.0}
OVERHEAD_GROUPS = [  # (group, lower case subs); checked in order before the fixed rule
    ("Travel", ["airlines", "car rental", "lodging", "taxi and rideshare", "rideshareandtaxis",
                "travel & transportation", "travel misc", "fuel and gas", "fuelandgas", "parking"]),
    ("Discretionary", ["restaurants", "supermarkets and grocery stores", "general merchandise", "retail",
                       "entertainment", "clothing", "alcohol and bars", "alcoholandbars", "fooddelivery", "reimbursement"]),
    ("Bill pay to individuals", ["bill pay"]),
    ("Professional services", ["professional services", "professionalservices"]),
    ("Marketing and ads", ["marketing & advertising", "advertising"]),
]
OVERHEAD_GROUP_NOTES = {
    "Travel": "Priced into each out of town quote at cost plus margin. Zero on local events.",
    "Discretionary": "Capped at $2,500 a month.",
    "Bill pay to individuals": "Needs a look. Event workers are event staff COGS. Recurring help is core team.",
    "Professional services": "",
    "Marketing and ads": "A flat monthly number. Edy is $3,250 once hired.",
}
OVERHEAD_FIXED_GROUP = "Software, insurance, ADP fees, storage"
OVERHEAD_OTHER_GROUP = "Everything else"
FIXED_GROUPS = {OVERHEAD_FIXED_GROUP, "Marketing and ads"}

# Peer benchmarks for the BLUF. Windansea values are computed; these are text with cites.
BENCHMARKS = [
    {"key": "gross", "metric": "Gross margin", "what": "Revenue minus coconuts, supplies and the people who work the event.",
     "agency": "50 to 60% [1]", "wholesale": "20 to 35% [2], 15% public distributors [3]"},
    {"key": "labor", "metric": "Labor", "what": "Event staff plus the salaried team.",
     "agency": "50 to 70% [4]", "wholesale": "not benchmarked"},
    {"key": "operating", "metric": "Operating margin", "what": "Revenue minus every cost including owner salaries, before income tax.",
     "agency": "13% public agencies [3], 20% or better well run [1]", "wholesale": "3% public distributors [3], 4 to 8% specialty [2]"},
    {"key": "after_tax", "metric": "After tax margin", "what": "Operating margin after a 35% income tax reserve.",
     "agency": "13% in 2025, 15% long run [5]", "wholesale": "1% public distributors [3]"},
    {"key": "marketing", "metric": "Marketing", "what": "Ads, PR and social.",
     "agency": "8 to 14% [1]", "wholesale": "not benchmarked"},
]
SOURCES = [
    ("Parakeeto agency benchmarks: delivery margin 50 to 60% of revenue, overhead 20 to 30% of gross income with sales and marketing 8 to 14%, target 20%+ profit.",
     "https://www.parakeeto.com/blog/agency-metrics/"),
    ("Wholesail, Wholesale Distributor Profit Margins: specialty and premium food distributors gross 20 to 35%, net 4 to 8%. Trade blog, figures not cited to a study.",
     "https://wholesailhub.com/blog/wholesale-distributor-profit-margins"),
    ("NYU Stern, Aswath Damodaran, Margins by Sector (US), January 2026: Food Wholesalers (13 firms) gross 15.4%, operating 2.8%, net 1.2%; Advertising (52 firms) gross 36.2%, operating 13.3%, net minus 0.3%.",
     "https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/margin.html"),
    ("Mercury, Marketing agency profit margins: labor 50 to 70% of agency revenue.",
     "https://mercury.com/blog/marketing-agency-profit-margins"),
    ("Promethean Research, How Profitable are Digital Agencies?, April 2026: 13% after tax net margin in 2025, 14% in 2024, about 15% long run since 2015.",
     "https://prometheanresearch.com/how-profitable-are-digital-agencies/"),
    ("Cucinovo, Prime Cost and Food Cost % by Restaurant Type: catering food cost 28 to 35%, catering prime cost (food plus labor) 55 to 62%, healthy prime cost 55 to 65%.",
     "https://cucinovo.com/blog/food-cost-percentage-by-restaurant-type"),
    ("Vellin, Typical Catering Food Cost Percentage Benchmarks: catering food cost 28 to 36%, well managed 25 to 30%, cocktail receptions 25 to 32%.",
     "https://vellinapp.com/blog/catering-food-cost-percentage"),
]
ASSUMPTIONS = [
    "Year estimate: actual Jan to Aug plus Sep to Dec tailed off August (minus Currency Cloud) at 70, 45, 20 and 15%.",
    "Owner pay at plan: Harrison $6,500, Jordan $2,700. Draws above plan are distributions, not cost. Trent, Juniper and Tim at actuals. Full plan team adds the Ops Manager and Edy and moves Trent to $9,125.",
    "Cost ratios held at summer levels across the year.",
    "Sales tax collected is in revenue and the remittance is a cost.",
    "No public source benchmarks luxury event food carts. Agency figures are digital and marketing agency surveys. Wholesale figures are public distributors and one uncited trade blog.",
]
OPEN_ITEMS = [
    "The golden rule says when the core team works events. Still open: how slow season prep time is used, and when Trent does branding.",
    "Is the ADP hourly line in event staff including Trent, Harrison and Juniper? No. ADP hourly is everyone on ADP except those three, who are pulled out by name into the core team.",
]
