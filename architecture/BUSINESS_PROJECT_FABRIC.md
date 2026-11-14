# NORYX7 — Business & Project Fabric

## Purpose

Structural plane for authorized project execution, service orchestration, opportunity analysis and transparent commission/revenue workflows.

## Project lifecycle

OPPORTUNITY → FEASIBILITY → RESEARCH → DESIGN → BUDGET → PLAN → AUTHORIZATION → EXECUTION → VERIFICATION → DELIVERY → ACCOUNTING → AUDIT

## Capabilities

- opportunity discovery and qualification;
- project decomposition and scheduling;
- budget and resource planning;
- supplier/service comparison;
- document preparation;
- procurement workflow support;
- travel/booking workflow support through authorized adapters;
- customer/service workflow management;
- revenue and commission calculation;
- reconciliation and reporting;
- fraud/anomaly detection;
- dispute/refund state management.

## Financial boundary

Customer funds, third-party funds and NORYX7/company revenue are separate ledgers and separate authorization domains.

A model may calculate or propose a transaction, but cannot directly move funds. Financial execution requires an explicit authorized adapter and applicable policy checks.

Commission calculation is deterministic from an auditable rule set:

TRANSACTION → ELIGIBILITY → RATE/RULE → COMMISSION CALCULATION → VALIDATION → ACCOUNTING ENTRY → AUDIT

Rules must identify the transaction, basis, rate/formula, currency, beneficiary, timestamp and policy/version used.

## Safety and compliance

Commercial operations require:
- explicit user consent where required;
- transparent fees/commission disclosure;
- applicable jurisdiction/compliance checks;
- identity and authorization verification;
- transaction limits;
- provenance and reconciliation;
- immutable audit records;
- fail-closed behavior on ambiguity or policy conflict.

No hidden monetization, unauthorized transaction or silent commission is permitted.

## Browser boundary

NORYX Browser v0.1 remains a standalone browser and does not embed this fabric. Future browser-mediated commercial/project actions use an explicit NORYX7/JARVIS adapter boundary.
