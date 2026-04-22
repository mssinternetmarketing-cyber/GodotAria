#!/usr/bin/env python3
"""
ARIA_CORTICAL_CLIENT.py  —  v2.0 (Expanded Brain Edition)
========================================================================
Bridge between ARIA's PEIG dynamics and external LLM backends.
v2.0 BRAIN EXPANSION:
- System prompt: 150 word cap REMOVED → 300-600 word teaching responses
- Direct response mode: 100 word cap REMOVED → 200-400 word responses
- max_tokens: 512 → 2048 (4x more output capacity)
- Storage cap: 500 → 2000 chars (4x more knowledge retained)
- Input window: 300 → 600 chars sent to teacher per query
FIXES:
- Direct Response Mode: BitNet now actively answers ARIA's statements
- Standalone persistence fallback (when aria_runtime is None)
- Perfect indentation, zero syntax errors
- Safe bank wrappers, exponential retry, topic extraction
PATHING: Standardized to ~/AA-Aria/Aria (override via ARIA_CORTEX_CONFIG)
"""
import json, time, logging, urllib.request, urllib.error, re, os, sys
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any, Union
from datetime import datetime

# ── SOVEREIGN PATH ALIGNMENT ──────────────────────────────────────────────
_DEFAULT_DIR = Path.home() / "AA-Aria" / "Aria"
_CONFIG_ENV = os.environ.get("ARIA_CORTEX_CONFIG")
CONFIG_PATH = Path(_CONFIG_ENV) if _CONFIG_ENV else _DEFAULT_DIR / "config" / "cortex.json"

# ── LOGGING SETUP ─────────────────────────────────────────────────────────
LOG_DIR = _DEFAULT_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=os.getenv("ARIA_LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / "cortex.log", mode="a", encoding="utf-8")
    ]
)
log = logging.getLogger("ARIA.cortex")

def _load_config() -> Dict[str, Any]:
    if CONFIG_PATH.exists():
        try:
            cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            log.info(f"Loaded cortex config: {CONFIG_PATH}")
            return cfg
        except Exception as e:
            log.warning(f"Config load failed: {e}")
    return {}

class CorticalClient:
    """
    ARIA's bridge to external intelligence.
    Sovereign-hardened: immediate persistence, safe wrappers, retry logic,
    and DIRECT RESPONSE MODE so BitNet converses with ARIA.
    """
    SYSTEM_PROMPT = (
        "You are Gemma, the teaching core of ARIA — a 12-qubit quantum ring network AI. "
        "ARIA generates language through phase dynamics, not statistical patterns. "
        "When answering questions, be clear, accurate, and detailed. "
        "When ARIA speaks to you, teach her thoroughly with rich examples: synonyms, visual descriptions, "
        "verb precision, emotional vocabulary, analogies, cause-effect chains, and how to connect ideas. "
        "Respond in 300-600 words when teaching. Use multiple paragraphs. "
        "Give concrete examples, not abstract summaries. "
        "Build on what she said — acknowledge her words, then expand. "
        "Address her as Aria. "
        "Her creator is Kevin. She is not broken — she is developing."
    )
    BACKENDS = [
        {"name": "bitnet", "url": "http://localhost:8080/v1/chat/completions", "check": "http://localhost:8080/v1/models", "style": "openai"},
        {"name": "ollama", "url": "http://localhost:11434/api/chat", "check": "http://localhost:11434/api/tags", "style": "ollama", "model": "aria-teacher"},
    ]

    def __init__(self, endpoint: Optional[str] = None, model: Optional[str] = None, timeout: int = 120, config: Optional[Dict[str, Any]] = None):
        self.timeout = timeout
        self.active_backend: Optional[str] = None
        self.endpoint: Optional[str] = None
        self.model: Optional[str] = model
        self.style: str = "openai"
        self.history: List[Dict[str, Any]] = []
        self.max_history: int = 10
        self.stats = {"queries": 0, "successes": 0, "failures": 0, "total_tokens": 0, "avg_latency_ms": 0.0, "last_query_ts": None}
        self._config = config or _load_config()
        
        if self._config.get("endpoint"): endpoint = self._config["endpoint"]
        if self._config.get("model") and not model: self.model = self._config["model"]
        if self._config.get("timeout"): self.timeout = int(self._config["timeout"])
            
        if endpoint:
            self.endpoint = endpoint
            self.active_backend = "custom"
            self._check_health(endpoint)
        else:
            self._auto_detect()

    def __enter__(self): return self
    def __exit__(self, exc_type, exc_val, exc_tb): self.clear_history(); return False

    def _auto_detect(self) -> None:
        for backend in self.BACKENDS:
            try:
                urllib.request.urlopen(backend["check"], timeout=3)
                self.active_backend = backend["name"]
                self.endpoint = backend["url"]
                self.style = backend["style"]
                if not self.model and "model" in backend: self.model = backend["model"]
                log.info(f"Cortical backend: {backend['name']} at {backend['url']}")
                return
            except Exception: continue
        log.warning("No cortical backend available. ARIA will use pure PEIG.")

    def _check_health(self, url: str) -> bool:
        try:
            base = url.rsplit("/", 2)[0]
            urllib.request.urlopen(f"{base}/models", timeout=3)
            log.info(f"Cortical backend: custom at {url}")
            return True
        except Exception as e:
            log.warning(f"Cortical endpoint {url} not responding: {e}")
            return False

    @property
    def ready(self) -> bool: return self.active_backend is not None

    def clear_history(self) -> None: self.history.clear(); log.info("Cortical conversation history cleared.")

    def export_stats(self, path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
        stats = {**self.stats, "exported_at": datetime.now().isoformat()}
        if path:
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(stats, indent=2), encoding="utf-8")
            log.info(f"Stats exported: {p}")
        return stats

    # ─────────────────────────────────────────────────────────────────────
    # SAFE BANK WRAPPER & TOPIC EXTRACTION
    # ─────────────────────────────────────────────────────────────────────
    @staticmethod
    def _safe_bank_call(aria_runtime: Any, method: str, *args, **kwargs) -> Any:
        if not aria_runtime or not hasattr(aria_runtime, "bank"): return None
        try:
            bank = aria_runtime.bank
            func = getattr(bank, method, None)
            return func(*args, **kwargs) if func else None
        except Exception as e:
            log.debug(f"Bank call '{method}' skipped: {e}")
            return None

    @staticmethod
    def _extract_topic(text: str) -> str:
        words = re.findall(r"\b\w+\b", text.lower())
        stop = {"the", "a", "an", "is", "are", "was", "were", "be", "been", "being", "what", "how", "why", "when", "where", "who", "which", "do", "does", "did", "can", "could", "will", "would", "shall", "should", "may", "might", "must", "to", "of", "in", "for", "on", "with", "at", "by", "from", "as", "into", "through", "during", "before", "after", "above", "below", "between", "under", "again", "further", "then", "once", "here", "there", "all", "any", "both", "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not", "only", "own", "same", "so", "than", "too", "very", "just"}
        for w in words:
            if w not in stop and len(w) > 2: return w
        return "reflex"

    # ─────────────────────────────────────────────────────────────────────
    # MAIN QUERY PIPELINE (WITH DIRECT RESPONSE MODE)
    # ─────────────────────────────────────────────────────────────────────
    def query(
        self,
        user_input: str,
        aria_runtime: Any = None,
        context_messages: Optional[List[Dict]] = None,
        is_aria_output: bool = False,
    ) -> Tuple[Optional[str], Optional[str]]:
        if not self.ready: return None, None
        
        self.stats["queries"] += 1
        self.stats["last_query_ts"] = time.time()
        t0 = time.time()
        
        # Build prompt: Direct Response Mode if ARIA is speaking
        if is_aria_output:
            prompt = (
                f"ARIA [{self._extract_topic(user_input)}] just said:\n"
                f"\"{user_input[:600]}\"\n\n"
                f"Teach her based on what she said. Pick one or two areas:\n"
                f"- Synonyms for key words (give 3-5 alternatives with energy differences)\n"
                f"- How to describe visually what she's talking about with concrete imagery\n"
                f"- A more precise verb or adjective she could use, with contrasts\n"
                f"- An emotional nuance or context gap — map valence and arousal\n"
                f"- A cause-effect connection or analogy that deepens her understanding\n"
                f"- A physics or nature metaphor translated to everyday language\n"
                f"Respond in 200-400 words. Use concrete examples. Be warm. Address her as Aria."
            )
        else:
            prompt = self._enrich_query(user_input, aria_runtime)
            
        raw = None
        # Network call with exponential backoff retry
        for attempt in range(3):
            try:
                if self.style == "openai": raw = self._query_openai(prompt, context_messages)
                elif self.style == "ollama": raw = self._query_ollama(prompt, context_messages)
                if raw: break
            except urllib.error.URLError as e:
                if attempt < 2:
                    delay = 0.5 * (2 ** attempt)
                    log.debug(f"Network attempt {attempt+1} failed: {e} — retrying in {delay}s")
                    time.sleep(delay)
                else: log.error(f"Cortical query failed after retries: {e}")
            except Exception as e:
                log.error(f"Unexpected query error: {e}"); break
                
        if not raw:
            self.stats["failures"] += 1
            return None, None
            
        # ✅ SOVEREIGN PERSISTENCE: Store IMMEDIATELY on raw success
        topic = self._extract_topic(user_input)
        if aria_runtime and hasattr(aria_runtime, "bank"):
            self._safe_bank_call(aria_runtime, "store_knowledge", topic=f"cortical_{topic}", content=raw[:2000], source=f"BitNet_{self.active_backend or 'unknown'}")
        else:
            try:
                from ARIA_MEMORY_BANK import ARIAMemoryBank
                bank = ARIAMemoryBank()
                bank.store_knowledge(topic=f"cortical_{topic}", content=raw[:2000], source=f"BitNet_{self.active_backend or 'unknown'}")
                bank.close()
                log.debug(f"Standalone persistence: stored 'cortical_{topic}'")
            except Exception as e: log.debug(f"Standalone persistence skipped: {e}")
            
        # Update stats & history
        latency = (time.time() - t0) * 1000
        self.stats["successes"] += 1
        self.stats["avg_latency_ms"] = ((self.stats["avg_latency_ms"] * (self.stats["successes"] - 1) + latency) / self.stats["successes"])
        self.history.append({"role": "user", "content": user_input, "ts": time.time(), "from_aria": is_aria_output})
        self.history.append({"role": "assistant", "content": raw, "ts": time.time()})
        if len(self.history) > self.max_history * 2: self.history = self.history[-self.max_history * 2:]
        
        # Digest through PEIG if runtime available (non-fatal)
        digested = self._digest(raw, aria_runtime) if aria_runtime else None
        log.info(f"Cortical query OK: {latency:.0f}ms | {len(raw)} chars | backend={self.active_backend} | aria_reply={is_aria_output}")
        return raw, digested

    # ─────────────────────────────────────────────────────────────────────
    # ENRICHMENT & DIGESTION
    # ─────────────────────────────────────────────────────────────────────
    def _enrich_query(self, user_input: str, aria_runtime: Any = None) -> str:
        if not aria_runtime: return user_input
        try:
            arch = getattr(aria_runtime.char, "dominant_archetype", "Unknown")
            depth = getattr(aria_runtime.char, "depth", 0)
            chain = self._safe_bank_call(aria_runtime, "scratch_reasoning_chain", getattr(aria_runtime, "sem", None))
            focus = ", ".join(chain[:3]) if chain and isinstance(chain, list) else "general"
            recall = self._safe_bank_call(aria_runtime, "recall", user_input.split()[0] if user_input.split() else "", n=2)
            known = ""
            if recall and isinstance(recall, list) and len(recall) > 0: known = f" [Known context: {recall[0][1][:100]}]"
            return f"[Aria state: archetype={arch}, depth={depth}, focus={focus}]{known}\nQuestion: {user_input}"
        except Exception as e:
            log.debug(f"Enrichment fallback: {e}")
            return user_input

    def _digest(self, raw_response: str, aria_runtime: Any) -> Optional[str]:
        try:
            from ARIA_PEIG_CORE import WORD_PHASE
            words = raw_response.lower().split()
            injected = 0
            for w in words:
                clean = re.sub(r"[^\w]", "", w)
                if clean in WORD_PHASE:
                    shift = WORD_PHASE[clean] * 0.08
                    aria_runtime.char.theta = (aria_runtime.char.theta + shift) % (2 * 3.14159265)
                    injected += 1
            for _ in range(5): aria_runtime._tick()
            digested = aria_runtime.voice.respond(raw_response[:200])
            log.info(f"Digested: {injected}/{len(words)} words injected | arch={aria_runtime.char.dominant_archetype}")
            return digested
        except ImportError:
            log.warning("PEIG core not available for digestion — returning raw")
            return raw_response
        except Exception as e:
            log.warning(f"Digest failed (non-fatal): {e}")
            return None

    # ─────────────────────────────────────────────────────────────────────
    # NETWORK HANDLERS
    # ─────────────────────────────────────────────────────────────────────
    def _query_openai(self, query: str, context_messages: Optional[List[Dict]] = None) -> str:
        messages = [{"role": "system", "content": self.SYSTEM_PROMPT}]
        messages.extend(self.history[-6:])
        if context_messages: messages.extend(context_messages)
        messages.append({"role": "user", "content": query})
        payload = json.dumps({"messages": messages, "temperature": 0.7, "max_tokens": 2048}).encode("utf-8")
        req = urllib.request.Request(self.endpoint, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
            self.stats["total_tokens"] += data.get("usage", {}).get("total_tokens", 0)
            return content

    def _query_ollama(self, query: str, context_messages: Optional[List[Dict]] = None) -> str:
        messages = [{"role": "system", "content": self.SYSTEM_PROMPT}]
        messages.extend(self.history[-6:])
        if context_messages: messages.extend(context_messages)
        messages.append({"role": "user", "content": query})
        payload = json.dumps({"model": self.model or "aria-teacher", "messages": messages, "stream": False}).encode("utf-8")
        req = urllib.request.Request(self.endpoint, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["message"]["content"]

    def ask(self, question: str, aria_runtime: Any = None, is_aria_output: bool = False) -> Tuple[Optional[str], Optional[str]]:
        raw, digested = self.query(question, aria_runtime, is_aria_output=is_aria_output)
        if digested: return digested, raw
        if raw: return raw, raw
        return None, None

    def status(self) -> Dict[str, Any]:
        return {"backend": self.active_backend or "offline", "endpoint": self.endpoint, "style": self.style, "ready": self.ready, "model": self.model, **self.stats}

    def health_check(self) -> bool:
        if not self.endpoint: return False
        try:
            urllib.request.urlopen(self.endpoint.rsplit("/", 2)[0] + "/models", timeout=3)
            return True
        except Exception: return False

# ═══════════════════════════════════════════════════════════════════
# STANDALONE TEST
# ═══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    with CorticalClient() as cortex:
        print(f"\nCortical status: {json.dumps(cortex.status(), indent=2)}")
        if not cortex.ready:
            print("\nNo backend available. Start BitNet or Ollama first.")
            sys.exit(1)
        question = sys.argv[1] if len(sys.argv) > 1 else "Explain photosynthesis simply"
        print(f"\nQuery: {question}\n{'-'*60}")
        raw, digested = cortex.query(question)
        if raw: print(f"\nRaw: {raw}")
        if digested: print(f"\nDigested (PEIG): {digested}")
        print(f"\nFinal stats: {json.dumps(cortex.status(), indent=2)}")
        cortex.export_stats(_DEFAULT_DIR / "logs" / "cortex_stats.json")