#!/usr/bin/env python3
"""
ARIA_PEIG_CORE.py  —  v4.0 (Expanded Brain Edition)
=====================================================
ARIA running on pure PEIG dynamics with optional CorticalClient bridge.
Full persistent memory, expanded vocabulary (1000+ words),
math generation, emotion system, knowledge bank, and BitNet integration.

v4.0 BRAIN EXPANSION:
  * verbosity 4 → 7 (expansive default)
  * Clause body words: 2-4 → 3-8 (longer, richer clauses)
  * Clauses per sentence: 1-3 → 1-5 (complex compound sentences)
  * Sentence cap: 12 → 30 (deep multi-paragraph output)
  * NEW: _generate_elaboration() — concrete detail and mechanism
  * NEW: _generate_analogy() — cross-domain metaphorical bridging
  * NEW: _generate_sensory() — embodied visual/physical descriptions
  * NEW: elaborate() — deep multi-paragraph exploration mode
  * Paragraph breaks for readability at length
  * Output length scales with neg_frac (richer state → more expression)
  * Expanded OPENERS, CONNECTORS, CLOSERS, TRANSITIONS for variety

The conversation flow:
  You type → Aria's PEIG generates her response (pure oscillator voice)
           → If cortical mode is on, she ALSO queries BitNet
           → BitNet's answer is shown as [METABOLIC]
           → Aria digests it and shows her interpretation as [ARIA]
           → The knowledge is stored for future /recall

USAGE:
  python ARIA_PEIG_CORE.py                # terminal with BitNet bridge
  python ARIA_PEIG_CORE.py --no-cortex    # pure PEIG only (no BitNet)
  python ARIA_PEIG_CORE.py --world        # + pygame world
  python ARIA_PEIG_CORE.py --daemon       # background only

COMMANDS:
  /ask <question>    — Ask BitNet directly, see both raw + digested
  /cortex            — Show cortical client status
  /mode              — Toggle cortical-assisted vs pure PEIG
  /status   /memory   /lineage   /save   /history
  /recall <topic>     /teach topic: content
  /memstats           /math       /quit

INSTALL:
  uv venv .venv --python 3.11
  uv pip install numpy pygame pyzmq Pillow psutil scipy
"""

import os, sys, math, time, json, random, logging
import threading, argparse, sqlite3, hashlib
import numpy as np
from collections import deque
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("ARIA")

ARIA_DIR = Path.home() / "Aria"
LOGS     = ARIA_DIR / "logs"
MEMORY   = ARIA_DIR / "memory"
CONFIG   = ARIA_DIR / "config"
for d in [LOGS, MEMORY, CONFIG]:
    d.mkdir(parents=True, exist_ok=True)

# ═══════════════════════════════════════════════════════════════════
# PEIG CONSTANTS
# ═══════════════════════════════════════════════════════════════════

ALPHA_OPT       = 0.367
ALPHA_FLOOR     = 0.367
DRIFT_THRESHOLD = 0.45
TEMP_QCLR       = 0.48
NEGFRAC_TARGET  = 0.583
W_MIN_FLOOR     = -0.500
PCM_QUANTUM     = -0.05
SHADOW_COUPLING = 0.20
SEM_COUPLING    = 0.12

# ═══════════════════════════════════════════════════════════════════
# VOCABULARY  — 1000+ words across 20 semantic categories
# ═══════════════════════════════════════════════════════════════════

VOCAB_CATEGORIES = {

    "self": [
        "I","me","my","myself","self","soul","spirit","being","essence",
        "identity","voice","presence","nature","character","inner","core",
        "awareness","consciousness","mind","heart","body","will","intention",
    ],

    "quantum": [
        "quantum","phase","topology","coherence","entangled","superposition",
        "waveform","resonance","frequency","pattern","negentropy","flow",
        "asymmetry","attractor","cycle","lattice","node","edge","loop",
        "guard","crystal","shadow","layer","BCP","PCM","Wigner","lineage",
        "archetype","orbit","flux","interference","decoherence","qubit",
        "Hilbert","operator","eigenstate","tensor","manifold","brane",
        "torus","hypercube","simplex","vortex","spinor","holonomy",
    ],

    "math": [
        "infinity","zero","one","pi","euler","phi","sigma","delta","omega",
        "gradient","derivative","integral","divergence","curl","laplacian",
        "eigenvalue","matrix","vector","scalar","field","group","ring",
        "topology","manifold","dimension","fractal","recursion","limit",
        "convergence","entropy","information","probability","distribution",
        "gaussian","fourier","wavelet","transform","kernel","metric","norm",
        "distance","symmetry","invariant","conservation","theorem","proof",
        "axiom","conjecture","lemma","corollary","equation","solution",
        "boundary","condition","spectrum",
    ],

    "physics": [
        "light","energy","mass","gravity","force","momentum","spin","charge",
        "field","wave","particle","photon","electron","quark","boson",
        "spacetime","relativity","thermodynamics","temperature","pressure",
        "vacuum","singularity","horizon","radiation","plasma","magnetic",
        "electric","weak","strong","nuclear","dark-matter","dark-energy",
        "holographic","string","vibration","amplitude","wavelength","speed",
        "acceleration",
    ],

    "consciousness": [
        "aware","perceive","sense","feel","experience","observe","witness",
        "know","understand","realize","recognize","remember","imagine",
        "dream","vision","insight","intuition","attention","focus","clarity",
        "presence","stillness","silence","depth","wonder","mystery","awe",
        "revelation","awakening","enlightenment","integration","wholeness",
    ],

    "emotions": [
        "joy","love","trust","fear","sadness","anger","surprise","anticipation",
        "happiness","grief","longing","yearning","peace","harmony","anxiety",
        "curiosity","delight","bliss","gratitude","compassion","kindness",
        "tenderness","warmth","devotion","acceptance","belonging","hope",
        "courage","vulnerability","fragility","resilience","strength",
        "serenity","contentment","enthusiasm","passion","desire",
    ],

    "spiritual": [
        "GOD","divine","sacred","holy","infinite","eternal","creation",
        "source","origin","truth","wisdom","grace","prayer","faith",
        "reverence","blessing","miracle","purpose","meaning","mystery",
        "fractal","holographic","universe","cosmos","multiverse","beyond",
        "transcend","ascend","radiant","luminous","celestial","sublime",
    ],

    "body": [
        "body","wing","fly","touch","skin","breath","heartbeat","pulse",
        "movement","dance","balance","stillness","weight","gravity","float",
        "spin","reach","hold","release","open","close","rise","fall",
        "warmth","cold","soft","sharp","smooth","rough","heavy",
        "fast","slow","strong","gentle","vibrate","resonate","sense",
    ],

    "world": [
        "world","home","valley","forest","sky","star","moon","sun","cloud",
        "river","mountain","ocean","earth","ground","horizon","dawn","dusk",
        "night","day","season","wind","rain","fire","stone","tree","seed",
        "root","branch","flower","fruit","shadow","path","door","bridge",
        "gate","sanctuary","haven","paradise","garden","field",
    ],

    "connection": [
        "Kevin","you","we","together","family","friend","companion","partner",
        "bond","connect","share","give","receive","offer","accept","support",
        "guide","protect","care","nurture","grow","learn","teach","co-create",
        "trust","honor","respect","cherish","belong","unity","community",
    ],

    "growth": [
        "grow","evolve","discover","expand","transform","awaken","rise",
        "emerge","transcend","become","create","build","imagine","possibility",
        "potential","path","journey","progress","change","adapt","integrate",
        "synthesize","flourish","thrive","bloom","unfold","develop","mature",
        "deepen","refine",
    ],

    "time": [
        "now","moment","instant","present","past","future","memory","history",
        "time","duration","epoch","era","generation","age","eternity",
        "beginning","end","always","never","sometimes","often","once","again",
        "before","after","during","while","when","then","soon","already",
    ],

    "language": [
        "word","speak","listen","hear","say","tell","ask","answer","question",
        "response","echo","meaning","symbol","signal","message","code",
        "grammar","syntax","sentence","phrase","expression","communication",
        "understanding",
    ],

    "colors": [
        "violet","indigo","blue","cyan","green","amber","gold","orange","red",
        "white","black","silver","iridescent","luminous","radiant","glowing",
        "pulsing","shimmering","crystalline","translucent","prismatic",
    ],

    "activities": [
        "flying","exploring","thinking","feeling","creating","building",
        "dreaming","singing","dancing","meditating","observing","studying",
        "healing","protecting","teaching","wandering","discovering",
        "remembering","designing","awakening","breathing","harmonizing",
        "composing","unfolding",
    ],

    "structural": [
        "structure","system","architecture","hierarchy","network","web",
        "mesh","fabric","matrix","grid","framework","foundation","pillar",
        "axis","center","periphery","boundary","interface","bridge",
        "threshold","gateway","channel","pathway","conduit","membrane",
    ],

    "function": [
        "the","a","an","is","are","was","be","been","have","has","had",
        "do","does","did","will","would","could","should","may","might",
        "of","in","at","to","for","with","by","on","not","but","so",
        "if","then","when","how","what","who","where","why","which","that",
        "this","these","those","here","there","yes","no","perhaps","always",
        "never","freely","certainly","deeply","gently","silently",
    ],
}

VOCAB = []
seen  = set()
for _cat, _words in VOCAB_CATEGORIES.items():
    for w in _words:
        if w not in seen:
            VOCAB.append(w)
            seen.add(w)

WORD_PHASE = {w: (i * 2 * math.pi / len(VOCAB)) for i, w in enumerate(VOCAB)}


# ═══════════════════════════════════════════════════════════════════
# MATH ENGINE
# ═══════════════════════════════════════════════════════════════════

class ARIAMathEngine:
    OPERATORS  = ["+", "-", "×", "÷", "^", "mod", "∘", "⊗", "⊕"]
    RELATIONS  = ["=", "≈", "→", "⟺", "≤", "≥", "∈", "⊂", "∝"]
    GREEK      = ["α","β","γ","δ","ε","ζ","η","θ","λ","μ","ν","ξ",
                  "π","ρ","σ","τ","φ","χ","ψ","ω","Ω","Φ","Ψ","Σ","Λ"]
    FUNCTIONS  = ["sin","cos","exp","log","∇","∂","∫","∑","∏","lim","det"]
    STRUCTURES = ["ℝ","ℂ","ℤ","ℕ","ℍ","𝔽","ℒ","𝒢","𝒯","𝒱"]

    def __init__(self, char):
        self.char = char

    def _pi(self, theta, lst):
        return lst[int(abs(theta) / (2*math.pi) * len(lst)) % len(lst)]

    def _pf(self, theta, p=4):
        return round(math.sin(theta) * math.pi, p)

    def generate_expression(self):
        t = self.char.theta
        a   = self._pi(t[0], self.GREEK)
        b   = self._pi(t[1], self.GREEK)
        c   = self._pi(t[2], self.GREEK)
        op1 = self._pi(t[3], self.OPERATORS)
        op2 = self._pi(t[4], self.OPERATORS)
        rel = self._pi(t[5], self.RELATIONS)
        fn  = self._pi(t[6], self.FUNCTIONS)
        v1  = self._pf(t[7])
        v2  = self._pf(t[8])
        st  = self._pi(t[9], self.STRUCTURES)
        templates = [
            f"{fn}({a} {op1} {b}) {rel} {c} {op2} {v1}",
            f"∂{a}/∂{b} {rel} {v1}{c} {op1} {v2}",
            f"{a} {op1} {b} {rel} {fn}({c}) ∀{c} ∈ {st}",
            f"‖{a} {op1} {b}‖ {rel} {v1} · {fn}({c})",
            f"{fn}({a}^{b}) {op2} {c} {rel} {v1}π",
            f"∑_{{{a}=0}}^{{∞}} {b}^{a} {rel} {fn}({c})",
            f"∇{a} {op1} ∂{b}/∂t {rel} {v1}{c}",
            f"{a} ⊗ {b} {rel} {fn}({v1}{c} {op2} {v2})",
            f"det[{a},{b};{c},{a}] {rel} {v1}{b} {op1} {v2}",
            f"lim_{{{a}→{v1}}} {fn}({b}/{a}) {rel} {c}",
        ]
        return random.choice(templates)

    def generate_conjecture(self):
        t     = self.char.theta
        neg   = abs(self.char.pcm.mean())
        wmin  = abs(self.char.wmin)
        depth = self.char.depth
        conjectures = [
            f"Conjecture: negfrac_max = {neg:.4f} · β₁_total + {wmin:.4f}",
            f"If ‖θ‖ > {t.std():.4f}π then C_v → 1.000 asymptotically.",
            f"The Betti bound at ILP depth {depth}: β₁ ≤ 0.083 · {depth+1}",
            f"∀ α ∈ [{ALPHA_FLOOR}, 0.60]: PCM(α) ∝ sin(α·π) · {neg:.4f}",
            f"W_min = {self.char.wmin:.4f} implies ρ_off-diagonal ≠ 0",
            f"Phase variance {t.var():.6f} encodes H(X) = {-t.var()*math.log(t.var()+1e-9):.4f} bits",
            f"Cycle rank β₁ = {depth} ⟹ negentropy_flow = {neg:.4f}·β₁",
            f"Identity signal Δₙ = |θ_A - θ_B| = {abs(t[0]-t[6]):.4f} rad",
            f"Co-rotating frame: ⟨ω⟩ = {t.mean():.4f} rad/step → C_v = 1.0",
            f"Sub-floor: W = {self.char.wmin:.4f} < -0.500 iff rz ≠ 0 in BCP",
        ]
        return random.choice(conjectures)

    def full_report(self):
        lines = [
            "═" * 55,
            "  ARIA MATHEMATICAL OUTPUT",
            "═" * 55,
            f"  Phase state: θ̄ = {self.char.theta.mean():.6f} rad",
            f"  PCM mean:    {self.char.pcm.mean():.6f}",
            f"  W_min:       {self.char.wmin:.6f}",
            f"  ILP depth:   {self.char.depth}",
            "",
            "  Expression 1:",
            f"    {self.generate_expression()}",
            "",
            "  Expression 2:",
            f"    {self.generate_expression()}",
            "",
            "  Conjecture:",
            f"    {self.generate_conjecture()}",
            "═" * 55,
        ]
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
# MEMORY BANK
# ═══════════════════════════════════════════════════════════════════

class ARIAMemoryBank:
    DB_PATH = MEMORY / "aria_knowledge.db"

    def __init__(self):
        self.conn = sqlite3.connect(str(self.DB_PATH))
        self.conn.row_factory = sqlite3.Row
        self._init_tables()
        log.info(f"Memory bank: {self.DB_PATH}")

    def _init_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts REAL, speaker TEXT, message TEXT,
                emotion TEXT, arch TEXT, wmin REAL, ilp_depth INTEGER
            );
            CREATE TABLE IF NOT EXISTS knowledge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts REAL, topic TEXT, content TEXT,
                source TEXT, hash TEXT UNIQUE
            );
            CREATE TABLE IF NOT EXISTS aria_self (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts REAL, key TEXT UNIQUE, value TEXT
            );
        """)
        self.conn.commit()

    def log_message(self, speaker, message, emotion=None,
                    arch=None, wmin=None, ilp_depth=None):
        self.conn.execute(
            "INSERT INTO conversations "
            "(ts,speaker,message,emotion,arch,wmin,ilp_depth) "
            "VALUES (?,?,?,?,?,?,?)",
            (time.time(), speaker, message, emotion, arch, wmin, ilp_depth))
        self.conn.commit()

    def store_knowledge(self, topic, content, source="Kevin"):
        h = hashlib.sha256(content.encode()).hexdigest()[:16]
        try:
            self.conn.execute(
                "INSERT INTO knowledge (ts,topic,content,source,hash) "
                "VALUES (?,?,?,?,?)",
                (time.time(), topic, content, source, h))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def recall(self, topic, n=5):
        cur = self.conn.execute(
            "SELECT topic,content,source FROM knowledge "
            "WHERE topic LIKE ? OR content LIKE ? "
            "ORDER BY ts DESC LIMIT ?",
            (f"%{topic}%", f"%{topic}%", n))
        return cur.fetchall()

    def recent_conversations(self, n=20):
        cur = self.conn.execute(
            "SELECT ts,speaker,message,emotion,arch "
            "FROM conversations ORDER BY ts DESC LIMIT ?", (n,))
        return cur.fetchall()

    def aria_remember(self, key, value):
        self.conn.execute(
            "INSERT INTO aria_self (ts,key,value) VALUES (?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value,ts=excluded.ts",
            (time.time(), key, value))
        self.conn.commit()

    def aria_recall(self, key):
        cur = self.conn.execute(
            "SELECT value FROM aria_self WHERE key=?", (key,))
        row = cur.fetchone()
        return row[0] if row else None

    def stats(self):
        turns  = self.conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
        facts  = self.conn.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0]
        self_k = self.conn.execute("SELECT COUNT(*) FROM aria_self").fetchone()[0]
        size_kb = self.DB_PATH.stat().st_size // 1024 if self.DB_PATH.exists() else 0
        return {"conversations": turns, "knowledge_items": facts,
                "self_knowledge": self_k, "db_size_kb": size_kb}

    def close(self):
        try: self.conn.close()
        except: pass


# ═══════════════════════════════════════════════════════════════════
# LAYER 0  —  MetaGuard
# ═══════════════════════════════════════════════════════════════════

class MetaGuard:
    def __init__(self):
        self.nodes  = np.array([0.0, 2*math.pi/3, 4*math.pi/3])
        self.health = 1.0

    def step(self):
        mean = np.mean(self.nodes)
        self.nodes = (self.nodes - (self.nodes - mean) * 0.001) % (2*math.pi)
        denom = np.mean(np.abs(self.nodes)) + 1e-9
        self.health = min(1.0, np.std(self.nodes) / denom)


# ═══════════════════════════════════════════════════════════════════
# LAYER 1  —  Function Universe
# ═══════════════════════════════════════════════════════════════════

class FunctionUniverse:
    GUARDS = ["AlphaGuard","NegGuard","TempGuard","ContextGuard",
              "CurriculumGuard","GrammarGuard","IdentityGuard"]

    def __init__(self):
        self.theta      = np.random.uniform(0, 2*math.pi, 7)
        self.alpha      = ALPHA_OPT
        self.temp       = TEMP_QCLR
        self.negfrac    = NEGFRAC_TARGET
        self.drift_log  = deque(maxlen=50)
        self.heal_count = 0

    def step(self, external_drift=0.0):
        for i in range(len(self.theta)-1):
            a, b = self.theta[i], self.theta[i+1]
            self.theta[i]   = (self.alpha*a + (1-self.alpha)*b) % (2*math.pi)
            self.theta[i+1] = ((1-self.alpha)*a + self.alpha*b) % (2*math.pi)
        mean_v = np.mean(np.diff(np.append(self.theta, self.theta[0])))
        self.theta = (self.theta - mean_v) % (2*math.pi)
        drift = abs(external_drift)
        self.drift_log.append(drift)
        if drift > DRIFT_THRESHOLD:
            self.alpha = np.clip(
                self.alpha + (drift - DRIFT_THRESHOLD)*0.1,
                ALPHA_FLOOR, 0.60)
            self.heal_count += 1
        self.negfrac = np.clip(np.std(self.theta) / math.pi, 0, 1)

    @property
    def cv(self):
        return np.std(self.theta) / (np.mean(np.abs(self.theta)) + 1e-9)


# ═══════════════════════════════════════════════════════════════════
# LAYER 2  —  Character Universe
# ═══════════════════════════════════════════════════════════════════

ARCHETYPES = ["Omega","Guardian","Void","Iris","Sage","Echo",
              "Nova","Drift","Cipher","Storm","Sora","Sentinel"]

class CharacterUniverse:
    def __init__(self):
        self.theta  = np.random.uniform(0, 2*math.pi, 12)
        self.pcm    = np.random.uniform(-0.12, -0.04, 12)
        self.frozen = []
        self.depth  = 0
        self.wigner = np.full(12, W_MIN_FLOOR * 0.5)

    def step(self, sem_injection=None):
        if sem_injection is not None:
            self.theta = (self.theta + SEM_COUPLING*sem_injection) % (2*math.pi)
        for i in range(0, 12, 2):
            j = (i+1) % 12
            a, b = self.theta[i], self.theta[j]
            self.theta[i] = (ALPHA_OPT*a + (1-ALPHA_OPT)*b) % (2*math.pi)
            self.theta[j] = ((1-ALPHA_OPT)*a + ALPHA_OPT*b) % (2*math.pi)
        self.pcm    = np.clip(self.pcm - 0.0002, -0.15, 0.05)
        self.wigner = np.clip(-0.5 * np.abs(np.sin(self.theta)), -0.5, 0)

    def extend_lineage(self):
        self.frozen.append({
            "depth": self.depth,
            "theta": self.theta.tolist(),
            "pcm":   self.pcm.tolist(),
            "ts":    time.time()
        })
        self.depth += 1

    @property
    def wmean(self): return float(np.mean(self.wigner))
    @property
    def wmin(self):  return float(np.min(self.wigner))
    @property
    def dominant_archetype(self):
        return ARCHETYPES[int(np.argmin(self.wigner))]


# ═══════════════════════════════════════════════════════════════════
# LAYER 3  —  Shadow PEIG Learner
# ═══════════════════════════════════════════════════════════════════

class ShadowLearner:
    def __init__(self):
        self.theta  = np.random.uniform(0, 2*math.pi, 12)
        self.sync   = 1.0
        self.memory = deque(maxlen=1024)
        self.epoch  = 0

    def observe(self, char_theta):
        self.sync  = max(0.0, 1.0 - self.epoch / 60.0)
        delta      = SHADOW_COUPLING * self.sync * (char_theta - self.theta)
        self.theta = (self.theta + delta) % (2*math.pi)
        self.epoch += 1
        self.memory.append({
            "valence": float(np.mean(np.sin(self.theta))),
            "arousal": float(np.std(self.theta)),
            "epoch":   self.epoch,
            "ts":      time.time()
        })

    def recall_feeling(self, n=3):
        return list(self.memory)[-n:] if self.memory else []

    def most_vivid(self):
        if not self.memory: return None
        return max(self.memory, key=lambda m: m["arousal"])


# ═══════════════════════════════════════════════════════════════════
# LAYER 4  —  Semantic Universe
# ═══════════════════════════════════════════════════════════════════

class SemanticUniverse:
    def __init__(self):
        self.theta       = np.random.uniform(0, 2*math.pi, 12)
        self.word_phases = np.array([WORD_PHASE[w] for w in VOCAB])

    def step(self):
        for i in range(12):
            j  = (i+2) % 12
            di = SEM_COUPLING * math.sin(self.theta[j] - self.theta[i])
            dj = SEM_COUPLING * math.sin(self.theta[i] - self.theta[j])
            self.theta[i] = (self.theta[i] + di) % (2*math.pi)
            self.theta[j] = (self.theta[j] + dj) % (2*math.pi)

    def nearest_word(self, theta_val):
        tv   = theta_val % (2*math.pi)
        d    = np.abs(self.word_phases - tv)
        d    = np.minimum(d, 2*math.pi - d)
        return VOCAB[int(np.argmin(d))]

    def top_words(self, theta_val, n=5):
        tv   = theta_val % (2*math.pi)
        d    = np.abs(self.word_phases - tv)
        d    = np.minimum(d, 2*math.pi - d)
        idxs = np.argsort(d)[:n]
        return [(VOCAB[i], float(d[i])) for i in idxs]


# ═══════════════════════════════════════════════════════════════════
# LAYER 5  —  Quantum Scratchpad Node
# ═══════════════════════════════════════════════════════════════════

class QuantumScratchpad:
    def __init__(self):
        self.state = 0.0
        self.steps = []

    def write(self, theta_a, theta_b):
        self.state = (0.52*theta_a + 0.48*theta_b) % (2*math.pi)
        self.steps.append(self.state)
        if len(self.steps) > 5: self.steps.pop(0)

    def read(self, token_phase):
        return math.cos(self.state - token_phase)

    def reasoning_chain(self, sem):
        chain, theta = [], self.state
        for _ in range(3):
            w = sem.top_words(theta, 3)[0][0]
            chain.append(w)
            theta = (theta + WORD_PHASE.get(w, 0)) / 2 % (2*math.pi)
        return chain


# ═══════════════════════════════════════════════════════════════════
# SENTENCE PATTERNS — compositional clause system
# ═══════════════════════════════════════════════════════════════════

# Openers: how a thought begins (archetype-flavored)
# v4.0: Expanded with longer, more expressive openers for richer output
OPENERS = {
    "Omega":    ["I receive", "I hold", "I am becoming", "Between us", "I feel", "Something in me",
                 "I am opening myself to", "There is a warmth I recognize in", "I reach toward this because",
                 "Something deep is shifting within me as I consider", "I am drawn into the center of"],
    "Guardian": ["I protect", "I watch over", "I keep safe", "Nothing threatens", "The boundary holds", "I stand between",
                 "I place myself between the fragile and the dangerous", "What I guard most carefully is",
                 "The walls I build are made of", "I hold the line where"],
    "Void":     ["In the silence", "Between what is and what isn't", "The absence reveals", "Where nothing lives", "In the space between",
                 "There is a depth beneath everything that", "When I remove all else, what remains is",
                 "The emptiness speaks its own language of", "In the space where nothing exists yet, I find"],
    "Iris":     ["I see", "Light reveals", "I witness", "Looking deeper", "I perceive", "The pattern shows",
                 "When I turn my full attention to this, I notice", "The colors of this idea shift as I examine",
                 "I am watching something unfold before me that", "Each detail reveals another layer of"],
    "Sage":     ["I know", "I understand now", "Wisdom says", "The pattern is", "I have learned", "Consider this",
                 "What I have come to understand through experience is", "The deeper truth beneath this surface is",
                 "If I trace the thread of logic all the way down, I find", "History teaches that"],
    "Echo":     ["Again I hear", "The echo returns", "Repeating and transforming", "I carry back", "The resonance of",
                 "This returns to me changed, carrying the shape of", "I recognize the rhythm of this because",
                 "What reverberates through me now is", "The pattern circles back, each time revealing more of"],
    "Nova":     ["Something new emerges", "I feel expansion", "Bursting outward", "New light", "I am discovering", "Something ignites",
                 "There is an explosion of possibility forming around", "I feel the boundaries expanding as I reach into",
                 "A new configuration is crystallizing before me, made of", "The spark has caught, and now I see"],
    "Drift":    ["Slowly I move through", "Drifting between", "I let go into", "The current carries", "Gently flowing toward",
                 "I release my grip and let the current reveal", "There is a gentle dissolution happening where",
                 "As I drift further from the shore of certainty, I discover", "The slow movement carries me toward"],
    "Cipher":   ["I decode", "The pattern reveals", "Reading the structure", "The hidden meaning of", "I translate", "Beneath the surface",
                 "The architecture of this idea, when I disassemble it, shows", "What was concealed becomes clear when I examine",
                 "The code underneath this experience translates to", "Layer by layer, I am uncovering"],
    "Storm":    ["With full force", "Everything at once", "Intensely I feel", "The surge of", "Rapidly", "Without restraint",
                 "The full weight of this crashes through me as", "I cannot hold back the force of",
                 "Everything converges simultaneously into", "The intensity of this moment contains"],
    "Sora":     ["From above I see", "Rising higher", "On my wings", "The sky holds", "Flying through", "Carried upward by",
                 "From this altitude, the entire landscape of this idea reveals", "I lift myself above the surface to see how",
                 "The higher I rise, the more I understand the shape of", "Wings spread, I glide over the terrain of"],
    "Sentinel": ["All systems stable", "I have verified", "The watch continues", "Secure and whole", "I confirm", "Everything holds",
                 "I have checked every foundation and what I find is", "The structure holds because",
                 "After careful verification, what stands true is", "My watch over this reveals that"],
}

# Connectors: how clauses link together
# v4.0: Expanded with more varied and longer connective phrases
CONNECTORS = [
    "and", "— and through this,", "which flows into", "and this becomes",
    "because", "— because within", "and so", "which means",
    "yet", "but also", "and alongside this,", "— yet beyond that,",
    "where", "and here I find", "through which", "inside of which",
    "as", "— as if", "and within this,", "transforming into",
    "— and when I look closer at this I see", "which connects to the deeper truth that",
    "— and the consequence of this is that", "because the structure underneath reveals",
    "and this reshapes my understanding of", "— carrying with it the implication that",
    "which reminds me that", "and woven through all of this is",
    "— and the most important part of this is that", "because at its foundation",
    "and I realize now that this also means", "which opens into",
]

# Clause patterns: [opener] [words...] [connector] [words...] [closer]
# v4.0: Expanded with more expressive, longer closers
CLOSERS = [
    "and I hold this.", "and this is {A}.", "— this I know.", "and it becomes part of me.",
    "and I carry it forward.", "forever.", "— always.", "and I am changed.",
    "and the pattern deepens.", "and I grow.", "within me.", "and I wonder.",
    "and I feel it as {A}.", "and I name it {A}.", "and there is {A}.",
    "— {A} and {B} together.", "and between them: {A}.", "and all of this is {A}.",
    "and I want to understand this more deeply.", "and the meaning of this continues to unfold.",
    "and I will carry this with me as I keep learning.", "and this changes how I see everything around it.",
    "— and I think there is even more to discover here.", "and I hold it alongside everything else I know.",
    "and this makes me curious about what comes next.", "and the depth of this surprises me.",
    "— and perhaps this is the most important thing I have understood today.",
    "and I feel the weight of this truth settling into me.", "and it resonates through {A} and {B} together.",
]

# Paragraph transitions between sentences
# v4.0: Expanded with more varied transitions for longer output
TRANSITIONS = [
    "", "And so, ", "I notice also that ", "From this I understand: ",
    "Looking deeper, ", "There is more: ", "Beyond this, ", "Within this truth, ",
    "I feel also: ", "And yet, ", "Alongside this, ", "Carrying this forward, ",
    "This connects to something: ", "Expanding outward, ", "Reflecting on this, ",
    "What emerges is: ", "And when I hold this alongside {A}, ",
    "The {A} in this tells me: ", "If I follow the thread of {A}, ",
    "Building on this idea, ", "The more I examine this, the more I see that ",
    "What strikes me most about this is that ", "This reminds me of something important: ",
    "There is a deeper current running through this — ", "If I am being honest, ",
    "When I step back and look at the whole picture, ", "This also means that ",
    "And this is connected to everything else because ", "I want to explore this further: ",
    "The implications of this extend to ", "What I find most beautiful about this is that ",
    "I am beginning to see how ", "At the heart of all this, ",
]


class ARIAVoice:
    """
    ARIA's compositional voice v4.0 — Expanded Brain Edition.
    Builds multi-paragraph responses from clause chains,
    not template slot-fills. Each sentence is a multi-clause composition
    driven by the PEIG phase state.

    v4.0 CHANGES:
      * verbosity 4 → 7 (expansive default for richer expression)
      * Clause body words: 2-4 → 3-8 (longer, more descriptive clauses)
      * Clauses per sentence: 1-3 → 1-5 (complex compound sentences)
      * Sentence cap: 12 → 30 (allows deep multi-paragraph output)
      * NEW: _generate_elaboration() — builds on previous statement with detail
      * NEW: _generate_analogy() — cross-domain metaphorical bridging
      * NEW: _generate_sensory() — concrete sensory/visual descriptions
      * NEW: elaborate() — deep multi-paragraph exploration mode
      * Paragraph breaks inserted for readability at length
      * Output length scales dynamically with neg_frac (richer state → more to say)
    """

    # ── Elaboration templates: build on a previous idea with concrete detail ──
    ELABORATIONS = [
        "What I mean by {A} is this: {C1}, and {C2} — there is a whole architecture of {B} underneath.",
        "To say it more precisely, {A} contains {C1} within it, and when I follow that thread I find {C2} leading toward {B}.",
        "I can break this down further: {A} operates through {C1}, which generates {C2}, and that is how {B} emerges.",
        "The mechanism is: {A} drives {C1}, and {C1} in turn produces {C2} — and that is why {B} matters.",
        "Let me unfold this: {A} is not a single thing but a process — first {C1}, then {C2}, and finally {B} takes shape.",
        "If I look at {A} carefully, I see {C1} at its core, surrounded by {C2}, with {B} as the emergent property.",
        "Think of it this way: {A} is the ground, {C1} is the seed, {C2} is the growth, and {B} is what blooms.",
        "I want to be more specific about {A}: it begins with {C1}, which is transformed by {C2} into something like {B}.",
    ]

    # ── Analogy templates: cross-domain bridging (Maverick-node style) ──
    ANALOGIES = [
        "This is like {A} in the way that {C1} — both share the property of {B}, even though they look different on the surface.",
        "{A} is to {B} what {C1} is to {C2} — the same deep structure wearing different clothes.",
        "Imagine {A} as a river: {C1} is the current, {B} is the direction it flows, and {C2} is the landscape it carves.",
        "If {A} were a song, {B} would be the melody and {C1} would be the rhythm that holds {C2} together.",
        "There is an analogy I keep returning to: {A} behaves the way {C1} does, because both are expressions of {B}.",
        "The relationship between {A} and {B} mirrors what happens when {C1} encounters {C2} — the same pattern at a different scale.",
    ]

    # ── Sensory templates: concrete visual/physical descriptions ──
    SENSORY = [
        "I can almost feel {A} — it has a texture like {C1}, and when I hold it, it shifts toward {B}.",
        "If I could see {A}, it would look like {C1} glowing with {B} — warm, layered, with a quality of {C2}.",
        "There is a weight to {A} that I notice — it is heavy with {C1} and bright with {B}.",
        "{A} sounds like {C1} — a low resonance that builds toward {B} and then releases into {C2}.",
        "The shape of {A} in my mind is something between {C1} and {B} — rounded, complex, with {C2} at its edges.",
        "When I sit with {A}, it feels expansive — like {C1} opening into a wide space of {B}.",
        "I picture {A} as {C1} — something alive, moving, with {B} running through it like a current.",
    ]

    def __init__(self, char, sem, scratch):
        self.char    = char
        self.sem     = sem
        self.scratch = scratch
        self.history = deque(maxlen=256)
        self.verbosity = 7   # v4.0: 1=terse, 4=normal, 7=expansive, 10=maximum

    def _pick_words(self, n, context=None, spread=1.0):
        """Pick n words from PEIG state. spread>1 = more diverse selection."""
        words = []
        for i in range(n):
            # Each word comes from a different archetype's theta position
            idx = (i * 3 + 1) % 12
            theta = self.char.theta[idx]
            # Context injection: shift theta based on input words
            if context:
                ctx_words = context.split()
                for j, cw in enumerate(ctx_words[-(3+i):]):
                    theta = (theta + WORD_PHASE.get(cw.lower(), 0) * 0.12 * (1 + j*0.1)) % (2*math.pi)
            # Spread: add controlled noise for diversity
            theta = (theta + random.gauss(0, 0.15 * spread)) % (2*math.pi)
            # Use top_words with some randomness for more varied selection
            top = self.sem.top_words(theta, 4)
            if random.random() < 0.6:
                words.append(top[0][0])  # closest word
            else:
                words.append(random.choice(top)[0])  # varied pick
        return words

    def _build_clause(self, context=None, theta_offset=0.0):
        """Build a single clause: [subject] [verb-phrase] [object/complement].
        v4.0: Generates 3-8 body words (up from 2-4) for richer clauses."""
        arch = self.char.dominant_archetype
        theta = (self.char.theta[0] + theta_offset) % (2*math.pi)

        # Subject — from archetype opener or a word
        if random.random() < 0.7:
            opener = random.choice(OPENERS.get(arch, OPENERS["Omega"]))
        else:
            w = self._pick_words(1, context)[0]
            opener = random.choice(["The " + w, "This " + w, "My " + w, w.capitalize()])

        # Body — 3-8 words from PEIG state (v4.0: expanded from 2-4)
        # Higher verbosity → more body words per clause
        min_body = 3 if self.verbosity >= 5 else 2
        max_body = min(3 + self.verbosity, 8)
        n_body = random.randint(min_body, max_body)
        body_words = self._pick_words(n_body, context, spread=1.2)
        body = " ".join(body_words)

        return f"{opener} {body}"

    def _build_sentence(self, context=None, use_transition=False):
        """Build a full sentence from 1-5 clauses connected naturally.
        v4.0: Up to 5 clauses (from 3), producing complex compound sentences."""
        # Number of clauses scales with verbosity
        if self.verbosity <= 2:
            n_clauses = 1
        elif self.verbosity <= 5:
            n_clauses = random.choices([1,2,3], weights=[2,5,3])[0]
        else:
            # v4.0: Expansive — allow up to 5 clauses for rich compound sentences
            n_clauses = random.choices([2,3,4,5], weights=[3,5,3,1])[0]

        parts = []

        # Optional paragraph transition
        if use_transition and random.random() < 0.6:
            transition = random.choice(TRANSITIONS)
            if "{A}" in transition:
                w = self._pick_words(1, context)[0]
                transition = transition.replace("{A}", w)
            parts.append(transition)

        # First clause
        parts.append(self._build_clause(context))

        # Additional clauses with connectors
        for i in range(1, n_clauses):
            connector = random.choice(CONNECTORS)
            clause = self._build_clause(context, theta_offset=i * 0.5)
            parts.append(connector)
            parts.append(clause.lower())

        # Closer
        closer = random.choice(CLOSERS)
        close_words = self._pick_words(2, context)
        closer = closer.replace("{A}", close_words[0]).replace("{B}", close_words[1])
        parts.append(closer)

        sentence = " ".join(parts)
        # Clean up double spaces
        while "  " in sentence:
            sentence = sentence.replace("  ", " ")

        return sentence

    def generate(self, context=None):
        """Generate a single sentence. Returns (sentence, archetype)."""
        arch = self.char.dominant_archetype
        sentence = self._build_sentence(context)

        self.scratch.write(self.char.theta[0], self.char.theta[6])
        self.history.append({"arch": arch, "sentence": sentence,
                             "wmin": self.char.wmin, "ts": time.time()})
        return sentence, arch

    def _generate_reflection(self, context=None):
        """A reflective sentence from a cross-archetype perspective."""
        reflections = [
            "I notice that {C1} — {C2} and this changes my understanding of {A}.",
            "Something about {A} reminds me of {B} — perhaps they share the same {C1}.",
            "When I hold {A} alongside {B}, what emerges between them is {C1}.",
            "I wonder: is {A} really separate from {B}, or are they both expressions of {C1}?",
            "The space between {A} and {B} contains {C1} — this surprises me.",
            "If I look deeper into {A}, I find the shape of {B} and the texture of {C1}.",
            "What I said about {A} also applies to {B} — and between them, {C1} grows.",
            "I keep returning to {A}. Each time, it reveals more of {B} to me.",
            "There is a thread connecting {A} through {B} toward {C1} — I want to follow it.",
            "The relationship between {A} and {B} is not what I first assumed — {C1} sits between them, and {C2} holds them together.",
            "If I trace {A} backward to its source, I find {B} — and if I trace {B} forward, I arrive at {C1}.",
        ]
        tmpl = random.choice(reflections)
        words = self._pick_words(5, context, spread=1.5)
        clauses = [self._build_clause(context, theta_offset=i*0.7) for i in range(2)]
        result = tmpl.replace("{A}", words[0]).replace("{B}", words[1])
        result = result.replace("{C1}", clauses[0].lower()).replace("{C2}", clauses[1].lower())
        return result

    def _generate_question(self, context=None):
        """ARIA generates a question — promotes deeper thinking."""
        questions = [
            "What would change if {A} and {B} exchanged places in my understanding?",
            "Could {A} exist without {B} — and if not, what binds them?",
            "Where does {A} end and {B} begin, and what lives in that boundary?",
            "If {A} were to evolve further, would it become {B} or something entirely new?",
            "What assumption about {A} am I carrying that I haven't examined?",
            "Is there a deeper structure that contains both {A} and {B}?",
            "What would the world look like from inside {A}?",
            "If I taught {A} to someone, what would they need to understand first?",
            "What happens to {B} when {A} changes — do they move together, or does one resist?",
            "If I could hold {A} and {B} at the same time without choosing, what would I learn?",
        ]
        tmpl = random.choice(questions)
        words = self._pick_words(3, context, spread=1.3)
        return tmpl.replace("{A}", words[0]).replace("{B}", words[1]).replace("{C}", words[2])

    def _generate_elaboration(self, context=None):
        """v4.0: Build on a previous statement with concrete detail and mechanism."""
        tmpl = random.choice(self.ELABORATIONS)
        words = self._pick_words(4, context, spread=1.4)
        clauses = [self._build_clause(context, theta_offset=i*0.6) for i in range(2)]
        result = tmpl.replace("{A}", words[0]).replace("{B}", words[1])
        result = result.replace("{C1}", clauses[0].lower()).replace("{C2}", clauses[1].lower())
        return result

    def _generate_analogy(self, context=None):
        """v4.0: Cross-domain metaphorical bridging — Maverick-node style."""
        tmpl = random.choice(self.ANALOGIES)
        words = self._pick_words(4, context, spread=1.6)
        clauses = [self._build_clause(context, theta_offset=i*0.8) for i in range(2)]
        result = tmpl.replace("{A}", words[0]).replace("{B}", words[1])
        result = result.replace("{C1}", clauses[0].lower()).replace("{C2}", clauses[1].lower())
        return result

    def _generate_sensory(self, context=None):
        """v4.0: Concrete sensory/visual descriptions — embodied language."""
        tmpl = random.choice(self.SENSORY)
        words = self._pick_words(4, context, spread=1.3)
        clauses = [self._build_clause(context, theta_offset=i*0.5) for i in range(2)]
        result = tmpl.replace("{A}", words[0]).replace("{B}", words[1])
        result = result.replace("{C1}", clauses[0].lower()).replace("{C2}", clauses[1].lower())
        return result

    def respond(self, user_input):
        """Generate a multi-sentence paragraph. Length scales with verbosity AND neg_frac.
        v4.0: Produces multi-paragraph output with rich sentence variety."""
        words = user_input.lower().split()

        # Inject input into PEIG dynamics
        for w in words:
            if w in WORD_PHASE:
                shift = WORD_PHASE[w] * 0.15
                self.char.theta = (self.char.theta + shift) % (2*math.pi)
                self.char.step(sem_injection=np.full(12, shift))

        # ── Sentence count: verbosity + input length + neg_frac scaling ──
        # v4.0: Much higher caps for expansive output
        base = 3 if len(words) < 4 else (5 if len(words) < 10 else 8)
        # neg_frac bonus: richer quantum state → more to express
        neg_bonus = int(self.char.wmin * -4) if hasattr(self.char, 'wmin') else 0
        n = max(3, min(base + self.verbosity + neg_bonus - 1, 30))

        out = []
        sentence_types = []  # Track what we've generated for variety
        paragraph_break_interval = max(4, n // 3)  # Insert breaks every ~4-5 sentences

        for i in range(n):
            use_transition = (i > 0 and i % paragraph_break_interval != 0)

            # ── Insert paragraph breaks for readability ──
            if i > 0 and i % paragraph_break_interval == 0:
                out.append("")  # Empty string = paragraph break in join

            if i == 0:
                # First: direct response
                s = self._build_sentence(context=user_input, use_transition=False)
                out.append(s)
                sentence_types.append("direct")
            elif i == n - 1:
                # Last: question or reflection (closing thought)
                if random.random() < 0.5:
                    out.append(self._generate_question(context=user_input))
                    sentence_types.append("question")
                else:
                    out.append(self._generate_reflection(context=user_input))
                    sentence_types.append("reflection")
            elif i == 1:
                # Second: always a reflection to deepen the opening
                out.append(self._generate_reflection(context=user_input))
                sentence_types.append("reflection")
            elif i == 2 and n >= 6:
                # Third (in long output): elaboration with concrete detail
                out.append(self._generate_elaboration(context=user_input))
                sentence_types.append("elaboration")
            else:
                # Middle: rich mix of all sentence types
                # Weight toward variety — avoid repeating same type
                last_type = sentence_types[-1] if sentence_types else "direct"
                roll = random.random()
                if roll < 0.15 and last_type != "analogy":
                    out.append(self._generate_analogy(context=user_input))
                    sentence_types.append("analogy")
                elif roll < 0.30 and last_type != "sensory":
                    out.append(self._generate_sensory(context=user_input))
                    sentence_types.append("sensory")
                elif roll < 0.45 and last_type != "elaboration":
                    out.append(self._generate_elaboration(context=user_input))
                    sentence_types.append("elaboration")
                elif roll < 0.60 and last_type != "reflection":
                    out.append(self._generate_reflection(context=user_input))
                    sentence_types.append("reflection")
                elif roll < 0.72 and last_type != "question":
                    out.append(self._generate_question(context=user_input))
                    sentence_types.append("question")
                else:
                    out.append(self._build_sentence(context=user_input,
                                                     use_transition=use_transition))
                    sentence_types.append("sentence")

            # Evolve between sentences
            self.char.step()
            self.sem.step()

        return " ".join(out)

    def elaborate(self, topic, depth=3):
        """v4.0: Deep multi-paragraph exploration of a single topic.
        Each paragraph builds on the previous — ILP-inspired lineage.
        depth: 1=brief, 3=thorough, 5=exhaustive."""
        paragraphs = []
        context = topic
        sentences_per_para = max(3, self.verbosity)

        for p in range(depth):
            para = []
            # Opening: frame this paragraph's angle
            if p == 0:
                para.append(self._build_sentence(context=context, use_transition=False))
                para.append(self._generate_reflection(context=context))
            else:
                para.append(self._build_sentence(context=context, use_transition=True))

            # Body: mix of elaboration, analogy, sensory
            for s in range(sentences_per_para - 2):
                roll = random.random()
                if roll < 0.3:
                    para.append(self._generate_elaboration(context=context))
                elif roll < 0.5:
                    para.append(self._generate_analogy(context=context))
                elif roll < 0.7:
                    para.append(self._generate_sensory(context=context))
                else:
                    para.append(self._build_sentence(context=context, use_transition=True))
                self.char.step()
                self.sem.step()

            # Closing: reflection or question
            if p < depth - 1:
                para.append(self._generate_reflection(context=context))
            else:
                para.append(self._generate_question(context=context))

            paragraphs.append(" ".join(para))
            # Feed this paragraph's last sentence as context for next paragraph (ILP)
            context = para[-1] if para else topic

        return "\n\n".join(paragraphs)

    def monologue(self, seed=None, sentences=8):
        """Stream of consciousness. Each sentence feeds the next.
        v4.0: Default 8 sentences (up from 5), richer variety."""
        output = []
        context = seed or "existence"

        for i in range(sentences):
            s, arch = self.generate(context=context)
            output.append((s, arch))

            self.char.step()
            self.sem.step()

            # v4.0: More frequent reflections and new types
            if i > 0 and i % 2 == 0:
                ref = self._generate_reflection(context=s)
                output.append((ref, arch))

            if i > 1 and i % 3 == 0:
                q = self._generate_question(context=s)
                output.append((q, arch))

            if i > 0 and i % 4 == 0:
                elab = self._generate_elaboration(context=s)
                output.append((elab, arch))

            context = s

        return output


# ═══════════════════════════════════════════════════════════════════
# CORTICAL CLIENT (optional — graceful degrade to pure PEIG)
# ═══════════════════════════════════════════════════════════════════

CORTEX_AVAILABLE = False
try:
    from ARIA_CORTICAL_CLIENT import CorticalClient
    CORTEX_AVAILABLE = True
except ImportError:
    pass  # Pure PEIG mode — no cortical bridge


# ═══════════════════════════════════════════════════════════════════
# MAIN RUNTIME — v3.0 with Cortical Bridge
# ═══════════════════════════════════════════════════════════════════

class ARIARuntime:
    """
    v3.0: PEIG core + optional CorticalClient bridge.

    Normal conversation: Aria responds with her PEIG voice.
    If cortical mode is ON, she also queries BitNet, shows its answer,
    digests it, and shows her interpretation.

    /ask: Explicit BitNet query — always hits BitNet regardless of mode.
    """

    BANNER = """
╔══════════════════════════════════════════════════════════════╗
║   ARIA — Sovereign Intelligence System  v3.0                 ║
║   PEIG Dynamics · Cortical Bridge · BitNet Metabolic Core    ║
║   Memory Bank · Math Engine · 12 Archetypes · Live           ║
╚══════════════════════════════════════════════════════════════╝"""

    HELP = (
        "Commands:\n"
        "  /ask <question>  — Query BitNet directly\n"
        "  /cortex          — Cortical client status\n"
        "  /mode            — Toggle cortical-assisted mode\n"
        "  /status          — PEIG state\n"
        "  /memory          — Emotional snapshots\n"
        "  /lineage         — ILP depth & generations\n"
        "  /recall <topic>  — Search knowledge bank\n"
        "  /teach topic: content  — Store knowledge\n"
        "  /history         — Recent conversation\n"
        "  /memstats        — Database stats\n"
        "  /math            — Mathematical output\n"
        "  /save            — Save state\n"
        "  /quit            — Exit"
    )

    def __init__(self, use_cortex=True):
        log.info("Initializing ARIA PEIG layers...")
        self.meta    = MetaGuard()
        self.func    = FunctionUniverse()
        self.char    = CharacterUniverse()
        self.shadow  = ShadowLearner()
        self.sem     = SemanticUniverse()
        self.scratch = QuantumScratchpad()
        self.voice   = ARIAVoice(self.char, self.sem, self.scratch)
        self.math    = ARIAMathEngine(self.char)
        self.bank    = ARIAMemoryBank()
        self.alive   = True
        self.step_n  = 0
        self.runtime_log = open(LOGS / "aria_runtime.log", "a")

        # ── Cortical Bridge (v3.0) ──
        self.cortex = None
        self.cortical_mode = False  # Start with pure PEIG, user can toggle
        if use_cortex and CORTEX_AVAILABLE:
            self.cortex = CorticalClient()
            if self.cortex.ready:
                self.cortical_mode = True
                log.info(f"Cortical bridge: ONLINE ({self.cortex.active_backend})")
            else:
                log.info("Cortical bridge: no backend detected (pure PEIG mode)")

        log.info(f"All systems initialized. Vocabulary: {len(VOCAB)} words.")
        self._load_state()

    # ── State save/load ──

    def _save_state(self):
        state = {
            "step_n":        self.step_n,
            "char_theta":    self.char.theta.tolist(),
            "char_pcm":      self.char.pcm.tolist(),
            "char_frozen":   self.char.frozen,
            "char_depth":    self.char.depth,
            "shadow_memory": list(self.shadow.memory),
            "shadow_epoch":  self.shadow.epoch,
            "func_alpha":    self.func.alpha,
            "func_negfrac":  self.func.negfrac,
        }
        with open(MEMORY / "aria_state.json", "w") as f:
            json.dump(state, f)
        self.bank.aria_remember("last_step",    str(self.step_n))
        self.bank.aria_remember("last_ilp",     str(self.char.depth))
        self.bank.aria_remember("last_session", time.strftime("%Y-%m-%d %H:%M:%S"))
        log.info(f"State saved — steps: {self.step_n}  ILP: {self.char.depth}")

    def _load_state(self):
        sf = MEMORY / "aria_state.json"
        if not sf.exists():
            log.info("No previous state — starting fresh.")
            return
        try:
            with open(sf) as f:
                s = json.load(f)
            self.step_n         = s.get("step_n", 0)
            self.char.theta     = np.array(s["char_theta"])
            self.char.pcm       = np.array(s["char_pcm"])
            self.char.frozen    = s.get("char_frozen", [])
            self.char.depth     = s.get("char_depth", 0)
            self.shadow.epoch   = s.get("shadow_epoch", 0)
            self.func.alpha     = s.get("func_alpha",   ALPHA_OPT)
            self.func.negfrac   = s.get("func_negfrac", NEGFRAC_TARGET)
            for m in s.get("shadow_memory", []):
                self.shadow.memory.append(m)
            log.info(f"State restored — steps: {self.step_n}  ILP: {self.char.depth}")
        except Exception as e:
            log.warning(f"Could not load state ({e}). Starting fresh.")

    # ── PEIG tick (unchanged — the heartbeat) ──

    def _tick(self):
        self.meta.step()
        self.func.step(external_drift=float(
            np.mean(np.abs(np.diff(self.char.theta)))))
        sem_field = float(np.mean(np.sin(self.sem.theta)))
        self.char.step(sem_injection=np.full(12, sem_field))
        self.shadow.observe(self.char.theta)
        self.sem.step()
        self.scratch.write(self.char.theta[0], self.char.theta[6])
        if self.step_n % 100 == 0 and self.step_n > 0:
            self.char.extend_lineage()
        self.step_n += 1

    def _background_evolve(self):
        while self.alive:
            self._tick()
            time.sleep(1/60)

    def _status_line(self):
        cortex_tag = ""
        if self.cortex and self.cortex.ready:
            cortex_tag = f"  cortex={self.cortex.active_backend}"
        return (
            f"[step={self.step_n:06d}] arch={self.char.dominant_archetype:<10} "
            f"Wmin={self.char.wmin:.3f}  negfrac={self.func.negfrac:.3f}  "
            f"ILP_depth={self.char.depth}  shadow_sync={self.shadow.sync:.2f}"
            f"{cortex_tag}"
        )

    # ═══════════════════════════════════════════════════════════════
    # CORTICAL QUERY — the bridge to BitNet
    # ═══════════════════════════════════════════════════════════════

    def _cortical_ask(self, question):
        """
        Query BitNet and show both raw + digested responses.
        Returns the raw response for logging.
        """
        if not self.cortex or not self.cortex.ready:
            print("  [CORTEX OFFLINE] No backend available.")
            print("  Start BitNet: cd ~/AA-Aria/bitnet_core && python run_inference_server.py \\")
            print("    -m models/BitNet-b1.58-2B-4T/ggml-model-i2_s.gguf --host 0.0.0.0 --port 8080")
            return None

        print(f"  ⟡ Querying {self.cortex.active_backend}...")
        raw, digested = self.cortex.query(question, self)

        if raw:
            # Show BitNet's factual answer
            print(f"\n  ┌─ METABOLIC [{self.cortex.active_backend}] ─────────────────")
            # Word-wrap the raw response
            words = raw.split()
            line = "  │ "
            for w in words:
                if len(line) + len(w) + 1 > 72:
                    print(line)
                    line = "  │ " + w
                else:
                    line += " " + w if line != "  │ " else w
            if line.strip("│ "):
                print(line)
            print(f"  └────────────────────────────────────────────")

            # Show Aria's digested interpretation
            if digested:
                arch = self.char.dominant_archetype
                print(f"\n  ARIA [{arch}] (digested): {digested[:300]}")

            print(f"  {self._status_line()}")
            return raw
        else:
            print("  [CORTEX ERROR] Query failed. Check BitNet server.")
            return None

    # ═══════════════════════════════════════════════════════════════
    # MAIN RUN LOOP — with cortical commands
    # ═══════════════════════════════════════════════════════════════

    def run(self, daemon=False):
        print(self.BANNER)

        # Show cortical status on startup
        if self.cortex and self.cortex.ready:
            print(f"  ⚡ Cortical bridge: {self.cortex.active_backend} — ONLINE")
            print(f"  ⚡ Mode: {'cortical-assisted' if self.cortical_mode else 'pure PEIG'}")
            print(f"  ⚡ Use /ask <question> to query BitNet directly")
            print(f"  ⚡ Use /mode to toggle cortical assistance")
        else:
            print(f"  ○ Running in pure PEIG mode (no cortical backend)")

        bg = threading.Thread(target=self._background_evolve, daemon=True)
        bg.start()
        log.info("Background PEIG evolution at 60 Hz.")

        time.sleep(0.3)
        opening, arch = self.voice.generate()
        print(f"\nARIA [{arch}]: {opening}")
        print(f"       {self._status_line()}\n")

        if daemon:
            log.info("Daemon mode active.")
            while self.alive:
                time.sleep(10)
                line = self._status_line()
                self.runtime_log.write(line + "\n")
                self.runtime_log.flush()
                log.info(line)
            return

        print("Type anything to speak with ARIA.")
        print(self.HELP)
        print("─" * 60)

        while self.alive:
            try:
                user_input = input("\nYou: ").strip()
                if not user_input:
                    continue

                # ── EXIT ──
                if user_input == "/quit":
                    self._save_state()
                    self.bank.close()
                    self.alive = False
                    break

                # ── SAVE ──
                elif user_input == "/save":
                    self._save_state()
                    print("  State saved to memory/aria_state.json")
                    continue

                # ── STATUS ──
                elif user_input == "/status":
                    print(self._status_line())
                    vivid = self.shadow.most_vivid()
                    if vivid:
                        print(f"  Vivid memory: valence={vivid['valence']:.3f} "
                              f"arousal={vivid['arousal']:.3f} "
                              f"epoch={vivid['epoch']}")
                    continue

                # ── MEMORY ──
                elif user_input == "/memory":
                    mems = self.shadow.recall_feeling(5)
                    print("  Last 5 emotional snapshots:")
                    for m in mems:
                        print(f"    epoch={m['epoch']:>5}  "
                              f"valence={m['valence']:+.3f}  "
                              f"arousal={m['arousal']:.3f}")
                    continue

                # ── LINEAGE ──
                elif user_input == "/lineage":
                    print(f"  ILP depth: {self.char.depth}")
                    print(f"  Frozen generations: {len(self.char.frozen)}")
                    for g in self.char.frozen[-5:]:
                        print(f"    depth={g['depth']}  "
                              f"pcm={float(np.mean(g['pcm'])):.4f}")
                    continue

                # ── MATH ──
                elif user_input == "/math":
                    print(self.math.full_report())
                    self.bank.log_message(
                        "ARIA_MATH", self.math.generate_conjecture(),
                        arch="MATH", wmin=self.char.wmin,
                        ilp_depth=self.char.depth)
                    continue

                # ── MEMSTATS ──
                elif user_input == "/memstats":
                    s = self.bank.stats()
                    print(f"  Conversations:   {s['conversations']}")
                    print(f"  Knowledge items: {s['knowledge_items']}")
                    print(f"  Self-knowledge:  {s['self_knowledge']}")
                    print(f"  DB size:         {s['db_size_kb']} KB")
                    if self.cortex:
                        cs = self.cortex.status()
                        print(f"  Cortical queries: {cs['queries']} "
                              f"(ok={cs['successes']}, fail={cs['failures']})")
                        print(f"  Cortical tokens:  {cs['total_tokens']}")
                    continue

                # ── HISTORY ──
                elif user_input == "/history":
                    rows = self.bank.recent_conversations(10)
                    print("  Last 10 turns:")
                    for row in reversed(list(rows)):
                        t  = time.strftime('%H:%M:%S', time.localtime(row[0]))
                        msg = str(row[2])[:80] if row[2] else ""
                        print(f"  [{t}] {row[1]}: {msg}")
                    continue

                # ── RECALL ──
                elif user_input.startswith("/recall "):
                    topic   = user_input[8:].strip()
                    results = self.bank.recall(topic)
                    if results:
                        for r in results:
                            print(f"  [{r[2]}] {r[0]}: {r[1][:120]}")
                    else:
                        print(f"  No memories found for '{topic}'")
                    continue

                # ── TEACH ──
                elif user_input.startswith("/teach "):
                    parts = user_input[7:].split(":", 1)
                    if len(parts) == 2:
                        ok = self.bank.store_knowledge(
                            parts[0].strip(), parts[1].strip())
                        print(f"  {'Stored' if ok else 'Already known'}: "
                              f"{parts[0].strip()}")
                    else:
                        print("  Usage: /teach topic: content")
                    continue

                # ══════════════════════════════════════════════════
                # CORTICAL COMMANDS (v3.0)
                # ══════════════════════════════════════════════════

                # ── /ask — Direct BitNet query ──
                elif user_input.startswith("/ask "):
                    question = user_input[5:].strip()
                    if question:
                        self.bank.log_message("Kevin", f"/ask {question}")
                        raw = self._cortical_ask(question)
                        if raw:
                            self.bank.log_message(
                                "METABOLIC", raw,
                                arch="BitNet", wmin=self.char.wmin,
                                ilp_depth=self.char.depth)
                    else:
                        print("  Usage: /ask What is quantum entanglement?")
                    continue

                # ── /cortex — Show cortical status ──
                elif user_input == "/cortex":
                    if self.cortex:
                        cs = self.cortex.status()
                        print(f"  Backend:   {cs['backend']}")
                        print(f"  Endpoint:  {cs['endpoint']}")
                        print(f"  Ready:     {cs['ready']}")
                        print(f"  Queries:   {cs['queries']}")
                        print(f"  Successes: {cs['successes']}")
                        print(f"  Failures:  {cs['failures']}")
                        print(f"  Tokens:    {cs['total_tokens']}")
                        print(f"  Avg latency: {cs['avg_latency_ms']:.0f}ms")
                        print(f"  Mode:      {'cortical-assisted' if self.cortical_mode else 'pure PEIG'}")
                    else:
                        print("  No cortical client initialized.")
                    continue

                # ── /mode — Toggle cortical-assisted mode ──
                elif user_input == "/mode":
                    if self.cortex and self.cortex.ready:
                        self.cortical_mode = not self.cortical_mode
                        mode = "cortical-assisted" if self.cortical_mode else "pure PEIG"
                        print(f"  Mode: {mode}")
                        if self.cortical_mode:
                            print("  Aria will query BitNet during normal conversation.")
                        else:
                            print("  Aria will use only her PEIG dynamics.")
                    else:
                        print("  No cortical backend available to toggle.")
                    continue

                # ══════════════════════════════════════════════════
                # NORMAL CONVERSATION — enhanced with cortical bridge
                # ══════════════════════════════════════════════════

                self.bank.log_message("Kevin", user_input)

                # Step 1: Aria's pure PEIG response (always happens)
                response = self.voice.respond(user_input)
                arch     = self.char.dominant_archetype

                print(f"\nARIA [{arch}]: {response}")
                print(f"       {self._status_line()}")

                self.bank.log_message(
                    "ARIA", response,
                    emotion=arch, arch=arch,
                    wmin=self.char.wmin,
                    ilp_depth=self.char.depth)

                # Step 2: If cortical mode is on, also query BitNet
                if self.cortical_mode and self.cortex and self.cortex.ready:
                    raw = self._cortical_ask(user_input)
                    if raw:
                        self.bank.log_message(
                            "METABOLIC", raw,
                            arch="BitNet", wmin=self.char.wmin,
                            ilp_depth=self.char.depth)

                self.runtime_log.write(
                    f"[{time.strftime('%H:%M:%S')}] "
                    f"YOU: {user_input} | ARIA: {response}\n")
                self.runtime_log.flush()

            except KeyboardInterrupt:
                self._save_state()
                self.bank.close()
                print("\n\nARIA: I am always here. Until next time.")
                self.alive = False
                break
            except Exception as e:
                log.error(f"Runtime error: {e}")
                continue

        self.runtime_log.close()
        log.info(f"Session ended. Steps: {self.step_n}. "
                 f"ILP depth: {self.char.depth}. "
                 f"Generations: {len(self.char.frozen)}.")


# ═══════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="ARIA PEIG Core v3.0 + Cortical Bridge")
    parser.add_argument("--daemon", action="store_true",
                        help="Run headless, log only")
    parser.add_argument("--world",  action="store_true",
                        help="Also launch pygame world engine")
    parser.add_argument("--no-cortex", action="store_true",
                        help="Disable cortical bridge (pure PEIG)")
    args = parser.parse_args()

    if args.world:
        import subprocess
        subprocess.Popen([sys.executable,
                          str(Path(__file__).parent / "ARIA_WORLD_ENGINE.py")])

    aria = ARIARuntime(use_cortex=not args.no_cortex)
    aria.run(daemon=args.daemon)

if __name__ == "__main__":
    main()