# NORYX7 — Edge Node Fabric inspired by ZimaBoard

## Decision

Integrate the useful *class* of capabilities demonstrated by ZimaBoard as an NORYX7 edge-node profile, not as a dependency on a specific vendor board.

ZimaBoard is an x86 single-board server platform with dual SATA, dual Gigabit Ethernet, USB 3.0, PCIe expansion and low-power passive operation; official material also describes NAS/personal-cloud, router/firewall, VPN, traffic shaping, Docker/edge applications and IoT/video workloads. citeturn0search0turn0search1turn0search2

## NORYX7 Edge Node capabilities

### 1. Local compute

- low-power always-on execution;
- local model inference where the workload permits;
- local preprocessing before cloud transfer;
- local verification and policy enforcement;
- containerized services;
- snapshot/rollback boundary;
- workload isolation.

### 2. Local storage

- dual-drive capable storage profile;
- encrypted persistent data;
- redundant storage profiles;
- backup staging;
- offline/air-gapped backup handoff;
- integrity verification;
- encrypted memory shards;
- local cache for latency-sensitive workloads.

The physical ZimaBoard reference exposes two SATA 3.0 ports and PCIe expansion, making this class of edge storage/expansion particularly relevant to the design. citeturn0search4

### 3. Network edge

The edge node can act as a controlled network boundary:

- dual-network-interface topology;
- inbound/outbound policy enforcement;
- firewall/perimeter integration;
- VPN termination;
- traffic segmentation;
- QoS/rate limiting;
- DNS/security filtering adapters;
- network telemetry;
- isolated management interface;
- fail-closed egress.

The ZimaBoard reference specifically supports dual Gigabit Ethernet and router deployments using OpenWrt/pfSense. citeturn0search1

### 4. Edge gateway

Sensors and external systems can connect to the edge node through explicit adapters:

`DEVICE/SENSOR → EDGE NODE → VALIDATION → NORMALIZATION → POLICY → NORYX7`

Potential connectivity adapters include Ethernet, USB and optional radio/cellular/IoT gateways. ZimaBoard-derived edge systems are documented for Wi-Fi/Bluetooth/4G/5G/LoRaWAN/Ethernet connectivity through appropriate expansion. citeturn0search2

### 5. Local media / vision processing

The edge profile can support:

- local video preprocessing;
- OpenCV-style computer-vision workloads;
- media transcoding through appropriate adapters;
- local stream analysis;
- event extraction;
- privacy-preserving preprocessing before cloud transmission.

The vendor's reference use cases include real-time video processing, OpenCV applications and edge data preprocessing. citeturn0search3

### 6. Home/lab/server role

The edge node can host selected self-contained services:

- personal cloud/storage;
- collaboration storage;
- local media services;
- private dashboards;
- development services;
- container workloads;
- local automation;
- monitoring.

The actual ZimaBoard ecosystem documents personal cloud, NAS, media, Docker and 24/7 scripts as representative workloads. citeturn0search0turn0search3

## Security adaptation

NORYX7 must improve substantially on a generic single-board server.

The edge node is treated as **potentially compromised**.

It therefore receives:

- device identity;
- attestation state;
- capability grants;
- epoch-bound authorization;
- encrypted storage;
- secure boot boundary;
- signed workload admission;
- sandboxed containers;
- network microsegmentation;
- independent security logging;
- revocation;
- remote isolation;
- recovery image;
- offline recovery path.

Compromise of the edge node must not expose global NORYX7 credentials, immutable Core keys, user master secrets or update authority.

## Resource placement

The edge node becomes an explicit member of:

`CLIENT → EDGE → CLOUD → OFFLINE`

The Resource Router chooses edge execution when it reduces latency, preserves privacy or reduces cloud dependency, while high-risk authority remains centralized/verified according to policy.

## Swiss-clock performance model

The node is optimized for predictable operation rather than maximum theoretical workload:

- bounded queues;
- admission control;
- backpressure;
- local caching;
- asynchronous I/O;
- parallel independent workloads;
- cancellation/deadlines;
- resource quotas;
- health checks;
- graceful degradation;
- failover to other nodes or cloud;
- recovery without silent state corruption.

## Vendor independence

The ZimaBoard capability profile is an architectural reference. NORYX7 should expose a generic `EdgeNode` contract so that ZimaBoard, x86 mini-PCs, ARM boards, industrial gateways and future custom hardware can implement the same role without coupling the cognitive core to one hardware vendor.

## Structural completion target

`EDGE NODE = COMPUTE + STORAGE + NETWORK + GATEWAY + LOCAL VERIFICATION + SECURITY + RECOVERY`

The verification phase must later test each capability independently and then test combined failure scenarios, including storage failure, network partition, compromised workload, compromised edge node, cloud unavailability and recovery from offline state.
