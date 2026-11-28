# NORYX7 — W12 Financial, Ledger, Governance, Marketplace and Impact Lifecycle Audit

**Review date:** 2026-11-27  
**Reviewed branch:** `architecture/system-wide-closure-mirror-world-2026-11-21`  
**Source-tree HEAD:** `1bc030726047790c5c9f3622b34d980bff1aedfd`  
**Mode:** architecture-only, bounded source reconciliation. No runtime, tests, dependencies, workflows, deployment, frozen baseline or production configuration changed.

## 1. Purpose and assurance vocabulary

This pass advances W12 while tracing its dependencies into W01–W11. It distinguishes:

- **source behavior**: behavior directly visible in inspected repository files;
- **declared architecture**: a design target or contract documented in architecture files;
- **external dependency**: a bank, payment processor, custodian, marketplace, auditor, registry or public authority outside the inspected source tree;
- **operational guarantee**: a property requiring deployed controls, durable state, external receipts and recovery evidence;
- **verified outcome**: a result supported by reproducible, independently reviewable evidence.

A payment-provider response is not automatically settlement. Settlement is not a ledger commit. A ledger entry is not proof of delivery. A community vote is not legal authority to move funds. A simulation or estimate is not realized environmental impact.

## 2. Bounded source reconciliation

### 2.1 What exists in the inspected source

The recursive source-tree inventory at the stated HEAD was filtered for payment, financial, economy, impact, marketplace, governance, ledger, contribution, community, treasury, settlement, donation, reward and wallet path names. It returned architecture documents, but no dedicated executable financial/payment/ledger/marketplace/governance/impact service path under those names.

Directly inspected source includes:

- `ecosystem/boundaries.py`: a generic four-front `IntentEnvelope` with front, operation, payload digest and principal label. If omitted, `principal_id` defaults to the front name. This is a convenience label, not an authenticated account or legal identity.
- `ecosystem/runtime_dispatch.py`: requires an injected principal authorizer and topology check before calling a handler. A successful receipt uses the Python return-value type as evidence; it is not a provider settlement receipt, bank statement, ledger posting or proof of an external effect.
- `ecosystem/closure_contract.py`: validates structural completeness of four front declarations. It does not establish that a financial service, accounting control or impact verifier is deployed.
- `architecture/BUSINESS_PROJECT_FABRIC.md`, `architecture/NORYX7_AGENT_EVIDENCE_MIRROR_WORLD_AND_GLOBAL_IMPACT_RECONCILIATION.md`, `architecture/NORYX7_DOMAIN_CALIBRATION_SPECIALIST_QUALIFICATION_CYBER_RANGE_AND_PUBLIC_IMPACT_RECONCILIATION.md`, and prior W12 reconciliation documents: these describe project, commission, accounting, funding separation and public-impact concepts at architecture level.

This is a bounded statement about the inspected tree and named source paths, not proof that no external provider, uninspected branch or separately operated service exists. The present review does not claim that NORYX7 can currently accept, hold, transfer, refund or settle real money.

### 2.2 Architectural consequence

W12 cannot be closed by adding a generic `payment_status`, a wallet balance, a success boolean or a provider callback to an existing dispatch receipt. It needs independently owned financial, governance and impact lifecycles, linked by stable references and evidence.

## 3. Canonical W12 bounded contexts and ownership

The architecture should define the following separate bounded contexts. Their records may reference one another but must not share a single mutable status field.

1. **Contribution and funding intent** — who proposes to contribute, amount/currency or non-cash resource, purpose, restrictions, consent, campaign and expiry.
2. **Payment orchestration** — payment method token/reference, provider selection, authorization, attempt, idempotency, timeout and reconciliation. NORYX7 should not store raw card credentials.
3. **Settlement and custody** — external processor/bank/custodian confirmation, value date, fees, reversals, reserve and withdrawal constraints.
4. **Double-entry ledger** — immutable journal postings, account ownership, currency, debit/credit balancing, period close, correction and audit.
5. **Treasury and allocation** — available, reserved, restricted, committed and encumbered balances; budget authority; liquidity and solvency limits.
6. **Marketplace and delivery** — listing, order, escrow or safeguarded funds where lawful, delivery evidence, dispute, refund and seller payout.
7. **Internal credits and rewards** — non-cash participation units, eligibility, issuance, redemption, expiry and transfer restrictions. These must not silently become deposits, e-money, investment products or a claim on cash.
8. **Governance** — proposal, deliberation, eligibility snapshot, voting, quorum, conflict disclosure, decision, appeal and execution authorization.
9. **Impact accounting** — baseline, counterfactual, activity evidence, measured output/outcome, uncertainty, additionality, leakage, durability and independent review.
10. **Compliance and safeguarding** — jurisdiction-specific onboarding, sanctions/AML obligations where applicable, fraud controls, privacy, consumer protection, tax/accounting, safeguarding and reporting. Applicability must be determined by qualified counsel and regulated partners, not inferred by the software.

No single service should be able to create a contribution, approve its own withdrawal, post the ledger entry, attest the impact and close its own dispute.

## 4. Financial operation state machines

### 4.1 Contribution and payment

Recommended lifecycle:

`DRAFT → SUBMITTED → ELIGIBILITY_PENDING → APPROVED/REJECTED → PAYMENT_PENDING → AUTHORIZED → CAPTURE_PENDING → SETTLED/FAILED/UNKNOWN`

Additional branches:

- `CANCELLED` only before the relevant irreversible provider boundary;
- `REQUIRES_ACTION` for step-up authentication or user confirmation;
- `PARTIALLY_SETTLED` where provider semantics support partial capture;
- `REVERSED`, `REFUND_PENDING`, `PARTIALLY_REFUNDED`, `REFUNDED`;
- `DISPUTED` / `CHARGEBACK_PENDING` / `CHARGEBACK_WON` / `CHARGEBACK_LOST`;
- `UNKNOWN` and `RECONCILIATION_REQUIRED` for timeout or ambiguous post-request outcomes.

Rules:

- A client request creates an intent, not money movement.
- Authorization reserves or approves a payment instrument according to provider semantics; it does not necessarily transfer funds.
- Capture request acceptance is not settlement.
- Settlement requires a provider/bank record whose issuer, transaction reference, amount, currency, status and effective time are authenticated and reconciled.
- Timeouts after a provider request must not trigger blind duplicate submission. Query by stable provider idempotency key and reconcile before retry.
- Refunds and chargebacks are new linked financial events, never destructive edits to the original payment.
- Amounts use integer minor units or an explicitly specified decimal representation; currency is mandatory. Never use binary floating point for money.
- Fees, FX conversion, rounding, tax, value date and provider gross/net amounts are explicit fields and separately reconciled.
- A successful HTTP response or dispatch handler return must never be mapped directly to `SETTLED`.

### 4.2 Canonical financial identifiers and receipts

Minimum distinct identifiers:

- `contribution_id`, `payment_intent_id`, `payment_attempt_id`;
- `provider_id`, `provider_transaction_id`, `provider_idempotency_key`;
- `settlement_id`, `refund_id`, `chargeback_id`;
- `ledger_batch_id`, `journal_entry_id`, `account_id`;
- `allocation_id`, `order_id`, `payout_id`, `dispute_id`.

Proposed typed records (design only):

- `ContributionIntent`: contributor principal reference, amount/currency or resource kind, purpose, beneficiary/campaign, restrictions, consent version, jurisdiction, expiry and source.
- `PaymentAttempt`: attempt ID, provider, idempotency key, request digest, amount/currency, timestamps, outcome certainty and retry classification.
- `ProviderTransactionReceipt`: authenticated provider issuer, provider transaction ID, exact operation, amount/currency, fees, status, effective/value time, raw evidence digest, signature or authenticated retrieval reference.
- `SettlementReceipt`: bank/processor source, settlement batch, gross/net, fees, currency, value date, matched payment IDs and reconciliation status.
- `LedgerPostingReceipt`: immutable journal batch ID, debit/credit lines, account and currency, balanced total, posting period, source event IDs and ledger sequence.
- `RefundReceipt` / `ChargebackRecord`: original transaction reference, amount, reason code, provider evidence, lifecycle and final outcome.
- `ReconciliationRecord`: expected versus observed transactions, unmatched items, variance, owner, resolution evidence and close approval.

All receipts need schema/version, issuer identity, audience, tenant or legal entity, timestamps, correlation, source evidence, digest, authenticity method, lifecycle and retention class. A digest alone is not an issuer-authenticated receipt.

## 5. Double-entry ledger, treasury and accounting invariants

The ledger is the accounting record, not the payment processor and not a user-facing wallet cache.

Required invariants:

1. Every posted journal batch balances per currency: total debits equal total credits.
2. Posted entries are immutable. Corrections use reversing and replacement entries with explicit links and approval.
3. Every entry references a source event and an authenticated posting authority.
4. Idempotency prevents duplicate posting of the same settled provider event.
5. Pending authorization, captured funds, unsettled funds, settled funds, restricted funds, reserves, fees, refunds and liabilities use distinct accounts and semantics.
6. User-visible balance is derived from ledger entries and account policy; cached balance is never authoritative.
7. Each legal entity, fund, campaign and currency is segregated in account scope; no cross-tenant or cross-campaign netting without explicit lawful authority.
8. Treasury allocation cannot exceed available unencumbered funds; reservations and commitments reduce available balance before external execution.
9. Period close, reconciliation, write-off, FX revaluation and financial statement generation have explicit operator roles and dual control.
10. Restore and disaster recovery must preserve journal sequence, immutable history, idempotency keys and reconciled external checkpoints.

A contribution restricted to environmental remediation cannot be silently diverted to general operating expenses. A community vote cannot override legal restrictions, donor terms, insolvency protections or regulated custody requirements.

## 6. Marketplace, producer network and delivery proof

Marketplace order lifecycle must be distinct from payment and settlement:

`LISTED → RESERVED → ORDER_ACCEPTED → FULFILMENT_PENDING → DELIVERY_EVIDENCE_PENDING → DELIVERED / DISPUTED / CANCELLED`

Seller payout is allowed only when the applicable payment, delivery, consumer-protection and dispute policy permits it. A seller's self-declared completion is not independent delivery evidence for high-risk or contested orders.

For direct-producer/community supply networks, model:

- producer and organization identity, authorization and relevant qualification;
- product/service specification, quantity, unit, provenance and batch;
- availability, reservation, expiry and substitution;
- order terms, tax/price disclosure and delivery route;
- delivery confirmation by recipient or trusted carrier;
- quality, spoilage, safety, recall and dispute paths;
- settlement and payout references;
- accessibility and offline workflows without weakening fraud controls.

Escrow, safeguarding, stored value, marketplace custody and seller payout can trigger regulated obligations depending on jurisdiction and operating model. The architecture must use a licensed partner or obtain qualified legal review before any real-money custody or transfer is enabled.

## 7. Internal credits, contributor rewards and participation

NORYX7 may need a way to recognize verified work without turning every contribution into a financial product. Separate at least:

- **reputation**: non-transferable record of reviewed contribution quality;
- **participation credits**: non-cash, non-interest-bearing, non-redeemable units for access or coordination, if lawful;
- **expense reimbursement**: actual documented expense under an approved policy;
- **cash compensation**: legally accounted payment subject to contracts, tax and labor rules;
- **ownership/equity or profit share**: separate legal instrument and governance, never implied by a points balance;
- **donation/contribution**: voluntary transfer with clear restrictions and no implied return.

Each reward program must specify issuer, purpose, eligibility, earning evidence, caps, expiry, reversal for fraud, appeal, transferability, redemption, tax treatment and whether any cash claim exists. No credit may be presented as euros, guaranteed income, investment return or a deposit unless the legal structure explicitly supports that status.

## 8. Governance lifecycle and separation of powers

Recommended proposal lifecycle:

`DRAFT → SPONSORSHIP → ELIGIBILITY_CHECK → DISCUSSION → CONFLICT_REVIEW → VOTING → QUORUM_CHECK → DECIDED → APPEAL_WINDOW → EXECUTION_AUTHORIZED → EXECUTED / EXPIRED / REVOKED`

A decision record should bind:

- proposal ID/version and exact immutable text/diff;
- scope: local group, project, fund, legal entity or network;
- eligible voter snapshot and eligibility rule version;
- voter credential/one-person-one-vote or explicitly weighted rule;
- ballot privacy and verifiability model;
- quorum, threshold, abstention and tie policy;
- conflict-of-interest declarations and recusals;
- deliberation evidence, dissent and minority report;
- tally method, independent audit and reproducibility;
- appeal window, grounds, reviewer and final disposition;
- execution authority, budget cap and expiry.

Governance is not one global vote for all domains. A local community may decide local priorities within its delegated budget; it cannot unilaterally change another legal entity's funds, waive a participant's rights, authorize regulated activity or overwrite a donor restriction.

Separate powers:

- proposal sponsor;
- voter/representative;
- independent eligibility/tally verifier;
- budget owner;
- payment approver;
- payment operator;
- ledger poster;
- impact verifier;
- auditor/appeal reviewer.

For material disbursements, require dual control and separation between proposer, approver and executor. Emergency powers must be narrow, time-limited, logged and appealable.

## 9. Environmental and social impact accounting

Impact must be a measurable outcome, not a popularity metric, activity counter or model-generated estimate.

Each claim should distinguish:

- **input**: money, volunteer hours, equipment or material;
- **activity**: cleanup, collection, repair, planting, training or delivery;
- **output**: kilograms sorted, area treated, units repaired, households served;
- **outcome**: independently measured change in pollution exposure, waste leakage, emissions, biodiversity, access or wellbeing;
- **impact**: attributable change relative to a credible baseline/counterfactual.

Required `ImpactMeasurementReceipt` fields:

- impact claim ID and metric definition/version;
- geography, time window, unit and boundary;
- baseline source and baseline date;
- counterfactual method and assumptions;
- activity and cost references;
- measurement instrument, calibration and sampling method;
- original observations and transformation lineage;
- uncertainty interval and missing-data treatment;
- additionality, leakage, rebound and durability assessment;
- double-counting check and ownership of claim;
- verifier identity, independence/conflicts and review scope;
- status: proposed, estimated, measured, independently verified, disputed, expired or withdrawn.

Rules:

- Simulated carbon savings or forecasted health benefits cannot be booked as realized impact.
- Avoid double-counting the same waste, tree, emission reduction or beneficiary across projects.
- Record negative externalities and displacement, not only positive outputs.
- Volunteer hours and euros spent are inputs, not proof of environmental outcome.
- Publish methodology, uncertainty and correction history; preserve dissent and failed interventions.
- Disbursement tied to outcomes requires a pre-agreed metric, independent measurement and dispute/appeal process. Do not let the beneficiary or payout approver certify its own impact.

## 10. Cross-stream handoffs and failure semantics

| Handoff | Required proof | Forbidden shortcut |
|---|---|---|
| W01 identity → W12 contributor/account | Issuer-authenticated principal and legal/account scope | UI label or front name as identity |
| W02 runtime → payment provider | Authorized immutable operation and idempotency key | Agent plan directly moves money |
| W03 memory/state → ledger | Durable append, sequence and recovery proof | In-memory balance or cache as ledger |
| W04 agent → finance workflow | Qualified role plus scoped authorization | Skill registration as payment authority |
| W05 provider routing → settlement | Provider-specific authenticated transaction receipt | Provider selection or HTTP 200 as settlement |
| W06 evidence → impact | Claim-to-source lineage and independent review | Model confidence or non-empty evidence as proof |
| W07 simulation → project estimate | Validity scope, calibration and uncertainty | Simulated outcome as realized impact |
| W08 surface/offline → financial action | Fresh authenticated session, replay protection and user confirmation | Offline queue ACK as transfer confirmation |
| W09 security/audit → finance | Signed, durable, tamper-evident event and key custody | Hash-only record as trusted audit |
| W10 specialist → regulated decision | Verified qualification, jurisdiction and scope | Keyword routing as professional authorization |
| W11 global operations → treasury | Fenced reservation, region/legal entity scope and reconciliation | Capacity/replica metadata as custody |
| W12 governance → disbursement | Final decision, budget reservation and dual authorization | Vote tally as provider authorization |

Failure rules:

- **Before provider submission**: safe cancellation if no external effect can have occurred.
- **After submission, before authenticated outcome**: `UNKNOWN`; reconcile by provider key, do not blindly retry.
- **After provider settlement, before ledger post**: settlement remains real; post/reconcile ledger from provider evidence, do not resubmit payment.
- **After ledger post, before user acknowledgement**: do not post again; query ledger by source event/idempotency key.
- **After payout, before delivery/dispute closure**: retain separate payout and fulfilment states.
- **After impact verifier failure**: mark claim disputed/withheld; do not rewrite the financial settlement as though payment never happened.
- **After governance appeal**: freeze only the affected execution scope where legally and operationally possible; preserve the original decision and appeal chain.

Compensation is a new authorized financial event, not rollback of external reality.

## 11. Privacy, security, fraud and legal perimeter

The architecture must minimize sensitive financial and identity data:

- store provider tokens/references, not raw card data or authentication secrets;
- separate identity vault, payment metadata, ledger and public impact data;
- enforce purpose limitation, consent, access logging, retention and deletion/tombstone semantics subject to accounting retention obligations;
- avoid exposing contributor identities, ballot choices, health or beneficiary data in public impact reports;
- use risk-based velocity limits, duplicate detection, account takeover controls, collusion and fake-project detection, supplier verification and human review;
- define incident freeze, evidence preservation, appeal, recovery and regulator/customer notification owners;
- define jurisdiction matrix for payments, donations, tax, consumer rights, labor, privacy, sanctions/AML, fundraising, stored value and marketplace obligations;
- use qualified counsel and licensed regulated partners before real-money custody, transfer, escrow, e-money, investment, donation solicitation or cross-border payout.

This document is an engineering architecture audit, not legal, tax, accounting or investment advice.

## 12. Proposed canonical W12 records and ownership

| Record | Authoritative owner | Must not be treated as |
|---|---|---|
| ContributionIntent | Contribution service | settled payment |
| PaymentAttempt | Payment orchestrator | provider settlement |
| ProviderTransactionReceipt | Authenticated provider adapter | ledger posting |
| SettlementReceipt | Bank/processor reconciliation | user balance |
| LedgerPostingReceipt | Ledger service | impact verification |
| TreasuryReservation | Treasury/budget authority | payment authorization |
| MarketplaceOrder | Marketplace service | payout receipt |
| DeliveryEvidence | Independent delivery source/reviewer | seller payout by itself |
| RewardAccount/RewardEntry | Reward program owner | cash deposit or equity |
| GovernanceProposal/Decision | Governance service and verifier | external payment authority |
| ImpactMeasurementReceipt | Independent measurement/verifier | money movement |
| FinancialReconciliationRecord | Independent reconciliation owner | self-attested success |

These are proposed schema names and responsibilities only. They do not establish an accepted ADR, a deployed service or a legal entity.

## 13. New bounded closure gaps

- `GAP-W12-PAYMENT-SETTLEMENT-AND-UNKNOWN-OUTCOME`: provider authorization/capture/settlement/refund/chargeback states, authenticated receipts, idempotency and unknown-outcome reconciliation.
- `GAP-W12-DOUBLE-ENTRY-LEDGER-AND-IMMUTABLE-CORRECTIONS`: balanced per-currency journal, immutable postings, reversals, source-event idempotency, period close and audit.
- `GAP-W12-TREASURY-SEGREGATION-AND-RESERVATION`: legal-entity/fund segregation, restricted balances, reservations, dual control, liquidity and restore evidence.
- `GAP-W12-MARKETPLACE-FULFILMENT-AND-PAYOUT-PROOF`: order/delivery/dispute/payout lifecycles, producer provenance and lawful custody model.
- `GAP-W12-INTERNAL-CREDIT-AND-CASH-CLAIM-CLASSIFICATION`: non-cash credits, rewards, reimbursement, compensation, donation and ownership kept distinct.
- `GAP-W12-GOVERNANCE-ELIGIBILITY-QUORUM-AND-APPEAL`: immutable proposals, voter snapshot, privacy, conflicts, quorum, tally, appeal and execution separation.
- `GAP-W12-IMPACT-BASELINE-COUNTERFACTUAL-AND-ADDITIONALITY`: independently verified outcomes, baseline/counterfactual, uncertainty, leakage, durability and double-counting.
- `GAP-W12-FINANCIAL-RECONCILIATION-AND-DUAL-CONTROL`: independent provider/bank-to-ledger matching, variance handling and separation of duties.
- `GAP-W12-JURISDICTION-AND-REGULATED-PARTNER-BOUNDARY`: jurisdiction-specific legal classification, licensed custody/payment partner and release gate.
- `GAP-W12-FINANCIAL-PRIVACY-AND-SAFEGUARDING`: data minimization, identity/ballot/beneficiary separation, retention, fraud controls and incident response.

## 14. Decision status and closure gates

This audit supplies source evidence and proposed contracts to existing OPEN decisions, including the W12-related B43/B83/B84/B101 family and cross-cutting operation, evidence, identity, key custody and global-placement decisions. It does not accept an ADR or create implementation authority.

W12 remains **PARTIAL** until its legal operating model, service ownership, schemas, state machines, external partner contracts, ledger invariants, governance powers, impact methodology, recovery and evidence requirements are accepted. W01–W11 also remain **PARTIAL**.

Before implementation, require explicit owner review and a conflict matrix. Before real-money pilot, require legal classification, regulated partner, sandbox-to-production separation, reconciliation, dual control, incident/chargeback handling and independent accounting review. Before public impact claims, require measurement protocol and independent verifier. Only after all architecture workstreams close should the project proceed to integration and the comprehensive test/validation phase.

## 15. Scope boundary

No source implementation, tests, workflows, dependencies, deployment, baseline or PR merge was changed by this audit. The contracts and records above are proposals for architecture closure, not working financial capabilities.
