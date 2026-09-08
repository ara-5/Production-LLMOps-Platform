"""OpenTelemetry GenAI semantic-convention attribute keys, plus this
platform's own `llmops.*` extension keys for fields not yet standardized
(cost, ttft, retrieval, thinking/effort)."""

# --- OTel GenAI semantic conventions ---
GEN_AI_SYSTEM = "gen_ai.system"
GEN_AI_OPERATION_NAME = "gen_ai.operation.name"
GEN_AI_REQUEST_MODEL = "gen_ai.request.model"
GEN_AI_REQUEST_MAX_TOKENS = "gen_ai.request.max_tokens"
GEN_AI_RESPONSE_MODEL = "gen_ai.response.model"
GEN_AI_RESPONSE_FINISH_REASONS = "gen_ai.response.finish_reasons"
GEN_AI_USAGE_INPUT_TOKENS = "gen_ai.usage.input_tokens"
GEN_AI_USAGE_OUTPUT_TOKENS = "gen_ai.usage.output_tokens"

# --- llmops.* extensions ---
LLMOPS_USAGE_CACHE_READ_TOKENS = "llmops.usage.cache_read_input_tokens"
LLMOPS_USAGE_CACHE_CREATION_TOKENS = "llmops.usage.cache_creation_input_tokens"
LLMOPS_COST_USD = "llmops.cost.usd"
LLMOPS_TTFT_MS = "llmops.ttft_ms"
LLMOPS_TOKENS_PER_SEC = "llmops.tokens_per_sec"
LLMOPS_EFFORT = "llmops.effort"
LLMOPS_THINKING_TYPE = "llmops.thinking.type"
LLMOPS_RETRIEVAL_DOC_IDS = "llmops.retrieval.doc_ids"
LLMOPS_RETRIEVAL_SCORES = "llmops.retrieval.scores"

ANTHROPIC_SYSTEM = "anthropic"
