# AURA four-paper agent report

Workflow: `738f04c8-dc67-43ba-8f0e-4bc40c9d645e`; state: **COMPLETED**

## Transformer

The Transformer replaces recurrent and convolutional sequence processing with attention that directly models global input-output dependencies. The paper claims this architecture improves training parallelism and achieves state-of-the-art translation quality after only twelve hours on eight P100 GPUs.

- Source quote: “relying entirely on an attention mechanism to draw global dependencies between input and output.” ([paper](https://arxiv.org/abs/1706.03762), chunk `df46b8be-3b58-5777-afe1-7c64d6257ccd`)

## RAG

RAG couples a pre-trained seq2seq generator’s parametric knowledge with Wikipedia passages retrieved from a dense vector index. It supports sequence-level or token-level passage conditioning and jointly trains retrieval and generation, improving knowledge-intensive QA and factual generation. For AURA, this suggests grounding generated answers in an updateable project-document index while retaining the language model’s generative capabilities.

- Source quote: “the parametric
memory is a pre-trained seq2seq model and the non-parametric memory is a dense” ([paper](https://arxiv.org/abs/2005.11401), chunk `13a98984-2096-58b8-8276-5d105247116c`)

## ReAct

ReAct interleaves verbal reasoning traces with task-specific actions. Reasoning creates and revises plans, while actions gather external information that informs subsequent reasoning. Its central contribution is a unified reasoning-and-acting loop that improves grounding and interpretability. For AURA, this supports an agent design that alternates planning, tool use, and observation-driven plan updates.

- Source quote: “prompts LLMs to generate both verbal reasoning traces and actions pertaining to a task” ([paper](https://arxiv.org/abs/2210.03629), chunk `82563abe-ccd5-59ac-9586-7c4cd35948ae`)

## Self-RAG

Self-RAG adaptively predicts a Retrieve reflection token from the prompt and current generation. When retrieval is triggered, it generates passage-conditioned candidates, critiques their relevance, support, and usefulness, then ranks candidates during segment-level decoding. Its contribution is replacing fixed retrieval with selective retrieval and self-evaluation to improve factuality and verifiability.

- Source quote: “SELF-RAG dynamically decides when to retrieve text passages by
predicting Retrieve .” ([paper](https://arxiv.org/abs/2310.11511), chunk `0190f982-4d78-54cf-90ed-8f1068f682ef`)

## Comparative synthesis

The papers form a complementary architecture for AURA. The Transformer supplies the language-model foundation by modeling global dependencies through attention. RAG extends that foundation with parametric and external non-parametric memory, suggesting an index of updateable project documents. ReAct adds an iterative reasoning-and-action loop, supporting planning, tool execution, and observation-driven revision. Self-RAG further makes retrieval conditional rather than automatic, suggesting AURA should retrieve only when needed and evaluate retrieved support before answering. Together, they imply four layers: Transformer generation, RAG grounding, ReAct tool orchestration, and Self-RAG retrieval control. RAG and ReAct address different needs: RAG supplies knowledge, while ReAct governs interaction with external capabilities.

## Verification

{
  "outcome": "PASS",
  "criteria": [
    {
      "criterion": "citation_and_quote",
      "outcome": "PASS"
    },
    {
      "criterion": "citation_and_quote",
      "outcome": "PASS"
    },
    {
      "criterion": "citation_and_quote",
      "outcome": "PASS"
    },
    {
      "criterion": "citation_and_quote",
      "outcome": "PASS"
    },
    {
      "criterion": "citation_and_quote",
      "outcome": "PASS"
    },
    {
      "criterion": "citation_and_quote",
      "outcome": "PASS"
    },
    {
      "criterion": "citation_and_quote",
      "outcome": "PASS"
    },
    {
      "criterion": "citation_and_quote",
      "outcome": "PASS"
    },
    {
      "criterion": "citation_and_quote",
      "outcome": "PASS"
    },
    {
      "criterion": "citation_and_quote",
      "outcome": "PASS"
    },
    {
      "criterion": "citation_and_quote",
      "outcome": "PASS"
    },
    {
      "criterion": "citation_and_quote",
      "outcome": "PASS"
    },
    {
      "criterion": "citation_and_quote",
      "outcome": "PASS"
    },
    {
      "criterion": "citation_and_quote",
      "outcome": "PASS"
    },
    {
      "criterion": "citation_and_quote",
      "outcome": "PASS"
    },
    {
      "criterion": "citation_and_quote",
      "outcome": "PASS"
    },
    {
      "criterion": "Evidence references and exact quotes are valid.",
      "outcome": "PASS"
    }
  ],
  "limitations": [
    "Exact quotes and explicit numeric relations verified; general semantic entailment is not established."
  ]
}
