# Assumptions and limitations

- The dataset is synthetic; recommendations demonstrate analytical method.
- Timestamps are treated as UTC after removing the source ` UTC` suffix where required.
- May 2024 is incomplete. Default trend comparisons use complete months.
- Net Sales excludes Cancelled and Returned item value; Gross Sales remains a separate demand KPI.
- Order status is treated as a snapshot classification, not a full event-sourced history.
- Observed Return Rate uses only Complete and Returned items as eligible outcomes.
- Invalid shipment-before-item-created records are excluded from lead-time statistics.
- Session-level identity may be recovered when some events are anonymous and later events identify the session.
- User PII and event IP addresses are excluded from analytics exports.
- No marketing cost exists, so ROAS/CAC cannot be calculated.
- No promotion/discount field exists, so pricing elasticity cannot be estimated.
- No product lines are linked to cart events, so product-level cart abandonment is unsupported.
- No experiment assignment/exposure data exists, so historical A/B effects cannot be estimated.
- No external delivery benchmark is included.


## Session reconstruction

- Sessions are derived from `events.csv` using `session_id`; no original session table exists.
- Customer, browser, and traffic source are expected to be stable within a session and are enforced by blocking tests.
- Anonymous sessions remain in session/funnel analysis but cannot join to customer demographics or RFM segments.
