EVAL_INPUT ?= testcase/manual_test_3.csv
RETRIEVAL_MAX_K ?= 30
QDRANT_HOST ?= localhost
RERANK_DEVICE ?= cuda
HYBRID_WORKERS ?= 10
RERANK_WORKERS ?= 1
SEMANTIC_WEIGHT ?= 0.6

.PHONY: help eval retrieval-tuning retrieval-hybrid-tuning retrieval-rerank-tuning

help:
	@echo "Available targets:"
	@echo "  make eval             - run evaluation with uv (EVAL_INPUT=path/to/file.csv)"
	@echo "  make retrieval-tuning - run retrieval tuning with uv"
	@echo "  make retrieval-hybrid-tuning - run hybrid alpha/k tuning"
	@echo "  make retrieval-rerank-tuning - run rerank k tuning"

eval:
	uv run python run_eval.py --input $(EVAL_INPUT)

retrieval-tuning:
	uv run python run_retrieval_tuning.py --max-k $(RETRIEVAL_MAX_K) --qdrant-host $(QDRANT_HOST) --rerank-device $(RERANK_DEVICE) --hybrid-workers $(HYBRID_WORKERS) --rerank-workers $(RERANK_WORKERS)

retrieval-hybrid-tuning:
	uv run python run_retrieval_hybrid_tuning.py --max-k $(RETRIEVAL_MAX_K) --qdrant-host $(QDRANT_HOST) --workers $(HYBRID_WORKERS)

retrieval-rerank-tuning:
	uv run python run_retrieval_rerank_tuning.py --max-k $(RETRIEVAL_MAX_K) --qdrant-host $(QDRANT_HOST) --rerank-device $(RERANK_DEVICE) --semantic-weight $(SEMANTIC_WEIGHT) --workers $(RERANK_WORKERS)
