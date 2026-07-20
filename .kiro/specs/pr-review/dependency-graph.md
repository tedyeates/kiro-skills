# Dependency Graph: PR Review Companion Skills

```mermaid
graph LR
  subgraph "Batch 1 (parallel)"
    T58[#58 Security checklist & agent]
    T59[#59 Test quality checklist & agent]
    T60[#60 Design conformance rules & agent]
    T61[#61 Extend to-spec]
  end
  subgraph "Batch 2"
    T62[#62 Orchestrator skill]
  end
  subgraph "Batch 3"
    T63[#63 Validation against stock-tracker]
  end
  T58 --> T62
  T59 --> T62
  T60 --> T62
  T62 --> T63
  T61 --> T63
```

## Issue Index

| # | Title | Blocked by |
|---|-------|-----------|
| #58 | Security review checklist and agent | — |
| #59 | Test quality checklist and agent | — |
| #60 | Design conformance rules and agent | — |
| #61 | Extend to-spec with security.md and testing.md | — |
| #62 | Orchestrator skill (pr-review) | #58, #59, #60 |
| #63 | Validation against stock-tracker | #62, #61 |
