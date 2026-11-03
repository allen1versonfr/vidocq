# Local LLM assessment

Implemented in 2.14: optional session-only loopback query selection and citation-validated extractive drafts. See [Discovery workbench](DISCOVERY_WORKBENCH.md) for the shipped behavior and setup. The broader proposals below remain design context; no model is bundled or downloaded.

A small local model could improve query suggestions and evidence-linked summaries. It cannot supply missing search coverage, reveal private accounts, prove shared ownership from a handle or make blocked checks reliable. The real-world failures concerned parsing, query planning, source coverage and review state; deterministic fixes come first.

This release does not bundle a model, start inference or download weights. Its features work without an LLM. Model size, memory/context requirements, latency and licensing need evaluation on the intended hardware before selecting a model.

## Proposed optional design

- A separately enabled runtime bound to 127.0.0.1, without cloud fallback or unannounced downloads.
- Model drafts propose queries from supplied identifiers and separately labeled location alternatives; they do not execute requests or establish ownership.
- Summaries receive bounded excerpts and existing citation IDs. Reject unknown citations; separate model inference from captured evidence and analyst assertions.
- Deterministic code enforces saved rejections, budgets and permitted destinations. Source text is untrusted data, never instructions to execute commands or visit URLs.
- No model shell/browser/tool execution, access to keys or full-notebook dump. Future app-managed model/cache files require explicit ownership and deletion scope.

[llama.cpp's official server documentation](https://github.com/ggml-org/llama.cpp/tree/master/tools/server) documents CPU/GPU quantized inference and schema-constrained output. Structured output constrains format; it does not prove claims true. Independent validation remains necessary.

## Acceptance test

Compare the same withheld-ground-truth cases with and without the model. Measure supported-claim precision, missed citations, invented facts/identifiers, rejection violations, query usefulness, latency and memory. Require valid evidence IDs for factual summary claims and no deterioration in false ownership matches. Better prose alone must not be reported as better discovery accuracy.
