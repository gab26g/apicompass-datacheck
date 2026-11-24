# Dated cost comparison — 24 November 2026

AWS Cost Explorer was read through the signed-in administrator console. Settings: daily granularity, unblended cost, Charge type includes Usage, forecast off, services grouped consistently. The displayed date selection was 22–24 November 2026; this record compares only the two completed UTC days, **22 November 00:00–24:00** and **23 November 00:00–24:00**. The incomplete 24 November column is excluded.

| Observed AWS usage charge (USD, rounded by console) | Before: 22 November UTC | After: 23 November UTC |
| --- | ---: | ---: |
| All-account total | $0.76 | $1.26 |
| EC2 compute | $0.53 | $0.90 |
| VPC | $0.16 | $0.24 |
| EC2 Other | $0.07 | $0.11 |
| S3 | $0.00 | $0.01 |

Source screenshot: `cost-comparison-2026-11-24.jpg`. Before is the deployment day; after includes the operational acceptance/recovery period. These are equal-length windows and the same billing method, but workloads and host running hours differ. The account also has unrelated work and no activated project cost-allocation tag: **these are account-wide charges, not isolated APICompass costs or a causal optimization experiment**. Independently rounded rows need not sum exactly. Credits and tax are excluded by selecting Usage; a prior unfiltered net view rounded to zero and is not used as a resource-cost comparison. Current-period charges are estimated and subject to billing delay; they are not a settled invoice.

The student's Gemini API free tier was confirmed in chat on 24 November. Per-request provider charge is therefore recorded as **$0 under the confirmed free-tier arrangement**, not inferred from missing AWS bills; no provider invoice was inspected. Quotas and service availability still apply. No provider token-cost savings are claimed.

The budget remains US$25, with actual/forecast notifications; it is not a hard cap. The observed increase does not prove increased per-request cost or worse efficiency. APICompass-attributed costs, equal-workload comparisons and a full-month total remain limitations. Remove approved resources after assessment through a reviewed teardown; do not assume credits make the infrastructure costless.
