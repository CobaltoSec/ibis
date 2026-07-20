from __future__ import annotations
import json
import subprocess

REPO_MAP: dict[str, str] = {
    # huntr scope
    "LibreChat": "danny-avila/LibreChat",
    "anything-llm": "Mintplex-Labs/anything-llm",
    "ComfyUI": "comfyanonymous/ComfyUI",
    "langflow": "langflow-ai/langflow",
    "open-webui": "open-webui/open-webui",
    "invokeai": "invoke-ai/InvokeAI",
    "InvokeAI": "invoke-ai/InvokeAI",
    "lollms-webui": "ParisNeo/lollms-webui",
    "text-generation-webui": "oobabooga/text-generation-webui",
    "dify": "langgenius/dify",
    "ragflow": "infiniflow/ragflow",
    "flowise": "FlowiseAI/Flowise",
    "Flowise": "FlowiseAI/Flowise",
    "vllm": "vllm-project/vllm",
    "bentoml": "bentoml/BentoML",
    "chroma": "chroma-core/chroma",
    "LocalAI": "mudler/LocalAI",
    "localai": "mudler/LocalAI",
    "ollama": "ollama/ollama",
    "Ollama": "ollama/ollama",
    "tabby": "TabbyML/tabby",
    "litellm": "BerriAI/litellm",
    "LiteLLM": "BerriAI/litellm",
    "stable-diffusion-webui": "AUTOMATIC1111/stable-diffusion-webui",
    "llama.cpp": "ggerganov/llama.cpp",
    # GHSA targets (no huntr program)
    "cheshire-cat": "cheshire-cat-ai/core",
    "cheshire-cat-ai": "cheshire-cat-ai/core",
    "superagi": "TransformerOptimus/SuperAGI",
    "SuperAGI": "TransformerOptimus/SuperAGI",
    "letta": "letta-ai/letta",
    "letta-ai": "letta-ai/letta",
    "autogen": "microsoft/autogen",
    "autogen-studio": "microsoft/autogen",
    "llama-index": "run-llama/llama_index",
    "llama_index": "run-llama/llama_index",
    "agno": "agno-agi/agno",
    "crewai": "crewAIInc/crewAI",
    "smolagents": "huggingface/smolagents",
    "openhands": "All-Hands-AI/OpenHands",
    "MaxKB": "1Panel-dev/MaxKB",
    "maxkb": "1Panel-dev/MaxKB",
    "LlamaFactory": "hiyouga/LlamaFactory",
    "llamafactory": "hiyouga/LlamaFactory",
    "kotaemon": "Cinnamon/kotaemon",
    "h2o-llmstudio": "h2oai/h2o-llmstudio",
    "h2ollmstudio": "h2oai/h2o-llmstudio",
}


def resolve_repo(target: str, explicit: str | None = None) -> str | None:
    """Resolve target → GitHub owner/repo.

    Priority: explicit → already owner/repo format → exact map → case-insensitive map.
    """
    if explicit:
        return explicit
    if "/" in target:
        return target
    if target in REPO_MAP:
        return REPO_MAP[target]
    t = target.lower()
    for k, v in REPO_MAP.items():
        if k.lower() == t:
            return v
    return None


def resolve_top_contributor(repo: str) -> str | None:
    """Return GitHub login of the top contributor for a repo, or None on failure."""
    result = subprocess.run(
        ["gh", "api", f"repos/{repo}/contributors?per_page=1"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        return None
    try:
        data = json.loads(result.stdout)
        return data[0]["login"] if data and isinstance(data, list) else None
    except (json.JSONDecodeError, KeyError, IndexError):
        return None
