# Markdown Mermaid embeds

Copy any block below into documentation pages. Sources of truth: sibling `.mmd` files.
See [README.md](README.md) for PDF rendering and LaTeX includes.

---

## 1. End-to-end pipeline

```mermaid
%%{init: {
  'theme': 'neutral',
  'themeVariables': {
    'fontFamily': 'Helvetica, Arial, sans-serif',
    'fontSize': '13px',
    'primaryColor': '#f4f6f8',
    'primaryBorderColor': '#2c3e50',
    'lineColor': '#4a5568'
  },
  'flowchart': { 'curve': 'basis', 'padding': 12, 'nodeSpacing': 36, 'rankSpacing': 44 }
}}%%
flowchart TB
  subgraph IN["Inputs (synthetic v0.1)"]
    SIG["Local signals<br/><i>PipelineInput</i>"]
  end

  subgraph L2["L2 Edge Perception"]
    PERC["Zone descriptors<br/><i>PerceptionSignal</i>"]
  end

  subgraph L3["L3 Semantic Events"]
    FUSE["Fusion & abstraction<br/><i>SemanticEvent</i>"]
  end

  subgraph L4["L4 Temporal Graph"]
    GRAPH["Graph updates<br/><i>GraphContext</i>"]
  end

  subgraph L5["L5 Local Reasoning"]
    LLM["Structured copilot<br/><i>ReasoningResponse</i>"]
  end

  subgraph L6["L6 Orchestration"]
    REC["Advisory recommendations<br/><i>requires_human_review</i>"]
  end

  subgraph OUT["Outputs"]
    EVAL["Evaluation metrics & audit<br/><i>PrivacyReport</i>"]
  end

  L1["L1 Privacy Runtime<br/>TB1–TB5 cross-cutting gates"]

  SIG --> PERC --> FUSE --> GRAPH --> LLM --> REC --> EVAL
  L1 -. enforce .-> PERC
  L1 -. enforce .-> FUSE
  L1 -. enforce .-> LLM
  L1 -. enforce .-> REC
  L1 -. enforce .-> EVAL

  classDef layer fill:#e8ecf0,stroke:#2c3e50,stroke-width:1.5px
  classDef privacy fill:#fdebd0,stroke:#b9770e,stroke-width:2px
  classDef io fill:#eafaf1,stroke:#1e8449,stroke-width:1.5px
  class PERC,FUSE,GRAPH,LLM,REC layer
  class L1 privacy
  class SIG,EVAL io
```

---

## 2. Privacy runtime

```mermaid
%%{init: {
  'theme': 'neutral',
  'themeVariables': {
    'fontFamily': 'Helvetica, Arial, sans-serif',
    'fontSize': '13px',
    'primaryColor': '#f4f6f8',
    'primaryBorderColor': '#2c3e50',
    'lineColor': '#4a5568'
  },
  'flowchart': { 'curve': 'basis', 'padding': 12, 'nodeSpacing': 32, 'rankSpacing': 40 }
}}%%
flowchart TB
  RAW["Ephemeral buffer<br/><i>PerceptionFrame</i>"]

  TB1{{"TB1<br/>TTL & no persistent media"}}
  SIG["PerceptionSignal<br/>zone descriptors only"]
  TB2{{"TB2<br/>Schema & payload validation"}}
  EVT["SemanticEvent<br/>retention tags"]
  TB3{{"TB3<br/>Publication & audit gates"}}
  COP["Local reasoning I/O<br/>structured events only"]
  TB4{{"TB4<br/>LLM serializer & filter"}}
  PUB["Publication bus"]
  TB5{{"TB5<br/>Egress allowlist"}}
  OUT["Structured events + PrivacyReport<br/><b>no raw media</b>"]

  RAW --> TB1 --> SIG --> TB2 --> EVT --> TB3 --> COP --> TB4 --> PUB --> TB5 --> OUT

  classDef gate fill:#fadbd8,stroke:#922b21,stroke-width:2px
  classDef proc fill:#ebf5fb,stroke:#1f618d,stroke-width:1.5px
  classDef out fill:#eafaf1,stroke:#1e8449,stroke-width:1.5px
  class TB1,TB2,TB3,TB4,TB5 gate
  class RAW,SIG,EVT,COP,PUB proc
  class OUT out
```

---

## 3. Temporal safety graph

```mermaid
%%{init: {
  'theme': 'neutral',
  'themeVariables': {
    'fontFamily': 'Helvetica, Arial, sans-serif',
    'fontSize': '13px',
    'primaryColor': '#f4f6f8',
    'primaryBorderColor': '#2c3e50',
    'lineColor': '#4a5568'
  },
  'flowchart': { 'curve': 'basis', 'padding': 12, 'nodeSpacing': 28, 'rankSpacing': 36 }
}}%%
flowchart LR
  subgraph ENT["Graph entities"]
    Z["Zone"]
    E["Exit"]
    R["Route"]
    SE["SemanticEventNode"]
    RS["RiskState"]
    RN["RecommendationNode"]
  end

  subgraph REL["Relations"]
    direction TB
    OI["OCCURRED_IN"]
    CT["CONNECTS_TO"]
    BL["BLOCKS"]
    AF["AFFECTS"]
    ES["ESCALATES / DEESCALATES"]
    SP["SUPPORTS / CONTRADICTS"]
    RC["RECOMMENDS"]
  end

  IN["Incoming SemanticEvent"] --> INGEST["InMemoryTemporalGraphService"]
  INGEST --> SE
  SE --> OI --> Z
  Z --> CT --> R
  E --> BL --> R
  SE --> AF --> R
  SE --> ES --> RS
  SE --> SP --> SE
  RN --> RC --> Z

  INGEST --> CTX["GraphContext"]
  CTX --> L5["L5 Local Reasoning"]

  classDef entity fill:#e8f6f3,stroke:#117a65,stroke-width:1.5px
  classDef rel fill:#fef9e7,stroke:#b7950b,stroke-width:1px
  classDef svc fill:#ebf5fb,stroke:#1f618d,stroke-width:1.5px
  class Z,E,R,SE,RS,RN entity
  class OI,CT,BL,AF,ES,SP,RC rel
  class IN,INGEST,CTX,L5 svc
```

---

## 4. Edge deployment architecture

```mermaid
%%{init: {
  'theme': 'neutral',
  'themeVariables': {
    'fontFamily': 'Helvetica, Arial, sans-serif',
    'fontSize': '13px',
    'primaryColor': '#f4f6f8',
    'primaryBorderColor': '#2c3e50',
    'lineColor': '#4a5568'
  },
  'flowchart': { 'curve': 'basis', 'padding': 12, 'nodeSpacing': 32, 'rankSpacing': 44 }
}}%%
flowchart TB
  subgraph SITE["Confined-space site (on-premises enclave)"]
    subgraph EDGE["Edge nodes"]
      EN1["Edge node A<br/>video / sensor"]
      EN2["Edge node B<br/>audio"]
    end

    subgraph RUNTIME["Edge runtime (dualexis/edge_runtime)"]
      CFG["EdgeNodeConfig<br/><i>strict-v1 policy</i>"]
      L1E["L1 validate + egress"]
      BUF["Ephemeral buffers<br/><i>no raw media store</i>"]
    end

    subgraph CORE["Local orchestrator"]
      PIPE["Pipeline L2–L6"]
      GRAPH["Temporal graph store"]
    end

    EN1 --> BUF
    EN2 --> BUF
    BUF --> L1E
    CFG -. policy .-> L1E
    L1E -->|"SemanticEvent"| PIPE
    PIPE --> GRAPH
  end

  subgraph EXT["External (optional / future)"]
    FED["Federated event bus<br/><i>structured events only</i>"]
    REV["Staff review workflow<br/><i>human disposition</i>"]
  end

  PIPE -->|"TB5 allowlist"| FED
  PIPE -->|"advisory recs"| REV

  classDef edge fill:#ebf5fb,stroke:#1f618d,stroke-width:1.5px
  classDef priv fill:#fdebd0,stroke:#b9770e,stroke-width:1.5px
  classDef ext fill:#f5eef8,stroke:#6c3483,stroke-width:1.5px
  class EN1,EN2,PIPE,GRAPH edge
  class CFG,L1E,BUF priv
  class FED,REV ext
```

---

## 5. Human-in-the-loop orchestration

```mermaid
%%{init: {
  'theme': 'neutral',
  'themeVariables': {
    'fontFamily': 'Helvetica, Arial, sans-serif',
    'fontSize': '13px',
    'primaryColor': '#f4f6f8',
    'primaryBorderColor': '#2c3e50',
    'lineColor': '#4a5568'
  },
  'flowchart': { 'curve': 'basis', 'padding': 12, 'nodeSpacing': 32, 'rankSpacing': 40 }
}}%%
flowchart TB
  EV["SemanticEvent<br/>+ GraphContext"]
  RS["L5 Local reasoning<br/><i>structured input only</i>"]
  ORCH["L6 Orchestration<br/><i>OrchestrationRecommendation</i>"]
  GATE{"Severity ≥ medium<br/>or policy rule?"}

  REV["Human review queue<br/><i>requires_human_review</i>"]
  STAFF["Licensed safety staff"]
  DISP{"Disposition"}

  DISM["Dismiss / monitor"]
  ESC["Escalate / notify"]
  ACT["External action<br/><i>outside DUALEXIS</i>"]

  AUD["AuditEntry<br/>append-only log"]

  EV --> RS --> ORCH --> GATE
  GATE -->|yes| REV --> STAFF --> DISP
  GATE -->|no| AUD
  DISP --> DISM --> AUD
  DISP --> ESC --> ACT --> AUD

  NOTE["DUALEXIS does not autonomously enforce<br/>physical or punitive actions"]

  ACT -.-> NOTE

  classDef auto fill:#ebf5fb,stroke:#1f618d,stroke-width:1.5px
  classDef human fill:#eafaf1,stroke:#1e8449,stroke-width:2px
  classDef gate fill:#fdebd0,stroke:#b9770e,stroke-width:1.5px
  classDef audit fill:#f4f6f7,stroke:#566573,stroke-width:1px
  class EV,RS,ORCH auto
  class REV,STAFF,DISP,ACT human
  class GATE gate
  class DISM,ESC,AUD audit
```

---

## 6. Experimental evaluation workflow

```mermaid
%%{init: {
  'theme': 'neutral',
  'themeVariables': {
    'fontFamily': 'Helvetica, Arial, sans-serif',
    'fontSize': '13px',
    'primaryColor': '#f4f6f8',
    'primaryBorderColor': '#2c3e50',
    'lineColor': '#4a5568'
  },
  'flowchart': { 'curve': 'basis', 'padding': 12, 'nodeSpacing': 32, 'rankSpacing': 40 }
}}%%
flowchart TB
  subgraph SPEC["Pre-registered specification"]
    PROTO["protocol.py / baselines"]
    MET["metrics.py / measurement"]
    YAML["experiments/configs/*.yaml"]
  end

  subgraph RUN["Deterministic execution"]
    SIM["run_scenario(name, seed)"]
    PIPE["run_pipeline / execute_protocol"]
    BASE["comparable baselines C1–C4"]
  end

  subgraph COLLECT["Metric collection"]
    LAT["Latency"]
    PRIV["Privacy violations"]
    ROB["Modality dropout"]
    EXPL["Explanation completeness"]
  end

  subgraph ART["Artifacts (descriptive only)"]
    JSON["JSON per run"]
    MD["Markdown reports"]
    TEX["LaTeX table scaffolds"]
  end

  subgraph CLI["CLI entry points"]
    C1["experiment run / run-all"]
    C2["experiment run-multiseed"]
    C3["experiment compare"]
  end

  PROTO --> SIM
  YAML --> PIPE
  SIM --> PIPE
  SIM --> BASE
  PIPE --> COLLECT
  BASE --> COLLECT
  COLLECT --> ART
  C1 --> RUN
  C2 --> RUN
  C3 --> BASE

  DISC["No inferential field claims<br/>synthetic inputs only"]

  ART -.-> DISC

  classDef spec fill:#fef9e7,stroke:#b7950b,stroke-width:1.5px
  classDef run fill:#ebf5fb,stroke:#1f618d,stroke-width:1.5px
  classDef metric fill:#e8f6f3,stroke:#117a65,stroke-width:1.5px
  classDef art fill:#f4f6f7,stroke:#566573,stroke-width:1.5px
  class PROTO,MET,YAML spec
  class SIM,PIPE,BASE run
  class LAT,PRIV,ROB,EXPL metric
  class JSON,MD,TEX art
```
