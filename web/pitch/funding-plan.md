# PASADHI: researched runway and funding proposal

Founder: **Mr. Supakrit Wapakpetch and AI Team**. Prepared 23 October 2026.
Status: M0 prototype. This is a planning proposal; no signed customers, committed funding, success probability or guaranteed profit is claimed.

## Recommended structure

**Raise $750,000 for 24 months of cash runway.** Deliver the first product and paid-pilot milestones within five months. These are different planning horizons.

- The older YC seed guide describes a 12–18 month path to the next fundable milestone: https://www.ycombinator.com/blog/how-to-raise-a-seed-round/
- Current Carta guidance recommends planning for 24–30 months as intervals between rounds have lengthened: https://carta.com/uk/en/learn/startups/fundraising/
- CRV also recommends 24–30 months for the seed-to-Series-A path: https://www.crv.com/content/when-to-raise-series-a

These are guidance ranges, not a universal standard or a measured median cash-runway duration. Time between financing rounds is not the time spent pitching. The 24-month proposal uses the lower end of the newer range. An **18-month scoped-down alternative of approximately $600,000** should be discussed if dilution or capital availability makes the main plan unsuitable.

## Cash basis for the proposed raise

| Component | Calculation | Amount |
|---|---|---:|
| Build and pilot phase | Months 1–5 × $34,000 | $170,000 |
| Lean repeatability phase | Months 6–24 × $24,000 | $456,000 |
| One-off deployment reserve | Planned allowance | $11,500 |
| Contingency | 15% of the proposed raise | $112,500 |
| **Total** | | **$750,000** |

This is a proposed cost envelope, not a set of verified salary or supplier quotations. No subscription receipts are assumed to extend base cash runway. Incremental paying-customer costs must be covered by collections; reconcile working-capital exposure and model cost allocations to actual cash expenses before hiring or signing pilots. The inherited per-node cost includes depreciation, which is not a cash outflow in the same period. Do not double count support or equipment in fixed and direct cost buckets.

## Use of funds: 24 months

| Use | Allocation | Share | Evidence bought |
|---|---:|---:|---|
| Engineering | $337,500 | 45% | Kernel, scheduler, two-host recovery; planned roles, not existing headcount |
| Pilot delivery + QA | $112,500 | 15% | Test hardware, rollout, workload benchmarks and recovery verification |
| Customer discovery + sales | $112,500 | 15% | Interviews, qualified pipeline and paid pilot conversion |
| Security + legal + operations | $75,000 | 10% | Data controls, contracts, IP and release operations |
| Contingency | $112,500 | 15% | 15% buffer; release only against milestone review |
| **Total** | **$750,000** | **100%** | |

The four operating categories sum to $637,500: $626,000 staged operations plus $11,500 one-off reserve. Contingency is a separate $112,500. Review cash and milestone evidence monthly; a missed gate triggers scope or hiring changes before reserve release.

## Milestones

- Months 1–5: target 15 buyer interviews, three design partners, two paid pilots and controlled two/ten-host correctness and recovery tests.
- Months 6–12: target ten paid sites; validate repeat use, retention, support burden and workload ROI.
- Months 13–18: target eighteen paid sites and verify the $24k/month lean operating model; review readiness for another round.
- Months 19–24: repeatable renewals and sales; twenty-five sites is an expansion scenario. Begin the next financing process while meaningful cash remains.

Targets are not pipeline or contracts. No probability of reaching them can be inferred from public market size alone.

## Market context

Synergy Research estimated global cloud infrastructure services revenue at **$500 billion over the trailing twelve months to Q2 2026**, and **$143.4 billion in Q2**: https://www.srgresearch.com/articles/q2-cloud-market-passes-143-billion-highest-growth-rate-in-eight-years

NVIDIA's equity market-cap snapshot was **$5.124 trillion** in the source accessed 23 October 2026: https://companiesmarketcap.com/nvidia/marketcap/
This moving public-comparable equity value is not PASADHI's TAM or proposed valuation. The reachable buyer segment needs a qualified site list and discovery evidence.

Eighteen sites × 50 active paying nodes × $44.28/month × 12 gives **$478,224 annualized recurring revenue**. This is about **0.0000956%** of the broad $500B spending context; the ratio is illustrative, not a capture probability or a validated market-share forecast.

## Conditional operating-profit scenarios

Assumptions: $44.28 price per active paying node/month; $16.37 inherited-model direct cost per node/month; 50 paying nodes/site; $24,000 monthly fixed overhead from month six. The lean fixed-cost envelope is planned, not automatic. Figures below are steady-state scenarios that may be evaluated at the end of the runway; they are not guaranteed month-24 outcomes.

| Scenario | Sites | Paying nodes | MRR | Direct cost/month | Operating profit/month |
|---|---:|---:|---:|---:|---:|
| Downside | 5 | 250 | $11,070.00 | $4,092.50 | $-17,022.50 |
| Base | 10 | 500 | $22,140.00 | $8,185.00 | $-10,045.00 |
| Profit gate | 18 | 900 | $39,852.00 | $14,733.00 | $1,119.00 |
| Expansion | 25 | 1250 | $55,350.00 | $20,462.50 | $10,887.50 |

Formula: paying nodes × ($44.28 − $16.37) − $24,000. Break-even is **860 active paying nodes**, rounded to **18 sites**. At 900 nodes, the initial $34k fixed-cost envelope would still lose $8,881/month; maintaining the lean cost phase is essential. The ten-site base case remains loss-making and requires lower costs, stronger sales or additional capital. The twenty-five-site scenario gives $10,887.50 operating profit/month before taxes, financing and exceptional costs.

Pilot fees are credited toward year one and cannot also be counted as recurring revenue. Revenue recognition and collection timing require a separate cash-flow review. No emissions-saving claim is made without energy and embodied-carbon measurements.

## Financing terms for discussion

Illustrative post-money valuation-cap SAFE sensitivity for a $750,000 raise:

| Cap | Raise | Simplified ownership sold |
|---|---:|---:|
| $3.75M | $750,000 | 20.00% |
| $5.0M | $750,000 | 15.00% |
| $7.5M | $750,000 | 10.00% |

The $5M cap is a negotiation illustration, not an independent company valuation. The simplified relation is investment / post-money cap; option pools, other SAFEs and later priced financing can change final ownership. Jurisdiction, corporate structure and conversion mechanics need review before signing. Source: https://www.ycombinator.com/safe

YC's own accelerator standard deal is a separate $500k package: $125k for 7% plus $375k on an uncapped MFN SAFE. This proposal is not the YC standard deal and implies no YC admission or endorsement: https://www.ycombinator.com/deal/

Local source prices are converted at 1 USD = 33.65 original local currency units, Bank of Thailand reference dated 22 October 2026. Pricing/cost sources: docs/SALES_KIT.th.md and paper/SOLUTION_FULL.md. Inputs and calculations: financial-plan.json.
