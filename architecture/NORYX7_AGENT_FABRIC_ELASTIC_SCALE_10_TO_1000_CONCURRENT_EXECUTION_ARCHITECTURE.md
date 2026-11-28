# NORYX7 — Agent Fabric elastico 10–1.000: scheduling, concorrenza, delega e capacità distribuita

**Stato:** PROPOSTA ARCHITETTURALE — non implementata, non approvata come ADR, non verificata operativamente  
**Data:** 2026-11-28  
**Ambito:** W01/W02/W03/W04/W05/W06/W09/W10/W11; interfacce con W07/W08/W12  
**Vincolo:** architecture-only. Nessuna modifica a runtime, sorgenti, test, dipendenze, workflow, deployment o baseline.

## 1. Obiettivo e definizioni

NORYX7 deve poter crescere da un piccolo pool di agenti a una flotta logica fino a 1.000 agenti, distribuendo lavoro indipendente e verificabile senza trasformare il numero di agenti registrati in una promessa di concorrenza fisica, capacità GPU, throughput o disponibilità.

Il termine agente è sovraccarico e deve essere disambiguato in ogni contratto e metrica:

1. **Agent identity:** identità logica, chiave, issuer, stato di fiducia e revoca.
2. **Agent profile:** ruolo, competenze dichiarate, qualifiche provate, modello/runtime, provider, strumenti, domini e limiti.
3. **Agent instance:** processo/worker vivo che può ricevere lease e heartbeat.
4. **Execution slot:** unità di capacità ammessa a eseguire un tentativo in un intervallo.
5. **Model invocation:** richiesta effettiva a un modello/provider; più agenti logici possono condividere un modello e un agente può effettuare più invocazioni.
6. **Task/attempt:** lavoro logico e singolo tentativo con identità, budget, lease e risultato separati.

1000 agenti registrati non implicano 1000 slot attivi, 1000 richieste simultanee ai modelli, né 1000 GPU/worker. La capacità attiva è sempre limitata dal minimo fra risorse ammesse, quote, limiti provider, budget, dipendenze, policy e disponibilità.

## 2. Ricognizione sorgente: ciò che esiste e ciò che non prova

Audit limitato allo snapshot di branch HEAD 5b57a247d8d96d5964df20876925637c8e6f2603 (PR #212). Riferimenti blob riportati nel Source Traceability Ledger.

- **core/agent_fabric.py** espone MAX_FABRIC_AGENTS = 1024 e un limite di registrazione. Il limite dimostra capacità massima dichiarata del registro locale, non 1.024 worker attivi, scheduler distribuito, code durevoli o esecuzione concorrente. Il dispatch esaminato attraversa i binding e chiama agent.run; non costituisce un execution plane distribuito con lease/capacity reservation.
- **core/coordination.py** usa plan.steps[:max_agents], assegna solo quel prefisso e il ciclo execute chiama gli agenti sequenzialmente. max_agents è un limite locale; non dimostra parallelismo né copertura completa di DAG oltre il prefisso.
- **core/agent_mesh.py** seleziona il primo agente ordinato per ID con ruolo esatto. Non esegue scoring di capacità, fairness, locality, provider independence o bilanciamento.
- **core/agent_runtime.py** osserva start/heartbeat/status attraverso il router; lo stato online è una vista locale e non una lease distribuita con fencing.
- **core/supervisor.py** seleziona e ammette risultati, ma non costituisce un control plane di scheduling durevole.
- **core/agent_skills.py** ha un registro locale limitato (default 1.024 skill); la registrazione di una skill non dimostra qualifica, capacità o autorità.
- **core/limits.py** definisce limiti per task (tempo, output, tool call, memoria ecc.); non definisce un budget aggregato globale di flotta o fairness tra tenant.
- **core/resource_router.py** seleziona DEVICE/EDGE/CLOUD con euristiche statiche; non prova telemetria di capacità live, prenotazione atomica o placement attested.
- **ecosystem/global_scale.py** offre registri locali di regioni/celle, selezione per health/capacity, ElasticComputeFabric, coda/event fabric e ResourceBudget. Le strutture sono primitive in-process; non dimostrano lease durevoli, decremento atomico multi-controller, fencing, broker esterno, scheduler GPU o control plane multi-regione.

**Conclusione limitata:** NORYX7 contiene primitive e un limite di registro che rendono naturale progettare una flotta da 1.000 identità; il codice esaminato non dimostra 1.000 esecuzioni concorrenti, né una piattaforma pronta a sostenerle. Nessun difetto di deployment esterno viene dedotto da questa ricognizione.

## 3. Principi architetturali

1. **Control plane ≠ execution plane.** Il control plane pianifica, assegna, autorizza, osserva e riconcilia. I worker eseguono solo tentativi autorizzati.
2. **Identità ≠ capacità ≠ qualifica ≠ autorità.** Nessun attributo implica gli altri.
3. **DAG prima della concorrenza.** Solo nodi indipendenti, con dipendenze soddisfatte e budget/permessi validi, possono partire in parallelo.
4. **Lease breve, fencing monotono.** Ogni assegnazione è un lease legato a task, attempt, agent, worker, audience, capability, policy/revocation epoch, deadline e fencing token.
5. **At-least-once delivery, effetti idempotenti o riconciliati.** Non promettere exactly-once. Un timeout dopo un effetto esterno genera UNKNOWN_OUTCOME, non retry cieco.
6. **Admission indipendente.** Il worker non può auto-approvare il proprio risultato. Il verificatore deve avere provenienza, scope e failure domain dichiarati.
7. **Budget hard, backpressure esplicita.** Esaurimento di GPU, token, costo, memoria, energia, banda, rate limit o quota non viene aggirato aumentando il numero logico di agenti.
8. **Degradazione sicura.** Se coordinatore, lease authority, identità, journal o verificatore non sono disponibili, sospendere/accodare/limitare il lavoro secondo la classe di rischio.
9. **Provider-agnostic ma non provider-blind.** Ogni adapter espone quote, rate limits, modello/versione, regione, retention, privacy, costo, latenza e modalità di errore.
10. **Nessun quorum fittizio.** Molti agenti sullo stesso modello, prompt, corpus, provider o tool non sono fonti indipendenti.

## 4. Topologia logica: coordinamento senza autorità implicita

La topologia usa livelli sostituibili e replicabili, non una singola AI madre:

- **Fleet Registry:** profili, identità, qualifica, capacità dichiarata, provider, domini, località, stato e revoca.
- **Admission & Policy Gate:** autentica principal e richiesta; verifica delega, scope, rischio, data residency, budget e capability.
- **Task Graph Planner:** crea DAG tipizzato; ogni nodo ha prerequisiti, input/output schema, rischio, scadenza, budget, idempotency class e criterio di ammissione.
- **Shard/Domain Coordinators:** partizionano lavoro per tenant/dominio/regione e gestiscono batch limitati. Non possono elevare privilegi né cambiare policy.
- **Global Scheduler / Placement:** seleziona worker e slot rispettando dipendenze, quote, locality, capacity lease, fairness e failure domains.
- **Durable Queue + Outbox/Inbox:** conserva richieste, lease, tentativi, cancellation e receipts attraverso crash e riavvii.
- **Worker Runtime:** esegue un singolo attempt con capability minima e contesto esplicito; non può autoassegnarsi nuovi task.
- **Result Admission & Independent Verification:** valida schema, lineage, identità, freshness, semantica, evidenza e indipendenza richiesta.
- **State/Commit Authority:** registra lo stato canonico e il receipt di ammissione; un risultato del worker non aggiorna da solo la memoria autorevole.
- **Observability & Recovery:** misura la flotta, rileva anomalie, drena worker, revoca lease e rientra solo dopo riconciliazione.

Coordinatori stateless o ricostruibili possono essere replicati; l'autorità di assegnazione resta nel servizio/registro durevole con epoch e fencing. La scelta concreta del broker, database, orchestratore e runtime è OPEN e dipende da requisiti e infrastruttura reali.

## 5. Contratti minimi

### 5.1 AgentProfile
agent_id, issuer, key_id, role, skill_manifest_digest, qualification_refs, model_provider, model_id, model_version, tool_allowlist, data_regions, privacy_class, failure_domain, max_concurrency, resource_vector, cost_profile, health_evidence, revocation_epoch, valid_from, valid_until.

Le skill dichiarate non sono qualifiche. Le qualifiche sono attestazioni emesse da autorità e verificatori specifici del dominio, con scope e scadenza.

### 5.2 TaskNode
task_id, graph_id, parent_ids, dependency_ids, tenant, principal, objective, input_refs, input_digest, required_qualification, risk_class, allowed_capabilities, output_schema, acceptance_policy, deadline, retry_class, idempotency_key, budget_id, residency, evidence_requirements.

### 5.3 DispatchLease
lease_id, task_id, attempt_id, agent_id, worker_id, audience, capability_digest, policy_epoch, revocation_epoch, fencing_token, issued_at, expires_at, resource_reservation_id, coordinator_epoch.

La lease scade automaticamente. Rinnovo richiede controllo di identità e policy correnti; un worker con lease scaduta o fencing token superato non può committare risultati o effetti.

### 5.4 AttemptReceipt / ResultReceipt / AdmissionReceipt
- AttemptReceipt: chi ha eseguito cosa, con quale lease, modello/tool version, input digest, start/end, costi e stato.
- ResultReceipt: output digest, schema, provenance, evidenze, warnings, error class e attempt ID.
- AdmissionReceipt: verificatore e qualifica, policy/versioni, controlli superati/falliti, dipendenze, esito e commit sequence.

Receipt firmati e canonicalizzati secondo il protocollo polyglot; non introdurre un secondo formato concorrente.

## 6. Scheduler: DAG, fairness e parallelismo controllato

Lo scheduler opera per ondate di nodi pronti del DAG. Per ogni nodo:

1. verifica dipendenze, stato, validità degli input e freshness;
2. applica policy, rischio, tenant quota, regione e privacy;
3. filtra agenti qualificati e worker attivi;
4. verifica capacity lease e riserva risorse atomicamente;
5. seleziona un failure domain/provider compatibile;
6. emette DispatchLease con attempt ID e fencing token;
7. avvia il tentativo entro il limite di concorrenza;
8. gestisce heartbeat, timeout, cancellation e revoca;
9. ammette o mette in quarantena il risultato;
10. rilascia risorse e aggiorna la coda con receipt durevole.

La concorrenza effettiva deve rispettare:
C_active <= min(C_global, C_tenant, C_provider, C_model, C_region, C_worker, C_budget, C_ready_DAG).

I limiti sono configurabili e misurati; non si assume che C_active sia 1.000. Un nodo lento non deve bloccare task indipendenti; un nodo critico non può essere saltato solo per aumentare throughput.

**Fairness:** weighted fair queuing o deficit round robin per tenant e classi, con quote riservate, priorità limitate, aging contro starvation e limiti per task. Nessun tenant può monopolizzare tutti gli slot.

**Backpressure:** coda con limiti per numero, byte, età e costo previsto; rifiuto o rinvio esplicito; adaptive concurrency; circuit breaker per provider; admission control prima di allocare GPU/token.

**Cancellation:** propagazione nel DAG; task non iniziati vengono cancellati; tentativi attivi ricevono cancellation; gli effetti esterni già possibili restano da riconciliare.

## 7. Modello di crescita e profili di capacità

Questi sono profili di progetto, non benchmark o capacità già provate:

| Profilo | Agenti registrati | Slot concorrenti obiettivo | Condizioni minime |
|---|---:|---:|---|
| S0 laboratorio | 10 | 1–5 | singolo runtime, limiti stretti, audit locale |
| S1 piccolo pool | 32 | 4–16 | coda durevole, lease, budget per task |
| S2 parallelo | 90–100 | 10–40 | DAG scheduler, fairness, provider quotas, verifica separata |
| S3 multi-pool | 256 | 25–100 | worker pool separati, placement, circuit breaker, recovery |
| S4 distribuito | 500 | 50–200 | control plane replicato, fencing durevole, multi-regione |
| S5 obiettivo massimo | 1.000 | determinato da risorse | quota/telemetria reali, autoscaling, DR, capacity admission e benchmark |

Le fasce di slot sono ipotesi per pianificazione e devono essere sostituite da benchmark su hardware/provider effettivi. 1.000 agenti logici possono essere multiplexati su un numero inferiore di processi/slot; agenti con GPU o tool dedicati possono richiedere risorse esclusive.

### 7.1 Budget multidimensionale
Ogni task/tenant/provider/region ha budget indipendenti: CPU, GPU memory, RAM, storage, network egress, token input/output, richieste/minuto, concurrency, wall time, energia, costo monetario, tool calls e rischio. Budget di flotta è somma con riserve e soglie; nessun costo infinito implicito.

### 7.2 Placement e failure domains
Distribuire per disponibilità e vincoli, non per numero: separare provider, modello, account, regione, zona, host, rete, corpus e tool quando si richiede indipendenza. Non collocare tutti i verificatori nello stesso failure domain del generatore per task ad alta criticità.

## 8. Modelli AI e agenti non-LLM

Un agent profile può utilizzare:
- modelli API commerciali differenti;
- modelli open-weight self-hosted;
- modelli locali/device/edge;
- worker deterministici (parser, compilatori, test runner, static analyzers, solver, indicizzatori);
- servizi specialistici con attestazione;
- combinazioni di modelli e tool.

Il modello è un adapter non attendibile, non l'identità dell'agente né la fonte dell'autorità. Le credenziali API risiedono nel provider broker/secret boundary, mai nei prompt, nei log o nel codice dell'agente. Per ogni provider: account owner, rate limit, concurrency, quota, regione, retention/training policy, data processing terms, retry semantics e costo sono espliciti. La presenza di più provider non garantisce indipendenza cognitiva o giuridica.

## 9. Identità, delega, sicurezza e isolamento

- Ogni agente/worker ha identità distinta; niente principal di fallback o credenziali condivise senza scope.
- Delega attenuata: un coordinatore può delegare solo un sottoinsieme di capability, durata, tenant, dati, strumenti e budget ricevuti.
- Agent registration non equivale a trust; l'ammissione richiede issuer attendibile, attestazione, policy, stato di revoca e lease valida.
- Isolamento per tenant e task: filesystem, processi, rete, secrets, cache, memoria e strumenti separati secondo classificazione dati.
- Tool e browser egress passano da policy centrale e lease on-demand; agenti non possono aprire canali arbitrari o creare agenti privilegiati.
- Input esterni, risultati modello, tool output e memoria sono dati non attendibili fino ad ammissione.
- Limiti per prompt injection, output poisoning, tool escalation, sybil identities, collusion, replay, resource exhaustion, model drift e supply-chain compromise.
- Kill switch: revoca lease, sospensione provider/worker, congelamento task ad alto rischio e quarantena con conservazione prove.
- Per azioni irreversibili, finanziarie, critiche o fisiche: approvazione umana/autorità esterna specifica; nessuna maggioranza di agenti sostituisce la firma autorizzativa.

## 10. Indipendenza e verifica del lavoro parallelo

Ogni task dichiara il livello di assurance richiesto:
- **L0 structural:** schema, completezza, identità, digest.
- **L1 deterministic:** test, parser, compilatore, regole riproducibili.
- **L2 independent review:** reviewer con provider/modello/corpus/tool/failure domain distinti e dichiarati.
- **L3 domain assurance:** specialista qualificato, oracle/holdout e fonti primarie.
- **L4 high-impact:** revisore indipendente + approvazione umana/autorità competente + audit trail.

La maggioranza non decide la verità. Per task critici, dissent e risultati discordanti restano espliciti; un arbitrator con mandato e fonti indipendenti decide o lascia INDETERMINATE. La stessa risposta generata da dieci agenti che condividono modello e prompt conta come un unico failure domain, non dieci conferme.

## 11. Stato, retry, lease e failure semantics

Stati proposti: QUEUED → READY → RESERVED → DISPATCHED → RUNNING → RESULT_RECEIVED → VERIFYING → ADMITTED → COMMITTED. Rami di uscita: REJECTED, FAILED_NO_EFFECT, CANCELLED, EXPIRED, QUARANTINED, UNKNOWN_OUTCOME, RECONCILIATION_REQUIRED.

- Lease scaduta: il tentativo perde diritto di commit; fencing token precedente rifiutato.
- Worker morto: attempt resta incompleto; recovery decide se ri-assegnare.
- Errore prima di dispatch provato: retry secondo policy.
- Errore dopo possibile effetto: UNKNOWN_OUTCOME; interrogare destinazione/receipt, non fare failover cieco.
- Duplicato: idempotency key e dedupe durevole.
- Risultato in ritardo: accettabile solo se attempt e fencing sono ancora correnti.
- Verificatore indisponibile: non promuovere risultato; accodare o degradare.
- Perdita del quorum/lease authority: stop ai commit privilegiati; lavoro puramente locale può continuare solo entro policy offline firmata e limitata.

## 12. Memoria, conoscenza e contesto per 1.000 agenti

La memoria non diventa un unico prompt condiviso:
- contesto task-scoped e tenant-scoped;
- memoria agente separata da memoria canonica di progetto;
- artefatti immutabili content-addressed e riferimenti con ACL;
- claim/evidence lineage e bitemporalità;
- scrittura canonica solo dopo AdmissionReceipt;
- cache volatile con TTL, versione e invalidazione;
- deduplica e content reuse senza confondere proprietà/consenso;
- budget di contesto e retrieval per rilevanza, non broadcast integrale;
- cancellazione, retention e data residency propagate a cache, repliche e provider secondo policy;
- conflitti conservati come dissent/claim alternativi, non sovrascritti da last-write-wins.

## 13. Osservabilità e controllo economico

Metriche minime per agente/worker/task/provider/tenant/region:
- queued/runnable/active/completed/failed/unknown/quarantined;
- queue wait, execution latency, p50/p95/p99, throughput e retry rate;
- utilization CPU/GPU/RAM, token rate, concurrency e provider 429/5xx;
- cost per accepted result, cost per useful task, waste/retry cost;
- cancellation lag, lease expiry, stale commit rejected, duplicate attempt;
- verifier rejection, disagreement, false admission discovered, calibration;
- fairness, starvation, data egress, energy, incident and recovery time.

I contatori devono distinguere agenti registrati, agenti online, worker attestati, slot prenotati, slot attivi, invocazioni provider e risultati ammessi. Dashboard non costituisce prova di integrità: metriche firmate/aggregate e audit durevole hanno owner separato.

## 14. Rollout e gate di scala

Non saltare direttamente da un registro da 1.024 agenti al claim di 1.000 concorrenti.

- **Gate A — 10 logici / 1–5 slot:** contract tests, lease expiry, cancellation, duplicate delivery, result admission.
- **Gate B — 32 / 4–16 slot:** crash/restart, queue durability, fairness, budget, provider rate-limit.
- **Gate C — 100 / 10–40 slot:** DAG concurrency, overload, verifier independence, partition e stale worker fencing.
- **Gate D — 256 / 25–100 slot:** multi-pool placement, worker drain, regional failover, key/revocation propagation.
- **Gate E — 500–1.000 logici:** load test ripetibile, capacity planning hardware/provider, cost envelope, multi-region recovery, security assessment e SLO misurati.

Ogni gate richiede test riproducibili, artifact/version pinning, report firmato, failure injection e criterio di rollback. Il numero di agenti è superato solo se tutti i requisiti del gate precedente restano soddisfatti.

## 15. Matrice W01–W12

- **W01:** principal/agent/worker identity, enrollment, delegation, revocation, lease audience e qualification issuer.
- **W02:** DAG planner, lifecycle owner, scheduler, cancellation, attempt state, composition root e admission.
- **W03:** durable queue, memory scope, task context, idempotency ledger, replay e recovery.
- **W04:** canonical Agent Fabric, registry, qualification, dispatch, supervisor, result admission e dissent.
- **W05:** provider/model broker, placement, resource vector, budgets, quotas, fairness, backpressure e failover.
- **W06:** evidence lineage, claim admission, independent verification, holdout e semantic validity.
- **W07:** simulation/Reality Bridge worker sandbox, calibrated kernels, resource budgets e no-actuation boundary.
- **W08:** device/edge agents, on-demand network lease, offline execution and safe reconnect.
- **W09:** isolation, secret management, signatures, canonical protocol, audit, supply chain, kill switch.
- **W10:** specialist qualifications, jurisdiction, scope, expiry and reviewer authority.
- **W11:** regional control plane, durable lease/fencing, placement, capacity, SLO, DR and partition semantics.
- **W12:** contribution/payment/governance/impact workers as segregated capability classes with dual control and independent receipts.

## 16. Gap register proposto

1. **GAP-W04-CANONICAL-AGENT-IDENTITY-AND-REGISTRY-OWNERSHIP** — unificare identità, profili, qualifiche, lifecycle e revoca senza fondere trust e ruolo.
2. **GAP-W02-W04-DURABLE-DAG-SCHEDULER-AND-FULL-PLAN-COVERAGE** — scheduler DAG con esecuzione concorrente limitata, dipendenze, cancellation e copertura senza truncation silenziosa.
3. **GAP-W04-W11-DISTRIBUTED-WORKER-LEASE-AND-FENCING** — lease durevole, heartbeat, fencing token, stale worker rejection e rejoin.
4. **GAP-W04-W05-ATOMIC-CAPACITY-RESERVATION-AND-RESOURCE-BUDGET** — risorse multidimensionali e reservation atomica per task/tenant/provider/region.
5. **GAP-W04-W05-FAIRNESS-BACKPRESSURE-AND-ADAPTIVE-CONCURRENCY** — quote, fairness, overload, coda limitata e protezione starvation.
6. **GAP-W01-W04-QUALIFICATION-DELEGATION-AND-CAPABILITY-ATTENUATION** — skill/role/qualification/delegation separati con scope, expiry, issuer e revocation.
7. **GAP-W04-W06-INDEPENDENT-VERIFICATION-AND-COMMON-FAILURE-DOMAINS** — attestare indipendenza reale, holdout, dissent e admission.
8. **GAP-W02-W03-W04-ATTEMPT-IDEMPOTENCY-AND-UNKNOWN-OUTCOME-RECONCILIATION** — durable attempt ledger, dedupe, remote receipts e retry sicuri.
9. **GAP-W03-W04-TASK-SCOPED-MEMORY-AND-CANONICAL-COMMIT** — contesto isolato, provenance, cache invalidation e scrittura dopo ammissione.
10. **GAP-W05-W09-MULTI-PROVIDER-QUOTA-SECRET-AND-PRIVACY-BROKER** — provider adapter con secret custody, retention, residency, costi e rate limit.
11. **GAP-W09-W11-AGENT-WORKER-ISOLATION-AND-FLEET-KILL-SWITCH** — sandbox, egress, revoca e quarantena fleet-wide.
12. **GAP-W11-1000-AGENT-CAPACITY-SLO-AND-RECOVERY-PROOF** — benchmark, capacity evidence, multi-region recovery e cost envelope prima del claim 1.000.

## 17. Decisioni lasciate OPEN

Non sono assunti come decisi: broker/coda, database lease, protocollo RPC, orchestratore, runtime container/microVM, policy scheduler, algoritmo fairness, formato AgentProfile/TaskNode definitivo, modello di capacity reservation, quorum/consensus, provider mix, region topology, cost envelope, hardware, SLO e requisiti legali/privacy. Queste scelte richiedono alternative confrontate, owner nominato e prove.

## 18. Criteri di accettazione architetturale (non ancora eseguiti)

1. Ogni agente registrato ha profilo, issuer, identità, qualifica distinta e stato di revoca.
2. Nessun task parte senza principal, policy, budget, DAG prerequisites e lease.
3. Il planner conserva tutti i nodi del DAG; non tronca silenziosamente il piano.
4. La concorrenza non supera nessuno dei limiti globali/tenant/provider/region/worker/budget.
5. Reservation e lease non sono duplicabili da scheduler concorrenti.
6. Un worker scaduto/revocato non può ammettere o committare risultati.
7. Crash/restart non perde task, tentativi, idempotency keys o receipts.
8. UNKNOWN_OUTCOME impedisce retry non idempotente fino a riconciliazione.
9. Risultati discordanti conservano dissent; agenti con stesso failure domain non sono conteggiati come indipendenti.
10. Un verificatore non può essere il generatore mascherato da secondo agente.
11. Isolamento tenant, egress, secret, data residency e retention sono provati con test.
12. Overload produce backpressure esplicita e nessuna crescita incontrollata di costo.
13. I gate 10→32→100→256→500→1.000 hanno benchmark e report ripetibili.
14. I dashboard distinguono registered/online/attested/leased/active/provider-invoked/admitted.
15. Il sistema può degradare, fermare, drenare, revocare e riprendere senza promuovere risultati non verificati.

**Stato di chiusura:** specifica architetturale proposta per il target logico 10–1.000. Non equivale a implementazione, esecuzione concorrente misurata, capacità provider acquistata o validazione. W01–W12 restano PARTIAL finché i rispettivi criteri e le dipendenze condivise non sono approvati, implementati e verificati.
