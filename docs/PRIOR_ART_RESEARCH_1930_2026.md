# NORYX7 — Initial Prior-Art Scan (1930–2026)

Status: initial, non-exhaustive landscape scan on 13 November 2026. This is technical research, not a patentability, infringement or freedom-to-operate opinion.

## 1. Scope and method

The search covers defensive cyber architecture, threat prediction, attack graphs, deception, moving-target defense, distributed trust, key management and autonomous investigation. Searches should include claims and descriptions, not titles alone, and should be repeated with IPC/CPC classifications, synonyms, inventors, assignees, citations, patent families and translations.

Primary search systems:
- WIPO PATENTSCOPE: international PCT documents and participating national/regional collections.
- EPO Espacenet, Global Dossier and Common Citation Document: worldwide patent publications, family and prosecution/citation context.
- USPTO Patent Public Search and Patent Center: U.S. grants and published applications, prosecution and legal-status records.
- Google Patents: broad multilingual discovery across many patent offices; its coverage is not guaranteed complete.
- National registers and non-patent literature: IEEE, ACM, USENIX, NIST, MITRE, standards bodies and historical technical reports.

Coverage caveat: searchable patent archives do not guarantee complete worldwide coverage. Some early documents are image-only or poorly OCR'd; unpublished applications and classified material are not publicly searchable. A search of published material cannot establish that no one has developed or patented a concept.

## 2. Initial patent examples requiring claim-level review

| Publication | Area | Initial technical relevance |
|---|---|---|
| US9215249B2 | Distributed trust computing and key management | Remote trusted execution, attestation and compartmentalized key/data handling |
| US10623442B2 | Multi-factor deception and honeytokens | Correlated decoy credential use to distinguish malicious access |
| US10992708B1 | Live deployment of deception systems | Creating a decoy clone in response to an imminent or active attack |
| US11902320B2 | Moving target defense | Dynamic changes to network addressing to make target discovery and sustained attack harder |
| US20220053022A1 | Automated preemptive polymorphic deception | Dynamic honeypot traps based on observed anomalous traffic |
| US20250036753A1 | Cyberattack prediction and response | Directed graph model predicting subsequent attack states and response actions |
| US20260006077A1 | Generative adversarial decoy honeypots | Generating and evolving decoys that imitate network device configurations |
| US20260030346A1 | Autonomous cyber investigation using graphs | Iterative enrichment and expansion of an investigation subgraph |

These examples show that several desired building blocks already exist in patent literature. They do not establish that every implementation is in force in every jurisdiction, that the claims are valid, or that NORYX7 infringes or avoids them. Verify each family, independent claims, priority chain, prosecution history, jurisdictions and legal status before relying on it.

## 3. Historical technical lineage

- 1930s–1960s: mathematical cryptanalysis, information theory, secure communications and early computer reliability research form important foundations. This period is broader than modern cybersecurity patents; many relevant developments were military, classified, academic or not computer-security inventions.
- 1970s: formal computer security, access control, security labels, cryptographic key management, public-key cryptography and early network security.
- 1980s: personal computing and network growth bring viruses, worms, intrusion detection, firewalls and secure software concerns.
- 1990s: commercial internet, PKI, SSL/TLS, VPNs, RBAC, vulnerability databases and security operations mature.
- 2000s: botnets, cloud, large-scale breaches, threat intelligence, DDoS defense and supply-chain risks expand.
- 2010s: zero trust, cloud-native identity, container isolation, deception, moving-target defense, software-defined security, secure enclaves and automated threat intelligence.
- 2020–2026: cyber-resiliency engineering, continuous threat-informed defense, graph-based investigations, autonomous response, confidential computing, post-quantum migration and AI-assisted deception receive substantial attention.

This timeline is a synthesis of public historical references, not a complete chronology of every patent or invention.

## 4. What appears differentiated for NORYX7—and what does not

Not novel by itself:
- zero trust or least privilege;
- anomaly detection or behavioral profiling;
- honeypots and honeytokens;
- moving-target defense;
- attack graphs and predictive attack sequencing;
- distributed key custody or threshold approvals;
- multi-agent orchestration;
- AI-assisted incident response.

Potentially differentiating engineering combinations to investigate:
1. A continuously reconciled, evidence-provenance graph spanning identity, data, workloads, network, storage, keys and financial/non-financial transactions.
2. A bounded partially observable attacker-defender game that plans before an alert, but only acts through independently authorized and reversible controls.
3. A falsification-first hypothesis engine that maintains competing benign and malicious explanations and records why each is accepted or rejected.
4. A cryptographic authorization protocol that binds exact transaction semantics, risk metadata, evidence, expiry and idempotency across independent execution domains.
5. A compartmentalized global data plane where compromise of one tenant, node, region or operator cannot expose unrelated keys and plaintext.
6. A safe-mode and recovery design that continues critical functions under partial compromise without silently weakening authorization.

These are research hypotheses, not novelty conclusions. A patentable invention must be reduced to a specific, enabled technical implementation with a defensible inventive step over the prior art. A broad statement that known technologies are combined is usually insufficient by itself.

## 5. Next research actions

1. Expand each area into IPC/CPC classification searches and multilingual synonym sets.
2. Search backward and forward citations from the listed families.
3. De-duplicate patent families and record earliest priority dates.
4. Read independent claims and prosecution amendments; separate claims from descriptive examples.
5. Map each relevant claim limitation to NORYX7 components and intended deployment.
6. Search non-patent literature and product documentation for prior disclosure.
7. Maintain a claim chart and a dated evidence register.
8. Have a qualified patent attorney perform freedom-to-operate and patentability review before commercial deployment or publication.

## 6. Public discovery sources

- WIPO PATENTSCOPE: https://patentscope.wipo.int/
- EPO Espacenet: https://worldwide.espacenet.com/
- EPO Global Dossier and Common Citation Document: https://www.epo.org/
- USPTO Patent Public Search: https://ppubs.uspto.gov/pubwebapp/
- Google Patents: https://patents.google.com/
