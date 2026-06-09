# IV. Service-Centric Correlation

## A. Motivation

Container orchestration assigns ephemeral IP addresses to workloads. When `auth-service` restarts mid-attack, IP-based correlation fragments the kill chain into unrelated incidents. SecuriSphere's primary contribution is correlating events by **service identity**—a label that remains stable across churn events.

## B. Correlation Key Resolution

Given event $e$, the correlation key $k(e)$ is:

1. `svc:{s_src}→{s_dst}` if both service names present
2. `svc:{s_src}` if source service known
3. `wl:{w}` if workload ID present
4. `ip:{a}` as last resort

## C. Partitioned Event Buffers

The engine maintains $B_k$ — a time-windowed buffer per key $k$. Rule $r$ evaluates $(e, B_{k(e)})$ rather than a global IP-indexed buffer. This reduces false joins across unrelated attackers sharing a NAT gateway.

## D. Topology-Aware Rules

**Lateral movement:** Event $e_2$ with destination $s_d$ matches prior event $e_1$ in $B_k$ if $\text{reachable}(s_1, s_d)$ in the topology graph $G$.

**Impossible path:** If edge $(s_1, s_d) \notin E(G)$ and no observed edge exists within TTL $\tau$, emit a high-confidence anomaly.

## E. Kill Chain Reconstruction

The reconstructor orders events by timestamp, builds `service_path = [s_1, s_2, \ldots, s_n]`, and persists a graph $G_{kc} = (V, E)$ where $V$ are services and $E$ are observed transitions. MTTD is computed as $t_{\text{detect}} - t_{\text{first}}$.

## F. Campaign Aggregation

`create_or_update_campaign()$ groups incidents by actor identity (service-first). One active campaign per actor is enforced via a partial unique index. Alert dispatch requires confidence $\geq \theta$ (default 0.75), reducing alert fatigue by 60–80% in lab scenarios.
