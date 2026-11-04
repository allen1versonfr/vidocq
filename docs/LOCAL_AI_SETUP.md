# Managed local AI setup (2.16)

Vidocq remains a portable Windows application. Its first-run notice and Updates screen open **Search connection → Install recommended local AI**. No separate Python, terminal commands, API account or paid service are required. The base executable does not contain model weights.

1. Read the download size/licenses, choose Vulkan (recommended for Radeon RX 7600 XT) or CPU, and approve setup.
2. Click **Install / repair local AI**. Vidocq downloads/verifies llama.cpp b12079 and Qwen3-4B-Instruct-2507 Q4_K_M (about 2.54 GB combined; allow about 3 GB free disk space). Progress is shown. Cancel leaves partial downloads for a later retry; cancellation can wait for an in-flight network operation (30-second socket timeout) or model check (45-second timeout).
3. Setup checks a synthetic response without case data, stops that test runtime to free memory, and enables on-demand local drafts. Manual drafts need their own approval. AI-assisted cases approve bounded planning/search/link-selection/synthesis through their case settings.

Your 16 GB RAM/Radeon configuration should suit this small model. Vulkan uses available compatible GPUs; CPU is retried if GPU startup fails. Existing graphics drivers and Windows runtime support are required; setup does not install drivers or system redistributables. If neither backend starts, Vidocq reports failure and leaves the AI disabled. No cloud fallback is used. This is a starting hardware profile, not a guarantee of performance on every driver/PC.

## Updates and storage

Model/runtime files live in the workspace's `local-ai` directory and preferences in `local-ai.json`. App executable updates and rollback leave these files intact. On restart settings are restored but no server starts until an approved draft or AI-assisted case. **Use installed AI** re-enables it, **Disable and stop AI** releases its process without deleting downloaded files. A normal app update never silently downloads a model/runtime replacement. Setup checks pinned versions and reuses verified files; future asset changes need the explicit setup/repair action.

Runtime/model URLs, revisions, byte counts, ZIP member inventory and SHA-256 values are pinned in `local_ai_assets.py`. Downloads accept only reviewed GitHub/Hugging Face hosts, validate range responses when resuming, and install files only after checksum verification. Runtime executable/DLLs and the model are reverified before starting a new managed process. Extra unowned DLLs/executables cause refusal rather than being loaded or deleted. Repair replaces known damaged files; move unrelated executable files out of the managed runtime folder yourself.

Inference binds to 127.0.0.1 on an ephemeral port, uses a fresh session API key supplied through the child environment, disables its web UI/logging and uses offline mode. Context is limited to 8,192 tokens with one server slot. Windows job-object lifecycle protection terminates the managed process tree on app exit, including forced termination. Manually configured external runtimes remain independent and are never stopped/deleted by Vidocq.

Burn Vidocq previews known managed model/runtime/configuration/partial-download paths alongside workspace files. It deletes only those exact paths after shutdown and preserves unknown files. Downloads saved elsewhere, provider-side download records and external model servers remain outside its scope. Setup must finish/cancel before applying an update or burning the app. AI files are not included in notebook backups; install them separately on another PC.

## Sources and licenses

- [llama.cpp pinned b12079 release](https://github.com/ggml-org/llama.cpp/releases/tag/b12079): MIT, with bundled LLVM/OpenMP notices. This is a reviewed pinned upstream nightly, not an automatically selected latest release.
- [Qwen model](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507): Apache-2.0.
- [Pinned LM Studio Community GGUF conversion](https://huggingface.co/lmstudio-community/Qwen3-4B-Instruct-2507-GGUF/tree/4edb920b6f14e3b9284d4502a6485103d72cde05).
- Full notices are available in the setup screen and [LOCAL_AI_LICENSES.txt](LOCAL_AI_LICENSES.txt).

## Validation

Unit tests use tiny synthetic downloads to exercise resume/restart, checksum refusal, cancellation, safe extraction, persisted settings, on-demand startup, CPU fallback and lifecycle protection. Frozen CI checks approval/default-off APIs and preservation of synthetic AI files across app replacement and rollback without downloading 2.5 GB per build. An optional local test, `scripts/live_local_ai_smoke.py --data .test-data/real-local-ai/data`, exercises actual inference/auth/lifecycle with an already installed disposable model. It refuses live workspace paths. Real local tests use only synthetic case content; these checks are not investigation accuracy benchmarks.

## AI-assisted cases

Enable AI-assisted investigation in a case to execute validated selections from supplied query combinations, select explicit cited profile links, and draft source-based findings. Search/follow-up limits and source permissions still apply. Read [the pipeline and validation limits](AUTOMATED_SETUP.md#the-ai-now-participates-in-a-case).
