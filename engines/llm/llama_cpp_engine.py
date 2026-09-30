"""llama.cpp（GGUF 量化模型）。PC 用 CPU wheel；Jetson 用 CUDA 版（n_gpu_layers=-1）。"""
from engines.base import LLMEngine


class LlamaCppLLM(LLMEngine):
    def __init__(self, repo_id, filename, n_ctx=2048, n_threads=None, n_gpu_layers=0):
        super().__init__()
        self.repo_id = repo_id
        self.filename = filename      # 可用 glob，例如 "*Q4_K_M.gguf"
        self.n_ctx = n_ctx
        self.n_threads = n_threads
        self.n_gpu_layers = n_gpu_layers

    def load(self):
        from llama_cpp import Llama
        self.llm = Llama.from_pretrained(
            repo_id=self.repo_id, filename=self.filename, n_ctx=self.n_ctx,
            n_threads=self.n_threads, n_gpu_layers=self.n_gpu_layers, verbose=False,
        )

    def close(self):
        # 明確釋放模型記憶體（GGUF 權重可達數 GB）
        if getattr(self, "llm", None) is not None:
            self.llm.close()
            self.llm = None

    def chat_stream(self, messages, max_tokens=160, temperature=0.3):
        stream = self.llm.create_chat_completion(
            messages=messages, max_tokens=max_tokens, temperature=temperature, stream=True,
        )
        for chunk in stream:
            delta = chunk["choices"][0].get("delta", {}).get("content")
            if delta:
                yield delta
