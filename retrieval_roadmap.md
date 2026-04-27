# Retrieval, Document Intelligence, and Knowledge Processing Roadmap

This document consolidates the strongest RAG-adjacent themes from prior work into a single open-source project roadmap and a parallel research roadmap. The source material points to four core foundations: retrieval research as an ongoing project, investigation into the limitations of standard vector-search RAG, advanced document-processing pipelines for complex PDFs, and substantial attention to multimodal retrieval and chunking techniques such as ColPali, HPC-ColPali, and mixture-of-experts chunking.[cite:4][cite:1][cite:10][cite:31][cite:32][cite:33]

The best project direction is not a narrow chatbot. It is a modular system for **retrieval, document extraction and processing, knowledge processing, storage, and communication** that treats documents as multimodal, structured knowledge objects rather than plain text blobs.[cite:1][cite:10][cite:31][cite:32] The best research direction is a next-generation retrieval architecture that combines OCR, layout understanding, adaptive chunking, multimodal indexing, hybrid retrieval, and agentic reasoning into one measurable framework.[cite:1][cite:10][cite:31][cite:32][cite:33]

## Strategic vision

The project should aim to build an open-source platform that can ingest hard documents, understand them across text and layout modalities, store them in multiple retrieval-friendly representations, and serve them through fast and accurate retrieval plus reasoning layers.[cite:10][cite:31][cite:32] This directly matches the prior themes around retrieval research, vector-search limitations, PageIndex or vectorless alternatives, and complex-document processing pipelines.[cite:4][cite:1][cite:10]

The research paper should target a broader claim: current retrieval pipelines fail because they flatten structure too early, overcommit to one representation, and separate extraction from reasoning too rigidly.[cite:1][cite:10][cite:31][cite:32] The proposed answer is a unified architecture with representation diversity, adaptive chunking, multimodal retrieval, and explicit knowledge communication layers between ingestion, storage, retrieval, and agent reasoning.[cite:1][cite:31][cite:32][cite:33]

## Project definition

### Project name candidates

- Knowledge Fabric
- OmniRetrieve
- DeepDocument Retrieval Stack
- StructRAG
- PageGraph
- Retrieval OS

### Core project thesis

The system should outperform standard RAG stacks on difficult enterprise and research documents by combining:

- Multimodal document ingestion for scanned PDFs, tables, formulas, diagrams, and handwriting.[cite:10]
- OCR ensembles and document parsing pipelines instead of one extractor per corpus.[cite:10]
- Layout-aware, semantic-aware, and task-aware chunking rather than fixed token windows.[cite:31]
- Multiple retrieval representations: lexical, dense, late-interaction, visual-page, graph, and vectorless or page-indexed forms.[cite:1][cite:31][cite:32]
- Agentic retrieval planning so the system can choose the best retrieval path per query rather than always doing the same ANN lookup.[cite:1][cite:31]
- Structured knowledge storage for communication across modules, not just opaque embeddings.[cite:1][cite:10]

## System architecture

### Layer 1: Document ingestion

This layer should accept born-digital PDFs, scanned PDFs, images, slide decks converted to PDF, HTML, and research papers.[cite:10][cite:3] The ingestion stack should preserve page geometry, reading order, section hierarchy, tables, figures, equations, footnotes, references, and detected entities because flattening too early is one of the main reasons retrieval quality degrades later.[cite:10][cite:32]

Recommended extraction stack:

| Function | Best stack choice | Why it belongs |
|---|---|---|
| Fast text OCR | PaddleOCR [cite:10] | Strong baseline for general OCR throughput and multilingual handling in prior work context. |
| Rich visual OCR | GLM-OCR [cite:10] | Useful where page structure and visual context matter. |
| Multimodal recovery | Qwen2.5-VL / Qwen 3 30B A3B pipeline [cite:10] | Better for diagrams, formulas, handwritten text, and hard pages. |
| Parsing orchestration | Python + async workers | Needed to route documents adaptively across OCR experts. |
| Layout normalization | Custom page JSON schema | Preserves boxes, spans, regions, tables, figures, formulas, and hierarchy. |

The key design principle is **ensemble extraction with confidence routing**. Instead of trusting one OCR engine, the pipeline should compare outputs, merge them, and escalate hard regions to multimodal parsing.[cite:10] This improves both accuracy and downstream retrieval fidelity on difficult document classes.[cite:10][cite:32]

### Layer 2: Knowledge representation

Every document should be stored in several synchronized forms because no single representation is sufficient for all queries.[cite:1][cite:31][cite:32] The internal canonical object should be a page-and-section graph with links among tokens, layout blocks, tables, figures, equations, references, and semantic entities.[cite:10][cite:32]

Recommended parallel representations:

- Clean text stream for lexical search and LLM consumption.
- Hierarchical section tree for document navigation and structured prompting.
- Page image and patch-level visual representation for ColPali-style retrieval.[cite:32]
- Late-interaction token representation for precise dense retrieval on long documents.[cite:31][cite:32]
- Table and figure sub-objects for targeted retrieval over non-prose content.[cite:10]
- Citation or reference graph for research corpora and linked documents.[cite:3]
- PageIndex or vectorless retrieval artifacts for fallback and interpretability-oriented retrieval paths.[cite:1]

### Layer 3: Chunking

Chunking should become a learned or rule-gated subsystem, not a hardcoded preprocessing step.[cite:31] Prior work strongly points toward a mixture-of-experts chunking design that combines late chunking, semantic-aware splitters, layout-aware segmentation, and document-type-specific heuristics.[cite:31]

Recommended chunking strategy:

| Document condition | Preferred chunking behavior | Reason |
|---|---|---|
| Linear prose | Late chunking + semantic breakpoints [cite:31] | Preserves context while avoiding arbitrary cuts. |
| Sectioned technical papers | Hierarchical section chunking + citation-aware splits [cite:3][cite:31] | Matches how research papers are read and retrieved. |
| Tables and forms | Structure-preserving table chunks [cite:10] | Prevents cell corruption and row mixing. |
| Visually rich PDFs | Layout-region chunks + page image anchors [cite:32] | Necessary for diagrams and mixed content. |
| Mixed hard documents | MoE chunk router [cite:31] | Selects chunker by page type, density, and task. |

The chunker should output linked chunks with provenance, parent section, page coordinates, modality tags, and confidence signals.[cite:10][cite:31] This metadata is critical for reranking, answer grounding, and future interpretability studies.[cite:10][cite:31]

### Layer 4: Retrieval engine

The retrieval layer should be hybrid by default and adaptive by design.[cite:1][cite:31][cite:32] That means combining lexical retrieval, dense retrieval, late-interaction retrieval, multimodal page retrieval, and graph or vectorless lookups behind a planner that selects the best path for the query.[cite:1][cite:31][cite:32]

Recommended retrieval stack:

| Retrieval path | Best-fit tools or model class | Role in system |
|---|---|---|
| Lexical | BM25 / SPLADE-style sparse search | Strong exact-match, entity, and term-sensitive retrieval. |
| Dense semantic | High-quality embedding model | Broad semantic recall over clean text chunks. |
| Late interaction | ColBERT-style / late-interaction retriever | Fine-grained ranking for long passages and precision-critical search. |
| Visual document retrieval | ColPali [cite:32] | Retrieval over visual pages and layout-heavy documents. |
| Efficient visual retrieval | HPC-ColPali [cite:33] | Practical compression and performance gains for multimodal retrieval. |
| Graph retrieval | Section/page/entity graph traversal | Useful for references, citation chains, and structured navigation. |
| Vectorless or PageIndex fallback | PageIndex-like route [cite:1] | Better transparency and robustness on some hard queries. |

The planner should route queries based on query type: exact fact lookup, table lookup, diagram query, citation chase, multi-hop synthesis, or exploratory search.[cite:1][cite:31][cite:32] This is where agentic retrieval becomes materially useful rather than ornamental.[cite:1][cite:31]

### Layer 5: Reranking and evidence consolidation

Reranking should combine cross-encoder or LLM scoring with modality-aware fusion. Standard top-k concatenation is too weak for complex documents and often destroys signal ordering.[cite:1][cite:31] The evidence layer should merge overlapping hits, preserve provenance, cluster corroborating evidence, and identify conflict between sources before generation begins.[cite:1][cite:10]

The evidence object passed downstream should include:

- Source chunks with scores from each retrieval path.
- Page thumbnails or page IDs for visual results.[cite:32]
- Structured table extracts when evidence came from a table.[cite:10]
- Citation links for research material.[cite:3]
- Conflict and redundancy annotations.
- Confidence estimate for answerability.

### Layer 6: Reasoning and communication

This layer should not only answer questions; it should communicate knowledge between subsystems and to end users in structured ways.[cite:1][cite:3] A retrieval system becomes more reliable when it can explain which representation found the answer, what evidence supports it, what uncertainty remains, and which follow-up retrieval step would improve confidence.[cite:1][cite:31]

Recommended communication objects:

- `retrieval_trace.json`: full route taken by the planner.
- `evidence_bundle.json`: normalized evidence with provenance and scores.
- `knowledge_card.json`: final structured answer with claims, support, ambiguity, and citations.
- `document_profile.json`: corpus-level structure, topics, entities, and complexity diagnostics.

This turns retrieval into a transparent and debuggable knowledge system rather than a black-box prompt stuffing pipeline.[cite:1][cite:31]

## Best stack choices

### Languages and core runtime

- Python for ingestion, parsing, retrieval orchestration, evaluation, and research iteration.
- Rust for latency-sensitive indexing, patch compression, reranking kernels, and memory-efficient retrieval services.
- TypeScript for developer tools, dashboards, and corpus inspection UIs.
- PyTorch for training or adapting retrieval, reranking, and chunk-routing models.

This split gives the fastest route to research iteration without sacrificing long-term performance for production indexing and serving.

### Storage and indexing

| Storage need | Best choice | Rationale |
|---|---|---|
| Raw document artifacts | Object storage / filesystem blobs | Needed for PDFs, page images, OCR outputs. |
| Metadata and provenance | PostgreSQL | Strong transactional schema for documents, pages, chunks, entities, and traces. |
| Lexical index | Elasticsearch or OpenSearch | Mature BM25 and hybrid retrieval integration. |
| Dense ANN index | Qdrant or Faiss-backed service | Strong vector retrieval ergonomics and performance. |
| Late-interaction store | Custom compressed token index | Needed for ColBERT-like and HPC-ColPali-like serving. |
| Graph layer | Postgres graph tables or Neo4j if needed | Useful for page, entity, citation, and section graph traversal. |
| Cache | Redis | Query-result, rerank, and planner cache. |

The strongest practical stack is PostgreSQL + OpenSearch + Qdrant + custom late-interaction store + object storage. This gives broad capability without overfitting the platform to one retrieval paradigm.

### Models and algorithmic preferences

The stack should remain model-agnostic at interfaces, but the architecture should prioritize the following categories because they directly connect to earlier work:[cite:1][cite:10][cite:31][cite:32][cite:33]

- OCR ensemble with multimodal fallback.[cite:10]
- ColPali for visual retrieval on PDFs and scanned pages.[cite:32]
- HPC-ColPali when scaling visual retrieval under real memory and latency constraints.[cite:33]
- Late chunking and MoE chunking for adaptive segmentation.[cite:31]
- Hybrid lexical+dense+late-interaction retrieval.[cite:31]
- Agentic planner for retrieval path selection and decomposition.[cite:1][cite:31]
- Vectorless or PageIndex-style interpretable lookup path as a non-embedding baseline and fallback.[cite:1]

## Open-source repo plan

### Monorepo structure

```text
retrieval-os/
  apps/
    inspector-ui/
    benchmark-dashboard/
  services/
    ingest-service/
    retrieval-service/
    rerank-service/
    planner-service/
    evaluation-service/
  libs/
    doc-schema/
    chunking/
    visual-retrieval/
    hybrid-retrieval/
    provenance/
    metrics/
  research/
    experiments/
    notebooks/
    paper-assets/
  datasets/
    manifests/
    eval-sets/
  docs/
    architecture/
    benchmarks/
    tutorials/
```

This structure cleanly separates production services, research experiments, reusable libraries, and paper assets while keeping evaluation as a first-class concern.

### Minimum lovable product

The first version should not attempt to solve every modality at once. The best MVP is a hard-document retrieval benchmark and system that can ingest PDFs, run OCR ensemble extraction, produce adaptive chunks, index them in hybrid form, and answer document questions with visible retrieval traces.[cite:10][cite:31][cite:32]

MVP features:

- PDF ingestion and page rendering.[cite:10]
- OCR ensemble plus fallback routing.[cite:10]
- Structured document schema with page, block, table, figure, and section objects.[cite:10]
- BM25 + dense retrieval baseline.
- ColPali visual retrieval for page-level search.[cite:32]
- Retrieval planner with rule-based routing to start, learned routing later.[cite:1][cite:31]
- Evaluation harness with accuracy, latency, memory, and cost reports.[cite:33]
- UI that shows answer, evidence, pages, and retrieval trace.

### Phase roadmap for product

#### Phase 0: Foundation

- Define canonical document schema.
- Build corpus manifest format.
- Implement page rendering and OCR orchestration.[cite:10]
- Add metadata store and provenance logging.
- Create reproducible evaluation harness from day one.

#### Phase 1: Strong baseline

- Add lexical and dense retrieval.
- Add section-aware and late chunking.[cite:31]
- Build baseline reranking and grounded QA.
- Add dataset slices: research papers, invoices/forms, reports, scanned notes.

#### Phase 2: Multimodal leap

- Integrate ColPali for visual page retrieval.[cite:32]
- Add layout-region retrieval and page-level evidence visualization.[cite:32]
- Build hard-page fallback to multimodal parsing.[cite:10]
- Add HPC-ColPali or equivalent compression path for serving efficiency.[cite:33]

#### Phase 3: Adaptive intelligence

- Introduce MoE chunk router.[cite:31]
- Add planner-based retrieval path selection.[cite:1][cite:31]
- Add graph or PageIndex retrieval branch.[cite:1]
- Fuse evidence across modalities and representations.

#### Phase 4: Knowledge system

- Add entity, citation, and section graph extraction.[cite:3]
- Build corpus memory and cross-document reasoning workflows.
- Add knowledge communication objects and downstream APIs.
- Expose tracing, debugging, and observability for retrieval decisions.

#### Phase 5: Research-grade platform

- Benchmark against standard RAG baselines on hard corpora.[cite:1][cite:31][cite:32]
- Release datasets, error taxonomy, and ablation suite.
- Publish model cards and system cards for retrieval pathways.
- Optimize hot paths in Rust and deploy scalable services.

## Evaluation framework

Accuracy alone is not enough. The project should optimize jointly for answer quality, evidence quality, retrieval recall, interpretability, latency, throughput, storage cost, and memory efficiency.[cite:33] This matters because earlier work already emphasized performance and cost tradeoffs, especially for HPC-ColPali and advanced retrieval pipelines.[cite:33]

Recommended metrics:

| Category | Metrics |
|---|---|
| Retrieval quality | Recall@k, nDCG@k, MRR, page hit rate, region hit rate |
| Answer quality | Exact match, F1, citation support rate, groundedness |
| Document extraction | OCR CER/WER, table fidelity, equation fidelity, region alignment |
| System performance | P50/P95 latency, throughput, GPU memory, index size |
| Economic efficiency | Cost/query, cost/indexed page, compression ratio |
| Interpretability | Trace completeness, evidence agreement, planner correctness |

The benchmark corpus should include born-digital papers, scanned documents, mixed-layout enterprise PDFs, tables, formulas, and visually dense pages because these are exactly the cases where standard RAG pipelines break.[cite:10][cite:32]

## Research paper roadmap

### Paper objective

The research paper should argue that retrieval quality improves substantially when documents are processed and stored as multimodal, structured, multi-representation knowledge objects rather than flattened text chunks.[cite:1][cite:10][cite:31][cite:32] The paper should also show that adaptive routing across retrieval methods beats one-size-fits-all ANN retrieval on hard document workloads.[cite:1][cite:31][cite:33]

### Candidate paper titles

- Beyond Text Chunks: A Unified Multimodal Retrieval Architecture for Complex Documents
- Retrieval OS: Adaptive Multi-Representation Retrieval for Hard Documents
- From OCR to Knowledge Graphs: Rethinking Retrieval for Complex Document Corpora
- StructRAG: Layout-Aware, Multimodal, and Agentic Retrieval for Document Intelligence

### Main research questions

- How much information is lost when visually rich documents are flattened into plain text before retrieval?[cite:10][cite:32]
- When do multimodal page retrieval methods such as ColPali outperform text-only retrieval?[cite:32]
- Does adaptive chunk routing outperform fixed chunking on heterogeneous documents?[cite:31]
- Can agentic or planner-based retrieval routing beat static hybrid retrieval in both accuracy and efficiency?[cite:1][cite:31]
- What is the cost-performance frontier introduced by HPC-ColPali-style compression and similar optimizations?[cite:33]
- When do PageIndex or vectorless retrieval methods provide superior transparency or robustness relative to dense-only systems?[cite:1]

### Core hypotheses

1. Multi-representation storage improves retrieval recall and answer grounding over single-representation text RAG.[cite:1][cite:31][cite:32]
2. Adaptive chunking improves evidence quality on heterogeneous documents over fixed token chunking.[cite:31]
3. Multimodal page retrieval is especially beneficial on tables, diagrams, equations, and visually structured layouts.[cite:10][cite:32]
4. Planner-routed retrieval reduces unnecessary compute while increasing answerability on hard queries.[cite:1][cite:31]
5. Compression-aware visual retrieval can preserve most of the quality gains while making deployment practical.[cite:33]

### Experimental design

A strong paper should include:

- Baselines: BM25, dense-only RAG, standard hybrid RAG, text-only chunking pipelines.
- Retrieval variants: late chunking, MoE chunking, ColPali, HPC-ColPali, PageIndex-like fallback, planner-routed hybrid retrieval.[cite:1][cite:31][cite:32][cite:33]
- Corpora: research papers, enterprise reports, forms, scanned PDFs, visually rich technical documents.[cite:10][cite:32]
- Tasks: question answering, page retrieval, table lookup, citation chase, multi-hop synthesis, evidence-grounded summarization.
- Ablations: remove visual retrieval, remove planner, remove graph path, replace MoE chunking with fixed windows, disable OCR ensemble.[cite:10][cite:31][cite:32][cite:33]

### Paper outline

#### 1. Introduction

Motivate why current RAG systems fail on hard documents because extraction, chunking, indexing, and reasoning are separated too rigidly and too early.[cite:1][cite:10][cite:32]

#### 2. Related work

Cover RAG limitations, semantic search limits, vector search tradeoffs, multimodal retrieval, agentic retrieval, chunking methods, and document OCR pipelines.[cite:1][cite:10][cite:31][cite:32][cite:33]

#### 3. System

Describe the unified stack: OCR ensemble, canonical schema, adaptive chunking, multi-representation indexing, planner-routed retrieval, evidence consolidation, and communication artifacts.[cite:10][cite:31][cite:32]

#### 4. Experimental setup

Define corpora, tasks, metrics, baselines, compute budgets, and implementation details.[cite:33]

#### 5. Results

Show quality, latency, memory, and cost tradeoffs, not just answer metrics.[cite:33]

#### 6. Analysis

Include failure taxonomy: OCR failure, layout misunderstanding, chunk misrouting, visual retrieval misses, planner errors, grounding errors.

#### 7. Conclusion

Argue for retrieval as a multi-stage knowledge systems problem, not just a vector database problem.[cite:1][cite:31]

## Important concepts that should not be dropped

To preserve the full value of earlier work, the following concepts should remain in scope because each one can materially improve the project or paper:[cite:1][cite:3][cite:10][cite:31][cite:32][cite:33]

- Retrieval research as a core identity, not a side feature.[cite:4]
- Limits of standard RAG and vector-search-first pipelines.[cite:1]
- PageIndex and vectorless retrieval as interpretable alternatives or fallbacks.[cite:1]
- Agentic or reasoning-based retrieval routing.[cite:1][cite:31]
- OCR ensembles and multimodal document parsing.[cite:10]
- Research-paper formatting and agent-ready paper processing.[cite:3]
- Late chunking and semantic-aware splitting.[cite:31]
- Mixture-of-experts chunking.[cite:31]
- ColPali for page-image retrieval.[cite:32]
- HPC-ColPali for compression and practical deployment.[cite:33]
- Performance, cost, and memory efficiency as first-class evaluation targets.[cite:33]
- Provenance, traces, and communication artifacts for trustworthy retrieval.[cite:1][cite:31]

## Team and execution plan

### Roles to cover

- Retrieval research lead
- Document intelligence and OCR pipeline lead
- Systems and indexing engineer
- Evaluation and benchmarking lead
- Frontend or tooling engineer for inspector UI
- Paper-writing and experiment documentation lead

### First 90 days

- Finalize architecture and schemas.
- Stand up ingestion, OCR ensemble, and metadata storage.[cite:10]
- Build baseline benchmark corpus and evaluation harness.
- Implement lexical+dense hybrid retrieval.
- Add adaptive chunking baseline from late chunking and section-aware routing.[cite:31]
- Release v0 open-source repo with reproducible baseline.

### Next 90 days

- Integrate ColPali and visual page retrieval.[cite:32]
- Add hard-document datasets and visual evidence viewer.
- Add planner-based routing and richer provenance traces.[cite:1][cite:31]
- Implement HPC-ColPali-inspired compression path.[cite:33]
- Start paper experiments and ablation matrix.

### 6-12 months

- Expand to graph and vectorless retrieval branches.[cite:1]
- Train or distill chunk router and planner models.
- Publish benchmark suite and first paper.
- Harden services for external contributors and production-scale corpora.

## Final recommendation

The strongest possible direction is to build an open-source **retrieval operating system for complex documents**: multimodal ingestion, adaptive chunking, hybrid and planner-routed retrieval, transparent evidence consolidation, and research-grade evaluation.[cite:1][cite:10][cite:31][cite:32][cite:33] This direction captures nearly all valuable themes found across prior work while maximizing both scientific novelty and practical usefulness.[cite:1][cite:4][cite:10][cite:31][cite:32][cite:33]
