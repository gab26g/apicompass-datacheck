# DataCheck v0.2 data contract

All content is invented. Each CSV has 60 data rows; the header is excluded from row numbering. Dataset versions are inventory-v2, shipments-v2 and equipment-v2. Rule versions use the dataset ID followed by -rules-v2.

| Dataset | ID | Integer | Inclusive bounds | Category and allowed values |
| --- | --- | --- | --- | --- |
| inventory | sku | quantity | 0 or more | status: active, archived |
| shipments | shipment_id | weight_kg | 1 to 1000 | status: pending, in_transit, delivered |
| equipment | asset_id | service_hours | 0 to 100000 | condition: operational, maintenance, retired |

Weights are whole kilograms for this demonstration. Fractional weights deliberately fail the integer rule; this is not a universal shipment business rule.

Trim whitespace for validation and preserve original observed values. IDs remain case sensitive. Categories ignore case. All three columns are required. Missing values skip further checks on that field. Type failures skip range checks. Report every row sharing a repeated, nonempty ID. Blank IDs are missing rather than duplicates. Numeric summaries include every parseable integer, including out-of-range values, and explicitly count excluded missing/type-invalid values.

Only fixed dataset IDs are accepted. Unknown IDs return 404. Malformed/unavailable files return 503, not an empty clean report. Incorrect columns and wrong-width CSV records are source errors. Each source is bounded to 1000 rows and 512 characters per cell.

Issues default to at most 20 findings, with a limit from 1 through 100. issue_count and affected_row_count are always totals across the whole source. returned_issue_count and truncated describe the sample. There is no pagination in this version. Never present a truncated sample as every finding.

## Golden results, specified independently of the validator

The first eight inventory rows retain the original demonstration defects. Rows 9-60 in all fixtures are valid, unique IDs. These expected findings are written directly into tests, not derived from the implementation.

| Dataset | Rows with findings | Expected findings |
| --- | --- | --- |
| inventory | 1, 2, 3, 4, 5, 6 | sku duplicate on 1/2; quantity range on 3; quantity type on 4; sku required on 5; status category on 6. Six issues across six rows. |
| shipments | 1, 2, 3, 4, 5, 6, 7 | shipment_id duplicate on 1/2; weight_kg range on 3/7; weight_kg type on 4; shipment_id required on 5; status category on 6. Seven issues across seven rows. |
| equipment | 1, 2, 3, 4, 5, 6, 7 | asset_id duplicate on 1/2; service_hours range on 3/7; service_hours type on 4; asset_id required on 5; condition category on 6. Seven issues across seven rows. |

Each numeric summary has 59 parsed values and one excluded value. Inventory min/max: -3/60. Shipments: 0/1001. Equipment: -1/100001. Each ID column has one missing value. Every other missing count is zero.
