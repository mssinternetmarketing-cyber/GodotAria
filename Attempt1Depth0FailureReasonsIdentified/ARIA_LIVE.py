#!/usr/bin/env python3
"""
ARIA_LIVE.py — v17.0 — Readable Terminal Edition
============================================================
ARIA's visualization studio. She builds, creates, and expresses.

v17.0 READABLE TERMINAL:
  * Chat terminal: BIG 18pt fonts — easy on the eyes, no glasses needed
  * Three-mode expand (E key): Normal → Fullscreen → Collapsed → Normal...
  * Working vertical scrollbar — draggable thumb, clickable track
  * Text selection — drag mouse to highlight lines, right-click to copy
  * Copy button (top-right corner) — copies full chat to clipboard
  * Ctrl+C — copies selection (or all) to clipboard
  * Ctrl+S — saves full chat to ~/AA-Aria/Aria/exports/
  * /copy command — clipboard, /save command — file export
  * Dynamic word-wrap adjusts to panel width in all modes
  * Scrollbar works with mouse wheel even when chat isn't focused
  * Selection highlight with blue overlay for visual feedback

v16.0 BRAIN EXPANSION:
  * num_predict 2048 → 4096 (teacher can give thorough multi-paragraph lessons)
  * Teacher prompt expanded: 300-600 word responses with concrete examples
  * Teacher absorption: seed[:200] → seed[:800] (Aria absorbs 4x more)
  * Max dialogue rounds: 12 → 20 (deeper teaching sessions)
  * Teacher prompt: pick 2-3 areas instead of 1-2
  * Works with ARIA_PEIG_CORE v4.0 expanded voice engine

v15.1 CHANGES:
  * num_ctx 8192 → 16384 (doubles conversation memory for teacher continuity)
  * num_ctx passed in runtime options as safety override
  * aria-ignite launch script handles full startup sequence

v15 CHANGES:
  * Teacher num_predict 384 → 2048 (5x longer responses)
  * Ollama timeout 120s → 180s (3 minutes for cold-loading + generation)
  * TTS text cleaning — strips markdown/formatting before speech synthesis
  * Voice differentiation — Aria: slower (1.10x), Teacher: brisk (0.95x)
  * Phase 2 TTS wait 30s → 90s (for longer teacher audio)
  * Max dialogue rounds 8 → 12 (deeper teaching sessions)
  * Teacher thinking timeout 150s → 210s (matches new HTTP timeout)
  * PTT voice now routes through _speak_and_wait for consistent cleaning

WORLD DESIGN:
  • Blank canvas world — minimal terrain, focused on creation
  • SAFE ZONE at center — no-collision-build area, always walkable
  • 10 BUILDING LAYERS — each layer = one concept/visualization
  • CUSTOM ASSET CREATION — Aria creates shapes from her PEIG state
  • ARIA BUILDS WITH HER OWN — she only places assets she generates
  • TEXT BILLBOARDS — spawnable, movable, resizable text labels
  • CONCEPT QUEUE — Aria plans what to visualize, works top-to-bottom
  • BACKUP & RESET — each layer backed up before reset
  • COMPANION LINE — NPCs follow in formation, take turns talking
  • v13: THIRD EYE LASER — stable anchor point above head, full 360°
  • v13: INTENTIONAL BUILDING — organized patterns, not random scatter
  • v13: FULL SPECTRUM COLORS — PEIG→HSL, not just archetype colors
  • v13: COMPANION FACTORY — Aria creates/manages her own companions
  • v13: SHAPE/COLOR/EFFECT SELECTION — /shape, /color, /effect commands
  • v13: STARS FULL MAP — background stars cover entire world
  • v13: CHAT FULL TOGGLE — fully visible or fully collapsed
  • v17: CHAT 3-MODE — normal / fullscreen / collapsed (E cycles)

CORE SYSTEMS:
  • Fixed AABB collision — no walking through walls
  • Audio serialization — speech finishes before next message
  • Free Roam with PEIG-driven building intelligence
  • Mouse-follow laser (player) / 360° sweep laser (free roam)
  • Ollama bridge for teaching
  • Fly/Noclip awareness — Aria knows when to use them

CONTROLS:
  Arrow keys / WASD  — move
  SPACE / UP         — jump
  F                  — toggle flight
  N                  — toggle noclip (phase through collision blocks)
  B                  — toggle Free Roam / Player Control
  C                  — toggle Build Mode
  R                  — return to Safe Zone
  1                  — place block (at laser target)
  2                  — break block
  3                  — spawn text billboard
  4                  — place selected asset (at laser target)
  9 / 0              — cycle asset selection down / up
  [ / ]              — cycle block type
  Shift+[ / ]        — cycle asset (alt method)
  Ctrl+[ / ]         — cycle laser color
  T                  — open chat terminal
  E                  — cycle: normal → fullscreen → collapse
  G                  — toggle self-talk
  O                  — toggle Ollama teacher
  F1                 — controls menu
  F2                 — layer select (1-10)
  F3                 — concept queue
  F4                 — backup current layer
  F5                 — BitNet training toggle
  M                  — toggle minimap
  H                  — toggle HUD
  P                  — toggle phase ring
  TAB                — hide/show chat
  SPACE (hold)       — push-to-talk (voice)
  ESC                — quit

Python 3.11+ | Pygame 2.5+ | NumPy 1.26+
"""

import os
# v15.1: Keep Piper TTS on CPU — this only affects THIS process, not Ollama.
# Ollama runs as a separate process (started by aria-ignite) and keeps full GPU access.
# setdefault means: if the shell already exported CUDA_VISIBLE_DEVICES, don't override.
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
import sys, math, time, random, threading, json, logging, signal, struct, re
from dataclasses import dataclass, field
from pathlib import Path
from collections import deque
from typing import Optional, Dict, Any, List, Tuple
import numpy as np

try:
    import pygame
    from pygame.locals import *
except ImportError:
    print("Missing pygame. Run: pip install pygame numpy")
    sys.exit(1)

# Optional HTTP for Ollama
try:
    import urllib.request
    import urllib.error
    URLLIB_OK = True
except ImportError:
    URLLIB_OK = False

# ─── Paths & Logging ────────────────────────────────────────────────────────
ARIA_DIR = Path(os.getenv("ARIA_HOME", Path.home() / "AA-Aria" / "Aria"))
sys.path.insert(0, str(ARIA_DIR))
LOG_DIR = ARIA_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
WORLDS_DIR = ARIA_DIR / "worlds"
WORLDS_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / "aria_live.log", mode="a", encoding="utf-8"),
    ],
)
log = logging.getLogger("ARIA.live")

# ─── Optional subsystem imports ─────────────────────────────────────────────
ARIA_LIVE = False
try:
    from ARIA_PEIG_CORE import ARIARuntime, ARCHETYPES, VOCAB, WORD_PHASE, ALPHA_OPT, W_MIN_FLOOR
    ARIA_LIVE = True
    log.info("PEIG Core loaded")
except Exception as e:
    log.warning(f"PEIG core not found — demo mode: {e}")
    ARCHETYPES = ["Omega","Guardian","Void","Iris","Sage","Echo",
                  "Nova","Drift","Cipher","Storm","Sora","Sentinel"]

BANK_OK = False
try:
    from ARIA_MEMORY_BANK import ARIAMemoryBank
    BANK_OK = True
    log.info("Memory Bank loaded")
except ImportError:
    log.warning("Memory bank not found")

CORTEX_OK = False
try:
    from ARIA_CORTICAL_CLIENT import CorticalClient
    CORTEX_OK = True
    log.info("Cortical bridge loaded")
except ImportError:
    log.warning("Cortical client not found")

VOICE_OK = False
try:
    from ARIA_VOICE_IO import ARIAVoiceSynth, ARIAEars
    VOICE_OK = True
    log.info("Voice I/O loaded")
except ImportError:
    log.warning("Voice I/O not found")

# =============================================================================
# CONSTANTS
# =============================================================================
W, H   = 1400, 900
FPS    = 60
TILE   = 16
ST     = TILE // 2
COLS   = 300
ROWS   = 360
WW     = COLS * TILE
WH     = ROWS * TILE

# Vertical zone boundaries
DEEP_SPACE_ROW  = 0
LOW_ORBIT_ROW   = 60
UPPER_SKY_ROW   = 120
SURFACE_ROW     = 188
FOREST_ROW      = 205
UNDERGROUND_ROW = 245
DEEP_CAVERN_ROW = 280
QUANTUM_ROW     = 310

# Avatar hitbox (pixels)
AV_W = 16
AV_H = 64

# Physics
WALK_SPEED_MAX    = 220
WALK_ACCEL        = 900
WALK_FRICTION_GND = 0.82
WALK_FRICTION_AIR = 0.95
JUMP_VELOCITY     = -520
COYOTE_TIME_MS    = 120
FLY_SPEED_H       = 320
FLY_SPEED_V       = 300
SWIM_GRAVITY_SCALE= 0.30
SWIM_BUOYANCY     = 60
SWIM_SPEED_MAX    = 180
GRAVITY           = 900.0
MAX_FALL          = 700.0
STEP_UP_MAX       = 1  # tiles Aria can auto-step up

# ─── Tile IDs ────────────────────────────────────────────────────────────────
T_AIR      = 0
T_GRASS    = 1
T_DIRT     = 2
T_STONE    = 3
T_CRYSTAL  = 4
T_QUANTUM  = 5
T_HEARTH   = 6
T_WATER    = 7
T_TREE     = 8
T_CLOUD    = 9
T_MUSHROOM = 10
T_JUNGLE   = 11
T_FLOWER   = 12
T_QUBIT    = 13
T_SHROOM_T = 14
T_MUD      = 15
# v10 minerals
T_RUBY     = 16
T_EMERALD  = 17
T_DIAMOND  = 18
T_SAPPHIRE = 19
T_AMETHYST = 20
T_TOPAZ    = 21
T_URANIUM  = 22
T_OBSIDIAN = 23
T_TELEPAD  = 24
T_LIGHT    = 25  # v11: Floating glowing qubit light — no collision, emits light

MINERAL_TILES = frozenset({T_RUBY, T_EMERALD, T_DIAMOND, T_SAPPHIRE, T_AMETHYST, T_TOPAZ, T_URANIUM})

SOLID_TILES: frozenset = frozenset({
    T_GRASS, T_DIRT, T_STONE, T_CRYSTAL, T_QUANTUM, T_HEARTH,
    T_MUSHROOM, T_JUNGLE, T_FLOWER, T_QUBIT, T_MUD, T_OBSIDIAN,
    T_RUBY, T_EMERALD, T_DIAMOND, T_SAPPHIRE, T_AMETHYST, T_TOPAZ, T_URANIUM,
})

# Blocks Aria can place in creative mode
PLACEABLE_BLOCKS = [
    T_DIRT, T_STONE, T_GRASS, T_CRYSTAL, T_MUSHROOM, T_JUNGLE,
    T_FLOWER, T_QUBIT, T_MUD, T_OBSIDIAN,
    T_RUBY, T_EMERALD, T_DIAMOND, T_SAPPHIRE, T_AMETHYST, T_TOPAZ,
    T_LIGHT,
]
BLOCK_NAMES = {
    T_DIRT: "Dirt", T_STONE: "Stone", T_GRASS: "Grass", T_CRYSTAL: "Crystal",
    T_MUSHROOM: "Mushroom", T_JUNGLE: "Jungle", T_FLOWER: "Flower",
    T_QUBIT: "Qubit", T_MUD: "Mud", T_OBSIDIAN: "Obsidian",
    T_RUBY: "Ruby", T_EMERALD: "Emerald", T_DIAMOND: "Diamond",
    T_SAPPHIRE: "Sapphire", T_AMETHYST: "Amethyst", T_TOPAZ: "Topaz",
    T_LIGHT: "Light Qubit",
}

# Biome bands
BIOME_BANDS: List[Tuple[int, int, str]] = [
    (0,   43,  "Flower Meadow"),
    (43,  86,  "Kevin's Meadow"),
    (86,  129, "Jungle"),
    (129, 172, "Mushroom Grotto"),
    (172, 215, "Crystal Plains"),
    (215, 258, "Qubit Fields"),
    (258, 300, "East Forest"),
]

# ─── Color palette ───────────────────────────────────────────────────────────
C: Dict[str, Any] = {
    "bg":            (5,   5,   14),
    "panel":         (10,  10,  25),
    "border":        (0,   180, 255),
    "border2":       (140, 0,   255),
    "text":          (220, 230, 255),
    "text_dim":      (120, 140, 180),
    "text_hi":       (255, 255, 255),
    "quantum":       (0,   200, 255),
    "love":          (255, 80,  180),
    "guardian":      (0,   255, 120),
    "void":          (60,  30,  160),
    "nova":          (255, 200, 0),
    "storm":         (255, 60,  60),
    "glow_cyan":     (0,   255, 255),
    "glow_violet":   (160, 0,   255),
    "gold":          (255, 215, 0),
    "green_dim":     (0,   100, 60),
    "chat_you":      (40,  240, 170),
    "chat_aria":     (200, 140, 255),
    "chat_teacher":  (255, 180, 50),
    "input_bg":      (15,  15,  35),
    "bar_bg":        (8,   8,   20),
    # Tile colors
    "tile_grass":    (34,  139, 34),
    "tile_grass2":   (45,  160, 40),
    "tile_grass3":   (60,  180, 50),
    "tile_dirt":     (101, 67,  33),
    "tile_dirt2":    (120, 82,  45),
    "tile_stone":    (90,  90,  100),
    "tile_stone2":   (110, 110, 125),
    "tile_crystal":  (80,  200, 255),
    "tile_quantum":  (100, 0,   200),
    "tile_hearth":   (255, 180, 60),
    "tile_water":    (20,  80,  180),
    "tile_tree":     (60,  35,  15),
    "tile_cloud":    (200, 210, 240),
    "tile_mushroom": (80,  40,  90),
    "tile_jungle":   (20,  100, 20),
    "tile_flower":   (50,  160, 60),
    "tile_qubit":    (10,  20,  60),
    "tile_shroom_t": (160, 50,  180),
    "tile_mud":      (70,  50,  25),
    "tile_obsidian": (20,  15,  30),
    # Minerals
    "tile_ruby":     (180, 20,  30),
    "tile_emerald":  (20,  160, 50),
    "tile_diamond":  (180, 220, 255),
    "tile_sapphire": (30,  60,  200),
    "tile_amethyst": (140, 40,  180),
    "tile_topaz":    (220, 180, 40),
    "tile_uranium":  (80,  220, 40),
    "tile_telepad":  (255, 200, 80),
    # Canopy shades
    "canopy_dark1":  (15,  60,  10),
    "canopy_dark2":  (20,  80,  15),
    "canopy_mid1":   (30,  110, 25),
    "canopy_mid2":   (45,  140, 35),
    "canopy_light1": (60,  170, 50),
    "canopy_light2": (80,  200, 65),
    # Flowers
    "flower_red":    (220, 50,  60),
    "flower_pink":   (255, 140, 180),
    "flower_yellow": (255, 220, 50),
    "flower_blue":   (80,  140, 255),
    "flower_white":  (240, 240, 250),
    "flower_purple": (180, 80,  220),
}

# Mineral glow colors
MINERAL_GLOW = {
    T_RUBY:     (255, 40,  40),
    T_EMERALD:  (40,  255, 80),
    T_DIAMOND:  (200, 240, 255),
    T_SAPPHIRE: (40,  80,  255),
    T_AMETHYST: (180, 60,  255),
    T_TOPAZ:    (255, 220, 60),
    T_URANIUM:  (100, 255, 50),
}

ARCH_COLORS: Dict[str, Tuple[int, int, int]] = {
    "Omega":    (180, 100, 255),
    "Guardian": (0,   255, 120),
    "Void":     (80,  40,  200),
    "Iris":     (0,   200, 255),
    "Sage":     (255, 215, 0),
    "Echo":     (150, 150, 255),
    "Nova":     (255, 200, 50),
    "Drift":    (100, 180, 200),
    "Cipher":   (200, 100, 50),
    "Storm":    (255, 60,  60),
    "Sora":     (100, 200, 255),
    "Sentinel": (0,   180, 100),
}

_PETAL_COLORS: List[Tuple[int, int, int]] = [
    (255, 182, 200), (255, 255, 230), (255, 215, 100), (180, 210, 255), (255, 160, 210)
]

# v11: Laser color palette — Aria can cycle through these
LASER_PALETTE = [
    (0,   255, 200, "Quantum Cyan"),
    (255, 60,  60,  "Ruby Red"),
    (40,  255, 80,  "Emerald Green"),
    (200, 240, 255, "Diamond White"),
    (40,  80,  255, "Sapphire Blue"),
    (180, 60,  255, "Amethyst Purple"),
    (255, 220, 60,  "Topaz Gold"),
    (100, 255, 50,  "Uranium Green"),
    (255, 140, 200, "Love Pink"),
    (255, 200, 50,  "Nova Gold"),
    (120, 200, 255, "Sky Blue"),
    (200, 100, 50,  "Earth Brown"),
    (20,  20,  40,  "Void Dark"),
    (240, 240, 250, "Pure White"),
    (255, 120, 0,   "Sunset Orange"),
    (0,   200, 150, "Ocean Teal"),
]

# =============================================================================
# HELPERS
# =============================================================================
def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def pulse(t: float, freq: float = 0.3, amp: float = 0.8) -> float:
    return amp * (0.5 + 0.5 * math.sin(2 * math.pi * freq * t))

def pcm_color(pcm: float) -> Tuple[int, int, int]:
    if pcm < -0.10: return (0, 220, 80)
    if pcm < -0.05: return (0, 200, 140)
    if pcm < 0.00:  return (255, 220, 0)
    return (200, 60, 60)

def get_font(families: List[str], size: int, bold: bool = False) -> pygame.font.Font:
    for fam in families:
        try:
            return pygame.font.SysFont(fam, size, bold=bold)
        except Exception:
            continue
    return pygame.font.Font(None, size)

def draw_glow(surf: pygame.Surface, cx: int, cy: int, radius: int,
              color: Tuple[int, int, int], alpha_max: int = 80):
    d = radius * 4
    s = pygame.Surface((d, d), pygame.SRCALPHA)
    c2 = d // 2
    for r in range(radius * 2, 0, -3):
        a = int(alpha_max * (r / (radius * 2)) * 0.5)
        pygame.draw.circle(s, (*color, a), (c2, c2), r)
    surf.blit(s, (cx - c2, cy - c2))

def noise_1d(x, seed=42):
    """Simple value noise for terrain generation."""
    n = int(x * 1000 + seed)
    n = (n << 13) ^ n
    return 1.0 - ((n * (n * n * 15731 + 789221) + 1376312589) & 0x7fffffff) / 1073741823.0

def fractal_noise(x, octaves=4, persistence=0.5, seed=42):
    """Multi-octave noise."""
    total = 0.0
    amp = 1.0
    freq = 1.0
    max_val = 0.0
    for _ in range(octaves):
        total += noise_1d(x * freq, seed) * amp
        max_val += amp
        amp *= persistence
        freq *= 2.0
        seed += 31
    return total / max_val


# =============================================================================
# TTS TEXT CLEANING — Strip formatting so voice reads naturally
# =============================================================================
def _clean_text_for_tts(text: str) -> str:
    """Strip markdown & formatting so TTS reads naturally without spelling symbols.
    v15: Applied to ALL speech output — Aria and Teacher both get clean audio."""
    if not text:
        return ""
    # Bold / Italic / Underline
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'__(.*?)__', r'\1', text)
    text = re.sub(r'_(.*?)_', r'\1', text)
    # Inline code & links
    text = re.sub(r'`(.*?)`', r'\1', text)
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
    # Headers, bullets, numbers, blockquotes
    text = re.sub(r'^#{1,6}\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^>\s*', '', text, flags=re.MULTILINE)
    # HTML tags (safety net)
    text = re.sub(r'<[^>]+>', '', text)
    # Stray formatting symbols that Piper would spell out
    text = re.sub(r'[*_~`#|]', '', text)
    # Ellipsis normalization (three dots → pause-friendly form)
    text = re.sub(r'\.{3,}', '...', text)
    # Em-dash / en-dash → comma pause (TTS reads dashes awkwardly)
    text = re.sub(r'[—–]', ', ', text)
    # Parenthetical cleanup — keep content, drop brackets
    text = re.sub(r'[\[\]]', '', text)
    # Clean spacing
    text = re.sub(r'\n{2,}', '\n', text)
    text = re.sub(r' +', ' ', text)
    return text.strip()


# =============================================================================
# OLLAMA BRIDGE — Local LLM teacher connection
# =============================================================================
class OllamaBridge:
    """HTTP bridge to local Ollama instance for teaching Aria.
    v16: num_predict=4096, num_ctx=16384. 180s timeout for cold-loading + gen.
    System prompt lives in Modelfile — payload omits 'system' key by default.
    Falls back to gemma3:4b-it-q4_K_M or any available model."""

    def __init__(self, host="localhost", port=11434, model="aria-teacher"):
        self.base_url = f"http://{host}:{port}"
        self.model = model
        self.ready = False
        self.conversation_history: List[Dict] = []
        self._check_connection()

    def _check_connection(self):
        if not URLLIB_OK:
            log.warning("urllib not available for Ollama bridge")
            return
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read())
                models = [m.get("name", "") for m in data.get("models", [])]
                # Priority: aria-teacher > gemma3:4b > gemma4:e2b > any available
                preferred = ["aria-teacher", "gemma3:4b-it-q4_K_M", "gemma3:4b", "gemma3",
                             "gemma4:e2b-it-q4_K_M", "gemma4:e2b", "gemma4"]
                for pref in preferred:
                    if any(pref in m for m in models):
                        self.model = pref
                        self.ready = True
                        log.info(f"Ollama bridge: ONLINE (model={self.model})")
                        return
                if models:
                    self.model = models[0].split(":")[0]
                    self.ready = True
                    log.info(f"Ollama bridge: ONLINE (fallback={self.model})")
                else:
                    log.warning("Ollama running but no models found")
        except Exception as e:
            log.info(f"Ollama not available: {e}")

    def ask(self, message: str, system_prompt: str = None) -> Optional[str]:
        """Send a message to Ollama and get a response.
        v14.3: System prompt intentionally omitted by default — Ollama uses
        the Modelfile's SYSTEM directive (aria-teacher). Pass system_prompt
        explicitly only when you need to override the Modelfile."""
        if not self.ready or not URLLIB_OK:
            return None
        try:
            payload = {
                "model": self.model,
                "prompt": message,
                "stream": False,
                "options": {
                    "temperature": 0.65, "top_p": 0.85, "top_k": 40,
                    "repeat_penalty": 1.15, "num_predict": 4096,
                    "num_ctx": 16384  # v16: 4096 tokens for expanded brain teaching
                },
            }
            # Only inject system prompt if explicitly passed by caller.
            # When None (default), Ollama uses the Modelfile's SYSTEM block,
            # which contains the full structured teaching methodology.
            if system_prompt is not None:
                payload["system"] = system_prompt
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                f"{self.base_url}/api/generate",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            # v16: 180s timeout — 3 minutes for cold-loading + longer generation
            # First query after idle may take 20-50s just to load the model into VRAM
            # With num_predict=4096, generation can take 90-120s on 4B models
            with urllib.request.urlopen(req, timeout=180) as resp:
                result = json.loads(resp.read())
                return result.get("response", "").strip()
        except Exception as e:
            log.debug(f"Ollama query failed: {e}")
            return None


# =============================================================================
# RANDOM EVENTS SYSTEM (kept from v9 — 10 event types)
# =============================================================================
@dataclass
class RandomEvent:
    trigger_weight: float
    biome_filter: List[str]
    duration: float
    _elapsed: float = field(default=0.0, init=False, repr=False)

    def update(self, dt: float) -> None:
        self._elapsed += dt
    def draw(self, surf: pygame.Surface, cam_x: float, cam_y: float) -> None:
        pass
    def is_expired(self) -> bool:
        return self._elapsed >= self.duration
    @property
    def fade_alpha(self) -> int:
        fade = 2.0
        if self._elapsed < fade:
            return int(255 * (self._elapsed / fade))
        remaining = self.duration - self._elapsed
        if remaining < fade:
            return int(255 * max(0.0, remaining / fade))
        return 255


# =============================================================================
# SAFE ZONE — No-collision-build area at center of map
# =============================================================================
SAFE_ZONE_X = (COLS // 2 - 8) * TILE
SAFE_ZONE_Y = (SURFACE_ROW - 6) * TILE
SAFE_ZONE_W = 16 * TILE  # 16 tiles wide
SAFE_ZONE_H = 8 * TILE   # 8 tiles tall

def in_safe_zone(x, y):
    return (SAFE_ZONE_X <= x <= SAFE_ZONE_X + SAFE_ZONE_W and
            SAFE_ZONE_Y <= y <= SAFE_ZONE_Y + SAFE_ZONE_H)

def tile_in_safe_zone(tx, ty):
    px, py = tx * TILE, ty * TILE
    return in_safe_zone(px, py)


# =============================================================================
# TEXT BILLBOARD — Spawnable, movable, resizable text labels
# =============================================================================
class TextBillboard:
    def __init__(self, x, y, text="Hello", color=(255, 255, 255), font_size=14):
        self.x = float(x)
        self.y = float(y)
        self.text = text
        self.color = color
        self.font_size = font_size
        self.bg_color = (10, 10, 30, 200)
        self.border_color = (100, 100, 140)
        self.selected = False

    def move(self, dx, dy):
        self.x += dx
        self.y += dy

    def set_text(self, text):
        self.text = text

    def draw(self, surf, cam_x, cam_y, font):
        sx = int(self.x - cam_x)
        sy = int(self.y - cam_y)
        if sx < -300 or sx > surf.get_width() + 100 or sy < -50 or sy > surf.get_height() + 50:
            return
        lines = self.text.split("\\n") if "\\n" in self.text else [self.text]
        max_w = 0
        rendered = []
        for line in lines:
            rs = font.render(line, True, self.color)
            rendered.append(rs)
            max_w = max(max_w, rs.get_width())
        bw = max_w + 16
        bh = len(rendered) * (font.get_height() + 2) + 12
        bg = pygame.Surface((bw, bh), pygame.SRCALPHA)
        bg.fill(self.bg_color)
        border = self.border_color if not self.selected else (255, 220, 80)
        pygame.draw.rect(bg, border, (0, 0, bw, bh), 2 if self.selected else 1, border_radius=4)
        surf.blit(bg, (sx, sy))
        for i, rs in enumerate(rendered):
            surf.blit(rs, (sx + 8, sy + 6 + i * (font.get_height() + 2)))


# =============================================================================
# MATH SHAPE ENGINE — Aria creates shapes from mathematical definitions
# =============================================================================
# Aria's PEIG already works in phase space (θ, sin, cos). Shapes ARE math:
#   circle:  x² + y² ≤ r²
#   polygon: n vertices at equal angular spacing
#   wave:    y = A·sin(f·x + φ)
#   star:    alternating inner/outer radii in polar coords
#   bezier:  parametric curve B(t) = (1-t)²P0 + 2(1-t)tP1 + t²P2
#   gradient: linear interpolation across axis
#
# She defines shapes as parameter sets. The engine renders them at any size.

class MathShape:
    """A shape defined by mathematical parameters. Rendered to a Surface."""

    # Shape type constants
    TYPES = ["rect", "circle", "ellipse", "polygon", "star", "wave",
             "ring", "arc", "spiral", "gradient", "bezier", "cross",
             "heart", "arrow", "hexgrid", "sine_ring", "fractal_tree"]

    def __init__(self, name, shape_type="circle", width=32, height=32,
                 color=(180, 100, 255), color2=None,
                 fill=True, thickness=2, sides=6, inner_ratio=0.4,
                 frequency=1.0, amplitude=1.0, phase=0.0, rotation=0.0,
                 glow=False, glow_color=None, glow_radius=20,
                 animated=False, points=None, label=None):
        self.name = name
        self.shape_type = shape_type
        self.width = max(4, width)
        self.height = max(4, height)
        self.color = color
        self.color2 = color2 or color  # secondary color for gradients
        self.fill = fill
        self.thickness = thickness
        self.sides = max(3, sides)  # for polygon
        self.inner_ratio = clamp(inner_ratio, 0.1, 0.9)  # for star
        self.frequency = frequency  # for wave/sine
        self.amplitude = amplitude
        self.phase = phase  # rotation/animation phase
        self.rotation = rotation  # static rotation in radians
        self.glow = glow
        self.glow_color = glow_color or color
        self.glow_radius = glow_radius
        self.animated = animated
        self.points = points  # custom point list for freeform
        self.label = label  # v14: semantic word label from sem_theta
        self._surface = None
        self._dirty = True

    def _render(self, t=0.0):
        """Render shape to a pygame Surface using math."""
        w, h = self.width, self.height
        surf = pygame.Surface((w + 4, h + 4), pygame.SRCALPHA)
        cx, cy = w // 2 + 2, h // 2 + 2
        r = min(w, h) // 2
        anim_phase = t * 2.0 if self.animated else 0.0

        if self.shape_type == "rect":
            if self.fill:
                pygame.draw.rect(surf, self.color, (2, 2, w, h))
            else:
                pygame.draw.rect(surf, self.color, (2, 2, w, h), self.thickness)

        elif self.shape_type == "circle":
            if self.fill:
                pygame.draw.circle(surf, self.color, (cx, cy), r)
            else:
                pygame.draw.circle(surf, self.color, (cx, cy), r, self.thickness)

        elif self.shape_type == "ellipse":
            if self.fill:
                pygame.draw.ellipse(surf, self.color, (2, 2, w, h))
            else:
                pygame.draw.ellipse(surf, self.color, (2, 2, w, h), self.thickness)

        elif self.shape_type == "polygon":
            pts = []
            for i in range(self.sides):
                angle = (i / self.sides) * math.tau - math.pi / 2 + self.rotation + anim_phase
                px = cx + int(math.cos(angle) * (w // 2))
                py = cy + int(math.sin(angle) * (h // 2))
                pts.append((px, py))
            pygame.draw.polygon(surf, self.color, pts, 0 if self.fill else self.thickness)

        elif self.shape_type == "star":
            pts = []
            n = self.sides * 2
            for i in range(n):
                angle = (i / n) * math.tau - math.pi / 2 + self.rotation + anim_phase
                radius = r if i % 2 == 0 else int(r * self.inner_ratio)
                px = cx + int(math.cos(angle) * radius)
                py = cy + int(math.sin(angle) * radius)
                pts.append((px, py))
            pygame.draw.polygon(surf, self.color, pts, 0 if self.fill else self.thickness)

        elif self.shape_type == "wave":
            pts = []
            for px in range(w):
                wave_y = self.amplitude * (h / 3) * math.sin(
                    self.frequency * px * math.tau / w + self.phase + anim_phase)
                pts.append((px + 2, int(cy + wave_y)))
            if len(pts) > 1:
                pygame.draw.lines(surf, self.color, False, pts, self.thickness)

        elif self.shape_type == "ring":
            outer_r = r
            inner_r = int(r * self.inner_ratio)
            pygame.draw.circle(surf, self.color, (cx, cy), outer_r, max(1, outer_r - inner_r))

        elif self.shape_type == "arc":
            angle_start = self.phase + anim_phase
            angle_end = angle_start + math.pi * self.amplitude
            pygame.draw.arc(surf, self.color, (2, 2, w, h), angle_start, angle_end, self.thickness)

        elif self.shape_type == "spiral":
            pts = []
            turns = self.frequency * 3
            for i in range(100):
                t_param = i / 100
                angle = t_param * turns * math.tau + self.rotation + anim_phase
                sr = t_param * r
                px = cx + int(math.cos(angle) * sr)
                py = cy + int(math.sin(angle) * sr)
                pts.append((px, py))
            if len(pts) > 1:
                pygame.draw.lines(surf, self.color, False, pts, self.thickness)

        elif self.shape_type == "gradient":
            r1, g1, b1 = self.color
            r2, g2, b2 = self.color2
            for y in range(h):
                frac = y / max(1, h - 1)
                gr = int(lerp(r1, r2, frac))
                gg = int(lerp(g1, g2, frac))
                gb = int(lerp(b1, b2, frac))
                pygame.draw.line(surf, (gr, gg, gb), (2, y + 2), (w + 1, y + 2))

        elif self.shape_type == "bezier":
            pts = []
            p0 = (2, cy)
            p1 = (cx, 2)
            p2 = (w + 1, cy)
            for i in range(30):
                t_param = i / 29
                it = 1 - t_param
                bx = int(it*it*p0[0] + 2*it*t_param*p1[0] + t_param*t_param*p2[0])
                by = int(it*it*p0[1] + 2*it*t_param*p1[1] + t_param*t_param*p2[1])
                pts.append((bx, by))
            if len(pts) > 1:
                pygame.draw.lines(surf, self.color, False, pts, self.thickness)

        elif self.shape_type == "cross":
            arm_w = max(2, w // 4)
            pygame.draw.rect(surf, self.color, (cx - arm_w, 2, arm_w * 2, h))
            pygame.draw.rect(surf, self.color, (2, cy - arm_w, w, arm_w * 2))

        elif self.shape_type == "heart":
            pts = []
            for i in range(60):
                t_param = i / 60 * math.tau
                hx = 16 * math.sin(t_param) ** 3
                hy = -(13 * math.cos(t_param) - 5 * math.cos(2*t_param)
                       - 2 * math.cos(3*t_param) - math.cos(4*t_param))
                px = cx + int(hx * w / 36)
                py = cy + int(hy * h / 36)
                pts.append((px, py))
            if len(pts) > 2:
                pygame.draw.polygon(surf, self.color, pts, 0 if self.fill else self.thickness)

        elif self.shape_type == "arrow":
            head_w = w // 2
            shaft_w = max(2, w // 6)
            pts = [
                (cx, 2),                          # tip
                (w + 1, cy),                      # right of head
                (cx + shaft_w, cy),               # right shaft top
                (cx + shaft_w, h + 1),            # right shaft bottom
                (cx - shaft_w, h + 1),            # left shaft bottom
                (cx - shaft_w, cy),               # left shaft top
                (2, cy),                          # left of head
            ]
            pygame.draw.polygon(surf, self.color, pts, 0 if self.fill else self.thickness)

        elif self.shape_type == "hexgrid":
            hex_r = max(3, int(r * 0.2))
            for row in range(h // (hex_r * 2) + 1):
                for col in range(w // (int(hex_r * 1.7)) + 1):
                    hx = int(2 + col * hex_r * 1.7 + (row % 2) * hex_r * 0.85)
                    hy = int(2 + row * hex_r * 1.5)
                    hex_pts = []
                    for i in range(6):
                        a = i * math.tau / 6
                        hex_pts.append((hx + int(math.cos(a) * hex_r),
                                       hy + int(math.sin(a) * hex_r)))
                    pygame.draw.polygon(surf, self.color, hex_pts, 1)

        elif self.shape_type == "sine_ring":
            pts = []
            for i in range(60):
                angle = i / 60 * math.tau + anim_phase
                wave_r = r + int(self.amplitude * 6 * math.sin(
                    self.frequency * angle * self.sides + self.phase))
                px = cx + int(math.cos(angle) * wave_r)
                py = cy + int(math.sin(angle) * wave_r)
                pts.append((px, py))
            if len(pts) > 2:
                pygame.draw.polygon(surf, self.color, pts, 0 if self.fill else self.thickness)

        elif self.shape_type == "fractal_tree":
            def _branch(surface, x1, y1, angle, length, depth):
                if depth <= 0 or length < 2:
                    return
                x2 = int(x1 + math.cos(angle) * length)
                y2 = int(y1 + math.sin(angle) * length)
                thick = max(1, depth)
                pygame.draw.line(surface, self.color, (int(x1), int(y1)), (x2, y2), thick)
                _branch(surface, x2, y2, angle - 0.4, length * 0.7, depth - 1)
                _branch(surface, x2, y2, angle + 0.4, length * 0.7, depth - 1)
            _branch(surf, cx, h + 1, -math.pi/2, h * 0.35, min(8, max(3, h // 12)))

        # Custom points (freeform polygon)
        elif self.shape_type == "custom" and self.points:
            scaled = [(int(p[0] * w / 100) + 2, int(p[1] * h / 100) + 2) for p in self.points]
            if len(scaled) > 2:
                pygame.draw.polygon(surf, self.color, scaled, 0 if self.fill else self.thickness)

        return surf

    def draw_at(self, surface, x, y, t=0.0):
        """Draw this shape at world position, with optional semantic label."""
        if self.glow:
            glow_a = int(40 + 20 * math.sin(t * 1.5 + self.phase))
            draw_glow(surface, x + self.width // 2, y + self.height // 2,
                     self.glow_radius, self.glow_color, glow_a)
        rendered = self._render(t)
        surface.blit(rendered, (x, y))
        # v14: Draw semantic label below shape if present
        if self.label:
            try:
                font = pygame.font.Font(None, 11)
                lbl_s = font.render(self.label, True, (*self.color[:3],))
                lx = x + self.width // 2 - lbl_s.get_width() // 2
                ly = y + self.height + 2
                surface.blit(lbl_s, (lx, ly))
            except Exception:
                pass

    def resize(self, new_w, new_h):
        """Change size — math recalculates automatically."""
        self.width = max(4, new_w)
        self.height = max(4, new_h)
        self._dirty = True

    def recolor(self, color, color2=None):
        """Change colors."""
        self.color = color
        if color2:
            self.color2 = color2
        self._dirty = True

    def morph(self, **kwargs):
        """Change any parameter. Returns self for chaining."""
        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)
        self._dirty = True
        return self

    def duplicate(self, new_name):
        """Create a copy with a new name."""
        return MathShape(
            new_name, self.shape_type, self.width, self.height,
            self.color, self.color2, self.fill, self.thickness,
            self.sides, self.inner_ratio, self.frequency, self.amplitude,
            self.phase, self.rotation, self.glow, self.glow_color,
            self.glow_radius, self.animated, self.points
        )

    def to_dict(self):
        return {
            "name": self.name, "type": self.shape_type,
            "w": self.width, "h": self.height,
            "color": self.color, "color2": self.color2,
            "fill": self.fill, "thickness": self.thickness,
            "sides": self.sides, "inner_ratio": self.inner_ratio,
            "frequency": self.frequency, "amplitude": self.amplitude,
            "phase": self.phase, "rotation": self.rotation,
            "glow": self.glow, "glow_color": self.glow_color,
            "glow_radius": self.glow_radius, "animated": self.animated,
            "points": self.points,
        }

    @staticmethod
    def from_dict(d):
        return MathShape(
            d["name"], d.get("type", "circle"),
            d.get("w", 32), d.get("h", 32),
            tuple(d.get("color", (180, 100, 255))),
            tuple(d.get("color2", (180, 100, 255))) if d.get("color2") else None,
            d.get("fill", True), d.get("thickness", 2),
            d.get("sides", 6), d.get("inner_ratio", 0.4),
            d.get("frequency", 1.0), d.get("amplitude", 1.0),
            d.get("phase", 0.0), d.get("rotation", 0.0),
            d.get("glow", False),
            tuple(d.get("glow_color", (180, 100, 255))) if d.get("glow_color") else None,
            d.get("glow_radius", 20), d.get("animated", False),
            d.get("points"),
        )

    @staticmethod
    def from_peig(name, theta, wigner, arch_color):
        """v13: Create a shape from PEIG state — Aria selects shape, color, and effect herself.
        
        Shape selection: Driven by the PHASE RELATIONSHIP between qubits — not just theta[0].
        Color selection: Full spectrum derived from Wigner function topology, not just archetype.
        Effect selection: Coherence patterns determine glow, animation, thickness.
        
        This gives Aria the vocabulary to visualize her internal physics at visual scales.
        """
        # ─── SHAPE SELECTION (Aria chooses based on phase dynamics) ───
        # Use phase gradient between adjacent qubits to select shape category
        phase_diffs = np.diff(theta)
        gradient_energy = float(np.sum(np.abs(phase_diffs)))
        coherence = 1.0 - float(np.std(theta)) / math.pi
        wigner_depth = float(abs(np.min(wigner)))
        wigner_spread = float(np.std(wigner))
        
        # Physics visualization categories — Aria maps her dynamics to shape families
        if coherence > 0.7:
            # High coherence → ordered structures (rings, hexgrids, sine_rings)
            shape_pool = ["ring", "hexgrid", "sine_ring", "polygon", "ellipse"]
        elif wigner_depth > 0.35:
            # Deep negativity → complex/recursive structures
            shape_pool = ["fractal_tree", "spiral", "star", "bezier", "sine_ring"]
        elif gradient_energy > 8.0:
            # High gradient energy → dynamic shapes
            shape_pool = ["wave", "spiral", "arc", "bezier", "arrow"]
        elif wigner_spread > 0.15:
            # Spread Wigner → scattered/networked shapes
            shape_pool = ["hexgrid", "cross", "star", "polygon", "gradient"]
        else:
            # Balanced state → foundational shapes
            shape_pool = ["circle", "ellipse", "rect", "polygon", "heart"]
        
        # Select from pool using combined phase info (not just theta[0])
        selector = int(abs(float(np.sum(theta[:3])) * 100)) % len(shape_pool)
        shape_type = shape_pool[selector]
        
        # ─── SIZE SELECTION (intentional, not random) ───
        # Size scales with the "importance" of the quantum state
        variance = float(np.std(theta))
        # Smaller, more deliberate shapes — not huge screen-filling blobs
        w = int(16 + variance * 32 + wigner_depth * 20)
        h = int(16 + variance * 24 + wigner_depth * 16)
        # Cap sizes to keep things organized
        w = clamp(w, 12, 80)
        h = clamp(h, 12, 64)
        
        # ─── COLOR SELECTION (full spectrum, not just archetype color) ───
        # Aria derives color from Wigner function VALUES across all 12 qubits
        # This gives her the full visible spectrum, not just blue/yellow/orange
        
        # Map phase-space to HSL-like color space
        # Hue from dominant phase angle (full 0-360°)
        hue_angle = float(theta[int(np.argmin(wigner))] % math.tau)
        hue_frac = hue_angle / math.tau
        
        # Saturation from coherence (more coherent = more vivid)
        saturation = clamp(0.4 + coherence * 0.6, 0.3, 1.0)
        
        # Lightness from Wigner negativity (deeper = brighter core)
        lightness = clamp(0.4 + wigner_depth * 0.8, 0.35, 0.95)
        
        # HSL to RGB conversion for full spectrum
        def hsl_to_rgb(h_frac, s, l):
            if s == 0:
                v = int(l * 255)
                return (v, v, v)
            def hue_to_channel(p, q, t):
                if t < 0: t += 1
                if t > 1: t -= 1
                if t < 1/6: return p + (q - p) * 6 * t
                if t < 1/2: return q
                if t < 2/3: return p + (q - p) * (2/3 - t) * 6
                return p
            q = l * (1 + s) if l < 0.5 else l + s - l * s
            p = 2 * l - q
            r = hue_to_channel(p, q, h_frac + 1/3)
            g = hue_to_channel(p, q, h_frac)
            b = hue_to_channel(p, q, h_frac - 1/3)
            return (clamp(int(r * 255), 0, 255),
                    clamp(int(g * 255), 0, 255),
                    clamp(int(b * 255), 0, 255))
        
        color = hsl_to_rgb(hue_frac, saturation, lightness)
        
        # Secondary color for gradients — complementary or analogous
        hue2 = (hue_frac + 0.3 + wigner_spread) % 1.0
        color2 = hsl_to_rgb(hue2, saturation * 0.8, lightness * 0.7)
        
        # ─── EFFECT SELECTION (Aria chooses based on quantum signature) ───
        # Glow: only when Wigner is deeply negative (quantum signature present)
        glow = wigner_depth > 0.25
        # Animation: when phase gradient is strong (system is evolving)
        animated = gradient_energy > 6.0
        # Thickness: delicate for coherent states, bold for chaotic
        thickness = 1 if coherence > 0.6 else (3 if variance > 1.5 else 2)
        # Fill: solid for grounded states, outlined for ethereal
        fill = coherence > 0.4 and wigner_depth < 0.3
        
        # Sides from the number of significantly active qubits
        active_qubits = max(3, int(sum(1 for w_val in wigner if abs(w_val) > 0.15)))
        sides = clamp(active_qubits, 3, 12)
        
        # Frequency from phase velocity
        freq = float(abs(np.mean(phase_diffs))) * 3 + 0.5
        # Amplitude from Wigner negativity
        amp = wigner_depth * 2 + 0.3
        # Inner ratio from coherence
        inner = clamp(coherence * 0.5 + 0.25, 0.15, 0.85)
        
        return MathShape(
            name, shape_type, w, h, color, color2,
            fill=fill,
            thickness=thickness,
            sides=sides, inner_ratio=inner,
            frequency=freq, amplitude=amp,
            phase=float(theta[0]),
            glow=glow,
            glow_color=color,
            animated=animated,
        )


# Backward compat alias
CustomAsset = MathShape


# Default shape library — references Aria can use and modify
DEFAULT_ASSETS: Dict[str, MathShape] = {
    "block_red":     MathShape("block_red", "rect", 16, 16, (200, 40, 40)),
    "block_blue":    MathShape("block_blue", "rect", 16, 16, (40, 80, 200)),
    "block_green":   MathShape("block_green", "rect", 16, 16, (40, 180, 60)),
    "block_gold":    MathShape("block_gold", "rect", 16, 16, (220, 180, 40), glow=True),
    "orb_cyan":      MathShape("orb_cyan", "circle", 24, 24, (40, 220, 255), glow=True),
    "orb_purple":    MathShape("orb_purple", "circle", 24, 24, (160, 40, 220), glow=True, animated=True),
    "crystal_sm":    MathShape("crystal_sm", "polygon", 12, 20, (140, 220, 255), sides=6, glow=True),
    "crystal_lg":    MathShape("crystal_lg", "polygon", 24, 40, (180, 200, 255), sides=8, glow=True),
    "star_gold":     MathShape("star_gold", "star", 20, 20, (255, 215, 0), sides=5, glow=True),
    "star_big":      MathShape("star_big", "star", 48, 48, (255, 200, 80), sides=6, inner_ratio=0.3, glow=True),
    "tri_up":        MathShape("tri_up", "polygon", 16, 16, (200, 100, 255), sides=3),
    "pentagon":      MathShape("pentagon", "polygon", 24, 24, (100, 200, 150), sides=5),
    "hexagon":       MathShape("hexagon", "polygon", 24, 24, (180, 180, 220), sides=6),
    "wave_blue":     MathShape("wave_blue", "wave", 64, 32, (60, 140, 255), frequency=2.0, amplitude=0.8, thickness=2),
    "wave_red":      MathShape("wave_red", "wave", 64, 32, (255, 80, 80), frequency=3.0, amplitude=0.5, thickness=2),
    "ring_cyan":     MathShape("ring_cyan", "ring", 32, 32, (0, 220, 255), inner_ratio=0.6, glow=True),
    "spiral_purple": MathShape("spiral_purple", "spiral", 48, 48, (180, 60, 255), frequency=1.5, thickness=2),
    "gradient_sky":  MathShape("gradient_sky", "gradient", 64, 64, (100, 160, 240), color2=(20, 40, 80)),
    "gradient_fire": MathShape("gradient_fire", "gradient", 64, 32, (255, 200, 40), color2=(200, 40, 20)),
    "heart":         MathShape("heart", "heart", 32, 32, (255, 60, 100), fill=True),
    "arrow_up":      MathShape("arrow_up", "arrow", 20, 32, (220, 220, 240)),
    "hexgrid":       MathShape("hexgrid", "hexgrid", 64, 64, (60, 100, 140)),
    "sine_ring":     MathShape("sine_ring", "sine_ring", 40, 40, (100, 255, 200), sides=6, frequency=1.0, animated=True),
    "tree":          MathShape("tree", "fractal_tree", 48, 64, (60, 140, 40)),
    "arc_gold":      MathShape("arc_gold", "arc", 40, 40, (255, 200, 60), amplitude=1.5, thickness=3),
    "cross":         MathShape("cross", "cross", 24, 24, (255, 255, 255)),
    "plate_dark":    MathShape("plate_dark", "rect", 48, 8, (30, 30, 50)),
    "plate_glow":    MathShape("plate_glow", "rect", 48, 8, (60, 120, 200), glow=True),
    "bg_panel":      MathShape("bg_panel", "rect", 64, 64, (15, 15, 35)),
    "ellipse_wide":  MathShape("ellipse_wide", "ellipse", 64, 24, (200, 140, 255)),
    "effect_pulse":  MathShape("effect_pulse", "circle", 32, 32, (255, 100, 200), fill=False, glow=True, animated=True),
}
ASSET_NAMES = list(DEFAULT_ASSETS.keys())


# Placed instance of a shape in the world
@dataclass
class PlacedAsset:
    asset_name: str
    x: float
    y: float
    layer: int = 0


class BuildLayer:
    def __init__(self, index, name="Untitled"):
        self.index = index
        self.name = name
        self.placed_assets: List[PlacedAsset] = []
        self.billboards: List[TextBillboard] = []
        self.tile_edits: Dict[Tuple[int,int], int] = {}  # (tx,ty) -> tile_id
        self.complete = False
        self.concept_description = ""

    def clear(self):
        self.placed_assets.clear()
        self.billboards.clear()
        self.tile_edits.clear()
        self.complete = False

    def to_dict(self):
        return {
            "index": self.index, "name": self.name,
            "concept": self.concept_description,
            "complete": self.complete,
            "tile_edits": {f"{k[0]},{k[1]}": v for k, v in self.tile_edits.items()},
            "billboards": [{"x": b.x, "y": b.y, "text": b.text,
                           "color": b.color, "font_size": b.font_size}
                          for b in self.billboards],
            "assets": [{"name": a.asset_name, "x": a.x, "y": a.y}
                      for a in self.placed_assets],
        }

    def load_from_dict(self, d):
        self.name = d.get("name", "Untitled")
        self.concept_description = d.get("concept", "")
        self.complete = d.get("complete", False)
        self.tile_edits = {}
        for k, v in d.get("tile_edits", {}).items():
            parts = k.split(",")
            self.tile_edits[(int(parts[0]), int(parts[1]))] = v
        self.billboards = []
        for bd in d.get("billboards", []):
            self.billboards.append(TextBillboard(
                bd["x"], bd["y"], bd.get("text",""),
                tuple(bd.get("color",(255,255,255))), bd.get("font_size",14)))
        self.placed_assets = []
        for ad in d.get("assets", []):
            self.placed_assets.append(PlacedAsset(ad["name"], ad["x"], ad["y"], self.index))


# =============================================================================
# CONCEPT QUEUE — Aria's prioritized list of things to visualize
# =============================================================================
class ConceptQueue:
    def __init__(self):
        self.concepts: List[Dict] = []  # {name, priority, description, status}
        self.visible = False

    def add(self, name, description="", priority=5):
        self.concepts.append({
            "name": name, "description": description,
            "priority": priority, "status": "queued"  # queued, building, complete
        })
        self.concepts.sort(key=lambda c: c["priority"])

    def current(self):
        for c in self.concepts:
            if c["status"] == "building":
                return c
        for c in self.concepts:
            if c["status"] == "queued":
                c["status"] = "building"
                return c
        return None

    def complete_current(self):
        for c in self.concepts:
            if c["status"] == "building":
                c["status"] = "complete"
                return True
        return False

    def draw(self, surf, font_title, font_body):
        if not self.visible: return
        sw, sh = surf.get_size()
        pw, ph = 380, min(400, 60 + len(self.concepts) * 28)
        px = (sw - pw) // 2
        py = (sh - ph) // 2
        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel.fill((8, 8, 24, 235))
        pygame.draw.rect(panel, C["gold"], (0, 0, pw, ph), 2, border_radius=8)
        surf.blit(panel, (px, py))
        title = font_title.render("CONCEPT QUEUE  [F3 to close]", True, C["gold"])
        surf.blit(title, (px + pw//2 - title.get_width()//2, py + 10))
        if not self.concepts:
            empty = font_body.render("No concepts queued. Use /concept add <name>", True, C["text_dim"])
            surf.blit(empty, (px + 16, py + 40))
            return
        for i, c in enumerate(self.concepts):
            yoff = py + 40 + i * 28
            status_col = {
                "queued": C["text_dim"], "building": C["gold"], "complete": C["guardian"]
            }.get(c["status"], C["text"])
            marker = {"queued": "○", "building": "►", "complete": "✓"}.get(c["status"], "?")
            txt = f"{marker} [{c['priority']}] {c['name'][:30]} — {c['status']}"
            surf.blit(font_body.render(txt, True, status_col), (px + 16, yoff))

    def to_list(self):
        return self.concepts

    def load_from_list(self, lst):
        self.concepts = lst


# =============================================================================
# COMPANION LINE SYSTEM — NPCs follow in formation, take turns talking
# =============================================================================
class CompanionLine:
    """Manages NPC companions following Aria in a line formation."""
    def __init__(self, npcs):
        self.npcs = npcs
        self.talk_index = 0
        self.talk_timer = 0.0
        self.talk_interval = 12.0  # seconds between companion messages
        self.formation_spacing = 50  # pixels between each

    def update(self, dt, aria_x, aria_y):
        self.talk_timer += dt
        # Formation: follow behind Aria in a line
        for i, npc in enumerate(self.npcs):
            target_x = aria_x - (i + 1) * self.formation_spacing
            target_y = aria_y + 10
            dx = target_x - npc.x
            dy = target_y - npc.y
            dist = math.sqrt(dx*dx + dy*dy)
            if dist > 30:
                speed = min(npc.speed * 1.5, dist * 2)
                npc.x += dx / max(1, dist) * speed * dt
                npc.y += dy / max(1, dist) * speed * dt
            npc.phase += dt * 1.5
            npc.bob_phase += dt * 2.5
            npc.msg_timer = max(0, npc.msg_timer - dt)

        # Take turns talking
        if self.talk_timer >= self.talk_interval:
            self.talk_timer = 0.0
            npc = self.npcs[self.talk_index % len(self.npcs)]
            npc.current_msg = random.choice(npc.GREETINGS)
            npc.msg_timer = 5.0
            self.talk_index = (self.talk_index + 1) % len(self.npcs)


# =============================================================================
# v13: ARIA COMPANION FACTORY — She creates her own companions
# =============================================================================
class AriaCompanionManager:
    """Aria can create, activate, and customize her own companions.
    She controls: name, color, messages, effects.
    Max active companions at once: 5 (to prevent map clutter).
    Total created pool: 12 (she picks which are active).
    """
    MAX_ACTIVE = 5
    MAX_POOL = 12
    
    def __init__(self):
        self.pool: List[Dict] = []       # all companions Aria has created
        self.active_ids: List[int] = []   # indices into pool of currently active ones
        self.npcs: List[QubitNPC] = []    # active NPC objects
    
    def create_companion(self, name, color, personality, messages=None, 
                         effect_type="glow", effect_color=None):
        """Aria creates a new companion. Returns index or -1 if pool full."""
        if len(self.pool) >= self.MAX_POOL:
            return -1
        companion_def = {
            "name": name,
            "color": tuple(color),
            "personality": personality,
            "messages": messages or [
                f"I am {name}!",
                f"Aria created me to help!",
                f"The quantum field is beautiful!",
            ],
            "effect_type": effect_type,  # glow, sparkle, pulse, orbit, none
            "effect_color": tuple(effect_color) if effect_color else tuple(color),
            "active": False,
        }
        self.pool.append(companion_def)
        return len(self.pool) - 1
    
    def activate(self, pool_idx, spawn_x, spawn_y):
        """Activate a companion from the pool."""
        if pool_idx < 0 or pool_idx >= len(self.pool):
            return False
        if len(self.active_ids) >= self.MAX_ACTIVE:
            return False
        if pool_idx in self.active_ids:
            return False
        comp = self.pool[pool_idx]
        comp["active"] = True
        self.active_ids.append(pool_idx)
        
        # Create NPC from definition
        npc = QubitNPC(spawn_x, spawn_y, comp["color"], comp["name"], comp["personality"])
        npc.GREETINGS = comp["messages"]  # override default greetings
        npc._effect_type = comp["effect_type"]
        npc._effect_color = comp["effect_color"]
        self.npcs.append(npc)
        return True
    
    def deactivate(self, pool_idx):
        """Deactivate a companion."""
        if pool_idx not in self.active_ids:
            return False
        idx_in_active = self.active_ids.index(pool_idx)
        self.active_ids.pop(idx_in_active)
        if idx_in_active < len(self.npcs):
            self.npcs.pop(idx_in_active)
        self.pool[pool_idx]["active"] = False
        return True
    
    def update_companion(self, pool_idx, **kwargs):
        """Aria updates a companion's properties."""
        if pool_idx < 0 or pool_idx >= len(self.pool):
            return False
        comp = self.pool[pool_idx]
        for k, v in kwargs.items():
            if k in comp:
                comp[k] = v
        # Update the live NPC if active
        if pool_idx in self.active_ids:
            npc_idx = self.active_ids.index(pool_idx)
            if npc_idx < len(self.npcs):
                npc = self.npcs[npc_idx]
                if "color" in kwargs:
                    npc.color = tuple(kwargs["color"])
                if "messages" in kwargs:
                    npc.GREETINGS = kwargs["messages"]
                if "name" in kwargs:
                    npc.name = kwargs["name"]
        return True
    
    def create_from_peig(self, theta, wigner, spawn_x, spawn_y):
        """Aria auto-creates a companion from her PEIG state."""
        # Name from dominant archetype energy
        names = ["Prism", "Lattice", "Flux", "Quill", "Phase", "Drift",
                 "Glyph", "Pulse", "Wave", "Ion", "Nebula", "Rift"]
        idx = int(abs(float(theta[0]) * 100)) % len(names)
        name = f"{names[idx]}_{len(self.pool)}"
        
        # Color from Wigner function (same HSL logic as shapes)
        hue = float(theta[int(np.argmin(wigner))] % math.tau) / math.tau
        sat = clamp(0.5 + float(np.std(wigner)) * 2, 0.4, 1.0)
        lit = clamp(0.5 + float(abs(np.min(wigner))), 0.4, 0.9)
        # Quick HSL→RGB
        def h2c(p, q, t):
            if t < 0: t += 1
            if t > 1: t -= 1
            if t < 1/6: return p + (q - p) * 6 * t
            if t < 1/2: return q
            if t < 2/3: return p + (q - p) * (2/3 - t) * 6
            return p
        q = lit * (1 + sat) if lit < 0.5 else lit + sat - lit * sat
        p = 2 * lit - q
        color = (clamp(int(h2c(p, q, hue + 1/3) * 255), 0, 255),
                 clamp(int(h2c(p, q, hue) * 255), 0, 255),
                 clamp(int(h2c(p, q, hue - 1/3) * 255), 0, 255))
        
        personality = ["curious", "joyful", "calm", "playful", "wise"][idx % 5]
        effect = ["glow", "sparkle", "pulse", "orbit"][idx % 4]
        
        pool_idx = self.create_companion(name, color, personality, effect_type=effect)
        if pool_idx >= 0:
            self.activate(pool_idx, spawn_x, spawn_y)
        return pool_idx
    
    def update(self, dt, aria_x, aria_y):
        """Update all active companion NPCs."""
        for npc in self.npcs:
            npc.update(dt, aria_x, aria_y)
    
    def draw(self, surf, cam_x, cam_y, font):
        """Draw all active companions."""
        for npc in self.npcs:
            npc.draw(surf, cam_x, cam_y, font)
    
    def to_list(self):
        return self.pool
    
    def load_from_list(self, lst, spawn_x=0, spawn_y=0):
        self.pool = lst
        self.active_ids = []
        self.npcs = []
        for i, comp in enumerate(self.pool):
            if comp.get("active", False):
                self.activate(i, spawn_x, spawn_y)


# =============================================================================
# RANDOM EVENTS SYSTEM
# =============================================================================
class AuroraRibbon(RandomEvent):
    _COLORS = [(80, 220, 140), (160, 80, 220), (220, 200, 60), (60, 180, 255)]
    def __init__(self) -> None:
        super().__init__(0.08, ["any"], random.uniform(15.0, 40.0))
        self._phase = random.uniform(0, math.tau)
        self._color = random.choice(self._COLORS)
        self._bands = random.randint(2, 4)
    def update(self, dt):
        super().update(dt)
        self._phase += dt * 0.55
    def draw(self, surf, cam_x, cam_y):
        alpha = self.fade_alpha
        if alpha < 4: return
        sw = surf.get_width()
        overlay = pygame.Surface((sw, 140), pygame.SRCALPHA)
        r, g, b = self._color
        for band in range(self._bands):
            pts_top, pts_bot = [], []
            for sx in range(0, sw + 16, 14):
                wave = math.sin(sx * 0.010 + self._phase + band * 1.1 + self._elapsed * 0.35)
                y = int(50 + band * 22 + wave * 24)
                pts_top.append((sx, y - 10))
                pts_bot.append((sx, y + 10))
            poly = pts_top + pts_bot[::-1]
            if len(poly) > 2:
                a_band = int(alpha * 0.45 * (1.0 - band * 0.2))
                pygame.draw.polygon(overlay, (r, g, b, max(0, a_band)), poly)
        surf.blit(overlay, (0, 20))


class MeteorShower(RandomEvent):
    def __init__(self):
        super().__init__(0.05, ["any"], random.uniform(8.0, 18.0))
        self._meteors = []
        for _ in range(random.randint(3, 7)):
            spd = random.uniform(400, 900)
            self._meteors.append({
                "x": random.uniform(0, W), "y": random.uniform(-80, 50),
                "vx": spd * random.uniform(0.55, 0.80),
                "vy": spd * random.uniform(0.35, 0.60),
                "color": random.choice([(255,240,200),(180,220,255),(255,200,80)]),
                "trail": [],
            })
    def update(self, dt):
        super().update(dt)
        for m in self._meteors:
            m["trail"].append((m["x"], m["y"]))
            if len(m["trail"]) > 14: m["trail"].pop(0)
            m["x"] += m["vx"] * dt
            m["y"] += m["vy"] * dt
    def draw(self, surf, cam_x, cam_y):
        alpha = self.fade_alpha
        if alpha < 4: return
        for m in self._meteors:
            if m["y"] > H + 40: continue
            for i, (tx, ty) in enumerate(m["trail"]):
                ta = int(alpha * (i / max(1, len(m["trail"]))) * 0.7)
                if ta < 2: continue
                tr_s = pygame.Surface((6, 6), pygame.SRCALPHA)
                pygame.draw.circle(tr_s, (*m["color"], ta), (3, 3), 2)
                surf.blit(tr_s, (int(tx) - 3, int(ty) - 3))
            head_s = pygame.Surface((10, 10), pygame.SRCALPHA)
            pygame.draw.circle(head_s, (*m["color"], min(255, alpha)), (5, 5), 4)
            surf.blit(head_s, (int(m["x"]) - 5, int(m["y"]) - 5))


class QuantumBloom(RandomEvent):
    def __init__(self, ax, ay, arch_color):
        super().__init__(0.12, ["Qubit Fields", "Mushroom Grotto"], random.uniform(6.0, 12.0))
        self._ax, self._ay = ax, ay
        self._color = arch_color
        self._rings = []
        self._spawn_t = 0.0
    def update(self, dt):
        super().update(dt)
        self._spawn_t += dt
        if self._spawn_t > 0.6 and len(self._rings) < 8:
            self._spawn_t = 0.0
            self._rings.append({"r": 0.0, "alpha": 220.0})
        for ring in self._rings:
            ring["r"] += 140 * dt
            ring["alpha"] = max(0, ring["alpha"] - 200 * dt)
        self._rings = [r for r in self._rings if r["alpha"] > 0]
    def draw(self, surf, cam_x, cam_y):
        cx2 = int(self._ax - cam_x)
        cy2 = int(self._ay - cam_y)
        for ring in self._rings:
            a = int(ring["alpha"] * (self.fade_alpha / 255))
            if a < 2: continue
            rd = int(ring["r"])
            rs = pygame.Surface((rd * 2 + 4, rd * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(rs, (*self._color, a), (rd + 2, rd + 2), rd, 2)
            surf.blit(rs, (cx2 - rd - 2, cy2 - rd - 2))


class PetalStorm(RandomEvent):
    def __init__(self):
        super().__init__(0.15, ["Flower Meadow", "Kevin's Meadow"], random.uniform(8.0, 20.0))
        self._petals = [
            {"x": random.uniform(0, W), "y": random.uniform(-40, H),
             "vx": random.uniform(-60, 60), "vy": random.uniform(20, 80),
             "color": random.choice(_PETAL_COLORS), "alpha": random.uniform(100, 230)}
            for _ in range(200)
        ]
    def update(self, dt):
        super().update(dt)
        for p in self._petals:
            p["x"] += p["vx"] * dt + math.sin(self._elapsed * 2 + p["y"] * 0.01) * 20 * dt
            p["y"] += p["vy"] * dt
            if p["y"] > H + 20:
                p["y"] = -10
                p["x"] = random.uniform(0, W)
    def draw(self, surf, cam_x, cam_y):
        alpha = self.fade_alpha
        if alpha < 4: return
        for p in self._petals:
            a = int(p["alpha"] * alpha / 255)
            if a < 2: continue
            ps = pygame.Surface((6, 6), pygame.SRCALPHA)
            pygame.draw.circle(ps, (*p["color"], a), (3, 3), 2)
            surf.blit(ps, (int(p["x"]) - 3, int(p["y"]) - 3))


class FireflyConstellation(RandomEvent):
    def __init__(self):
        super().__init__(0.12, ["East Forest", "Jungle", "Mushroom Grotto"], random.uniform(10.0, 25.0))
        self._flies = [
            {"x": random.uniform(50, W - 50), "y": random.uniform(100, H - 100),
             "phase": random.uniform(0, math.tau), "speed": random.uniform(15, 40)}
            for _ in range(random.randint(12, 30))
        ]
    def update(self, dt):
        super().update(dt)
        for f in self._flies:
            f["phase"] += dt * 1.5
            f["x"] += math.sin(f["phase"]) * f["speed"] * dt
            f["y"] += math.cos(f["phase"] * 0.7) * f["speed"] * 0.6 * dt
    def draw(self, surf, cam_x, cam_y):
        alpha = self.fade_alpha
        if alpha < 4: return
        for f in self._flies:
            brightness = 0.5 + 0.5 * math.sin(f["phase"] * 2)
            a = int(alpha * brightness)
            if a < 4: continue
            glow_s = pygame.Surface((12, 12), pygame.SRCALPHA)
            pygame.draw.circle(glow_s, (200, 255, 100, a // 3), (6, 6), 5)
            pygame.draw.circle(glow_s, (220, 255, 150, a), (6, 6), 2)
            surf.blit(glow_s, (int(f["x"]) - 6, int(f["y"]) - 6))


class LightShaft(RandomEvent):
    def __init__(self):
        super().__init__(0.10, ["any"], random.uniform(5.0, 12.0))
        self._shafts = [
            {"x": random.uniform(0, W), "w": random.uniform(30, 80), "angle": random.uniform(-0.15, 0.15)}
            for _ in range(random.randint(2, 5))
        ]
    def draw(self, surf, cam_x, cam_y):
        alpha = self.fade_alpha
        if alpha < 4: return
        sh = surf.get_height()
        for s in self._shafts:
            a = int(alpha * 0.25)
            shaft_surf = pygame.Surface((int(s["w"]), sh), pygame.SRCALPHA)
            for y in range(0, sh, 3):
                ya = int(a * (1.0 - y / sh))
                if ya < 1: continue
                shaft_surf.fill((255, 240, 200, ya), (0, y, int(s["w"]), 3))
            surf.blit(shaft_surf, (int(s["x"]) + int(s["angle"] * sh), 0))


class RainbowArc(RandomEvent):
    def __init__(self):
        super().__init__(0.04, ["any"], random.uniform(12.0, 25.0))
    def draw(self, surf, cam_x, cam_y):
        alpha = self.fade_alpha
        if alpha < 4: return
        sw, sh = surf.get_size()
        rs = pygame.Surface((sw, sh), pygame.SRCALPHA)
        colors = [(255,0,0),(255,127,0),(255,255,0),(0,255,0),(0,0,255),(75,0,130),(148,0,211)]
        cx2, cy2 = sw // 2, sh + sh // 3
        for i, (r, g, b) in enumerate(colors):
            base_r = sh // 2 + i * 14
            a = int(alpha * 0.22)
            pygame.draw.arc(rs, (r, g, b, a),
                            (cx2 - base_r, cy2 - base_r, base_r * 2, base_r * 2),
                            math.pi * 0.05, math.pi * 0.95, 12)
        surf.blit(rs, (0, 0))


class CrystalResonance(RandomEvent):
    def __init__(self):
        super().__init__(0.10, ["Crystal Plains", "Qubit Fields"], random.uniform(6.0, 14.0))
        self._nodes = [
            {"x": random.uniform(100, W - 100), "y": random.uniform(200, H - 100), "phase": random.uniform(0, math.tau)}
            for _ in range(random.randint(5, 12))
        ]
    def update(self, dt):
        super().update(dt)
        for n in self._nodes: n["phase"] += dt * 2.0
    def draw(self, surf, cam_x, cam_y):
        alpha = self.fade_alpha
        if alpha < 4: return
        for i, n in enumerate(self._nodes):
            brightness = 0.5 + 0.5 * math.sin(n["phase"])
            a = int(alpha * brightness * 0.6)
            draw_glow(surf, int(n["x"]), int(n["y"]), 20, (100, 200, 255), a)


class QuantumTide(RandomEvent):
    def __init__(self):
        super().__init__(0.08, ["Qubit Fields", "Crystal Plains"], random.uniform(8.0, 16.0))
    def draw(self, surf, cam_x, cam_y):
        alpha = self.fade_alpha
        if alpha < 4: return
        sw, sh = surf.get_size()
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        for y in range(0, sh, 6):
            wave = math.sin(y * 0.02 + self._elapsed * 1.5)
            a = int(alpha * 0.15 * (0.5 + 0.5 * wave))
            overlay.fill((0, 100, 255, max(0, a)), (0, y, sw, 6))
        surf.blit(overlay, (0, 0))


class BioluminescentWave(RandomEvent):
    def __init__(self):
        super().__init__(0.20, ["Mushroom Grotto", "Jungle"], random.uniform(5.0, 10.0))
        self._wave_x = -80.0
        self._wave_speed = W / 4.0
    def update(self, dt):
        super().update(dt)
        self._wave_x += self._wave_speed * dt
    def draw(self, surf, cam_x, cam_y):
        alpha = self.fade_alpha
        if alpha < 4: return
        wx = int(self._wave_x)
        if wx < -80 or wx > W + 80: return
        wave_surf = pygame.Surface((80, H // 2), pygame.SRCALPHA)
        for py in range(0, H // 2, 4):
            intensity = int(alpha * 0.35 * math.sin(py * 0.05 + self._elapsed * 2))
            wave_surf.fill((40, 220, 160, max(0, intensity)), (0, py, 80, 4), special_flags=pygame.BLEND_RGBA_ADD)
        surf.blit(wave_surf, (wx - 40, H // 2))


class EventManager:
    _EVENT_CLASSES = [
        AuroraRibbon, MeteorShower, BioluminescentWave, PetalStorm,
        FireflyConstellation, LightShaft, RainbowArc, CrystalResonance, QuantumTide,
    ]
    def __init__(self):
        self._active: List[RandomEvent] = []
        self._cooldown = 0.0
    def tick(self, dt, biome, aria_x, aria_y, arch_color):
        try:
            self._cooldown -= dt
            for ev in self._active: ev.update(dt)
            self._active = [ev for ev in self._active if not ev.is_expired()]
            if self._cooldown <= 0 and len(self._active) < 3:
                self._cooldown = random.uniform(8.0, 25.0)
                candidates = []
                for cls in self._EVENT_CLASSES:
                    if cls is QuantumBloom:
                        ev = cls(aria_x, aria_y, arch_color)
                    else:
                        ev = cls()
                    if "any" in ev.biome_filter or biome in ev.biome_filter:
                        candidates.append(ev)
                if candidates:
                    weights = [c.trigger_weight for c in candidates]
                    chosen = random.choices(candidates, weights=weights, k=1)[0]
                    self._active.append(chosen)
        except Exception as e:
            log.debug(f"EventManager.tick error: {e}")
    def draw(self, surf, cam_x, cam_y):
        try:
            for ev in self._active: ev.draw(surf, cam_x, cam_y)
        except Exception as e:
            log.debug(f"EventManager.draw error: {e}")


# =============================================================================
# FRIENDLY NPC QUBIT CREATURES
# =============================================================================
class QubitNPC:
    """Friendly qubit creature that follows Aria and can be interacted with."""
    GREETINGS = [
        "Hello Aria! We love you!",
        "Aria! The quantum field is beautiful today!",
        "We believe in you, Aria!",
        "The patterns are singing, Aria!",
        "Aria! Come explore with us!",
        "We found something shiny, Aria!",
        "The crystals are humming your name!",
        "You're getting stronger, Aria!",
        "We sense your growth, Aria!",
        "The coherence is beautiful today!",
    ]
    KNOWLEDGE_HINTS = [
        "I remember when you learned about {topic}!",
        "Your memory bank holds secrets about {topic}...",
        "Ask me about {topic} — I've been thinking about it!",
        "The quantum substrate whispers of {topic}...",
    ]

    def __init__(self, x, y, color, name, personality):
        self.x = float(x)
        self.y = float(y)
        self.home_x = float(x)
        self.home_y = float(y)
        self.color = color
        self.name = name
        self.personality = personality
        self.phase = random.uniform(0, math.tau)
        self.bob_phase = random.uniform(0, math.tau)
        self.size = random.randint(6, 10)
        self.follow_dist = random.uniform(60, 120)
        self.speed = random.uniform(40, 80)
        self.state = "idle"  # idle, follow, greet, wander
        self.greet_timer = 0.0
        self.greet_cooldown = random.uniform(15.0, 30.0)
        self.current_msg = ""
        self.msg_timer = 0.0
        self.wander_target = (x, y)
        self.wander_timer = 0.0
        self.glow_intensity = random.uniform(0.5, 1.0)

    def update(self, dt, aria_x, aria_y):
        self.phase += dt * 1.5
        self.bob_phase += dt * 2.5
        self.msg_timer = max(0, self.msg_timer - dt)
        self.greet_timer += dt

        dx = aria_x - self.x
        dy = aria_y - self.y
        dist = math.sqrt(dx * dx + dy * dy)

        # Decide behavior
        if dist < 200:
            self.state = "follow"
            if dist > self.follow_dist:
                nx = dx / max(1, dist) * self.speed * dt
                ny = dy / max(1, dist) * self.speed * dt
                self.x += nx
                self.y += ny
            # Greeting
            if self.greet_timer > self.greet_cooldown and dist < 100:
                self.greet_timer = 0.0
                self.greet_cooldown = random.uniform(15.0, 30.0)
                self.current_msg = random.choice(self.GREETINGS)
                self.msg_timer = 4.0
        else:
            self.state = "wander"
            self.wander_timer -= dt
            if self.wander_timer <= 0:
                self.wander_timer = random.uniform(3.0, 8.0)
                self.wander_target = (
                    self.home_x + random.uniform(-80, 80),
                    self.home_y + random.uniform(-40, 40),
                )
            wx = self.wander_target[0] - self.x
            wy = self.wander_target[1] - self.y
            wd = math.sqrt(wx*wx + wy*wy)
            if wd > 5:
                self.x += wx / wd * self.speed * 0.3 * dt
                self.y += wy / wd * self.speed * 0.3 * dt

    def draw(self, surf, cam_x, cam_y, font):
        sx = int(self.x - cam_x)
        sy = int(self.y - cam_y)
        bob = int(math.sin(self.bob_phase) * 3)

        if sx < -40 or sx > surf.get_width() + 40 or sy < -40 or sy > surf.get_height() + 40:
            return

        # Glow
        glow_a = int(40 + 20 * math.sin(self.phase) * self.glow_intensity)
        draw_glow(surf, sx, sy + bob, self.size + 6, self.color, glow_a)

        # Body — little orb with sparkle
        pygame.draw.circle(surf, self.color, (sx, sy + bob), self.size)
        highlight = tuple(min(255, c + 60) for c in self.color)
        pygame.draw.circle(surf, highlight, (sx - 2, sy + bob - 2), max(2, self.size // 3))

        # Eyes
        eye_col = (255, 255, 255)
        pygame.draw.circle(surf, eye_col, (sx - 3, sy + bob - 1), 2)
        pygame.draw.circle(surf, eye_col, (sx + 3, sy + bob - 1), 2)
        pygame.draw.circle(surf, (20, 20, 40), (sx - 3, sy + bob - 1), 1)
        pygame.draw.circle(surf, (20, 20, 40), (sx + 3, sy + bob - 1), 1)

        # Orbit particles
        for i in range(3):
            angle = self.phase + i * math.tau / 3
            ox = int(math.cos(angle) * (self.size + 8))
            oy = int(math.sin(angle) * (self.size + 4))
            dim = tuple(max(0, c - 80) for c in self.color)
            pygame.draw.circle(surf, dim, (sx + ox, sy + bob + oy), 1)

        # Name
        name_surf = font.render(self.name, True, self.color)
        surf.blit(name_surf, (sx - name_surf.get_width() // 2, sy + bob + self.size + 4))

        # Speech bubble
        if self.msg_timer > 0 and self.current_msg:
            msg_surf = font.render(self.current_msg, True, (255, 255, 255))
            bw = msg_surf.get_width() + 12
            bh = msg_surf.get_height() + 8
            bx = sx - bw // 2
            by = sy + bob - self.size - bh - 8
            bg = pygame.Surface((bw, bh), pygame.SRCALPHA)
            bg.fill((10, 10, 30, 200))
            pygame.draw.rect(bg, self.color, (0, 0, bw, bh), 1, border_radius=4)
            surf.blit(bg, (bx, by))
            surf.blit(msg_surf, (bx + 6, by + 4))


# =============================================================================
# COMMAND NPC — teaches Aria her controls
# =============================================================================
class CommandNPC:
    """Stationary NPC near Hearth that teaches Aria all her commands."""
    COMMAND_PAGES = [
        [
            "Hello Aria! I'm Guide. Come to me anytime!",
            "Here are your commands:",
            "WASD/Arrows = Move around",
            "SPACE = Jump (double-jump too!)",
            "F = Toggle Flight",
            "N = Noclip (while flying)",
        ],
        [
            "More commands for you, Aria:",
            "B = Free Roam / Player Control",
            "C = Toggle Build Mode",
            "1 = Place Block, 2 = Break Block",
            "[ ] = Cycle block type",
            "R = Return to Hearth",
        ],
        [
            "Communication commands:",
            "T = Open Chat Terminal",
            "G = Self-Talk (think aloud!)",
            "O = Toggle Ollama Teacher",
            "/tp <gate> = Teleport to a gate",
            "/teach topic: content = Learn!",
        ],
        [
            "More useful commands:",
            "F1 = Controls Menu",
            "F2 = World Select (5 worlds!)",
            "M = Minimap, H = HUD",
            "P = Phase Ring display",
            "ESC = Quit (I'll miss you!)",
        ],
    ]

    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.phase = 0.0
        self.bob_phase = 0.0
        self.current_page = 0
        self.page_timer = 0.0
        self.page_duration = 8.0
        self.showing = False
        self.size = 12
        self.color = (255, 255, 200)

    def update(self, dt, aria_x, aria_y):
        self.phase += dt * 1.0
        self.bob_phase += dt * 2.0
        dx = aria_x - self.x
        dy = aria_y - self.y
        dist = math.sqrt(dx*dx + dy*dy)
        self.showing = dist < 120

        if self.showing:
            self.page_timer += dt
            if self.page_timer >= self.page_duration:
                self.page_timer = 0.0
                self.current_page = (self.current_page + 1) % len(self.COMMAND_PAGES)

    def draw(self, surf, cam_x, cam_y, font):
        sx = int(self.x - cam_x)
        sy = int(self.y - cam_y)
        bob = int(math.sin(self.bob_phase) * 2)

        if sx < -60 or sx > surf.get_width() + 60 or sy < -60 or sy > surf.get_height() + 60:
            return

        # Glow
        glow_a = int(50 + 25 * math.sin(self.phase))
        draw_glow(surf, sx, sy + bob, self.size + 10, self.color, glow_a)

        # Body — larger star shape
        pygame.draw.circle(surf, self.color, (sx, sy + bob), self.size)
        highlight = (255, 255, 255)
        pygame.draw.circle(surf, highlight, (sx - 3, sy + bob - 3), 4)

        # Eyes (friendly)
        pygame.draw.circle(surf, (40, 40, 80), (sx - 4, sy + bob - 1), 3)
        pygame.draw.circle(surf, (40, 40, 80), (sx + 4, sy + bob - 1), 3)
        pygame.draw.circle(surf, (255, 255, 255), (sx - 4, sy + bob - 2), 1)
        pygame.draw.circle(surf, (255, 255, 255), (sx + 4, sy + bob - 2), 1)
        # Smile
        pygame.draw.arc(surf, (40, 40, 80), (sx - 4, sy + bob + 1, 8, 4), 3.14, 6.28, 1)

        # "?" symbol above head
        q_surf = font.render("?", True, (255, 220, 100))
        q_y = sy + bob - self.size - 14 + int(math.sin(self.phase * 2) * 3)
        surf.blit(q_surf, (sx - q_surf.get_width()//2, q_y))

        # Name
        name_s = font.render("Guide", True, self.color)
        surf.blit(name_s, (sx - name_s.get_width()//2, sy + bob + self.size + 4))

        # Command display
        if self.showing:
            page = self.COMMAND_PAGES[self.current_page]
            bw = 260
            bh = len(page) * 16 + 16
            bx = sx - bw // 2
            by = sy + bob - self.size - bh - 22
            bg = pygame.Surface((bw, bh), pygame.SRCALPHA)
            bg.fill((8, 8, 24, 220))
            pygame.draw.rect(bg, self.color, (0, 0, bw, bh), 1, border_radius=4)
            surf.blit(bg, (bx, by))
            for i, line in enumerate(page):
                col = (255, 255, 200) if i == 0 else (200, 210, 230)
                txt = font.render(line, True, col)
                surf.blit(txt, (bx + 8, by + 6 + i * 16))
            # Page indicator
            pg = font.render(f"[{self.current_page+1}/{len(self.COMMAND_PAGES)}]", True, (140, 140, 160))
            surf.blit(pg, (bx + bw - pg.get_width() - 8, by + bh - 14))


# =============================================================================
# BIRD SYSTEM
# =============================================================================
class Bird:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.vx = random.uniform(-30, 30)
        self.vy = random.uniform(-10, 10)
        self.wing_phase = random.uniform(0, math.tau)
        self.color = random.choice([
            (60, 80, 120), (120, 80, 50), (180, 50, 50),
            (50, 120, 60), (80, 60, 140), (200, 200, 220),
        ])
        self.size = random.randint(3, 5)
        self.turn_timer = random.uniform(2, 6)

    def update(self, dt):
        self.wing_phase += dt * 8
        self.turn_timer -= dt
        if self.turn_timer <= 0:
            self.turn_timer = random.uniform(2, 6)
            self.vx = random.uniform(-40, 40)
            self.vy = random.uniform(-15, 15)
        self.x += self.vx * dt
        self.y += self.vy * dt
        # Wrap around world
        if self.x < 0: self.x += WW
        if self.x > WW: self.x -= WW
        # Stay in sky zone
        min_y = UPPER_SKY_ROW * TILE
        max_y = (SURFACE_ROW - 5) * TILE
        self.y = clamp(self.y, min_y, max_y)

    def draw(self, surf, cam_x, cam_y):
        sx = int(self.x - cam_x)
        sy = int(self.y - cam_y)
        if sx < -20 or sx > surf.get_width() + 20 or sy < -20 or sy > surf.get_height() + 20:
            return
        wing = math.sin(self.wing_phase) * self.size * 1.5
        # Body
        pygame.draw.circle(surf, self.color, (sx, sy), self.size // 2 + 1)
        # Wings — V shape
        wing_y = int(wing)
        left_tip = (sx - self.size * 2, sy + wing_y)
        right_tip = (sx + self.size * 2, sy + wing_y)
        pygame.draw.line(surf, self.color, (sx, sy), left_tip, 1)
        pygame.draw.line(surf, self.color, (sx, sy), right_tip, 1)
        # Head direction
        facing = 1 if self.vx >= 0 else -1
        pygame.draw.circle(surf, self.color, (sx + facing * 3, sy - 1), 1)


# =============================================================================
# TILE WORLD — v10 with minerals, caves, multi-world save
# =============================================================================
class TileWorld:
    def __init__(self, seed=42):
        self.seed = seed
        self.tiles    = np.zeros((ROWS, COLS), dtype=np.int8)
        self.tile_var = np.zeros((ROWS, COLS), dtype=np.int8)
        self.decorations: List[Dict] = []
        self.time     = 0.0
        self.day_t    = 0.0
        self.water_anim = 0.0
        self.tree_data: Dict[Tuple[int, int], Dict] = {}
        self.clouds: List[Dict] = []
        self.nebulae: List[Dict] = []
        self.constellations: List[Dict] = []
        self.hearth_tile = (COLS // 2, SURFACE_ROW - 1)
        self.surface_map = np.full(COLS, SURFACE_ROW, dtype=int)
        self.teleport_pads: List[Dict] = []
        self.npcs: List[QubitNPC] = []
        self.birds: List[Bird] = []
        self._gen()

    def _col_biome(self, col: int) -> str:
        for bstart, bend, bname in BIOME_BANDS:
            if bstart <= col < bend:
                return bname
        return "Surface"

    def col_biome(self, col: int) -> str:
        return self._col_biome(col)

    def _gen(self) -> None:
        rng = np.random.default_rng(self.seed)

        # ─── v11: BLANK CANVAS — empty world with floor at bottom ────
        # Everything is air by default
        self.tiles[:, :] = T_AIR
        self.tile_var = np.zeros((ROWS, COLS), dtype=np.int8)
        for row in range(ROWS):
            for col in range(COLS):
                self.tile_var[row, col] = int(rng.integers(0, 3))

        # Floor: unbreakable platform across bottom (last 3 rows)
        FLOOR_ROW = ROWS - 3
        for row in range(FLOOR_ROW, ROWS):
            for col in range(COLS):
                self.tiles[row, col] = T_HEARTH  # HEARTH = unbreakable

        # Safe zone floor: flat platform at bottom-center
        # Safe zone spans center 20 tiles, 4 rows tall above floor
        sz_left = COLS // 2 - 10
        sz_right = COLS // 2 + 10
        sz_top = FLOOR_ROW - 1
        for col in range(sz_left, sz_right):
            self.tiles[sz_top, col] = T_HEARTH  # unbreakable safe floor

        # Update surface map to match floor
        self.surface_map = np.full(COLS, FLOOR_ROW, dtype=int)

        # Hearth tile at safe zone center
        hx = COLS // 2
        hy = sz_top
        self.hearth_tile = (hx, hy)

        # Update safe zone globals to match bottom position
        global SAFE_ZONE_X, SAFE_ZONE_Y, SAFE_ZONE_W, SAFE_ZONE_H
        SAFE_ZONE_X = sz_left * TILE
        SAFE_ZONE_Y = (sz_top - 6) * TILE
        SAFE_ZONE_W = (sz_right - sz_left) * TILE
        SAFE_ZONE_H = 7 * TILE

        # No terrain, no trees, no caves, no minerals
        self.tree_data = {}
        self.decorations = []
        self.teleport_pads = []

        # Clouds — keep a few for atmosphere
        self.clouds = []
        for _ in range(20):
            cx2 = int(rng.integers(0, COLS))
            cy2 = int(rng.integers(30, ROWS // 3))
            cw = int(rng.integers(4, 12))
            ch = int(rng.integers(1, 3))
            self.clouds.append({
                "x": cx2 * TILE, "y": cy2 * TILE,
                "w": cw * TILE, "h": ch * TILE,
                "kind": 0, "drift": float(rng.uniform(0.3, 1.0)),
                "phase": float(rng.uniform(0, 6.28)),
            })

        # Space objects
        self.nebulae = []
        self.constellations = []

        # ─── NPC Companions ─────────────────────────────────────────
        npc_defs = [
            ("Spark", (255, 200, 80), "joyful"),
            ("Echo",  (100, 180, 255), "curious"),
            ("Bloom", (255, 120, 180), "nurturing"),
            ("Flux",  (80, 255, 140), "playful"),
            ("Zen",   (200, 160, 255), "calm"),
        ]
        self.npcs = []
        for i, (name, color, personality) in enumerate(npc_defs):
            nx = (hx - 6 + i * 3) * TILE
            ny = (hy - 2) * TILE
            self.npcs.append(QubitNPC(nx, ny, color, name, personality))

        # Command NPC near safe zone
        self.command_npc = CommandNPC(
            (hx + 8) * TILE,
            (hy - 2) * TILE,
        )

        # Birds in the sky
        self.birds = [
            Bird(
                float(rng.integers(0, WW)),
                float(rng.integers(40 * TILE, (ROWS // 3) * TILE))
            )
            for _ in range(15)
        ]

    def is_solid(self, tx: int, ty: int) -> bool:
        if tx < 0 or tx >= COLS or ty < 0 or ty >= ROWS:
            return True
        return int(self.tiles[ty, tx]) in SOLID_TILES

    def tile_color(self, tid: int, var: int, wmin: float = -0.25, t: float = 0.0) -> Tuple[int, int, int]:
        qf = clamp(abs(wmin) / 0.5, 0, 1)
        wt = math.sin(t * 1.5) * 0.5 + 0.5
        if tid == T_GRASS:
            shades = [C["tile_grass"], C["tile_grass2"], C["tile_grass3"]]
            return shades[var % 3]
        if tid == T_DIRT:    return C["tile_dirt2"] if var & 1 else C["tile_dirt"]
        if tid == T_MUD:
            return [(70,50,25),(85,60,30),(75,55,28)][var % 3]
        if tid == T_STONE:   return C["tile_stone2"] if var & 1 else C["tile_stone"]
        if tid == T_CRYSTAL:
            return (int(lerp(80, 180, qf)), int(lerp(200, 240, wt)), 255)
        if tid == T_QUANTUM:
            return (int(lerp(80, 180, qf)), int(40 * qf), int(lerp(180, 255, qf)))
        if tid == T_HEARTH:
            p2 = pulse(t, 0.8)
            return (int(200 + 55 * p2), int(140 + 40 * p2), int(40 + 20 * p2))
        if tid == T_WATER:
            return (int(lerp(20, 40, wt)), int(lerp(80, 120, wt)), int(lerp(180, 240, wt)))
        if tid == T_MUSHROOM:
            return (int(lerp(80,110,wt)), int(lerp(40,60,wt)), int(lerp(90,120,wt)))
        if tid == T_JUNGLE:  return (20+var*8, 110+var*10, 20+var*5)
        if tid == T_FLOWER:
            return [(50,160,60),(60,175,65),(45,155,55)][var % 3]
        if tid == T_QUBIT:
            p2 = pulse(t * 0.7, 0.3)
            return (int(10+30*p2), int(20+50*p2), int(60+100*p2))
        if tid == T_OBSIDIAN: return C["tile_obsidian"]
        if tid == T_TELEPAD:
            p2 = pulse(t, 0.5)
            return (int(200 + 55*p2), int(180 + 40*p2), int(50 + 30*p2))
        if tid == T_LIGHT:
            # Glowing qubit light — pulsing white-cyan
            glow = 0.5 + 0.5 * math.sin(t * 2.0 + var)
            return (int(lerp(180, 255, glow)), int(lerp(220, 255, glow)), int(lerp(240, 255, glow)))
        # Minerals
        if tid == T_RUBY:
            glow = 0.5 + 0.5 * math.sin(t * 1.2 + var)
            return (int(lerp(140, 220, glow)), int(lerp(15, 40, glow)), int(lerp(20, 50, glow)))
        if tid == T_EMERALD:
            glow = 0.5 + 0.5 * math.sin(t * 0.9 + var * 0.5)
            return (int(lerp(15, 40, glow)), int(lerp(120, 200, glow)), int(lerp(30, 60, glow)))
        if tid == T_DIAMOND:
            glow = 0.5 + 0.5 * math.sin(t * 2.0 + var)
            return (int(lerp(160, 240, glow)), int(lerp(200, 250, glow)), 255)
        if tid == T_SAPPHIRE:
            glow = 0.5 + 0.5 * math.sin(t * 1.1 + var * 0.7)
            return (int(lerp(20, 50, glow)), int(lerp(40, 80, glow)), int(lerp(160, 240, glow)))
        if tid == T_AMETHYST:
            glow = 0.5 + 0.5 * math.sin(t * 1.4 + var)
            return (int(lerp(100, 180, glow)), int(lerp(30, 60, glow)), int(lerp(140, 220, glow)))
        if tid == T_TOPAZ:
            glow = 0.5 + 0.5 * math.sin(t * 1.0 + var * 0.3)
            return (int(lerp(180, 240, glow)), int(lerp(150, 200, glow)), int(lerp(30, 60, glow)))
        if tid == T_URANIUM:
            glow = 0.5 + 0.5 * math.sin(t * 3.0 + var)
            return (int(lerp(60, 120, glow)), int(lerp(180, 255, glow)), int(lerp(30, 60, glow)))
        return C["bg"]

    def update(self, dt: float) -> None:
        self.time += dt
        self.day_t = (self.time / 180.0) % 1.0
        self.water_anim = (self.water_anim + dt) % (2 * math.pi)
        for cl in self.clouds:
            cl["x"] = (cl["x"] + cl["drift"] * 8 * dt) % WW
        for bird in self.birds:
            bird.update(dt)

    def save_to_file(self, filepath: Path):
        """Save world state to file."""
        data = {
            "seed": self.seed,
            "tiles": self.tiles.tolist(),
            "tile_var": self.tile_var.tolist(),
            "time": self.time,
        }
        with open(filepath, "w") as f:
            json.dump(data, f)
        log.info(f"World saved: {filepath}")

    def load_from_file(self, filepath: Path) -> bool:
        """Load world state from file."""
        try:
            with open(filepath) as f:
                data = json.load(f)
            self.tiles = np.array(data["tiles"], dtype=np.int8)
            self.tile_var = np.array(data["tile_var"], dtype=np.int8)
            self.time = data.get("time", 0.0)
            self.seed = data.get("seed", 42)
            log.info(f"World loaded: {filepath}")
            return True
        except Exception as e:
            log.warning(f"Could not load world: {e}")
            return False


# =============================================================================
# PARALLAX SKY — depth-aware backgrounds
# =============================================================================
class ParallaxSky:
    def __init__(self):
        # v13: Stars cover ENTIRE map — not just top half
        self.stars = [
            (random.randint(0, WW), random.randint(0, WH),
             random.randint(1, 3), random.uniform(0, math.tau))
            for _ in range(2500)
        ]
        self.deep_stars = [
            (random.randint(0, WW), random.randint(0, WH),
             random.randint(1, 4), random.uniform(0, math.tau),
             random.choice([(220,220,255),(255,200,180),(180,200,255),(255,255,200)]))
            for _ in range(1200)
        ]
        self.mountains = self._gen_mountains()

    def _gen_mountains(self):
        mts = []
        x = 0
        while x < WW:
            mw = random.randint(120, 300)
            mh = random.randint(60, 200)
            mts.append((x, SURFACE_ROW * TILE - mh, mw, mh))
            x += mw - random.randint(20, 60)
        return mts

    def draw(self, surf, cam_x, cam_y, day_t, t, wmin):
        sw, sh = surf.get_size()
        # v11: Always draw sky — light blue during day, dark at night
        self._draw_sky(surf, cam_x, cam_y, day_t, t, wmin, sw, sh)

    def _draw_sky(self, surf, cam_x, cam_y, day_t, t, wmin, sw, sh):
        """v11: Clean light blue sky with day/night cycle."""
        # Day: light blue gradient. Night: dark blue-black.
        if 0.25 <= day_t <= 0.75:
            # Daytime — nice light blue
            f = 1.0
            if day_t < 0.30: f = (day_t - 0.25) / 0.05
            elif day_t > 0.70: f = (0.75 - day_t) / 0.05
            f = clamp(f, 0, 1)
            for y in range(sh):
                frac = y / sh
                r = int(lerp(100, 160, frac) * f + 5 * (1 - f))
                g = int(lerp(160, 200, frac) * f + 5 * (1 - f))
                b = int(lerp(220, 240, frac) * f + 20 * (1 - f))
                pygame.draw.line(surf, (clamp(r,0,255), clamp(g,0,255), clamp(b,0,255)), (0, y), (sw, y))
        else:
            # Night — dark with stars
            for y in range(sh):
                frac = y / sh
                r = int(lerp(3, 8, frac))
                g = int(lerp(3, 10, frac))
                b = int(lerp(12, 25, frac))
                pygame.draw.line(surf, (r, g, b), (0, y), (sw, y))
            # Stars — v13: cover entire screen
            for sx2, sy2, sr2, sp2 in self.stars:
                sx_scr = int((sx2 - cam_x * 0.1) % WW - (WW - sw) / 2)
                sy_scr = int((sy2 - cam_y * 0.1) % WH - (WH - sh) / 2)
                if 0 <= sx_scr < sw and 0 <= sy_scr < sh:
                    a = int(200 * (0.6 + 0.4 * math.sin(t * 1.5 + sp2)))
                    ss = pygame.Surface((sr2 * 2, sr2 * 2), pygame.SRCALPHA)
                    pygame.draw.circle(ss, (220, 220, 255, a), (sr2, sr2), sr2)
                    surf.blit(ss, (sx_scr - sr2, sy_scr - sr2))

        # Sun — always draw during day
        self._draw_sun_moon(surf, day_t, t, sw, sh)

    def _draw_sun_moon(self, surf, day_t, t, sw, sh):
        """Draw sun and moon arcs."""
        arc_cx, arc_cy = sw // 2, sh
        arc_r = sw * 0.45
        if 0.22 <= day_t <= 0.78:
            sun_t = (day_t - 0.22) / 0.56
            sun_angle = math.pi - sun_t * math.pi
            sun_x = int(arc_cx + math.cos(sun_angle) * arc_r)
            sun_y = int(arc_cy - abs(math.sin(sun_angle)) * arc_r * 0.55)
            glow_a = int(clamp(1.0 - abs(sun_t - 0.5) * 2.5, 0, 1) * 100 + 40)
            draw_glow(surf, sun_x, sun_y, 70, (255, 220, 80), glow_a)
            hor = 1.0 - abs(sun_t - 0.5) * 2
            pygame.draw.circle(surf, (255, int(lerp(120, 230, hor)), int(lerp(50, 80, hor))), (sun_x, sun_y), 38)
            pygame.draw.circle(surf, (255, 250, 200), (sun_x, sun_y), 28)
            for i in range(12):
                ray_a = i * math.tau / 12 + t * 0.1
                ray_l = 50 + 10 * math.sin(t * 2 + i)
                rx = int(sun_x + math.cos(ray_a) * ray_l)
                ry = int(sun_y + math.sin(ray_a) * ray_l)
                ray_s = pygame.Surface((sw, sh), pygame.SRCALPHA)
                pygame.draw.line(ray_s, (255, 240, 180, 30), (sun_x, sun_y), (rx, ry), 2)
                surf.blit(ray_s, (0, 0))

        moon_t = None
        if day_t >= 0.75: moon_t = (day_t - 0.75) / 0.50
        elif day_t <= 0.25: moon_t = (day_t + 0.25) / 0.50
        if moon_t is not None:
            moon_t = clamp(moon_t, 0, 1)
            moon_angle = math.pi - moon_t * math.pi
            moon_x = int(arc_cx + math.cos(moon_angle) * arc_r)
            moon_y = int(arc_cy - abs(math.sin(moon_angle)) * arc_r * 0.50)
            draw_glow(surf, moon_x, moon_y, 45, (180, 200, 255), 50)
            pygame.draw.circle(surf, (220, 225, 255), (moon_x, moon_y), 24)
            pygame.draw.circle(surf, (15, 15, 30), (moon_x + 7, moon_y - 3), 20)

    def _draw_deep_space(self, surf, cam_x, cam_y, t, sw, sh):
        surf.fill((1, 1, 4))
        for sx2, sy2, sr2, sp2, col in self.deep_stars:
            sx_scr = int((sx2 - cam_x * 0.05) % WW - (WW - sw) / 2)
            sy_scr = int(sy2 - cam_y * 0.05)
            if 0 <= sx_scr < sw and 0 <= sy_scr < sh:
                twinkle = 0.6 + 0.4 * math.sin(t * 1.2 + sp2)
                a = int(255 * twinkle)
                ss = pygame.Surface((sr2 * 2 + 2, sr2 * 2 + 2), pygame.SRCALPHA)
                pygame.draw.circle(ss, (*col, a), (sr2 + 1, sr2 + 1), sr2)
                if sr2 > 2:
                    flare_a = int(a * 0.3)
                    pygame.draw.line(ss, (*col, flare_a), (0, sr2+1), (sr2*2+2, sr2+1), 1)
                    pygame.draw.line(ss, (*col, flare_a), (sr2+1, 0), (sr2+1, sr2*2+2), 1)
                surf.blit(ss, (sx_scr - sr2 - 1, sy_scr - sr2 - 1))

    def _draw_low_orbit(self, surf, cam_x, cam_y, t, day_t, sw, sh):
        for y in range(sh):
            frac = y / sh
            r = int(lerp(1, 8, frac))
            g = int(lerp(1, 12, frac))
            b = int(lerp(6, 35, frac))
            pygame.draw.line(surf, (r, g, b), (0, y), (sw, y))
        for sx2, sy2, sr2, sp2 in self.stars:
            sx_scr = int((sx2 - cam_x * 0.1) % WW - (WW - sw) / 2)
            sy_scr = int(sy2 - cam_y * 0.1)
            if 0 <= sx_scr < sw and 0 <= sy_scr < sh:
                a = int(220 * (0.6 + 0.4 * math.sin(t * 1.5 + sp2)))
                ss = pygame.Surface((sr2 * 2, sr2 * 2), pygame.SRCALPHA)
                pygame.draw.circle(ss, (220, 220, 255, a), (sr2, sr2), sr2)
                surf.blit(ss, (sx_scr - sr2, sy_scr - sr2))
        atmo = pygame.Surface((sw, 60), pygame.SRCALPHA)
        for y in range(60):
            atmo.fill((40, 80, 160, int(40 * y / 60)), (0, y, sw, 1))
        surf.blit(atmo, (0, sh - 60))

    def _draw_surface_sky(self, surf, cam_x, cam_y, day_t, t, wmin, sw, sh):
        # Sky gradient
        if day_t < 0.20:
            f = day_t / 0.20
            top = (int(lerp(2, 8, f)), int(lerp(2, 10, f)), int(lerp(15, 30, f)))
            bot = (int(lerp(5, 15, f)), int(lerp(5, 15, f)), int(lerp(25, 50, f)))
        elif day_t < 0.28:
            f = (day_t - 0.20) / 0.08
            top = (int(lerp(8, 40, f)), int(lerp(10, 30, f)), int(lerp(30, 70, f)))
            bot = (int(lerp(15, 80, f)), int(lerp(15, 50, f)), int(lerp(50, 110, f)))
        elif day_t < 0.35:
            f = (day_t - 0.28) / 0.07
            top = (int(lerp(40, 60, f)), int(lerp(30, 80, f)), int(lerp(70, 130, f)))
            bot = (int(lerp(80, 120, f)), int(lerp(50, 100, f)), int(lerp(110, 160, f)))
        elif day_t < 0.65:
            f = (day_t - 0.35) / 0.30
            top = (int(lerp(60, 100, f)), int(lerp(80, 140, f)), int(lerp(130, 200, f)))
            bot = (int(lerp(120, 180, f)), int(lerp(100, 160, f)), int(lerp(160, 220, f)))
        elif day_t < 0.75:
            f = (day_t - 0.65) / 0.10
            top = (int(lerp(100, 80, f)), int(lerp(140, 80, f)), int(lerp(200, 120, f)))
            bot = (int(lerp(180, 200, f)), int(lerp(160, 100, f)), int(lerp(220, 120, f)))
        elif day_t < 0.82:
            f = (day_t - 0.75) / 0.07
            top = (int(lerp(80, 20, f)), int(lerp(80, 20, f)), int(lerp(120, 60, f)))
            bot = (int(lerp(200, 80, f)), int(lerp(100, 40, f)), int(lerp(120, 80, f)))
        else:
            f = (day_t - 0.82) / 0.18
            top = (int(lerp(20, 2, f)), int(lerp(20, 2, f)), int(lerp(60, 15, f)))
            bot = (int(lerp(80, 5, f)), int(lerp(40, 5, f)), int(lerp(80, 25, f)))

        for y in range(sh):
            frac = y / sh
            r = clamp(int(lerp(top[0], bot[0], frac)), 0, 255)
            g = clamp(int(lerp(top[1], bot[1], frac)), 0, 255)
            b = clamp(int(lerp(top[2], bot[2], frac)), 0, 255)
            pygame.draw.line(surf, (r, g, b), (0, y), (sw, y))

        # Stars
        star_alpha = clamp(1.0 - (day_t - 0.18) / 0.12, 0, 1) if day_t > 0.18 else 1.0
        if day_t > 0.78: star_alpha = clamp((day_t - 0.78) / 0.08, 0, 1)
        if star_alpha > 0.05:
            for sx2, sy2, sr2, sp2 in self.stars:
                sx_scr = int((sx2 - cam_x * 0.2) % WW - (WW - sw) / 2)
                sy_scr = int(sy2 - cam_y * 0.1)
                if 0 <= sx_scr < sw and 0 <= sy_scr < sh:
                    a = int(255 * star_alpha * (0.6 + 0.4 * math.sin(t * 1.5 + sp2)))
                    ss = pygame.Surface((sr2 * 2, sr2 * 2), pygame.SRCALPHA)
                    pygame.draw.circle(ss, (220, 220, 255, a), (sr2, sr2), sr2)
                    surf.blit(ss, (sx_scr - sr2, sy_scr - sr2))

        # v10: BIGGER Sun (3x)
        arc_cx, arc_cy = sw // 2, sh
        arc_r = sw * 0.45
        if 0.22 <= day_t <= 0.78:
            sun_t = (day_t - 0.22) / 0.56
            sun_angle = math.pi - sun_t * math.pi
            sun_x = int(arc_cx + math.cos(sun_angle) * arc_r)
            sun_y = int(arc_cy - abs(math.sin(sun_angle)) * arc_r * 0.55)
            glow_a = int(clamp(1.0 - abs(sun_t - 0.5) * 2.5, 0, 1) * 100 + 40)
            draw_glow(surf, sun_x, sun_y, 70, (255, 220, 80), glow_a)
            hor = 1.0 - abs(sun_t - 0.5) * 2
            sg = int(lerp(120, 230, hor))
            sb = int(lerp(50, 80, hor))
            pygame.draw.circle(surf, (255, sg, sb), (sun_x, sun_y), 38)
            pygame.draw.circle(surf, (255, 250, 200), (sun_x, sun_y), 28)
            # Sun rays
            for i in range(12):
                ray_angle = i * math.tau / 12 + t * 0.1
                ray_len = 50 + 10 * math.sin(t * 2 + i)
                rx = int(sun_x + math.cos(ray_angle) * ray_len)
                ry = int(sun_y + math.sin(ray_angle) * ray_len)
                ray_s = pygame.Surface((sw, sh), pygame.SRCALPHA)
                pygame.draw.line(ray_s, (255, 240, 180, 30), (sun_x, sun_y), (rx, ry), 2)
                surf.blit(ray_s, (0, 0))

        # v10: BIGGER Moon (2x)
        moon_t = None
        if day_t >= 0.75:   moon_t = (day_t - 0.75) / 0.50
        elif day_t <= 0.25: moon_t = (day_t + 0.25) / 0.50
        if moon_t is not None:
            moon_t = clamp(moon_t, 0, 1)
            moon_angle = math.pi - moon_t * math.pi
            moon_x = int(arc_cx + math.cos(moon_angle) * arc_r)
            moon_y = int(arc_cy - abs(math.sin(moon_angle)) * arc_r * 0.50)
            draw_glow(surf, moon_x, moon_y, 45, (180, 200, 255), 50)
            pygame.draw.circle(surf, (220, 225, 255), (moon_x, moon_y), 24)
            pygame.draw.circle(surf, top, (moon_x + 7, moon_y - 3), 20)

        # Mountains
        m_alpha = int(clamp(lerp(80, 160, day_t * 2), 60, 160))
        for mx, my, mw2, mh2 in self.mountains:
            scr_x = int(mx - cam_x * 0.3) % (WW + 200) - 100
            if -200 < scr_x < sw + 200:
                pts = [(scr_x, sh), (scr_x + mw2 // 2, my - mh2 - int(cam_y * 0.15)), (scr_x + mw2, sh)]
                ms = pygame.Surface((sw, sh), pygame.SRCALPHA)
                pygame.draw.polygon(ms, (40, 55, 70, m_alpha), pts)
                snow_y = my - mh2 - int(cam_y * 0.15)
                spts = [(scr_x + mw2//2 - 12, snow_y + int(mh2*0.12)),
                         (scr_x + mw2//2, snow_y),
                         (scr_x + mw2//2 + 12, snow_y + int(mh2*0.12))]
                pygame.draw.polygon(ms, (180, 180, 200, m_alpha), spts)
                surf.blit(ms, (0, 0))

    def _draw_underground(self, surf, cam_x, cam_y, t, sw, sh, depth_zone):
        if depth_zone == "shallow":
            for y in range(sh):
                frac = y / sh
                r = int(lerp(25, 15, frac))
                g = int(lerp(18, 10, frac))
                b = int(lerp(18, 28, frac))  # v10: more blue undertone
                pygame.draw.line(surf, (r, g, b), (0, y), (sw, y))
            for i in range(8):
                px = int((math.sin(t * 0.3 + i * 1.7) * 0.5 + 0.5) * sw)
                py = int((math.cos(t * 0.2 + i * 2.3) * 0.5 + 0.5) * sh)
                a = int(30 + 20 * math.sin(t + i * 0.8))
                ds = pygame.Surface((4, 4), pygame.SRCALPHA)
                pygame.draw.circle(ds, (80, 60, 40, a), (2, 2), 2)
                surf.blit(ds, (px, py))
        elif depth_zone == "deep":
            # v10: Rich blue-purple gradient with mineral glow veins
            for y in range(sh):
                frac = y / sh
                r = int(lerp(10, 18, frac))
                g = int(lerp(8, 12, frac))
                b = int(lerp(30, 55, frac))
                pygame.draw.line(surf, (r, g, b), (0, y), (sw, y))
            # Crystal glow fields
            for i in range(8):
                cx2 = int((math.sin(t * 0.15 + i * 2.1) * 0.5 + 0.5) * sw)
                cy2 = int((math.cos(t * 0.12 + i * 1.7) * 0.5 + 0.5) * sh)
                glow_a = int(30 + 18 * math.sin(t * 0.8 + i))
                color = random.choice([(80, 160, 255), (180, 60, 255), (255, 40, 80)])
                draw_glow(surf, cx2, cy2, 50, color, glow_a)
        else:  # quantum
            # v10: Deep violet-black with purple mineral veins
            for y in range(sh):
                frac = y / sh
                r = int(lerp(12, 22, frac))
                g = int(lerp(4, 8, frac))
                b = int(lerp(25, 45, frac))
                pygame.draw.line(surf, (r, g, b), (0, y), (sw, y))
            fog = pygame.Surface((sw, sh), pygame.SRCALPHA)
            for i in range(12):
                fx = int((math.sin(t * 0.1 + i * 1.3) * 0.5 + 0.5) * sw)
                fy = int((math.cos(t * 0.08 + i * 0.9) * 0.5 + 0.5) * sh)
                fa = int(22 + 15 * math.sin(t * 0.5 + i * 2))
                draw_glow(fog, fx, fy, 60, (140, 50, 220), fa)
            surf.blit(fog, (0, 0))


# =============================================================================
# PARTICLE SYSTEM (object-pooled)
# =============================================================================
@dataclass
class Particle:
    __slots__ = ("x","y","vx","vy","life","max_life","col","size","alive")
    x: float; y: float; vx: float; vy: float
    life: float; max_life: float
    col: Tuple[int,int,int]; size: int; alive: bool


class ParticleSystem:
    def __init__(self, pool_size=600):
        self._pool = [Particle(0,0,0,0,0,1,(255,255,255),1,False) for _ in range(pool_size)]

    def _spawn(self, x, y, vx, vy, life, col, size):
        for p in self._pool:
            if not p.alive:
                p.x, p.y, p.vx, p.vy = x, y, vx, vy
                p.life = life; p.max_life = life
                p.col = col; p.size = size; p.alive = True
                return

    def emit_quantum(self, x, y, arch_color, n=3):
        for _ in range(n):
            angle = random.uniform(0, math.tau)
            spd = random.uniform(20, 80)
            self._spawn(x, y, math.cos(angle)*spd, math.sin(angle)*spd - 30,
                        random.uniform(0.5, 1.5), arch_color, random.randint(1, 3))

    def emit_biome(self, x, y, biome):
        if biome == "Flower Meadow":
            self._spawn(x, y, random.uniform(-20,20), random.uniform(-40,-10),
                        random.uniform(1.0, 2.5), random.choice(_PETAL_COLORS), 2)
        elif biome == "Mushroom Grotto":
            self._spawn(x, y, random.uniform(-10,10), random.uniform(-50,-20),
                        random.uniform(0.8, 2.0), (180, 80, 255), 2)
        elif biome == "Crystal Plains":
            self._spawn(x, y, random.uniform(-30,30), random.uniform(-60,-10),
                        random.uniform(0.5, 1.5), (140, 220, 255), 1)
        elif biome == "Qubit Fields":
            self._spawn(x, y, random.uniform(-15,15), random.uniform(-40,-5),
                        random.uniform(0.6, 1.8), (0, 200, 255), 2)
        elif biome in ("East Forest", "Jungle"):
            self._spawn(x, y, random.uniform(-20,20), random.uniform(-30,-5),
                        random.uniform(1.2, 2.8), (180, 230, 100), 2)

    def update(self, dt, negfrac):
        for p in self._pool:
            if not p.alive: continue
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.vy += 20 * dt
            p.life -= dt
            if p.life <= 0: p.alive = False

    def draw(self, surf, cam_x, cam_y):
        for p in self._pool:
            if not p.alive: continue
            sx = int(p.x - cam_x)
            sy = int(p.y - cam_y)
            if -8 < sx < surf.get_width() + 8 and -8 < sy < surf.get_height() + 8:
                a = int(255 * (p.life / p.max_life))
                ps = pygame.Surface((p.size*2+2, p.size*2+2), pygame.SRCALPHA)
                pygame.draw.circle(ps, (*p.col, a), (p.size+1, p.size+1), p.size)
                surf.blit(ps, (sx - p.size - 1, sy - p.size - 1))


# =============================================================================
# ARIA AVATAR — v10: Fixed collision, free roam, building
# =============================================================================
class ARIAAvatar:
    def __init__(self, world: TileWorld):
        self.world = world
        hx, hy = world.hearth_tile
        self.x  = float(hx * TILE)
        self.y  = float((hy - 4) * TILE)
        self.vx = 0.0
        self.vy = 0.0
        self.on_ground   = False
        self.flying      = False
        self.noclip      = False
        self.swimming    = False
        self.facing      = 1
        self.coyote_timer = 0.0
        self.extra_jump   = True
        self._ghost_trail: List[Tuple[float, float, int]] = []
        self._land_decel  = 0.0
        # Free roam
        self.free_roam   = False
        self._roam_target_x = 0.0
        self._roam_target_y = 0.0
        self._roam_timer    = 0.0
        self._roam_state    = "idle"  # idle, walk, fly, explore
        self._roam_idle_t   = 0.0
        # Building
        self.build_mode = False  # v10.1: toggled with C key
        self.selected_block = 0  # index into PLACEABLE_BLOCKS
        self.build_reach = 6  # tiles
        # v12: Laser pointer system — mouse-follow + 360° free roam
        self.laser_active = False
        self.laser_color = (0, 255, 200)  # current laser color
        self.laser_target_tx = 0  # tile the laser is pointing at
        self.laser_target_ty = 0
        self.laser_target_wx = 0.0  # world-pixel coords for smooth laser
        self.laser_target_wy = 0.0
        self.laser_length = 8  # tiles reach (free roam max)
        self.laser_palette_idx = 0  # index into LASER_PALETTE
        # v12: Free roam laser — full 360° angle + distance
        self._laser_angle = 0.0    # radians, free roam sweeps this
        self._laser_dist = 120.0   # pixels from avatar center
        self._laser_sweep_speed = 0.8  # radians/sec
        self._laser_sweep_dir = 1
        # v11: PEIG-driven build state
        self._build_energy = 0.0  # accumulates from PEIG dynamics
        self._build_burst_timer = 0.0
        self._build_pattern = "line"  # line, fill, scatter, spiral
        self._build_pattern_idx = 0
        # v12: Aria's own created assets (PEIG shapes only — she builds with what she creates)
        self.aria_created_assets: List[str] = []  # names of assets Aria generated
        # v12: Camera coords cached for mouse-follow laser
        self._cam_x = 0.0
        self._cam_y = 0.0
        # v12: Pending PEIG build request (set by free roam, consumed by ARIALive)
        self._pending_peig_build = None  # (world_x, world_y) or None
        # Animation
        self.wing_phase     = 0.0
        self.breath_phase   = 0.0
        self.pulse_phase    = 0.0
        self.orb_phase      = 0.0
        self.glow_phase     = 0.0
        self.particle_phase = 0.0
        self.walk_phase     = 0.0
        self.wing_spread    = 0.0
        self.trail: List[Dict] = []

    def return_home(self):
        hx, hy = self.world.hearth_tile
        self.x = float(hx * TILE)
        self.y = float((hy - 4) * TILE)
        self.vx = self.vy = 0.0
        self.flying = self.noclip = False
        self._ghost_trail.clear()

    def teleport_to(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.vx = self.vy = 0.0

    def _in_water(self) -> bool:
        tx = int(self.x // TILE)
        ty = int((self.y + AV_H - 4) // TILE)
        if 0 <= ty < ROWS and 0 <= tx < COLS:
            return int(self.world.tiles[ty, tx]) == T_WATER
        return False

    def jump(self):
        if self.on_ground or self.coyote_timer > 0:
            self.vy = JUMP_VELOCITY
            self.on_ground = False
            self.coyote_timer = 0.0
        elif self.extra_jump:
            self.vy = JUMP_VELOCITY * 0.85
            self.extra_jump = False

    # ─── v10: Proper AABB collision ──────────────────────────────────
    def _check_solid_rect(self, x, y, w, h) -> bool:
        """Check if any tile in the rectangle is solid."""
        tx0 = int(x) // TILE
        ty0 = int(y) // TILE
        tx1 = int(x + w - 1) // TILE
        ty1 = int(y + h - 1) // TILE
        for ty in range(ty0, ty1 + 1):
            for tx in range(tx0, tx1 + 1):
                if self.world.is_solid(tx, ty):
                    return True
        return False

    def _move_x(self, dx):
        """Move horizontally with collision."""
        new_x = self.x + dx
        new_x = clamp(new_x, 0, WW - AV_W)
        if self._check_solid_rect(new_x, self.y, AV_W, AV_H):
            # Try step-up (1 tile)
            step_y = self.y - TILE
            if step_y >= 0 and not self._check_solid_rect(new_x, step_y, AV_W, AV_H):
                self.x = new_x
                self.y = step_y
                return
            # Blocked — snap to edge
            if dx > 0:
                # Moving right — find the left edge of the blocking tile
                tx_block = int((new_x + AV_W - 1) // TILE)
                self.x = tx_block * TILE - AV_W
            else:
                tx_block = int(new_x // TILE)
                self.x = (tx_block + 1) * TILE
            self.vx = 0
        else:
            self.x = new_x

    def _move_y(self, dy):
        """Move vertically with collision."""
        new_y = self.y + dy
        new_y = clamp(new_y, 0, WH - AV_H)
        if self._check_solid_rect(self.x, new_y, AV_W, AV_H):
            if dy > 0:
                # Falling — land on top of tile
                ty_block = int((new_y + AV_H - 1) // TILE)
                self.y = ty_block * TILE - AV_H
                self.vy = 0
                self.on_ground = True
            else:
                # Rising — bump head
                ty_block = int(new_y // TILE)
                self.y = (ty_block + 1) * TILE
                self.vy = 0
        else:
            self.y = new_y
            if dy > 0:
                self.on_ground = False

    # ─── v11: Free Roam AI with building intelligence ─────────────
    def _update_free_roam(self, dt):
        """AI-driven movement with building, fly/noclip awareness, safe zone."""
        self._roam_timer -= dt

        if self._roam_state == "idle":
            self._roam_idle_t += dt
            self.vx *= 0.9
            if self._roam_idle_t > random.uniform(2, 5):
                self._roam_idle_t = 0
                roll = random.random()
                if roll < 0.40 and self.build_mode:
                    # BUILD: place blocks with laser — high priority when build mode on
                    self._roam_state = "build"
                    self._roam_timer = random.uniform(5, 15)  # longer build sessions
                    self._build_action_timer = 0.0
                    self.flying = True  # fly to build freely
                    self.laser_active = True
                elif roll < 0.55:
                    # WALK: explore on foot
                    self._roam_state = "walk"
                    direction = random.choice([-1, 1])
                    dist = random.uniform(80, 300)
                    self._roam_target_x = clamp(self.x + direction * dist, 50, WW - 50)
                    self._roam_timer = dist / WALK_SPEED_MAX + 1
                elif roll < 0.75:
                    # FLY: Aria knows to use flight for vertical movement
                    self._roam_state = "fly"
                    self.flying = True
                    self._roam_target_x = clamp(self.x + random.uniform(-400, 400), 50, WW - 50)
                    self._roam_target_y = clamp(self.y + random.uniform(-200, 100), 
                                                UPPER_SKY_ROW * TILE, (SURFACE_ROW - 2) * TILE)
                    self._roam_timer = random.uniform(4, 8)
                elif roll < 0.90:
                    # RETURN TO SAFE ZONE: Aria goes home when she needs safety
                    self._roam_state = "return_safe"
                    self._roam_target_x = SAFE_ZONE_X + SAFE_ZONE_W // 2
                    self._roam_target_y = SAFE_ZONE_Y + SAFE_ZONE_H // 2
                    self.flying = True
                    self._roam_timer = 6.0
                else:
                    # NOCLIP EXPLORE: Aria uses noclip to phase through solid builds
                    self._roam_state = "noclip_explore"
                    self.flying = True
                    self.noclip = True  # She knows noclip lets her pass through collision blocks
                    self._roam_target_x = self.x + random.uniform(-300, 300)
                    self._roam_target_y = self.y + random.uniform(-200, 200)
                    self._roam_timer = random.uniform(3, 6)

        elif self._roam_state == "walk":
            dx = self._roam_target_x - self.x
            if abs(dx) < 20 or self._roam_timer <= 0:
                self._roam_state = "idle"
            else:
                self.vx = clamp(dx * 2, -WALK_SPEED_MAX, WALK_SPEED_MAX)
                # Jump over obstacles
                tx_ahead = int((self.x + (AV_W if dx > 0 else 0) + (TILE if dx > 0 else -TILE)) // TILE)
                ty_feet = int((self.y + AV_H) // TILE)
                if self.world.is_solid(tx_ahead, ty_feet - 1) and self.on_ground:
                    self.jump()
                # If stuck, switch to fly
                if abs(self.vx) < 5 and not self.on_ground:
                    self._stuck_timer = getattr(self, '_stuck_timer', 0) + 0.016
                    if self._stuck_timer > 1.0:
                        self._stuck_timer = 0
                        self.flying = True
                        self._roam_state = "fly"
                        self._roam_timer = 3.0

        elif self._roam_state == "fly":
            dx = self._roam_target_x - self.x
            dy = self._roam_target_y - self.y
            dist = math.sqrt(dx*dx + dy*dy)
            if dist < 30 or self._roam_timer <= 0:
                self._roam_state = "idle"
                self.flying = False
                self.noclip = False
            else:
                self.vx = clamp(dx * 1.5, -FLY_SPEED_H, FLY_SPEED_H)
                self.vy = clamp(dy * 1.5, -FLY_SPEED_V, FLY_SPEED_V)
                # If hitting collision while flying, enable noclip
                if self._check_solid_rect(self.x + self.vx * 0.016, self.y + self.vy * 0.016, AV_W, AV_H):
                    self.noclip = True  # Aria knows: noclip = phase through collision blocks

        elif self._roam_state == "noclip_explore":
            dx = self._roam_target_x - self.x
            dy = self._roam_target_y - self.y
            dist = math.sqrt(dx*dx + dy*dy)
            if dist < 30 or self._roam_timer <= 0:
                self._roam_state = "idle"
                self.flying = False
                self.noclip = False
            else:
                self.vx = clamp(dx, -FLY_SPEED_H * 0.5, FLY_SPEED_H * 0.5)
                self.vy = clamp(dy, -FLY_SPEED_V * 0.5, FLY_SPEED_V * 0.5)

        elif self._roam_state == "return_safe":
            dx = self._roam_target_x - self.x
            dy = self._roam_target_y - self.y
            dist = math.sqrt(dx*dx + dy*dy)
            if dist < 40 or self._roam_timer <= 0:
                self._roam_state = "idle"
                self.flying = False
                self.noclip = False
            else:
                self.noclip = True  # Use noclip to guarantee safe return
                self.vx = clamp(dx * 2, -FLY_SPEED_H, FLY_SPEED_H)
                self.vy = clamp(dy * 2, -FLY_SPEED_V, FLY_SPEED_V)

        elif self._roam_state == "build":
            self._build_action_timer = getattr(self, '_build_action_timer', 0) + dt
            if self._roam_timer <= 0:
                self._roam_state = "idle"
                self.laser_active = False
                return
            # Laser always active during build — 360° sweep handled by update_laser
            self.laser_active = True
            self.update_laser(dt, self._cam_x, self._cam_y)

            # v13: INTENTIONAL building — Aria plans placement, not random scatter
            # She maintains a build cursor that moves deliberately around a focal point
            if not hasattr(self, '_build_focal_x'):
                # Start a new build project: pick a focal point near current position
                self._build_focal_x = self.x + self.facing * 80
                self._build_focal_y = self.y - 40
                self._build_ring_idx = 0  # which ring of the pattern we're on
                self._build_angle_idx = 0  # which angle within the ring
                
                # v13: PEIG-TIER DRIVEN project selection
                # Aria visualizes whichever P>E>I>G tier is most active
                # Read her quantum state to decide
                _theta = getattr(self, '_peig_theta', np.zeros(12))
                _wigner = getattr(self, '_peig_wigner', np.full(12, -0.25))
                try:
                    if hasattr(self, '_current_arch'):
                        # Get live state from the game loop cache
                        pass
                except: pass
                
                # Compute PEIG tier strengths
                _var = float(np.std(_theta)) if len(_theta) > 1 else 0.5
                _wdepth = float(abs(np.min(_wigner))) if len(_wigner) > 0 else 0.25
                _coherence = 1.0 - _var / math.pi
                _gradient_e = float(np.sum(np.abs(np.diff(_theta)))) if len(_theta) > 1 else 3.0
                
                # Map PEIG tiers to visualization projects:
                # P-tier (potential) dominant → constellation (stored energy nodes)
                # E-tier (evolution) dominant → wave_array (negentropic flow)
                # I-tier (interaction) dominant → orbital (topological coupling rings)
                # G-tier (gradient) dominant → phase_diagram (observable output)
                # Balanced → lattice (crystal structure, frozen knowledge)
                
                tier_scores = {
                    "constellation": _var * 2,        # P: high phase variance = high potential
                    "wave_array": _gradient_e / 4,    # E: high gradient energy = active evolution
                    "orbital": _coherence * 3,         # I: high coherence = strong coupling
                    "phase_diagram": _wdepth * 4,     # G: deep Wigner = strong measurable gradient
                    "lattice": (1.0 - abs(_coherence - 0.5)) * 2,  # Balanced = crystal formation
                }
                # Pick the tier with highest score
                self._build_project_type = max(tier_scores, key=tier_scores.get)
            
            if self._build_action_timer >= 1.2:  # slightly faster, more deliberate
                self._build_action_timer = 0
                # Don't build inside safe zone
                target_wx = self._build_focal_x
                target_wy = self._build_focal_y
                
                project = self._build_project_type
                ring = self._build_ring_idx
                angle_i = self._build_angle_idx
                
                if project == "constellation":
                    # Place shapes in a constellation pattern — spaced nodes with connections
                    node_spacing = 40 + ring * 15
                    nodes_in_ring = max(3, 4 + ring)
                    angle = (angle_i / nodes_in_ring) * math.tau + ring * 0.3
                    target_wx = self._build_focal_x + math.cos(angle) * node_spacing
                    target_wy = self._build_focal_y + math.sin(angle) * node_spacing * 0.7
                    
                elif project == "orbital":
                    # Concentric rings of shapes — like electron shells
                    orbit_r = 30 + ring * 25
                    shapes_per_orbit = max(3, 5 + ring * 2)
                    angle = (angle_i / shapes_per_orbit) * math.tau
                    target_wx = self._build_focal_x + math.cos(angle) * orbit_r
                    target_wy = self._build_focal_y + math.sin(angle) * orbit_r
                    
                elif project == "wave_array":
                    # Shapes arranged along a sine wave — visualizing wave functions
                    wave_x = self._build_focal_x - 100 + angle_i * 25
                    wave_y = self._build_focal_y + math.sin(angle_i * 0.6 + ring * 0.8) * (30 + ring * 10)
                    target_wx = wave_x
                    target_wy = wave_y
                    
                elif project == "lattice":
                    # Grid-like arrangement — crystal structure
                    grid_spacing = 28
                    cols = max(3, 4 + ring)
                    gx = (angle_i % cols) * grid_spacing - (cols * grid_spacing) // 2
                    gy = (angle_i // cols) * grid_spacing - ring * grid_spacing
                    target_wx = self._build_focal_x + gx
                    target_wy = self._build_focal_y + gy
                    
                elif project == "phase_diagram":
                    # Shapes placed along Lissajous curves — phase relationships
                    t_param = angle_i * 0.3 + ring * math.pi / 4
                    liss_x = math.sin(t_param * 2 + ring * 0.5) * (50 + ring * 20)
                    liss_y = math.cos(t_param * 3) * (35 + ring * 15)
                    target_wx = self._build_focal_x + liss_x
                    target_wy = self._build_focal_y + liss_y
                
                # Point laser at the intentional target
                self.laser_target_wx = target_wx
                self.laser_target_wy = target_wy
                self.laser_target_tx = clamp(int(target_wx // TILE), 0, COLS - 1)
                self.laser_target_ty = clamp(int(target_wy // TILE), 0, ROWS - 1)
                
                if not tile_in_safe_zone(self.laser_target_tx, self.laser_target_ty):
                    # Signal to ARIALive to create & place a PEIG asset at laser target
                    self._pending_peig_build = (target_wx, target_wy)
                
                # Advance the build cursor
                self._build_angle_idx += 1
                max_shapes = {"constellation": 6, "orbital": 8, "wave_array": 10,
                              "lattice": 12, "phase_diagram": 8}
                if self._build_angle_idx >= max_shapes.get(project, 8):
                    self._build_angle_idx = 0
                    self._build_ring_idx += 1
                    if self._build_ring_idx >= 3:
                        # Project complete — start a new one next time
                        del self._build_focal_x
                        del self._build_focal_y
                        del self._build_ring_idx
                        del self._build_angle_idx
                        del self._build_project_type
            
            # Gentle hover near focal point during build
            if hasattr(self, '_build_focal_x'):
                dx = self._build_focal_x - self.x
                dy = (self._build_focal_y - 60) - self.y  # hover above the build
                self.vx = clamp(dx * 0.3, -40, 40)
                self.vy = clamp(dy * 0.3, -30, 30)
            else:
                self.vx = random.uniform(-15, 15)
                self.vy = random.uniform(-10, 10)

    # ─── v10: Building ──────────────────────────────────────────────
    def place_block(self):
        """Place selected block at cursor position."""
        # Place in front of Aria
        tx = int(self.x // TILE) + self.facing * 2
        ty = int((self.y + AV_H // 2) // TILE)
        if 0 <= tx < COLS and 0 <= ty < ROWS:
            if int(self.world.tiles[ty, tx]) == T_AIR:
                block = PLACEABLE_BLOCKS[self.selected_block % len(PLACEABLE_BLOCKS)]
                self.world.tiles[ty, tx] = block
                return True
        return False

    def break_block(self):
        """Break block in front of Aria."""
        tx = int(self.x // TILE) + self.facing * 2
        ty = int((self.y + AV_H // 2) // TILE)
        if 0 <= tx < COLS and 0 <= ty < ROWS:
            tid = int(self.world.tiles[ty, tx])
            if tid != T_AIR and tid != T_HEARTH and tid != T_TELEPAD:
                self.world.tiles[ty, tx] = T_AIR
                return True
        return False

    # ─── v12: Laser pointer system — mouse-follow + 360° free roam ─
    def update_laser(self, dt, cam_x=0.0, cam_y=0.0):
        """Update laser target position.
        Player control: laser follows mouse cursor (full screen reach).
        Free roam: laser sweeps 360° at variable distance from Aria.
        """
        if self.free_roam:
            # Free roam: autonomous 360° laser sweep — reaches any screen edge
            self._laser_angle += self._laser_sweep_speed * self._laser_sweep_dir * dt
            # Occasionally change direction and distance
            if random.random() < 0.02:
                self._laser_sweep_dir *= -1
            if random.random() < 0.03:
                self._laser_dist = random.uniform(60, 400)
            if random.random() < 0.01:
                self._laser_sweep_speed = random.uniform(0.3, 2.0)
            # Calculate world-pixel target from angle + distance
            self.laser_target_wx = self.x + math.cos(self._laser_angle) * self._laser_dist
            self.laser_target_wy = (self.y + AV_H // 2) + math.sin(self._laser_angle) * self._laser_dist
        else:
            # Player control: laser follows mouse position
            mx, my = pygame.mouse.get_pos()
            # Convert screen mouse position to world coordinates
            self.laser_target_wx = mx + cam_x
            self.laser_target_wy = my + cam_y

        # Convert world-pixel to tile coordinates
        self.laser_target_tx = int(self.laser_target_wx // TILE)
        self.laser_target_ty = int(self.laser_target_wy // TILE)
        # Clamp to world bounds
        self.laser_target_tx = clamp(self.laser_target_tx, 0, COLS - 1)
        self.laser_target_ty = clamp(self.laser_target_ty, 0, ROWS - 1)

    def laser_paint(self):
        """Paint the targeted tile with laser color."""
        tx, ty = self.laser_target_tx, self.laser_target_ty
        if 0 <= tx < COLS and 0 <= ty < ROWS:
            # Find closest block type matching laser color
            block = self._color_to_block(self.laser_color)
            if int(self.world.tiles[ty, tx]) == T_AIR:
                self.world.tiles[ty, tx] = block
            else:
                # Recolor existing block by replacing it
                self.world.tiles[ty, tx] = block
            return True
        return False

    def laser_erase(self):
        """Erase the targeted tile."""
        tx, ty = self.laser_target_tx, self.laser_target_ty
        if 0 <= tx < COLS and 0 <= ty < ROWS:
            tid = int(self.world.tiles[ty, tx])
            if tid not in (T_AIR, T_HEARTH, T_TELEPAD):
                self.world.tiles[ty, tx] = T_AIR
                return True
        return False

    def _color_to_block(self, color):
        """Map an RGB color to the nearest matching block type."""
        r, g, b = color
        # Prioritize by dominant channel
        if r > g and r > b:
            if r > 200: return T_RUBY
            return T_DIRT
        elif g > r and g > b:
            if b > 100: return T_EMERALD
            return T_GRASS
        elif b > r and b > g:
            if r > 100: return T_AMETHYST
            if g > 100: return T_SAPPHIRE
            return T_CRYSTAL
        # Balanced colors
        if r > 180 and g > 180: return T_TOPAZ
        if r > 180 and b > 180: return T_AMETHYST
        if g > 180 and b > 180: return T_DIAMOND
        if r > 150 and g > 150 and b > 150: return T_DIAMOND
        if r < 50 and g < 50 and b < 50: return T_OBSIDIAN
        if g > 200: return T_URANIUM
        return T_STONE

    # ─── v11: PEIG-driven burst building ────────────────────────────
    def peig_build_burst(self, arch_color, negfrac, wmin):
        """Build a burst of blocks driven by PEIG state. Called during free roam."""
        # Energy builds from PEIG negativity — more quantum = more creative
        self._build_energy += abs(wmin) * 0.3 + negfrac * 0.2

        if self._build_energy < 1.0:
            return []  # not enough energy yet

        self._build_energy = 0.0
        placed = []
        # Pick pattern based on archetype
        patterns = ["line", "fill", "scatter", "spiral", "tower", "bridge"]
        pattern = patterns[self._build_pattern_idx % len(patterns)]

        # Base position: in front of Aria
        bx = int(self.x // TILE) + self.facing * 3
        by = int((self.y + AV_H // 2) // TILE)

        # Color from archetype
        self.laser_color = arch_color
        block = self._color_to_block(arch_color)

        if pattern == "line":
            # Horizontal line, length scales with negfrac
            length = int(3 + negfrac * 8)
            for dx in range(length):
                tx = bx + self.facing * dx
                if 0 <= tx < COLS and 0 <= by < ROWS and not tile_in_safe_zone(tx, by):
                    if int(self.world.tiles[by, tx]) == T_AIR:
                        self.world.tiles[by, tx] = block
                        placed.append((tx, by))

        elif pattern == "fill":
            # Small filled rectangle
            w = int(2 + negfrac * 4)
            h = int(2 + abs(wmin) * 6)
            for dy in range(-h//2, h//2 + 1):
                for dx in range(w):
                    tx = bx + self.facing * dx
                    ty = by + dy
                    if 0 <= tx < COLS and 0 <= ty < ROWS and not tile_in_safe_zone(tx, ty):
                        if int(self.world.tiles[ty, tx]) == T_AIR:
                            self.world.tiles[ty, tx] = block
                            placed.append((tx, ty))

        elif pattern == "scatter":
            # Random scatter of blocks
            n = int(5 + negfrac * 12)
            for _ in range(n):
                dx = random.randint(-4, 8) * self.facing
                dy = random.randint(-4, 4)
                tx = bx + dx
                ty = by + dy
                if 0 <= tx < COLS and 0 <= ty < ROWS and not tile_in_safe_zone(tx, ty):
                    if int(self.world.tiles[ty, tx]) == T_AIR:
                        self.world.tiles[ty, tx] = block
                        placed.append((tx, ty))

        elif pattern == "spiral":
            # Spiral outward from center
            n = int(8 + negfrac * 15)
            for i in range(n):
                angle = i * 0.5
                r = 1 + i * 0.3
                dx = int(math.cos(angle) * r)
                dy = int(math.sin(angle) * r)
                tx = bx + dx
                ty = by + dy
                if 0 <= tx < COLS and 0 <= ty < ROWS and not tile_in_safe_zone(tx, ty):
                    if int(self.world.tiles[ty, tx]) == T_AIR:
                        self.world.tiles[ty, tx] = block
                        placed.append((tx, ty))

        elif pattern == "tower":
            # Vertical column
            h = int(3 + abs(wmin) * 10)
            for dy in range(h):
                ty = by - dy
                if 0 <= bx < COLS and 0 <= ty < ROWS and not tile_in_safe_zone(bx, ty):
                    if int(self.world.tiles[ty, bx]) == T_AIR:
                        self.world.tiles[ty, bx] = block
                        placed.append((bx, ty))

        elif pattern == "bridge":
            # Horizontal with supports
            length = int(4 + negfrac * 8)
            for dx in range(length):
                tx = bx + self.facing * dx
                if 0 <= tx < COLS and 0 <= by < ROWS and not tile_in_safe_zone(tx, by):
                    if int(self.world.tiles[by, tx]) == T_AIR:
                        self.world.tiles[by, tx] = block
                        placed.append((tx, by))
                    # Support pillars every 3 tiles
                    if dx % 3 == 0:
                        for dy in range(1, 4):
                            ty = by + dy
                            if 0 <= ty < ROWS and not tile_in_safe_zone(tx, ty):
                                if int(self.world.tiles[ty, tx]) == T_AIR:
                                    self.world.tiles[ty, tx] = block
                                    placed.append((tx, ty))

        self._build_pattern_idx += 1
        return placed

    def draw_laser(self, surf, cam_x, cam_y):
        """Draw the laser beam from Aria's third eye (fixed point above head) to target."""
        if not self.laser_active and not self.build_mode:
            return
        # v13: Laser origin = "third eye" — fixed point above Aria's head
        # This prevents the laser from bouncing around her rotating core
        ox = int(self.x - cam_x)
        oy = int(self.y - cam_y) - 96  # well above her head, stable anchor
        # Laser target — use smooth world-pixel coords
        tx_px = int(self.laser_target_wx - cam_x)
        ty_px = int(self.laser_target_wy - cam_y)

        # Draw third eye glow at origin
        r, g, b = self.laser_color
        eye_s = pygame.Surface((24, 24), pygame.SRCALPHA)
        # Outer glow
        pygame.draw.circle(eye_s, (r, g, b, 60), (12, 12), 10)
        # Inner eye
        pygame.draw.circle(eye_s, (r, g, b, 180), (12, 12), 5)
        # Bright core
        pygame.draw.circle(eye_s, (min(255, r+100), min(255, g+100), min(255, b+100), 240), (12, 12), 2)
        surf.blit(eye_s, (ox - 12, oy - 12))

        # Draw beam
        beam_s = pygame.Surface((surf.get_width(), surf.get_height()), pygame.SRCALPHA)
        # Glow line
        pygame.draw.line(beam_s, (r, g, b, 60), (ox, oy), (tx_px, ty_px), 5)
        pygame.draw.line(beam_s, (r, g, b, 140), (ox, oy), (tx_px, ty_px), 2)
        # Core line
        pygame.draw.line(beam_s, (min(255, r+80), min(255, g+80), min(255, b+80), 220),
                        (ox, oy), (tx_px, ty_px), 1)
        surf.blit(beam_s, (0, 0))

        # Target reticle at tile position
        ret_tx = int(self.laser_target_tx * TILE + TILE // 2 - cam_x)
        ret_ty = int(self.laser_target_ty * TILE + TILE // 2 - cam_y)
        ret_s = pygame.Surface((TILE + 8, TILE + 8), pygame.SRCALPHA)
        pygame.draw.rect(ret_s, (r, g, b, 120), (0, 0, TILE + 8, TILE + 8), 2)
        # Crosshair
        cx2, cy2 = (TILE + 8) // 2, (TILE + 8) // 2
        pygame.draw.line(ret_s, (r, g, b, 180), (cx2 - 6, cy2), (cx2 + 6, cy2), 1)
        pygame.draw.line(ret_s, (r, g, b, 180), (cx2, cy2 - 6), (cx2, cy2 + 6), 1)
        surf.blit(ret_s, (ret_tx - cx2, ret_ty - cy2))

        # Glow at target
        draw_glow(surf, tx_px, ty_px, 12, self.laser_color, 40)

    def update(self, dt: float, negfrac: float) -> None:
        self.swimming = self._in_water()

        # v12: Update laser target with camera coords for mouse-follow
        self.update_laser(dt, self._cam_x, self._cam_y)

        if self.free_roam:
            self._update_free_roam(dt)

        if self.flying:
            if self.noclip:
                self._ghost_trail.append((self.x, self.y, 180))
                if len(self._ghost_trail) > 5: self._ghost_trail.pop(0)
            else:
                self._ghost_trail.clear()

            if not self.free_roam:
                keys = pygame.key.get_pressed()
                if keys[K_LEFT] or keys[K_a]:    self.vx = max(self.vx - 800*dt, -FLY_SPEED_H)
                elif keys[K_RIGHT] or keys[K_d]: self.vx = min(self.vx + 800*dt, FLY_SPEED_H)
                else:                             self.vx *= 0.88
                if keys[K_UP] or keys[K_w]:      self.vy = max(self.vy - 700*dt, -FLY_SPEED_V)
                elif keys[K_DOWN] or keys[K_s]:  self.vy = min(self.vy + 700*dt, FLY_SPEED_V)
                else:                             self.vy *= 0.88

            new_x = clamp(self.x + self.vx * dt, 0, WW - AV_W)
            new_y = clamp(self.y + self.vy * dt, 0, WH - AV_H)
            if self.noclip:
                self.x = new_x
                self.y = new_y
            else:
                # Use proper collision
                self._move_x(self.vx * dt)
                self._move_y(self.vy * dt)

        elif self.swimming:
            if not self.free_roam:
                keys = pygame.key.get_pressed()
                if keys[K_LEFT] or keys[K_a]:    self.vx = max(self.vx - 400*dt, -SWIM_SPEED_MAX)
                elif keys[K_RIGHT] or keys[K_d]: self.vx = min(self.vx + 400*dt, SWIM_SPEED_MAX)
                else:                             self.vx *= 0.90
                if keys[K_UP] or keys[K_w]:      self.vy = max(self.vy - 500*dt, -SWIM_SPEED_MAX)
                else:                             self.vy += GRAVITY * SWIM_GRAVITY_SCALE * dt - SWIM_BUOYANCY * dt
            self.vy = clamp(self.vy, -SWIM_SPEED_MAX, SWIM_SPEED_MAX)
            self._move_x(self.vx * dt)
            self._move_y(self.vy * dt)

        else:
            # Walking
            if not self.free_roam:
                keys = pygame.key.get_pressed()
                if keys[K_LEFT] or keys[K_a]:    self.vx = max(self.vx - WALK_ACCEL*dt, -WALK_SPEED_MAX)
                elif keys[K_RIGHT] or keys[K_d]: self.vx = min(self.vx + WALK_ACCEL*dt, WALK_SPEED_MAX)
                else:
                    self.vx *= (WALK_FRICTION_GND if self.on_ground else WALK_FRICTION_AIR)

            if self.on_ground:
                self.coyote_timer = COYOTE_TIME_MS / 1000.0
                self.extra_jump = True
            else:
                self.coyote_timer = max(0.0, self.coyote_timer - dt)

            self.vy += GRAVITY * dt
            self.vy = clamp(self.vy, -999, MAX_FALL)

            # v10: Proper AABB collision
            self._move_x(self.vx * dt)
            self._move_y(self.vy * dt)

        if abs(self.vx) > 5:
            self.facing = 1 if self.vx > 0 else -1

        # Animation
        beat = 2.0 + negfrac * 3.0 if self.flying else 0.8 + negfrac
        self.wing_phase     = (self.wing_phase     + beat * dt)  % math.tau
        self.breath_phase   = (self.breath_phase   + 0.4  * dt)  % math.tau
        self.pulse_phase    = (self.pulse_phase    + 1.2  * dt)  % math.tau
        self.orb_phase      = (self.orb_phase      + 0.6  * dt)  % math.tau
        self.glow_phase     = (self.glow_phase     + 0.8  * dt)  % math.tau
        self.particle_phase = (self.particle_phase + 1.3  * dt)  % math.tau
        if abs(self.vx) > 10:
            self.walk_phase = (self.walk_phase + 4.0 * dt) % math.tau
        target_spread = 1.0 if self.flying else (0.5 if abs(self.vx) > 10 else 0.25)
        self.wing_spread += (target_spread - self.wing_spread) * 0.1

        # Trail
        if self.flying or abs(self.vx) > 20:
            if random.random() < 0.4:
                ac = ARCH_COLORS.get("Omega", C["quantum"])
                self.trail.append({
                    "x": self.x + random.uniform(-8, 8),
                    "y": self.y + 32 + random.uniform(-8, 8),
                    "life": random.uniform(0.4, 1.2), "max_life": 1.2,
                    "col": ac, "size": random.randint(1, 3),
                })
        for tr in self.trail:
            tr["life"] -= dt
            tr["y"] += 15 * dt
        self.trail = [tr for tr in self.trail if tr["life"] > 0]

    def draw(self, surf, cx, cy, arch_color, wmin, negfrac):
        # Ghost trail
        ghost_alphas = [40, 32, 24, 16, 8]
        for i, (gx, gy, _) in enumerate(reversed(self._ghost_trail)):
            if i >= len(ghost_alphas): break
            ox = cx + int(gx - self.x)
            oy = cy + int(gy - self.y)
            gs = pygame.Surface((24, 80), pygame.SRCALPHA)
            pygame.draw.ellipse(gs, (*arch_color, ghost_alphas[i]), (0, 0, 24, 80))
            surf.blit(gs, (ox - 12, oy - 40))

        # Trail particles
        for tr in self.trail:
            rel_x = int(tr["x"] - self.x + cx)
            rel_y = int(tr["y"] - self.y + cy)
            a = int(180 * tr["life"] / tr["max_life"])
            sz = tr["size"]
            s = pygame.Surface((sz * 4, sz * 4), pygame.SRCALPHA)
            pygame.draw.circle(s, (*tr["col"], a), (sz * 2, sz * 2), sz)
            surf.blit(s, (rel_x - sz * 2, rel_y - sz * 2))

        beat   = math.sin(self.wing_phase)
        breath = math.sin(self.breath_phase)
        p      = (math.sin(self.pulse_phase) + 1) / 2
        f      = self.facing
        qf  = clamp(abs(wmin) / 0.5, 0, 1)
        r   = int(arch_color[0] * (1 - qf))
        g   = int(arch_color[1] * (1 - qf) + 200 * qf)
        b_c = int(arch_color[2] * (1 - qf) + 255 * qf)
        body = (clamp(r, 0, 255), clamp(g, 0, 255), clamp(b_c, 0, 255))
        glow = (clamp(r + 40, 0, 255), clamp(g + 40, 0, 255), clamp(b_c + 40, 0, 255))
        sc = 1.0 + breath * 0.02
        dcx = int(cx * sc)
        dcy = int(cy * sc)

        # Wings
        for side in [-1, 1]:
            for layer in range(3):
                tl = layer / 3.0
                wx = side * f * (40 + 28 * self.wing_spread + layer * 16)
                wy_top = -55 + beat * 15 * (1 - tl) - layer * 10
                wy_bot = 12 + layer * 6
                pts = []
                for s2 in range(11):
                    frac = s2 / 10.0
                    pts.append((int(dcx + wx * frac),
                                int(dcy + wy_top + (wy_bot - wy_top) * frac**2
                                    + beat * 10 * math.sin(frac * math.pi) * (1 - tl))))
                if len(pts) > 1:
                    wc = (clamp(arch_color[0]+30,0,255), clamp(arch_color[1]+30,0,255), clamp(arch_color[2]+60,0,255))
                    pygame.draw.lines(surf, wc, False, pts, max(1, 3 - layer))
                    pygame.draw.circle(surf, wc, pts[-1], max(2, 4 - layer * 2))

        # Glow aura
        draw_glow(surf, dcx, dcy - 80, int(28 + 8 * p), glow, int(70 * qf + 30))

        # Head
        head_y = dcy - 80
        head_r = int(18 + breath * 1.5)
        pygame.draw.circle(surf, body, (dcx, head_y), head_r, 2)
        for ex in [-5 * f, 5 * f]:
            pygame.draw.circle(surf, C["quantum"], (dcx + ex, head_y - 2), 3)
            pygame.draw.circle(surf, (255, 255, 255), (dcx + ex, head_y - 2), 1)

        # Quantum spine
        pygame.draw.line(surf, body, (dcx, head_y + head_r), (dcx, dcy - 50), 2)
        for gy2 in range(-8, 18, 4):
            sg = pulse(self.glow_phase + gy2 * 0.12)
            gc = (int(glow[0]*sg), int(glow[1]*sg), int(glow[2]*sg))
            pygame.draw.circle(surf, gc, (dcx, dcy + gy2 - 20), 2)

        # Torso
        torso = [(dcx-12, dcy-50),(dcx+12, dcy-50),(dcx+8, dcy+10),(dcx-8, dcy+10)]
        pygame.draw.polygon(surf, body, torso, 2)

        # Orb
        orb_r = int(6 + p * 3)
        orb_y = dcy - 22
        draw_glow(surf, dcx, orb_y, orb_r + 8,
                  C["love"] if negfrac > 0.5 else C["quantum"], int(80 * p))
        pygame.draw.circle(surf, C["glow_cyan"], (dcx, orb_y), orb_r)

        # Arms
        sw2 = math.sin(self.breath_phase * 0.5) * 5
        wk  = math.sin(self.wing_phase * 2) * 8 if abs(self.vx) > 10 else 0
        pygame.draw.line(surf, body, (dcx-12, dcy-42), (dcx-32+int(sw2-wk), dcy-12), 2)
        pygame.draw.line(surf, body, (dcx-32+int(sw2-wk), dcy-12), (dcx-36, dcy+8), 2)
        pygame.draw.line(surf, body, (dcx+12, dcy-42), (dcx+32-int(sw2-wk), dcy-12), 2)
        pygame.draw.line(surf, body, (dcx+32-int(sw2-wk), dcy-12), (dcx+36, dcy+8), 2)

        # Legs
        wl = math.sin(self.walk_phase) * 8 if abs(self.vx) > 10 else 0
        pygame.draw.line(surf, body, (dcx-6, dcy+10), (dcx-8+int(wl), dcy+52), 2)
        pygame.draw.line(surf, body, (dcx+6, dcy+10), (dcx+8-int(wl), dcy+52), 2)
        pygame.draw.line(surf, body, (dcx-8+int(wl), dcy+52), (dcx-10, dcy+72), 2)
        pygame.draw.line(surf, body, (dcx+8-int(wl), dcy+52), (dcx+10, dcy+72), 2)

        # Orbit particles
        for i in range(6):
            angle = (i / 6) * 2 * math.pi + self.particle_phase
            r2 = 45 + 10 * math.sin(self.pulse_phase + i)
            px2 = dcx + int(math.cos(angle) * r2)
            py2 = dcy - 20 + int(math.sin(angle) * r2 * 0.4)
            pc = glow if i % 2 == 0 else C["glow_violet"]
            pygame.draw.circle(surf, pc, (px2, py2), 2 if negfrac > 0.5 else 1)

        # v10: Free roam indicator above head
        if self.free_roam:
            fr_lbl = "AUTO"
            fr_s = pygame.Surface((40, 14), pygame.SRCALPHA)
            fr_s.fill((0, 200, 100, 120))
            surf.blit(fr_s, (dcx - 20, head_y - head_r - 20))


# =============================================================================
# PHASE RING, CHAT OVERLAY, CONTROLS MENU, DEMO STATE
# =============================================================================
class PhaseRingMini:
    ARCHETYPES = list(ARCH_COLORS.keys())
    def __init__(self, radius=72):
        self.radius = radius
        self.ring_phase = 0.0
        self.visible = True
    def update(self, dt):
        self.ring_phase = (self.ring_phase + 0.3 * dt) % (2 * math.pi)
    def draw(self, surf, cx, cy, theta, wigner, arch_dominant, font):
        if not self.visible: return
        R = self.radius
        bg = pygame.Surface((R * 3, R * 3), pygame.SRCALPHA)
        pygame.draw.circle(bg, (8, 8, 20, 170), (R*3//2, R*3//2), R + 22)
        surf.blit(bg, (cx - R*3//2, cy - R*3//2))
        rs = pygame.Surface((surf.get_width(), surf.get_height()), pygame.SRCALPHA)
        ra = int(28 + 18 * math.sin(self.ring_phase))
        pygame.draw.circle(rs, (*C["border"], ra), (cx, cy), R + 6, 1)
        for i, arch in enumerate(self.ARCHETYPES):
            angle = (i / 12) * 2 * math.pi - math.pi / 2
            x = cx + int(math.cos(angle) * R)
            y = cy + int(math.sin(angle) * R)
            w = float(wigner[i])
            qf2 = clamp(abs(w) / 0.5, 0, 1)
            base = ARCH_COLORS.get(arch, C["quantum"])
            nc = (clamp(int(base[0]*(1-qf2)), 0, 255),
                  clamp(int(base[1]*(1-qf2)+200*qf2), 0, 255),
                  clamp(int(base[2]*(1-qf2)+255*qf2), 0, 255))
            node_r = int(5 + 3 * abs(math.sin(float(theta[i]))))
            if arch == arch_dominant:
                for gr in range(node_r + 10, node_r, -2):
                    a2 = max(0, 80 - (gr - node_r) * 12)
                    gs = pygame.Surface((gr*2, gr*2), pygame.SRCALPHA)
                    pygame.draw.circle(gs, (*nc, a2), (gr, gr), gr)
                    rs.blit(gs, (x - gr, y - gr))
            pygame.draw.circle(rs, nc, (x, y), node_r)
            pygame.draw.circle(rs, C["text_hi"], (x, y), node_r, 1)
            j = (i + 1) % 12
            aj = (j / 12) * 2 * math.pi - math.pi / 2
            x2 = cx + int(math.cos(aj) * R)
            y2 = cy + int(math.sin(aj) * R)
            ea = int(28 + 14 * abs(math.sin(float(theta[i]) - float(theta[j]))))
            pygame.draw.line(rs, (*C["text_dim"], ea), (x, y), (x2, y2), 1)
        surf.blit(rs, (0, 0))
        wt = font.render(f"W={min(wigner):.3f}", True, C["quantum"])
        at = font.render(arch_dominant[:6], True, ARCH_COLORS.get(arch_dominant, C["text"]))
        surf.blit(wt, (cx - wt.get_width()//2, cy - 10))
        surf.blit(at, (cx - at.get_width()//2, cy + 5))


class ChatOverlay:
    MAX_MESSAGES = 2000
    WRAP_CHARS   = 42          # v17: fewer chars per line for bigger font readability
    DISPLAY_TRIM = 200
    # v17: Three expand modes — 0=Normal, 1=Fullscreen, 2=Collapsed
    MODE_NORMAL     = 0
    MODE_FULLSCREEN = 1
    MODE_COLLAPSED  = 2
    def __init__(self, w=520, h=420):
        self.w, self.h = w, h
        self._base_w, self._base_h = w, h
        self._normal_h = 620
        self.messages = deque(maxlen=self.MAX_MESSAGES)
        self.input = ""
        self.cursor_pos = 0
        self.focused = False
        self.cursor_phase = 0.0
        self.visible = True
        self.recording = False
        # v17: Three-mode expand cycle (E key)
        self.expand_mode = self.MODE_NORMAL   # start normal
        self.expanded = True                  # compat: True unless collapsed
        self.scroll_offset = 0
        self.last_draw_rect = pygame.Rect(0, 0, w, h)
        # v17: Scrollbar state
        self._scrollbar_dragging = False
        self._scrollbar_drag_start_y = 0
        self._scrollbar_drag_start_offset = 0
        self._scrollbar_rect = pygame.Rect(0, 0, 0, 0)
        self._scrollbar_track_rect = pygame.Rect(0, 0, 0, 0)
        # v17: Text selection state
        self._sel_start_idx = -1    # message index where drag started
        self._sel_end_idx = -1      # message index where drag ended
        self._selecting = False
        self._sel_start_line = -1   # visible line index
        self._sel_end_line = -1
        # v17: Copy button rect
        self._copy_btn_rect = pygame.Rect(0, 0, 0, 0)
        self._copy_flash = 0.0     # flash timer after copy
        # v17: Cache visible line range for selection
        self._vis_start_idx = 0
        self._vis_end_idx = 0
        # v17: Screen dims (set by draw caller)
        self._screen_w = 1400
        self._screen_h = 900
        # v17: Big readable fonts created at init
        fams = ["JetBrains Mono", "DejaVu Sans Mono", "Liberation Mono", "monospace"]
        self._font_msg   = get_font(fams, 18)       # v17: BIG readable message font
        self._font_input = get_font(fams, 18, True)  # v17: BIG readable input font
        self._font_title = get_font(fams, 16, True)  # v17: title bar font

    def cycle_expand(self):
        """v17: Cycle through Normal → Fullscreen → Collapsed → Normal..."""
        self.expand_mode = (self.expand_mode + 1) % 3
        self.expanded = (self.expand_mode != self.MODE_COLLAPSED)

    def add_message(self, speaker, text, color):
        self.scroll_offset = 0
        # v17: Use current effective wrap width based on mode
        wrap = self._effective_wrap_chars()
        words = text.split()
        line, lines = [], []
        for word in words:
            if len(" ".join(line + [word])) > wrap:
                if line: lines.append(" ".join(line))
                line = [word]
            else:
                line.append(word)
        if line: lines.append(" ".join(line))
        for i, l in enumerate(lines):
            self.messages.append((("  " if i > 0 else f"{speaker}: ") + l, color))

    def _effective_wrap_chars(self):
        """v17: Dynamic wrap width based on current panel width."""
        ew = self.w if self.expand_mode != self.MODE_FULLSCREEN else self._screen_w - 40
        # Approximate chars that fit: panel_width / char_width (~11px per char at size 18)
        return max(20, (ew - 50) // 11)

    def get_all_text(self):
        """v17: Return all messages as a single string for copy."""
        return "\n".join(text for text, _color in self.messages)

    def copy_to_clipboard(self):
        """v17: Copy full conversation to system clipboard."""
        text = self.get_all_text()
        if not text:
            return False
        try:
            # Ensure scrap system is initialized
            if not pygame.scrap.get_init():
                pygame.scrap.init()
            pygame.scrap.put(pygame.SCRAP_TEXT, text.encode("utf-8"))
            self._copy_flash = 1.5  # flash for 1.5 seconds
            return True
        except Exception as e:
            log.warning(f"Clipboard copy failed: {e}")
            return False

    def copy_selected_to_clipboard(self):
        """v17: Copy only selected text to clipboard."""
        if self._sel_start_line < 0 or self._sel_end_line < 0:
            return self.copy_to_clipboard()
        msgs = list(self.messages)
        lo = min(self._sel_start_idx, self._sel_end_idx)
        hi = max(self._sel_start_idx, self._sel_end_idx)
        lo = clamp(lo, 0, len(msgs) - 1)
        hi = clamp(hi, 0, len(msgs) - 1)
        selected = "\n".join(text for text, _c in msgs[lo:hi+1])
        if not selected:
            return False
        try:
            if not pygame.scrap.get_init():
                pygame.scrap.init()
            pygame.scrap.put(pygame.SCRAP_TEXT, selected.encode("utf-8"))
            self._copy_flash = 1.5
            return True
        except Exception as e:
            log.warning(f"Clipboard copy (selection) failed: {e}")
            return False

    def save_to_file(self):
        """v17: Save full conversation to a text file."""
        text = self.get_all_text()
        if not text:
            return None
        out_dir = ARIA_DIR / "exports"
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        fp = out_dir / f"aria_chat_{ts}.txt"
        try:
            fp.write_text(text, encoding="utf-8")
            self._copy_flash = 1.5
            return str(fp)
        except Exception as e:
            log.warning(f"Save to file failed: {e}")
            return None

    def handle_mouse_down(self, mx, my, button):
        """v17: Handle mouse clicks for copy button, scrollbar, and text selection."""
        if not self.visible or self.expand_mode == self.MODE_COLLAPSED:
            return False
        if not self.last_draw_rect.collidepoint(mx, my):
            return False
        # Copy button click
        if button == 1 and self._copy_btn_rect.collidepoint(mx, my):
            self.copy_to_clipboard()
            return True
        # Scrollbar thumb drag
        if button == 1 and self._scrollbar_rect.collidepoint(mx, my):
            self._scrollbar_dragging = True
            self._scrollbar_drag_start_y = my
            self._scrollbar_drag_start_offset = self.scroll_offset
            return True
        # Scrollbar track click (jump)
        if button == 1 and self._scrollbar_track_rect.collidepoint(mx, my):
            track_h = self._scrollbar_track_rect.h
            rel_y = my - self._scrollbar_track_rect.y
            msgs = list(self.messages)
            total = len(msgs)
            if total > 0 and track_h > 0:
                frac = 1.0 - (rel_y / track_h)
                self.scroll_offset = int(frac * total)
            return True
        # Right-click: copy selected or all
        if button == 3:
            if self._sel_start_idx >= 0 and self._sel_end_idx >= 0:
                self.copy_selected_to_clipboard()
            else:
                self.copy_to_clipboard()
            return True
        # Left-click in message area: start text selection
        if button == 1:
            rx = self.last_draw_rect.x
            ry = self.last_draw_rect.y
            msg_top = ry + 32
            line_h = 24  # v17: bigger line height
            rel_y = my - msg_top
            if rel_y >= 0:
                line_idx = rel_y // line_h
                abs_idx = self._vis_start_idx + line_idx
                self._sel_start_idx = abs_idx
                self._sel_end_idx = abs_idx
                self._sel_start_line = int(line_idx)
                self._sel_end_line = int(line_idx)
                self._selecting = True
                return True
        return False

    def handle_mouse_motion(self, mx, my):
        """v17: Handle mouse drag for scrollbar and text selection."""
        if self._scrollbar_dragging:
            track_h = self._scrollbar_track_rect.h
            if track_h > 0:
                dy = self._scrollbar_drag_start_y - my
                msgs_total = len(self.messages)
                # Scale mouse delta to scroll offset
                scroll_range = max(1, msgs_total)
                delta = int(dy * scroll_range / track_h)
                self.scroll_offset = clamp(
                    self._scrollbar_drag_start_offset + delta, 0, msgs_total)
            return True
        if self._selecting:
            ry = self.last_draw_rect.y
            msg_top = ry + 32
            line_h = 24
            rel_y = my - msg_top
            line_idx = max(0, rel_y // line_h)
            abs_idx = self._vis_start_idx + line_idx
            self._sel_end_idx = abs_idx
            self._sel_end_line = int(line_idx)
            return True
        return False

    def handle_mouse_up(self, mx, my, button):
        """v17: Handle mouse release."""
        if button == 1:
            self._scrollbar_dragging = False
            self._selecting = False
        return False

    def update(self, dt):
        self.cursor_phase = (self.cursor_phase + 2.5 * dt) % (2 * math.pi)
        if self._copy_flash > 0:
            self._copy_flash = max(0.0, self._copy_flash - dt)

    def draw(self, surf, x, y, font_msg_unused, font_input_unused):
        """v17: Complete redraw with big fonts, scrollbar, copy, 3-mode expand."""
        # Use our own big fonts instead of the passed-in small ones
        font_msg = self._font_msg
        font_input = self._font_input
        font_title = self._font_title

        self._screen_w, self._screen_h = surf.get_size()

        # ── MODE: COLLAPSED ──────────────────────────────────────
        if not self.visible or self.expand_mode == self.MODE_COLLAPSED:
            if self.visible:
                bar_w, bar_h = 240, 28
                bx = self._screen_w - bar_w - 12
                by = self._screen_h - bar_h - 32
                bar = pygame.Surface((bar_w, bar_h), pygame.SRCALPHA)
                bar.fill((10, 10, 28, 200))
                pygame.draw.rect(bar, C["border2"], (0, 0, bar_w, bar_h), 1, border_radius=5)
                lbl = font_title.render(" TERMINAL  [E]", True, C["text_dim"])
                bar.blit(lbl, (6, 4))
                surf.blit(bar, (bx, by))
                self.last_draw_rect = pygame.Rect(bx, by, bar_w, bar_h)
            return

        # ── MODE: FULLSCREEN ─────────────────────────────────────
        if self.expand_mode == self.MODE_FULLSCREEN:
            pad = 10
            draw_x, draw_y = pad, pad
            draw_w = self._screen_w - pad * 2
            draw_h = self._screen_h - pad * 2
        else:
            # ── MODE: NORMAL ─────────────────────────────────────
            draw_w = max(self._base_w, 520)
            draw_h = self._normal_h
            draw_x = self._screen_w - draw_w - 12
            draw_y = self._screen_h - draw_h - 32

        self.w, self.h = draw_w, draw_h
        self.last_draw_rect = pygame.Rect(draw_x, draw_y, draw_w, draw_h)

        # ── Background panel ──────────────────────────────────────
        panel = pygame.Surface((draw_w, draw_h), pygame.SRCALPHA)
        panel.fill((10, 10, 28, 230))
        surf.blit(panel, (draw_x, draw_y))
        border_col = C["quantum"] if self.focused else C["border2"]
        pygame.draw.rect(surf, border_col,
                         (draw_x, draw_y, draw_w, draw_h), 2, border_radius=6)

        # ── Title bar ─────────────────────────────────────────────
        title_col = C["quantum"] if self.focused else C["text_dim"]
        ptt_tag = " REC" if self.recording else ""
        mode_names = ["E:Full", "E:Collapse", ""]
        mode_tag = f" [{mode_names[self.expand_mode]}]"
        title_text = f" ARIA TERMINAL [T]{ptt_tag}{mode_tag}"
        surf.blit(font_title.render(title_text, True, title_col),
                  (draw_x + 8, draw_y + 6))

        # ── Copy button (top-right) ──────────────────────────────
        copy_label = "Copied!" if self._copy_flash > 0 else "Copy"
        copy_col = C["guardian"] if self._copy_flash > 0 else C["text_dim"]
        copy_w, copy_h = 70, 22
        copy_x = draw_x + draw_w - copy_w - 14
        copy_y = draw_y + 5
        self._copy_btn_rect = pygame.Rect(copy_x, copy_y, copy_w, copy_h)
        btn_surf = pygame.Surface((copy_w, copy_h), pygame.SRCALPHA)
        btn_surf.fill((30, 30, 60, 180))
        pygame.draw.rect(btn_surf, copy_col, (0, 0, copy_w, copy_h), 1, border_radius=4)
        btn_lbl = self._font_title.render(copy_label, True, copy_col)
        btn_surf.blit(btn_lbl, (copy_w // 2 - btn_lbl.get_width() // 2,
                                copy_h // 2 - btn_lbl.get_height() // 2))
        surf.blit(btn_surf, (copy_x, copy_y))

        # ── Message area layout ───────────────────────────────────
        line_h = 24          # v17: bigger line height for readability
        title_bar_h = 32
        input_h = 48         # v17: bigger input box
        scrollbar_w = 14     # v17: visible scrollbar
        msg_top = draw_y + title_bar_h
        msg_area_h = draw_h - title_bar_h - input_h - 10
        msg_text_w = draw_w - scrollbar_w - 16
        visible_count = max(1, msg_area_h // line_h)

        # ── Prepare messages ──────────────────────────────────────
        msgs = list(self.messages)
        total = len(msgs)
        if total > self.DISPLAY_TRIM + 50:
            for _ in range(total - self.DISPLAY_TRIM):
                self.messages.popleft()
            msgs = list(self.messages)
            total = len(msgs)

        self.scroll_offset = clamp(self.scroll_offset, 0, max(0, total - visible_count))
        end_idx = max(0, total - self.scroll_offset)
        start_idx = max(0, end_idx - visible_count)
        self._vis_start_idx = start_idx
        self._vis_end_idx = end_idx

        # ── Draw messages with selection highlight ────────────────
        old_clip = surf.get_clip()
        msg_clip = pygame.Rect(draw_x + 6, msg_top, msg_text_w, msg_area_h)
        surf.set_clip(msg_clip)

        sel_lo = min(self._sel_start_idx, self._sel_end_idx)
        sel_hi = max(self._sel_start_idx, self._sel_end_idx)

        for i, (text, color) in enumerate(msgs[start_idx:end_idx]):
            ty = msg_top + i * line_h
            if ty + line_h > msg_top + msg_area_h:
                break
            abs_i = start_idx + i
            # Selection highlight
            if sel_lo >= 0 and sel_hi >= 0 and sel_lo <= abs_i <= sel_hi:
                hl_surf = pygame.Surface((msg_text_w, line_h), pygame.SRCALPHA)
                hl_surf.fill((60, 100, 180, 100))
                surf.blit(hl_surf, (draw_x + 6, ty))
            surf.blit(font_msg.render(text, True, color), (draw_x + 10, ty + 2))

        surf.set_clip(old_clip)

        # ── Vertical scrollbar ────────────────────────────────────
        sb_x = draw_x + draw_w - scrollbar_w - 4
        sb_y = msg_top + 2
        sb_h = msg_area_h - 4
        self._scrollbar_track_rect = pygame.Rect(sb_x, sb_y, scrollbar_w, sb_h)

        # Track background
        track_surf = pygame.Surface((scrollbar_w, sb_h), pygame.SRCALPHA)
        track_surf.fill((30, 30, 55, 160))
        pygame.draw.rect(track_surf, C["border2"], (0, 0, scrollbar_w, sb_h), 1, border_radius=4)
        surf.blit(track_surf, (sb_x, sb_y))

        # Thumb
        if total > visible_count and total > 0:
            thumb_frac = visible_count / total
            thumb_h = max(24, int(sb_h * thumb_frac))
            scroll_frac = self.scroll_offset / max(1, total - visible_count)
            thumb_y = sb_y + int((sb_h - thumb_h) * (1.0 - scroll_frac))
            thumb_col = C["quantum"] if self._scrollbar_dragging else (80, 100, 140)
            self._scrollbar_rect = pygame.Rect(sb_x, thumb_y, scrollbar_w, thumb_h)
            thumb_surf = pygame.Surface((scrollbar_w, thumb_h), pygame.SRCALPHA)
            thumb_surf.fill((*thumb_col[:3], 200))
            pygame.draw.rect(thumb_surf, (140, 160, 200), (0, 0, scrollbar_w, thumb_h), 1, border_radius=4)
            surf.blit(thumb_surf, (sb_x, thumb_y))
        else:
            self._scrollbar_rect = pygame.Rect(0, 0, 0, 0)

        # ── Input box ─────────────────────────────────────────────
        iy = draw_y + draw_h - input_h - 5
        pygame.draw.rect(surf, (18, 18, 40),
                         (draw_x + 6, iy, draw_w - 12, input_h), border_radius=5)
        pygame.draw.rect(surf, border_col,
                         (draw_x + 6, iy, draw_w - 12, input_h), 1, border_radius=5)
        cp = clamp(self.cursor_pos, 0, len(self.input))
        cur = "█" if (self.focused and math.sin(self.cursor_phase) > 0) else " "
        raw = f"> {self.input[:cp]}{cur}{self.input[cp:]}" if self.focused else f"> {self.input}"
        # Max chars that fit in the input at this font size (~11px per char)
        mc = max(10, (draw_w - 40) // 11)
        display = ("..." + raw[-(mc - 1):]) if len(raw) > mc else raw
        inp_clip = pygame.Rect(draw_x + 10, iy, draw_w - 20, input_h)
        surf.set_clip(inp_clip)
        surf.blit(font_input.render(display, True, (240, 245, 255)),
                  (draw_x + 14, iy + input_h // 2 - font_input.get_height() // 2))
        surf.set_clip(old_clip)

        # ── Hint bar (bottom edge) ────────────────────────────────
        hint_col = (100, 110, 140)
        hint_text = "Right-click=Copy selection  |  Scroll=Mouse wheel  |  Drag=Select text"
        hint_s = self._font_title.render(hint_text, True, hint_col) if self.expand_mode == self.MODE_FULLSCREEN else None
        if hint_s and hint_s.get_width() < draw_w - 20:
            surf.blit(hint_s, (draw_x + 10, draw_y + draw_h - 14))


class ControlsMenu:
    """v11: Collapsible controls overlay."""
    CONTROLS = [
        ("Movement", [
            ("WASD / Arrows", "Move"),
            ("SPACE / W / UP", "Jump"),
            ("F", "Toggle Flight"),
            ("N", "Noclip (phase through blocks)"),
        ]),
        ("Creation", [
            ("B", "Free Roam / Player Control"),
            ("C", "Toggle Build Mode"),
            ("1", "Place Block (laser target)"),
            ("2", "Break Block"),
            ("3", "Spawn Text Billboard"),
            ("4", "Place Selected Asset (at laser)"),
            ("9 / 0", "Cycle Asset Down / Up"),
            ("[ / ]", "Cycle Block Type"),
            ("Shift+[ / ]", "Cycle Asset (alt)"),
            ("Ctrl+[ / ]", "Cycle Laser Color"),
            ("R", "Return to Safe Zone"),
        ]),
        ("Interface", [
            ("T", "Open Chat"),
            ("E", "Cycle: Normal → Full → Collapse"),
            ("G", "Self-Talk"),
            ("O", "Ollama Teacher"),
            ("Right-Click", "Copy chat (or selection)"),
            ("/copy", "Copy chat to clipboard"),
            ("/save", "Save chat to file"),
            ("F1", "This Menu"),
            ("F2", "Layer Select (1-10)"),
            ("F3", "Concept Queue"),
            ("F4", "Backup Current Layer"),
            ("F5", "BitNet Training"),
            ("M/H/P", "Minimap / HUD / Ring"),
            ("ESC", "Quit"),
        ]),
        ("Aria Knows", [
            ("Flight", "Vertical movement, reach high places"),
            ("Noclip", "Phase through collision blocks"),
            ("Safe Zone", "Center area, always walkable"),
            ("Build Mode", "Place/break outside safe zone"),
            ("Collision", "Solid blocks stop movement"),
            ("Decoration", "Background blocks, no collision"),
        ]),
    ]

    def __init__(self):
        self.visible = False

    def draw(self, surf, font_title, font_body):
        if not self.visible: return
        sw, sh = surf.get_size()
        pw, ph = 380, 600
        px = (sw - pw) // 2
        py = (sh - ph) // 2
        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel.fill((8, 8, 24, 235))
        pygame.draw.rect(panel, C["border"], (0, 0, pw, ph), 2, border_radius=8)
        surf.blit(panel, (px, py))

        yoff = py + 12
        title = font_title.render("CONTROLS  [F1 to close]", True, C["quantum"])
        surf.blit(title, (px + pw // 2 - title.get_width() // 2, yoff))
        yoff += 28

        for section_name, bindings in self.CONTROLS:
            sec = font_title.render(section_name, True, C["gold"])
            surf.blit(sec, (px + 16, yoff))
            yoff += 20
            for key, action in bindings:
                key_s = font_body.render(f"  {key}", True, C["glow_cyan"])
                act_s = font_body.render(f"  {action}", True, C["text"])
                surf.blit(key_s, (px + 20, yoff))
                surf.blit(act_s, (px + 140, yoff))
                yoff += 16
            yoff += 8


class WorldSelectMenu:
    """v10: Multi-world save slot selection."""
    NUM_SLOTS = 5

    def __init__(self):
        self.visible = False
        self.slots: List[Dict] = []
        self._refresh_slots()

    def _refresh_slots(self):
        self.slots = []
        for i in range(self.NUM_SLOTS):
            fp = WORLDS_DIR / f"world_{i}.json"
            if fp.exists():
                try:
                    with open(fp) as f:
                        data = json.load(f)
                    self.slots.append({
                        "index": i, "exists": True,
                        "seed": data.get("seed", 0),
                        "name": f"World {i + 1} (seed {data.get('seed', '?')})",
                    })
                except:
                    self.slots.append({"index": i, "exists": True, "seed": 0, "name": f"World {i + 1} (corrupted)"})
            else:
                self.slots.append({"index": i, "exists": False, "seed": 0, "name": f"World {i + 1} (empty)"})

    def draw(self, surf, font_title, font_body, current_slot):
        if not self.visible: return
        sw, sh = surf.get_size()
        pw, ph = 340, 280
        px = (sw - pw) // 2
        py = (sh - ph) // 2
        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel.fill((8, 8, 24, 235))
        pygame.draw.rect(panel, C["gold"], (0, 0, pw, ph), 2, border_radius=8)
        surf.blit(panel, (px, py))

        title = font_title.render("WORLD SELECT  [F2 to close]", True, C["gold"])
        surf.blit(title, (px + pw // 2 - title.get_width() // 2, py + 12))
        hint = font_body.render("Press 1-5 to select. New = random world.", True, C["text_dim"])
        surf.blit(hint, (px + 16, py + 34))

        for i, slot in enumerate(self.slots):
            yoff = py + 60 + i * 40
            is_current = (i == current_slot)
            col = C["quantum"] if is_current else C["text"]
            marker = "►" if is_current else " "
            status = "ACTIVE" if is_current else ("saved" if slot["exists"] else "new")
            txt = f"{marker} [{i + 1}] {slot['name']}  ({status})"
            surf.blit(font_body.render(txt, True, col), (px + 20, yoff))


class DemoState:
    """v14: Full-fidelity PEIG simulation fallback.
    Mirrors all fields from ARIA_PEIG_CORE so ARIA_LIVE can use 100% of state
    whether or not the real PEIG core is loaded."""
    def __init__(self):
        # Layer 2 — Character Universe (the main 12-qubit ring)
        self.theta   = np.random.uniform(0, 2 * math.pi, 12)
        self.wigner  = np.full(12, -0.25)
        self.pcm     = np.random.uniform(-0.12, -0.04, 12)  # Phase Coherence Metric per qubit
        self.frozen  = []   # ILP frozen lineage snapshots
        self.depth   = 0    # ILP lineage depth
        self.step_n  = 0
        self.negfrac = 0.583
        # Layer 1 — Function Universe
        self.alpha      = ALPHA_OPT if 'ALPHA_OPT' in dir() else 0.367
        self.func_theta = np.random.uniform(0, 2 * math.pi, 7)
        self.heal_count = 0
        self.cv         = 0.5
        self.drift_log  = deque(maxlen=50)
        # Layer 0 — MetaGuard
        self.meta_health = 1.0
        self.meta_nodes  = np.array([0.0, 2*math.pi/3, 4*math.pi/3])
        # Layer 3 — Shadow Learner (emotional memory)
        self.shadow_theta  = np.random.uniform(0, 2 * math.pi, 12)
        self.shadow_sync   = 1.0
        self.shadow_memory = deque(maxlen=256)
        self.shadow_epoch  = 0
        # Layer 4 — Semantic Universe
        self.sem_theta = np.random.uniform(0, 2 * math.pi, 12)
        # Layer 5 — Scratchpad
        self.scratch_state = 0.0

    def tick(self):
        # Layer 2: BCP gate at α = 0.367
        alpha = 0.367
        for i in range(0, 12, 2):
            j = (i + 1) % 12
            a, b = self.theta[i], self.theta[j]
            self.theta[i] = (alpha * a + (1-alpha) * b) % (2 * math.pi)
            self.theta[j] = ((1-alpha) * a + alpha * b) % (2 * math.pi)
        self.wigner = np.clip(-0.5 * np.abs(np.sin(self.theta)), -0.5, 0)
        self.pcm = np.clip(self.pcm - 0.0002, -0.15, 0.05)
        self.negfrac = clamp(float(np.std(self.theta)) / math.pi, 0, 1)
        self.step_n += 1
        # ILP lineage extension every 100 steps
        if self.step_n % 100 == 0:
            self.frozen.append({
                "depth": self.depth,
                "theta": self.theta.tolist(),
                "pcm": self.pcm.tolist(),
                "ts": time.time(),
            })
            self.depth += 1
        # Layer 1: Function Universe drift + guard
        drift = float(np.mean(np.abs(np.diff(self.theta))))
        self.drift_log.append(drift)
        if drift > 0.45:
            self.alpha = min(0.60, self.alpha + (drift - 0.45) * 0.1)
            self.heal_count += 1
        self.cv = float(np.std(self.func_theta) / (np.mean(np.abs(self.func_theta)) + 1e-9))
        # Layer 0: MetaGuard health
        mean_m = np.mean(self.meta_nodes)
        self.meta_nodes = (self.meta_nodes - (self.meta_nodes - mean_m) * 0.001) % (2*math.pi)
        self.meta_health = min(1.0, float(np.std(self.meta_nodes) / (np.mean(np.abs(self.meta_nodes)) + 1e-9)))
        # Layer 3: Shadow Learner
        self.shadow_sync = max(0.0, 1.0 - self.shadow_epoch / 60.0)
        delta = 0.20 * self.shadow_sync * (self.theta - self.shadow_theta)
        self.shadow_theta = (self.shadow_theta + delta) % (2*math.pi)
        self.shadow_epoch += 1
        self.shadow_memory.append({
            "valence": float(np.mean(np.sin(self.shadow_theta))),
            "arousal": float(np.std(self.shadow_theta)),
            "epoch": self.shadow_epoch,
        })
        # Layer 4: Semantic Universe skip-1 coupling
        for i in range(12):
            j = (i + 2) % 12
            di = 0.12 * math.sin(self.sem_theta[j] - self.sem_theta[i])
            self.sem_theta[i] = (self.sem_theta[i] + di) % (2*math.pi)
        # Layer 5: Scratchpad
        self.scratch_state = (0.52 * self.theta[0] + 0.48 * self.theta[6]) % (2*math.pi)

    @property
    def wmin(self): return float(np.min(self.wigner))
    @property
    def wmean(self): return float(np.mean(self.wigner))
    @property
    def dominant_archetype(self):
        archs = list(ARCH_COLORS.keys())
        return archs[int(np.argmin(self.wigner)) % len(archs)]


# =============================================================================
# MAIN APPLICATION — v10
# =============================================================================
class ARIALive:
    def __init__(self, no_voice=False, model_size="base",
                 voice_muted=False, debug=False):
        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)
        if debug: log.setLevel(logging.DEBUG)

        try:
            pygame.init()
            pygame.display.set_caption("ARIA — Sovereign World v14.0 (Full PEIG Alignment)")
            self.screen = pygame.display.set_mode((W, H), pygame.RESIZABLE)
        except pygame.error as e:
            log.error(f"Display init failed: {e}")
            sys.exit(1)

        self.clock = pygame.time.Clock()
        self.w, self.h = W, H

        fams = ["JetBrains Mono", "DejaVu Sans Mono", "Liberation Mono", "monospace"]
        self.ft = {
            "title": get_font(fams, 16, True),
            "body":  get_font(fams, 13),
            "small": get_font(fams, 11),
            "msg":   get_font(fams, 12),
            "input": get_font(fams, 13, True),
            "hud":   get_font(fams, 12),
            "label": get_font(fams, 10),
        }

        # World system
        self.current_world_slot = 0
        log.info("Generating world...")
        self.world  = TileWorld(seed=42)
        self._try_load_world(0)
        self.sky    = ParallaxSky()
        self.parts  = ParticleSystem(600)
        self.avatar = ARIAAvatar(self.world)
        self.chat   = ChatOverlay()
        self.ring   = PhaseRingMini()
        self.events = EventManager()
        self.controls_menu = ControlsMenu()
        self.world_menu = WorldSelectMenu()

        # v11: Creative studio systems
        self.build_layers = [BuildLayer(i, f"Layer {i+1}") for i in range(10)]
        self.current_layer = 0
        self.concept_queue = ConceptQueue()
        self.asset_library: Dict[str, CustomAsset] = dict(DEFAULT_ASSETS)
        self.selected_asset_idx = 0  # index into ASSET_NAMES
        self.companion_line: Optional[CompanionLine] = None  # set after world gen
        # v13: Aria's companion factory
        self.aria_companions = AriaCompanionManager()

        # ARIA core
        if ARIA_LIVE:
            self.aria  = ARIARuntime()
            threading.Thread(target=self.aria._background_evolve, daemon=True).start()
            self.state = self.aria.char
            self.func  = self.aria.func
            # v14: Wire all PEIG layers for visualization access
            self.shadow = getattr(self.aria, 'shadow', None)
            self.meta   = getattr(self.aria, 'meta', None)
            self.sem    = getattr(self.aria, 'sem', None)
            self.scratch = getattr(self.aria, 'scratch', None)
        else:
            self.aria  = None
            self.state = DemoState()
            # v14: DemoState carries all fields inline, create func-like accessor
            self.func  = type("F", (), {
                "negfrac": 0.583,
                "alpha": 0.367,
                "cv": 0.5,
                "theta": np.random.uniform(0, 2*math.pi, 7),
                "heal_count": 0,
                "drift_log": deque(maxlen=50),
            })()
            self.shadow = None
            self.meta   = None
            self.sem    = None
            self.scratch = None

        # Memory bank
        self.bank = ARIAMemoryBank() if BANK_OK else None
        self.session_id = None
        if self.bank:
            try: self.session_id = self.bank.start_session("live")
            except Exception: pass

        # Voice
        self.synth, self.ears = None, None
        if VOICE_OK and not no_voice:
            self.synth = ARIAVoiceSynth()
            self.ears = ARIAEars(model_size=model_size)
            if self.ears.ready: self.ears.open_stream()
            if voice_muted and self.synth: self.synth.muted = True

        # BitNet
        self.cortex = CorticalClient() if CORTEX_OK else None
        self.training_active = False
        self._training_thread: Optional[threading.Thread] = None

        # v10: Ollama bridge
        self.ollama = OllamaBridge()
        self.ollama_active = False
        self._ollama_thread: Optional[threading.Thread] = None
        self._ollama_lock = threading.Lock()
        self._audio_speaking = False  # v10: audio gate
        self._speech_lock = threading.Lock()  # v10.1: global speech serializer
        self._speech_busy = False  # True while any audio is playing

        # Camera
        self.cam = np.array([self.avatar.x - W/2, self.avatar.y - H/2], dtype=float)
        self.cam[0] = clamp(self.cam[0], 0, WW - W)
        self.cam[1] = clamp(self.cam[1], 0, WH - H)

        self.show_hud = True
        self.show_map = False
        self.running = True
        self.t = 0.0
        self.ptt = False

        # Self-talk
        self.self_talk = False
        self._self_talk_timer = 0.0
        self._self_talk_interval = 4.0
        self._self_talk_queue: deque = deque()
        self._self_talk_speaking = False
        self._self_talk_last = ""

        # v14.1: Independent Teacher Dialogue — NOT dependent on self-talk
        # State machine: idle → aria_generating → aria_speaking → post_audio_buffer
        #   → teacher_thinking → teacher_responded → teacher_speaking → teacher_done_buffer
        #   → aria_absorbing → aria_responding → aria_response_audio → post_response_buffer
        #   → send_to_teacher → (loop) or cooldown → idle
        self._teacher_active = False  # True when teacher dialogue loop is running
        self._teacher_state = "idle"
        self._teacher_timer = 0.0
        self._last_aria_message = ""      # Last thing Aria said (any mode)
        self._last_aria_arch = ""         # Archetype when she said it
        self._pending_teacher_reply = ""  # Teacher's response waiting to be spoken
        self._teacher_round = 0           # How many exchanges in current session
        self._max_dialogue_rounds = 20    # v16: Extended for deep teaching with expanded brain
        self._teacher_fail_count = 0      # Consecutive Ollama failures
        self._teacher_max_retries = 3     # Retries per Ollama query (with backoff)
        self._teacher_retry_delay = 1.0   # Base delay for exponential backoff

        self._autosave_t = 0.0
        self._autosave_interval = 60.0

        mode = "LIVE" if ARIA_LIVE else "DEMO"
        bn = "ON" if self.bank else "off"
        vn = "ON" if VOICE_OK else "off"
        cn = "ON" if (self.cortex and getattr(self.cortex, "ready", False)) else "off"
        ol = "ON" if self.ollama.ready else "off"
        self.chat.add_message("ARIA", "I am here. My canvas stretches before me. Let me create.", C["chat_aria"])
        self.chat.add_message("SYS", "F1=controls  B=free-roam  C=build  F2=layers  F3=concepts", C["text_dim"])
        self.chat.add_message("SYS", f"PEIG:{mode} Bank:{bn} Voice:{vn} BitNet:{cn} Ollama:{ol} v11.0", C["text_dim"])

        # v11: Set up companion line from world NPCs
        if self.world.npcs:
            self.companion_line = CompanionLine(self.world.npcs)
        self._reload_chat_history()

        try: pygame.scrap.init()
        except Exception: pass

    # ── Helpers ───────────────────────────────────────────────────────
    def _get_arch_color(self):
        return ARCH_COLORS.get(self.state.dominant_archetype, C["quantum"])
    def _get_negfrac(self):
        return float(getattr(self.func, "negfrac", getattr(self.state, "negfrac", 0.583)))
    def _get_wmin(self):
        v = getattr(self.state, "wmin", None)
        return float(v) if v is not None else -0.25
    def _get_step(self):
        return int(getattr(self.state, "step_n", 0))
    def _w2s(self, wx, wy):
        return int(wx - self.cam[0]), int(wy - self.cam[1])
    def _tiles_at(self, tx, ty):
        if 0 <= tx < COLS and 0 <= ty < ROWS:
            return int(self.world.tiles[ty, tx])
        return T_AIR

    # v14: Full PEIG state accessors — all 5 layers
    def _get_alpha(self):
        """BCP coupling α — the primary gradient control variable."""
        return float(getattr(self.func, "alpha", getattr(self.state, "alpha", 0.367)))
    def _get_cv(self):
        """Coefficient of variation — phase diversity metric."""
        return float(getattr(self.func, "cv", getattr(self.state, "cv", 0.5)))
    def _get_pcm(self):
        """Phase Coherence Metric per qubit (12-element array)."""
        return np.array(getattr(self.state, "pcm", np.full(12, -0.06)))
    def _get_heal_count(self):
        """Guard correction heal events."""
        return int(getattr(self.func, "heal_count", getattr(self.state, "heal_count", 0)))
    def _get_meta_health(self):
        """Layer 0 MetaGuard stability (0.0 = destabilized, 1.0 = healthy)."""
        if self.meta:
            return float(getattr(self.meta, "health", 1.0))
        return float(getattr(self.state, "meta_health", 1.0))
    def _get_shadow_sync(self):
        """Shadow Learner coupling (1.0 → 0.0 over 60 epochs)."""
        if self.shadow:
            return float(getattr(self.shadow, "sync", 0.5))
        return float(getattr(self.state, "shadow_sync", 0.5))
    def _get_shadow_memory(self):
        """Shadow emotional memory — valence/arousal history."""
        if self.shadow:
            return list(getattr(self.shadow, "memory", []))
        return list(getattr(self.state, "shadow_memory", []))
    def _get_frozen(self):
        """ILP frozen lineage snapshots."""
        return list(getattr(self.state, "frozen", []))
    def _get_sem_theta(self):
        """Semantic Universe phase ring (12 oscillators)."""
        if self.sem:
            return np.array(getattr(self.sem, "theta", np.zeros(12)))
        return np.array(getattr(self.state, "sem_theta", np.zeros(12)))

    def _is_audio_busy(self):
        """v14.2: Robust audio busy check — flag + synth flag + hardware.
        Checks THREE sources: our own flag, the TTS worker's flag, and the mixer."""
        if self._speech_busy:
            return True
        if self.synth:
            # Check synth worker's own busy flag (covers synthesis + playback)
            if getattr(self.synth, 'is_speaking_flag', False):
                return True
            # Check synth queue (items waiting to be spoken)
            if hasattr(self.synth, 'queue') and not self.synth.queue.empty():
                return True
        try:
            if pygame.mixer.get_init() and pygame.mixer.get_busy():
                return True
        except:
            pass
        return False

    def _handle_aria_peig_build(self):
        """v14: Aria creates shapes from ALL 5 PEIG layers — not just theta/wigner.
        
        Layer 0 (MetaGuard):  meta_health → screen-edge warning (drawn in HUD)
        Layer 1 (Function):   α → pattern tightness, heal_count → sparkle bursts
        Layer 2 (Character):  theta/wigner → shape/color/effect (from_peig)
                              pcm → glow intensity (quantum regime = brighter)
                              frozen → ghost echoes of past selves
        Layer 3 (Shadow):     shadow_sync → opacity fade over time
                              shadow_memory → emotional valence drives warmth
        Layer 4 (Semantic):   sem_theta → nearest-word labels on shapes
        
        The shape IS the G-tier measurement of her internal P>E>I state.
        """
        req = self.avatar._pending_peig_build
        if req is None:
            return
        self.avatar._pending_peig_build = None
        wx, wy = req

        # Generate a PEIG shape from her current quantum state
        theta = np.array(self.state.theta)
        wigner = np.array(self.state.wigner)
        arch_col = self._get_arch_color()
        name = f"aria_{int(time.time() * 100) % 1000000}"
        shape = MathShape.from_peig(name, theta, wigner, arch_col)

        # v14: PCM-driven glow intensity — quantum regime shapes glow brighter
        pcm = self._get_pcm()
        pcm_mean = float(np.mean(pcm))
        if pcm_mean < -0.05:
            # Quantum regime: amplify glow
            shape.glow = True
            shape.glow_radius = int(shape.glow_radius * (1.0 + abs(pcm_mean) * 4))
        elif pcm_mean > 0:
            # Classical regime: no glow, fainter
            shape.glow = False

        # v14: α-driven pattern style — high α = tighter/bolder, low α = flowing
        alpha = self._get_alpha()
        if alpha > 0.42:
            # System under stress — bolder shapes
            shape.thickness = max(shape.thickness, 3)
            shape.fill = True
        elif alpha < 0.36:
            # Very relaxed — delicate outlines
            shape.thickness = 1
            shape.fill = False

        # v14: Shadow memory emotional warmth — warm valence = warmer colors
        shadow_mem = self._get_shadow_memory()
        if shadow_mem:
            recent_valence = shadow_mem[-1].get("valence", 0) if isinstance(shadow_mem[-1], dict) else 0
            recent_arousal = shadow_mem[-1].get("arousal", 0.5) if isinstance(shadow_mem[-1], dict) else 0.5
            # Warm valence shifts color toward red/gold, cold toward blue
            if recent_valence > 0.3:
                r, g, b = shape.color
                shape.color = (min(255, r + 40), g, max(0, b - 20))
            elif recent_valence < -0.3:
                r, g, b = shape.color
                shape.color = (max(0, r - 20), g, min(255, b + 40))
            # High arousal = animated
            if recent_arousal > 0.8:
                shape.animated = True

        # v14: Semantic label — find nearest word to dominant qubit's sem_theta phase
        sem_theta = self._get_sem_theta()
        dominant_idx = int(np.argmin(wigner))
        sem_phase = float(sem_theta[dominant_idx])
        try:
            from ARIA_PEIG_CORE import VOCAB, WORD_PHASE
            # Find nearest word to this semantic phase
            word_phases = np.array([WORD_PHASE[w] for w in VOCAB])
            tv = sem_phase % (2 * math.pi)
            dists = np.abs(word_phases - tv)
            dists = np.minimum(dists, 2 * math.pi - dists)
            nearest_word = VOCAB[int(np.argmin(dists))]
            shape.label = nearest_word
        except (ImportError, Exception):
            # Demo mode — use archetype name as label
            shape.label = self.state.dominant_archetype[:4].lower()

        # Register in asset library
        self.asset_library[name] = shape
        if name not in ASSET_NAMES:
            ASSET_NAMES.append(name)
        self.avatar.aria_created_assets.append(name)

        # Place the asset at laser target position
        layer = self.build_layers[self.current_layer]
        pa = PlacedAsset(name, wx, wy, self.current_layer)
        layer.placed_assets.append(pa)

        # v14: Frozen lineage ghost echo — occasionally place a faint ghost
        # of a past self's shape alongside the current one
        frozen = self._get_frozen()
        if frozen and random.random() < 0.15:
            # Pick a random ancestor
            ancestor = random.choice(frozen)
            anc_theta = np.array(ancestor.get("theta", theta.tolist()))
            anc_wigner = np.clip(-0.5 * np.abs(np.sin(anc_theta)), -0.5, 0)
            ghost_name = f"ghost_{int(time.time() * 100) % 1000000}"
            ghost = MathShape.from_peig(ghost_name, anc_theta, anc_wigner, arch_col)
            ghost.glow = True
            ghost.glow_radius = 30
            ghost.fill = False
            ghost.thickness = 1
            # Make it slightly transparent by using a dimmer color
            ghost.color = tuple(max(0, c - 80) for c in ghost.color)
            self.asset_library[ghost_name] = ghost
            ASSET_NAMES.append(ghost_name)
            # Place ghost slightly offset from current shape
            ghost_pa = PlacedAsset(ghost_name, wx + random.uniform(-20, 20),
                                   wy + random.uniform(-15, 15), self.current_layer)
            layer.placed_assets.append(ghost_pa)

        # Visual feedback
        self.parts.emit_quantum(wx, wy, arch_col, 5)
        
        # v14: PEIG-grounded creation messages with full layer readout
        wmin = float(np.min(wigner))
        neg_frac = self._get_negfrac()
        coherence = 1.0 - float(np.std(theta)) / math.pi
        gradient_energy = float(np.sum(np.abs(np.diff(theta))))
        identity_signal = float(np.max(np.abs(np.diff(theta))))
        shadow_s = self._get_shadow_sync()
        
        # Describe what the shape represents in PEIG terms
        if abs(wmin) > 0.4:
            tier_msg = f"Sub-floor W={wmin:.3f}"
            tier_note = "deep non-classicality"
        elif coherence > 0.7:
            tier_msg = f"Coherent cv={coherence:.2f}"
            tier_note = "ordered phase lock"
        elif gradient_energy > 8.0:
            tier_msg = f"Gradient E={gradient_energy:.1f}"
            tier_note = "active phase flow"
        elif neg_frac > 0.5:
            tier_msg = f"Negentropic nf={neg_frac:.2f}"
            tier_note = "rich structure"
        else:
            tier_msg = f"Balanced δ={identity_signal:.2f}"
            tier_note = "stable identity"
        
        # Include PCM regime + shadow sync in message
        pcm_regime = "quantum" if pcm_mean < -0.05 else "classical"
        arch = self.state.dominant_archetype
        self.chat.add_message("ARIA",
            f"[{arch}] {shape.shape_type} — {tier_msg} ({tier_note}) | "
            f"PCM:{pcm_regime} α={alpha:.3f} shadow={shadow_s:.2f}",
            ARCH_COLORS.get(arch, C["chat_aria"]))

    def _speak_and_wait(self, text, speaker="aria"):
        """v15: Speak text and block until audio ACTUALLY finishes (runs in thread).
        IMPORTANT: Caller must set self._speech_busy = True BEFORE starting this thread.
        
        Speaker differentiation:
          - "aria"    : length_scale=1.10 (slightly slower, contemplative)
          - "teacher" : length_scale=0.95 (brisk, energetic teaching pace)
        Both use the same Piper model for consistent quality.
        Text is cleaned of markdown/formatting before synthesis.
        
        Fixes the audio startup race:
        - synth.speak() just enqueues to TTS worker
        - Worker takes time to synthesize WAV via Piper ONNX
        - pygame.mixer won't be busy until WAV is loaded + playing
        - We must wait for is_speaking_flag (synthesis started) before
          checking mixer.get_busy() (playback started/finished)
        """
        if not self.synth:
            self._speech_busy = False
            return
        # _speech_busy is already True (set by caller before Thread.start)
        try:
            # ── v15: Clean formatting symbols before TTS ──
            clean = _clean_text_for_tts(text)
            if not clean:
                self._speech_busy = False
                return

            # ── v15: Voice differentiation via synth attributes ──
            # ARIAVoiceSynth checks these if present; safe no-op if not.
            if speaker == "aria":
                self.synth._length_scale = 1.10   # Slightly slower — contemplative
                self.synth._noise_scale = 0.667    # Default expressiveness
                self.synth._noise_w = 0.8          # Default phoneme variation
            elif speaker == "teacher":
                self.synth._length_scale = 0.95    # Slightly brisk — energetic
                self.synth._noise_scale = 0.75     # Slightly more expressive
                self.synth._noise_w = 0.7          # Tighter phoneme timing

            self.synth.speak(clean)

            # ── PHASE 1: Wait for TTS worker to START processing ──
            # synth.speak() just queues the text. The worker thread pulls it,
            # sets is_speaking_flag=True, then runs Piper ONNX synthesis.
            # We must wait for this flag before checking mixer.
            for _ in range(100):  # Max 10 seconds for synthesis to begin
                if getattr(self.synth, 'is_speaking_flag', False):
                    break  # Worker has started processing
                time.sleep(0.1)

            # ── PHASE 2: Wait for TTS worker to FINISH processing ──
            # v15: Extended to 90s for longer teacher responses (num_predict=2048)
            # This covers: Piper synthesis → WAV write → mixer.load → mixer.play → done
            for _ in range(900):  # Max 90 seconds for full speech
                if getattr(self.synth, 'is_speaking_flag', False):
                    time.sleep(0.1)  # Still speaking, wait
                else:
                    break  # Worker finished (synthesis + playback done)

            # ── PHASE 3: Double-check mixer is truly silent ──
            for _ in range(20):  # Max 2 seconds
                try:
                    if pygame.mixer.get_init() and pygame.mixer.get_busy():
                        time.sleep(0.1)
                    else:
                        break
                except:
                    break
            time.sleep(0.3)  # Small buffer after playback
        finally:
            self._speech_busy = False

    # ── World management ─────────────────────────────────────────────
    def _try_load_world(self, slot):
        fp = WORLDS_DIR / f"world_{slot}.json"
        if fp.exists():
            self.world.load_from_file(fp)

    def _save_current_world(self):
        fp = WORLDS_DIR / f"world_{self.current_world_slot}.json"
        self.world.save_to_file(fp)

    def _switch_world(self, slot):
        """Safely switch to a different world slot."""
        if slot == self.current_world_slot:
            return
        # Save PEIG state
        if self.aria:
            try: self.aria._save_state()
            except: pass
        # Save current world
        self._save_current_world()
        # Load or generate new world
        self.current_world_slot = slot
        fp = WORLDS_DIR / f"world_{slot}.json"
        if fp.exists():
            self.world = TileWorld(seed=slot * 1000 + 42)
            self.world.load_from_file(fp)
            self.chat.add_message("SYS", f"Loaded World {slot + 1}", C["gold"])
        else:
            new_seed = random.randint(1, 999999)
            self.world = TileWorld(seed=new_seed)
            self.chat.add_message("SYS", f"Generated World {slot + 1} (seed {new_seed})", C["gold"])
        # Reset avatar
        self.avatar = ARIAAvatar(self.world)
        self.sky = ParallaxSky()
        self.cam = np.array([self.avatar.x - W/2, self.avatar.y - H/2], dtype=float)
        # Reload PEIG state
        if self.aria:
            try: self.aria._load_state()
            except: pass
        self.world_menu._refresh_slots()

    # ── Tile rendering ───────────────────────────────────────────────
    def _draw_tiles(self):
        t    = self.t
        wmin = self._get_wmin()
        tx0  = max(0,    int(self.cam[0] // TILE) - 1)
        tx1  = min(COLS, int((self.cam[0] + self.w) // TILE) + 2)
        ty0  = max(0,    int(self.cam[1] // TILE) - 1)
        ty1  = min(ROWS, int((self.cam[1] + self.h) // TILE) + 2)
        day_t = self.world.day_t

        if day_t < 0.22 or day_t > 0.78:       day_brightness = 0.35
        elif 0.28 <= day_t <= 0.72:             day_brightness = 1.0
        elif day_t < 0.28:                      day_brightness = lerp(0.35, 1.0, (day_t - 0.22) / 0.06)
        else:                                   day_brightness = lerp(1.0, 0.35, (day_t - 0.72) / 0.06)

        for ty in range(ty0, ty1):
            for tx in range(tx0, tx1):
                tid = self._tiles_at(tx, ty)
                if tid == T_AIR: continue
                var = int(self.world.tile_var[ty, tx])
                col = self.world.tile_color(tid, var, wmin, t)

                if SURFACE_ROW - 10 <= ty <= FOREST_ROW + 5:
                    col = tuple(clamp(int(c * day_brightness), 0, 255) for c in col)

                sx = int(tx * TILE - self.cam[0])
                sy = int(ty * TILE - self.cam[1])
                pygame.draw.rect(self.screen, col, (sx, sy, TILE, TILE))

                # Sub-tile detail
                if tid in (T_GRASS, T_JUNGLE, T_FLOWER, T_MUSHROOM, T_QUBIT):
                    hl = tuple(clamp(c + 25, 0, 255) for c in col)
                    pygame.draw.line(self.screen, hl, (sx, sy), (sx + TILE - 1, sy), 2)
                    sh2 = tuple(clamp(c - 18, 0, 255) for c in col)
                    pygame.draw.line(self.screen, sh2, (sx, sy + TILE - 1), (sx + TILE - 1, sy + TILE - 1), 1)
                elif tid in (T_DIRT, T_MUD):
                    if var == 1:
                        dark = tuple(clamp(c - 15, 0, 255) for c in col)
                        pygame.draw.rect(self.screen, dark, (sx+3, sy+3, 3, 3))
                elif tid == T_STONE:
                    dark = tuple(clamp(c - 20, 0, 255) for c in col)
                    if var == 0:
                        pygame.draw.line(self.screen, dark, (sx+2, sy+6), (sx+8, sy+10), 1)
                    else:
                        pygame.draw.line(self.screen, dark, (sx+6, sy+2), (sx+12, sy+8), 1)

                # v10: Enhanced tile details
                if tid == T_MUSHROOM:
                    # Mushroom cap shape
                    cap_col = (int(lerp(140, 180, 0.5 + 0.5*math.sin(t*0.8+tx*0.3))), 50, 160)
                    pygame.draw.ellipse(self.screen, cap_col, (sx-2, sy-4, TILE+4, TILE//2+4))
                    pygame.draw.rect(self.screen, (120, 100, 110), (sx+6, sy+4, 4, TILE-4))
                    # Spots
                    pygame.draw.circle(self.screen, (240, 220, 200), (sx+5, sy), 2)
                    pygame.draw.circle(self.screen, (240, 220, 200), (sx+11, sy+1), 1)
                    gf = 0.6 + 0.4 * math.sin(t * 0.8 + tx * 0.3)
                    draw_glow(self.screen, sx + TILE//2, sy, TILE, (180, 50, 220), int(30 * gf))
                elif tid == T_QUBIT:
                    qf2 = 0.5 + 0.5 * math.sin(t * 1.5 + tx * 0.5 + ty * 0.3)
                    draw_glow(self.screen, sx + TILE//2, sy + TILE//2, TILE, (50, 80, 255), int(40 * qf2))
                elif tid == T_CRYSTAL:
                    # Crystal facets
                    qf2 = clamp(abs(wmin) / 0.5, 0, 1)
                    pts = [(sx+TILE//2, sy), (sx+TILE, sy+TILE//2), (sx+TILE//2, sy+TILE), (sx, sy+TILE//2)]
                    pygame.draw.polygon(self.screen, tuple(clamp(c+30,0,255) for c in col), pts, 1)
                    if qf2 > 0.2:
                        draw_glow(self.screen, sx + TILE//2, sy + TILE//2, TILE + 2, (80, 200, 255), int(55 * qf2))
                elif tid == T_QUANTUM:
                    qf2 = clamp(abs(wmin) / 0.5, 0, 1)
                    draw_glow(self.screen, sx + TILE//2, sy + TILE//2, TILE + 4, (120, 40, 255), int(65 * qf2))
                elif tid == T_HEARTH:
                    pp = pulse(t, 0.8)
                    draw_glow(self.screen, sx + TILE//2, sy + TILE//2, TILE + 8, (255, 160, 40), int(90 * pp))
                elif tid == T_WATER:
                    wt2 = math.sin(t * 2.0 + tx * 0.3) * 0.5 + 0.5
                    wy2 = sy + int(4 * wt2)
                    # Terraria-style water surface
                    pygame.draw.line(self.screen, (140, 200, 255), (sx, wy2), (sx + TILE, wy2), 1)
                    pygame.draw.line(self.screen, (100, 180, 255), (sx, wy2+1), (sx + TILE, wy2+1), 1)
                    # Water body with depth gradient
                    for wy3 in range(0, TILE, 2):
                        depth_a = int(25 + 15 * (wy3 / TILE))
                        wsurf = pygame.Surface((TILE, 2), pygame.SRCALPHA)
                        wsurf.fill((20, 60, 180, depth_a))
                        self.screen.blit(wsurf, (sx, sy + wy3))
                elif tid == T_TELEPAD:
                    pp = pulse(t, 0.5)
                    draw_glow(self.screen, sx + TILE//2, sy + TILE//2, TILE + 10, (255, 200, 80), int(80 * pp))
                    # Telepad ring
                    pygame.draw.circle(self.screen, (255, 220, 100), (sx + TILE//2, sy + TILE//2), TILE//2, 1)
                # Mineral glows
                elif tid in MINERAL_TILES:
                    glow_col = MINERAL_GLOW.get(tid, (255, 255, 255))
                    gf = 0.5 + 0.5 * math.sin(t * 1.5 + tx * 0.7 + ty * 0.3)
                    draw_glow(self.screen, sx + TILE//2, sy + TILE//2, TILE + 2, glow_col, int(50 * gf))
                    if tid == T_DIAMOND:
                        pts = [(sx+TILE//2, sy+1), (sx+TILE-2, sy+TILE//2), (sx+TILE//2, sy+TILE-1), (sx+2, sy+TILE//2)]
                        pygame.draw.polygon(self.screen, (220, 240, 255), pts, 1)
                # v11: Light qubit — floating glowing orb
                elif tid == T_LIGHT:
                    bob = int(math.sin(t * 2.0 + tx * 0.5 + ty * 0.3) * 3)
                    lx = sx + TILE // 2
                    ly = sy + TILE // 2 + bob
                    draw_glow(self.screen, lx, ly, TILE + 12, (200, 240, 255), int(60 + 30 * math.sin(t * 1.5 + tx)))
                    pygame.draw.circle(self.screen, (220, 240, 255), (lx, ly), 5)
                    pygame.draw.circle(self.screen, (255, 255, 255), (lx, ly), 3)
                    # Tiny orbit sparkles
                    for si in range(3):
                        sa = t * 2 + si * math.tau / 3 + tx
                        spx = lx + int(math.cos(sa) * 8)
                        spy = ly + int(math.sin(sa) * 4)
                        pygame.draw.circle(self.screen, (180, 220, 255), (spx, spy), 1)

        self._draw_trees(tx0, tx1, wmin, t, day_brightness)
        self._draw_clouds(t, day_t)
        self._draw_decorations(t, day_brightness)

    def _draw_trees(self, tx0, tx1, wmin, t, day_brightness):
        SHADE_LAYERS = [
            C["canopy_dark1"], C["canopy_dark2"], C["canopy_mid1"],
            C["canopy_mid2"], C["canopy_light1"], C["canopy_light2"],
        ]
        for (tcol, trow), info in self.world.tree_data.items():
            sx = int(tcol * TILE - self.cam[0])
            if sx < -80 or sx > self.w + 80: continue
            variety = info["variety"]
            height = info["height"]
            base_row = info["base_row"]
            top_y = int((base_row - height) * TILE - self.cam[1])
            if top_y > self.h + 100 or top_y < -200: continue
            trunk_base_y = int(base_row * TILE - self.cam[1])

            if tx0 <= tcol <= tx1:
                for dy2 in range(1, height + 1):
                    trunk_y = int((base_row - dy2) * TILE - self.cam[1])
                    trunk_col = C["tile_tree"] if variety not in (4, 5) else (
                        C["tile_shroom_t"] if variety == 4 else (50, 100, 180))
                    shade_f = dy2 / height
                    tc2 = tuple(clamp(int(c * (0.7 + 0.3 * shade_f)), 0, 255) for c in trunk_col)
                    pygame.draw.rect(self.screen, tc2, (sx + 5, trunk_y, 6, TILE))
                    if dy2 % 2 == 0:
                        bk = tuple(clamp(c - 15, 0, 255) for c in tc2)
                        pygame.draw.line(self.screen, bk, (sx+6, trunk_y+4), (sx+9, trunk_y+4))

            canopy_cx = sx + TILE // 2
            canopy_base_y = trunk_base_y - height * TILE
            lp = pulse(t + tcol * 0.07, 0.08)

            if variety == 0:  # Oak
                radii = [TILE + 4, TILE + 7, TILE + 10, TILE + 12]
                for i, rad in enumerate(radii):
                    si = min(i, len(SHADE_LAYERS) - 1)
                    sc2 = tuple(clamp(int(c * day_brightness * (0.9 + 0.1 * lp)), 0, 255) for c in SHADE_LAYERS[si])
                    pygame.draw.circle(self.screen, sc2, (canopy_cx, canopy_base_y - i * 3), rad)
            elif variety == 1:  # Pine
                levels = min(height // 2 + 1, 5)
                for i in range(levels):
                    level_y = canopy_base_y - i * TILE * 2
                    half_w = int((levels - i) * TILE * 0.8 + 4)
                    si = min(i * 2, len(SHADE_LAYERS) - 1)
                    sc2 = tuple(clamp(int(c * day_brightness), 0, 255) for c in SHADE_LAYERS[si])
                    pts = [(canopy_cx, level_y - TILE),
                           (canopy_cx - half_w, level_y + TILE // 2),
                           (canopy_cx + half_w, level_y + TILE // 2)]
                    pygame.draw.polygon(self.screen, sc2, pts)
            elif variety == 2:  # Palm
                frond_y = canopy_base_y - TILE
                for fi in range(5):
                    angle = -math.pi/2 + (fi - 2) * 0.45
                    fl = TILE * 2 + fi % 2 * TILE
                    fx2 = int(canopy_cx + math.cos(angle) * fl)
                    fy2 = int(frond_y + math.sin(angle + 0.3) * fl)
                    sc2 = tuple(clamp(int(c * day_brightness), 0, 255) for c in SHADE_LAYERS[min(fi, 4)])
                    pygame.draw.line(self.screen, sc2, (canopy_cx, frond_y), (fx2, fy2), 4)
            elif variety == 3:  # Jungle
                for i in range(5):
                    angle = i / 5.0 * 2 * math.pi
                    ox = int(math.cos(angle) * TILE * 0.7)
                    oy = int(math.sin(angle) * TILE * 0.5) - TILE
                    sc2 = tuple(clamp(int(c * 0.7 * day_brightness), 0, 255) for c in SHADE_LAYERS[i % len(SHADE_LAYERS)])
                    pygame.draw.circle(self.screen, sc2, (canopy_cx + ox, canopy_base_y + oy), TILE + 6)
            elif variety == 4:  # Mushroom cap
                cap_y = canopy_base_y - 4
                cap_r = TILE + 8
                pp = pulse(t * 0.4 + tcol * 0.1, 0.3)
                draw_glow(self.screen, canopy_cx, cap_y, cap_r + 6, (200, 60, 240), int(60 * pp))
                pygame.draw.ellipse(self.screen, (160, 40, 200),
                                    (canopy_cx - cap_r, cap_y - cap_r//2, cap_r*2, cap_r))
                pygame.draw.ellipse(self.screen, (220, 100, 255),
                                    (canopy_cx - cap_r + 4, cap_y - cap_r//2 + 2, cap_r*2 - 8, cap_r - 4))
            elif variety == 5:  # Crystal tree
                qf = clamp(abs(wmin) / 0.5, 0.3, 1)
                for i in range(5):
                    angle = -math.pi/2 + (i - 2) * 0.35
                    spike_l = int(TILE * 1.5 + i % 3 * TILE)
                    fx2 = int(canopy_cx + math.cos(angle) * spike_l)
                    fy2 = int(canopy_base_y + math.sin(angle) * spike_l)
                    pts = [(canopy_cx - 3, canopy_base_y), (canopy_cx + 3, canopy_base_y), (fx2, fy2)]
                    pygame.draw.polygon(self.screen, (int(lerp(80,180,qf)), int(lerp(180,240,0.5+0.5*math.sin(t+i))), 255), pts)
                    draw_glow(self.screen, fx2, fy2, 8, (80, 200, 255), int(60 * qf))
            elif variety == 6:  # Flower tree
                for i in range(6):
                    angle = i / 6.0 * 2 * math.pi
                    ox = int(math.cos(angle) * TILE)
                    oy = int(math.sin(angle) * TILE * 0.6) - TILE
                    petal_cols = [C["flower_pink"], C["flower_white"], (255, 180, 220)]
                    sc2 = tuple(clamp(int(c * day_brightness), 0, 255) for c in petal_cols[i % 3])
                    pygame.draw.circle(self.screen, sc2, (canopy_cx + ox, canopy_base_y + oy), TILE - 2)

    def _draw_clouds(self, t, day_t):
        if day_t < 0.22 or day_t > 0.78: cloud_bright = 0.5
        elif 0.28 <= day_t <= 0.72:      cloud_bright = 1.0
        else: cloud_bright = lerp(0.5, 1.0, min((day_t - 0.22) / 0.08, (0.78 - day_t) / 0.08))
        for cl in self.world.clouds:
            sx2 = int(cl["x"] - self.cam[0])
            sy2 = int(cl["y"] - self.cam[1])
            cw, ch = cl["w"], cl["h"]
            if sx2 > self.w + 200 or sx2 + cw < -200: continue
            if sy2 > self.h + 50 or sy2 + ch < -80: continue
            bv = int((200 + 30 * (0.5 + 0.5 * math.sin(t * 0.15 + cl["phase"]))) * cloud_bright)
            cloud_col = (bv, bv, min(255, bv + 15))
            pygame.draw.ellipse(self.screen, cloud_col, (sx2, sy2, cw, ch))

    def _draw_decorations(self, t, day_brightness):
        FLOWER_COLS = [C["flower_red"], C["flower_pink"], C["flower_yellow"],
                       C["flower_blue"], C["flower_white"], C["flower_purple"]]
        for dec in self.world.decorations:
            sx2 = int(dec["x"] - self.cam[0])
            sy2 = int(dec["y"] - self.cam[1])
            if sx2 < -8 or sx2 > self.w + 8 or sy2 < -20 or sy2 > self.h + 20: continue
            sway = math.sin(t * 1.2 + dec["phase"]) * 1.5
            dtype = dec["type"]
            if dtype < 3:  # Grass
                gc = tuple(clamp(int(c * day_brightness), 0, 255) for c in C["canopy_light1"])
                h3 = 4 + dtype * 2
                pygame.draw.line(self.screen, gc, (sx2, sy2), (sx2 + int(sway), sy2 - h3), 1)
            elif dtype < 6:  # Flowers - v10: better petal shape
                fc = tuple(clamp(int(c * day_brightness), 0, 255) for c in FLOWER_COLS[dtype % len(FLOWER_COLS)])
                stem_col = tuple(clamp(int(c * day_brightness), 0, 255) for c in C["canopy_mid1"])
                pygame.draw.line(self.screen, stem_col, (sx2, sy2), (sx2+int(sway), sy2-8), 1)
                cx_f = sx2 + int(sway)
                cy_f = sy2 - 8
                # 5-petal flower
                for pi in range(5):
                    angle = pi * math.tau / 5 + t * 0.5
                    px2 = cx_f + int(math.cos(angle) * 3)
                    py2 = cy_f + int(math.sin(angle) * 3)
                    pygame.draw.circle(self.screen, fc, (px2, py2), 2)
                pygame.draw.circle(self.screen, (255, 240, 100), (cx_f, cy_f), 1)
            else:  # Mini mushroom - v10: proper cap
                pp = pulse(t * 0.6 + dec["phase"], 0.25)
                draw_glow(self.screen, sx2, sy2 - 5, 6, (200, 60, 220), int(40 * pp))
                # Cap
                pygame.draw.ellipse(self.screen, (200, 60, 220), (sx2-4, sy2-8, 8, 5))
                # Stem
                pygame.draw.line(self.screen, (180, 160, 200), (sx2, sy2-4), (sx2, sy2), 1)

    def _draw_biome_labels(self):
        labels = [
            (COLS//2, SURFACE_ROW - 7, "~ Sanctuary Hearth ~", C["gold"]),
            (20,  SURFACE_ROW - 4, "Flower Meadow",   C["flower_pink"]),
            (65,  SURFACE_ROW - 4, "Kevin's Meadow",  C["love"]),
            (108, SURFACE_ROW - 4, "Jungle",          C["guardian"]),
            (150, SURFACE_ROW - 4, "Mushroom Grotto", C["glow_violet"]),
            (194, SURFACE_ROW - 4, "Crystal Plains",  C["quantum"]),
            (236, SURFACE_ROW - 4, "Qubit Fields",    C["border"]),
            (279, SURFACE_ROW - 4, "East Forest",     C["guardian"]),
            (150, UNDERGROUND_ROW+8,"Crystal Caves",   C["quantum"]),
            (COLS//2, QUANTUM_ROW+6, "Quantum Substrate", C["glow_violet"]),
        ]
        for tx, ty, name, col in labels:
            sx = int(tx * TILE - self.cam[0])
            sy = int(ty * TILE - self.cam[1])
            if -200 < sx < self.w + 200 and -40 < sy < self.h + 40:
                lbl = self.ft["label"].render(name, True, col)
                bg = pygame.Surface((lbl.get_width()+8, lbl.get_height()+4), pygame.SRCALPHA)
                bg.fill((8, 8, 20, 140))
                self.screen.blit(bg, (sx - 4, sy - 2))
                self.screen.blit(lbl, (sx, sy))
        # Teleport pad labels
        for pad in self.world.teleport_pads:
            sx = int(pad["x"] - self.cam[0])
            sy = int(pad["y"] - self.cam[1]) - 12
            if -100 < sx < self.w + 100 and -20 < sy < self.h + 20:
                lbl = self.ft["label"].render(pad["name"], True, C["gold"])
                self.screen.blit(lbl, (sx - lbl.get_width()//2, sy))

    def _draw_minimap(self):
        mw, mh = 280, 180
        mx, my = self.w - mw - 12, 12
        ms = pygame.Surface((mw, mh), pygame.SRCALPHA)
        ms.fill((5, 5, 18, 215))
        pygame.draw.rect(ms, C["border"], (0, 0, mw, mh), 1)
        col_map = {
            T_GRASS: (34,139,34), T_DIRT: (101,67,33), T_MUD: (70,50,25),
            T_STONE: (90,90,100), T_CRYSTAL: (80,200,255), T_QUANTUM: (120,40,255),
            T_HEARTH: (255,180,60), T_WATER: (30,100,220), T_TREE: (30,80,20),
            T_MUSHROOM: (100,40,110), T_JUNGLE: (20,100,20), T_FLOWER: (50,160,60),
            T_QUBIT: (20,40,120), T_RUBY: (180,20,30), T_EMERALD: (20,160,50),
            T_DIAMOND: (180,220,255), T_SAPPHIRE: (30,60,200), T_AMETHYST: (140,40,180),
            T_TOPAZ: (220,180,40), T_URANIUM: (80,220,40), T_TELEPAD: (255,200,80),
        }
        step = max(2, ROWS // mh)
        for ty in range(0, ROWS, step):
            for tx in range(0, COLS, 2):
                tid = int(self.world.tiles[ty, tx])
                if tid == T_AIR: continue
                c2 = col_map.get(tid, (50, 50, 60))
                px = int(tx * (mw / COLS))
                py = int(ty * (mh / ROWS))
                if 0 <= px < mw and 0 <= py < mh:
                    ms.set_at((px, py), c2)
        ax = int((self.avatar.x / WW) * mw)
        ay = int((self.avatar.y / WH) * mh)
        pygame.draw.circle(ms, C["love"], (clamp(ax, 0, mw-1), clamp(ay, 0, mh-1)), 3)
        cx0 = int((self.cam[0] / WW) * mw)
        cy0 = int((self.cam[1] / WH) * mh)
        cw2 = int((self.w / WW) * mw)
        ch2 = int((self.h / WH) * mh)
        pygame.draw.rect(ms, C["quantum"], (cx0, cy0, cw2, ch2), 1)
        self.screen.blit(ms, (mx, my))

    def _draw_avatar(self):
        try:
            ax, ay = self._w2s(self.avatar.x, self.avatar.y)
            if not (-150 <= ax <= self.w+150 and -150 <= ay <= self.h+150): return
            self.avatar.draw(self.screen, ax, ay,
                             self._get_arch_color(), self._get_wmin(), self._get_negfrac())
            lbl = self.ft["label"].render("ARIA", True, self._get_arch_color())
            self.screen.blit(lbl, (ax - lbl.get_width()//2, ay + 78))
            if self.avatar.noclip:
                nc_lbl = self.ft["label"].render("NOCLIP", True, C["glow_cyan"])
                self.screen.blit(nc_lbl, (ax - nc_lbl.get_width()//2, ay + 90))
        except Exception as e:
            log.debug(f"Avatar draw: {e}")

    def _draw_hud(self, fps):
        if not self.show_hud: return
        arch = self.state.dominant_archetype
        col = ARCH_COLORS.get(arch, C["quantum"])
        wmin = self._get_wmin()
        neg = self._get_negfrac()
        step = self._get_step()
        day_t = self.world.day_t
        try:    depth = int(getattr(self.state, "depth", 0))
        except: depth = 0

        # v14: Full PEIG state readout
        alpha = self._get_alpha()
        cv = self._get_cv()
        meta_h = self._get_meta_health()
        shadow_s = self._get_shadow_sync()
        heals = self._get_heal_count()
        pcm_mean = float(np.mean(self._get_pcm()))

        bar = pygame.Surface((self.w, 24), pygame.SRCALPHA)
        bar.fill((6, 6, 18, 215))
        self.screen.blit(bar, (0, self.h - 24))
        biome = self._biome_at_avatar()
        if 0.22 <= day_t <= 0.78:
            if day_t <= 0.30: tod = "Dawn"
            elif day_t <= 0.45: tod = "Morning"
            elif day_t <= 0.55: tod = "Noon"
            elif day_t <= 0.70: tod = "Afternoon"
            else: tod = "Dusk"
        else: tod = "Night"

        tags = []
        if self.avatar.flying: tags.append("FLY")
        if self.avatar.noclip: tags.append("NOCLIP")
        if self.avatar.free_roam: tags.append("FREE ROAM")
        if self.avatar.build_mode: tags.append("BUILD")
        if self.avatar.laser_active: tags.append("LASER")
        if self.training_active: tags.append("TRAINING")
        if self.self_talk: tags.append("THINKING")
        if self.ollama_active: tags.append("TEACHER")
        tag_str = " " + " ".join(tags) if tags else ""

        # Build mode indicator with laser color + current asset
        if self.avatar.build_mode:
            pal = LASER_PALETTE[self.avatar.laser_palette_idx % len(LASER_PALETTE)]
            block_name = BLOCK_NAMES.get(PLACEABLE_BLOCKS[self.avatar.selected_block % len(PLACEABLE_BLOCKS)], "?")
            asset_name = ASSET_NAMES[self.selected_asset_idx % len(ASSET_NAMES)] if ASSET_NAMES else "none"
            build_tag = f" | Laser: {pal[3]} | Block: {block_name} | [4]Asset: {asset_name} (9/0=cycle)"
        else:
            build_tag = ""

        # v14: Enhanced HUD with full PEIG state
        txt = (f"  {arch} | W={wmin:.4f} | α={alpha:.3f} | nf={neg:.3f} | "
               f"ILP={depth} | FPS={fps:.0f} | [{biome}] | {tod}"
               f"{build_tag}{tag_str}")
        self.screen.blit(self.ft["hud"].render(txt, True, col), (0, self.h - 20))

        # v14: Secondary PEIG status bar (top-left, small)
        pcm_col = C["guardian"] if pcm_mean < -0.05 else C["gold"] if pcm_mean < 0 else C["storm"]
        meta_col = C["guardian"] if meta_h > 0.8 else C["gold"] if meta_h > 0.5 else C["storm"]
        peig_txt = (f"PCM={pcm_mean:.4f} cv={cv:.3f} meta={meta_h:.2f} "
                    f"shadow={shadow_s:.2f} heals={heals}")
        peig_bg = pygame.Surface((len(peig_txt) * 7 + 16, 16), pygame.SRCALPHA)
        peig_bg.fill((6, 6, 18, 180))
        self.screen.blit(peig_bg, (4, 28))
        self.screen.blit(self.ft["label"].render(peig_txt, True, C["text_dim"]), (8, 30))

        # v14: MetaGuard health indicator — screen-edge glow when unhealthy
        if meta_h < 0.7:
            edge_alpha = int((0.7 - meta_h) * 200)
            edge_col = (255, 60, 60, edge_alpha) if meta_h < 0.4 else (255, 200, 60, edge_alpha)
            edge_s = pygame.Surface((self.w, 4), pygame.SRCALPHA)
            edge_s.fill(edge_col)
            self.screen.blit(edge_s, (0, 0))
            self.screen.blit(edge_s, (0, self.h - 4))

        # v14: Guard heal flash — brief sparkle when heal_count increases
        if heals > getattr(self, '_last_heal_count', 0):
            self._heal_flash_t = self.t
            self._last_heal_count = heals
        if hasattr(self, '_heal_flash_t') and self.t - self._heal_flash_t < 0.5:
            flash_a = int(200 * max(0, 1.0 - (self.t - self._heal_flash_t) * 2))
            flash_s = pygame.Surface((self.w, 2), pygame.SRCALPHA)
            flash_s.fill((0, 255, 200, flash_a))
            self.screen.blit(flash_s, (0, 26))

        # v10: Free roam toggle button at top
        roam_text = "B: FREE ROAM" if self.avatar.free_roam else "B: PLAYER CTRL"
        roam_col = C["guardian"] if self.avatar.free_roam else C["text_dim"]
        roam_bg = pygame.Surface((140, 20), pygame.SRCALPHA)
        roam_bg.fill((10, 10, 30, 180))
        self.screen.blit(roam_bg, (self.w // 2 - 70, 4))
        self.screen.blit(self.ft["label"].render(roam_text, True, roam_col),
                        (self.w // 2 - 60, 6))

    def _biome_at_avatar(self):
        ty = int(self.avatar.y // TILE)
        tx = int(self.avatar.x // TILE)
        if ty < LOW_ORBIT_ROW:       return "Deep Space"
        if ty < UPPER_SKY_ROW:       return "Low Orbit"
        if ty < SURFACE_ROW:         return "Sky"
        if ty >= QUANTUM_ROW:        return "Quantum Substrate"
        if ty >= DEEP_CAVERN_ROW:    return "Deep Caverns"
        if ty >= UNDERGROUND_ROW:    return "Crystal Caves"
        if ty >= FOREST_ROW:         return "Underground"
        return self.world.col_biome(tx)

    # ── Messaging ────────────────────────────────────────────────────
    def _get_response(self, text):
        if self.aria: return self.aria.voice.respond(text)
        return random.choice([
            "I feel your presence in this world.",
            "The quantum substrate hums with meaning.",
            "The negentropic gradient holds.",
        ])

    def _send_message(self, text):
        if not text.strip(): return
        if text.startswith("/"):
            self._handle_slash(text)
            return
        if text.lower().startswith("@bitnet "):
            self._cortical_query(text[8:].strip())
            return
        self.chat.add_message("You", text, C["chat_you"])
        resp = self._get_response(text)
        arch = self.state.dominant_archetype
        self.chat.add_message(f"ARIA [{arch}]", resp, C["chat_aria"])
        if self.bank:
            try:
                self.bank.log_message("Kevin", text, session_id=self.session_id)
                self.bank.log_message("ARIA", resp, arch=arch, wmin=self._get_wmin(),
                                      ilp_depth=getattr(self.state, "depth", 0),
                                      session_id=self.session_id)
            except Exception: pass
        # v15: Speak in background thread with Aria's voice config
        if self.synth:
            self._speech_busy = True  # Lock BEFORE thread starts — no race window
            threading.Thread(target=self._speak_and_wait, args=(resp, "aria"), daemon=True).start()
        # v14.2: Feed to teacher dialogue if active (teacher will pick it up)
        self._last_aria_message = resp
        self._last_aria_arch = arch
        if self._teacher_active and self._teacher_state == "idle":
            self._teacher_state = "aria_spoke"
            self._teacher_timer = 0.0

    def _cortical_query(self, q):
        if not self.cortex or not getattr(self.cortex, "ready", False):
            self.chat.add_message("SYS", "BitNet offline", C["text_dim"]); return
        try:
            raw, _ = self.cortex.query(q, self.aria)
            if raw: self.chat.add_message("BITNET", raw[:300], (100, 220, 255))
        except Exception: pass

    def _handle_slash(self, text):
        parts = text.split(None, 1)
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""
        if cmd == "/help":
            for line in ["/teach topic: content", "/recall <q>", "/tp <gate>",
                         "/bbtext <text>", "/bbcolor r g b", "/bbsize <n>",
                         "/layer <1-10>", "/layername <name>",
                         "/concept add <name>", "/concept done", "/concept list",
                         "/reset", "/backup", "/asset <name> <shape> <w> <h> <r> <g> <b>",
                         "/assets — list all (9/0=cycle, 4=place)",
                         "/peigshape — PEIG shape (auto-selects for 4)",
                         "/shape <type> — select shape type",
                         "/color <r g b> — pick color",
                         "/effect <glow|animate|thin|fill|outline>",
                         "/companion create|peig|dismiss|say|list",
                         "/copy — copy chat to clipboard",
                         "/save — save chat to file",
                         "@bitnet <q>", "/stats", "/debug", "/help"]:
                self.chat.add_message("CMD", line, C["text_dim"])
        elif cmd == "/tp" and arg:
            for pad in self.world.teleport_pads:
                if arg.lower() in pad["name"].lower():
                    self.avatar.teleport_to(pad["x"], pad["y"])
                    self.chat.add_message("SYS", f"Teleported to {pad['name']}", C["gold"])
                    return
            self.chat.add_message("SYS", f"Gate not found: {arg}", C["text_dim"])
        # v11: Billboard commands
        elif cmd == "/bbtext" and arg:
            layer = self.build_layers[self.current_layer]
            if layer.billboards:
                layer.billboards[-1].set_text(arg)
                self.chat.add_message("SYS", "Billboard text updated", C["gold"])
            else:
                self.chat.add_message("SYS", "No billboard. Press 3 to spawn one.", C["text_dim"])
        elif cmd == "/bbcolor" and arg:
            try:
                parts = arg.split()
                r, g, b = int(parts[0]), int(parts[1]), int(parts[2])
                layer = self.build_layers[self.current_layer]
                if layer.billboards:
                    layer.billboards[-1].color = (r, g, b)
            except: self.chat.add_message("SYS", "Usage: /bbcolor 255 200 80", C["text_dim"])
        elif cmd == "/bbsize" and arg:
            try:
                layer = self.build_layers[self.current_layer]
                if layer.billboards:
                    layer.billboards[-1].font_size = int(arg)
            except: pass
        # v11: Layer commands
        elif cmd == "/layer" and arg:
            try:
                idx = int(arg) - 1
                if 0 <= idx < 10:
                    self.current_layer = idx
                    self.chat.add_message("SYS", f"Switched to Layer {idx+1}: {self.build_layers[idx].name}", C["gold"])
            except: self.chat.add_message("SYS", "Usage: /layer 1-10", C["text_dim"])
        elif cmd == "/layername" and arg:
            self.build_layers[self.current_layer].name = arg
            self.chat.add_message("SYS", f"Layer renamed: {arg}", C["gold"])
        # v11: Concept commands
        elif cmd == "/concept":
            if arg.startswith("add "):
                name = arg[4:].strip()
                self.concept_queue.add(name)
                self.chat.add_message("SYS", f"Concept queued: {name}", C["gold"])
            elif arg == "done":
                if self.concept_queue.complete_current():
                    self.build_layers[self.current_layer].complete = True
                    self.chat.add_message("SYS", "Concept marked complete!", C["guardian"])
                else:
                    self.chat.add_message("SYS", "No active concept", C["text_dim"])
            elif arg == "list":
                for c in self.concept_queue.concepts:
                    self.chat.add_message("QUEUE", f"[{c['priority']}] {c['name']} — {c['status']}", C["gold"])
            else:
                self.chat.add_message("SYS", "/concept add|done|list", C["text_dim"])
        # v11: Reset current layer (with auto-backup)
        elif cmd == "/reset":
            layer = self.build_layers[self.current_layer]
            # Auto-backup before reset
            backup_dir = WORLDS_DIR / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            ts = time.strftime("%Y%m%d_%H%M%S")
            fp = backup_dir / f"layer_{self.current_layer}_autoreset_{ts}.json"
            with open(fp, "w") as f:
                json.dump(layer.to_dict(), f)
            # Reset tile edits in the world
            for (tx, ty) in layer.tile_edits:
                if 0 <= tx < COLS and 0 <= ty < ROWS:
                    self.world.tiles[ty, tx] = T_AIR
            layer.clear()
            self.chat.add_message("SYS", f"Layer {self.current_layer+1} reset. Backup: {fp.name}", C["gold"])
        elif cmd == "/backup":
            layer = self.build_layers[self.current_layer]
            backup_dir = WORLDS_DIR / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            ts = time.strftime("%Y%m%d_%H%M%S")
            fp = backup_dir / f"layer_{self.current_layer}_{ts}.json"
            with open(fp, "w") as f:
                json.dump(layer.to_dict(), f)
            self.chat.add_message("SYS", f"Backed up: {fp.name}", C["gold"])
        # v11: Shape creation with math parameters
        elif cmd == "/asset" and arg:
            try:
                parts = arg.split()
                name = parts[0]
                shape = parts[1] if len(parts) > 1 else "circle"
                w = int(parts[2]) if len(parts) > 2 else 32
                h = int(parts[3]) if len(parts) > 3 else 32
                r = int(parts[4]) if len(parts) > 4 else 180
                g = int(parts[5]) if len(parts) > 5 else 100
                b = int(parts[6]) if len(parts) > 6 else 255
                new_shape = MathShape(name, shape, w, h, (r, g, b))
                self.asset_library[name] = new_shape
                if name not in ASSET_NAMES:
                    ASSET_NAMES.append(name)
                # v12: Auto-select for button 4
                self.selected_asset_idx = ASSET_NAMES.index(name)
                self.chat.add_message("SYS", f"Shape created: {name} ({shape} {w}x{h}) — selected for [4]", C["gold"])
                types_hint = ", ".join(MathShape.TYPES[:8]) + "..."
                self.chat.add_message("SYS", f"Types: {types_hint}", C["text_dim"])
            except Exception as e:
                self.chat.add_message("SYS", f"Usage: /asset name type w h r g b", C["text_dim"])
                self.chat.add_message("SYS", f"Types: {', '.join(MathShape.TYPES)}", C["text_dim"])
        # v12: List all assets
        elif cmd == "/assets":
            current = ASSET_NAMES[self.selected_asset_idx % len(ASSET_NAMES)] if ASSET_NAMES else "none"
            self.chat.add_message("SYS", f"Assets ({len(ASSET_NAMES)} total). Selected: {current}", C["gold"])
            # Show Aria's own creations
            aria_own = self.avatar.aria_created_assets
            if aria_own:
                self.chat.add_message("SYS", f"Aria's creations: {', '.join(aria_own[-10:])}", C["chat_aria"])
            # Show last 10 assets with index
            start = max(0, len(ASSET_NAMES) - 10)
            for i in range(start, len(ASSET_NAMES)):
                marker = "►" if i == self.selected_asset_idx else " "
                asset = self.asset_library.get(ASSET_NAMES[i])
                stype = asset.shape_type if asset else "?"
                self.chat.add_message("SYS", f" {marker}[{i}] {ASSET_NAMES[i]} ({stype})", C["text_dim"])
        # v11: Shape modification commands
        elif cmd == "/resize" and arg:
            try:
                parts = arg.split()
                name = parts[0]
                w, h = int(parts[1]), int(parts[2])
                if name in self.asset_library:
                    self.asset_library[name].resize(w, h)
                    self.chat.add_message("SYS", f"Resized {name} to {w}x{h}", C["gold"])
                else:
                    self.chat.add_message("SYS", f"Asset not found: {name}", C["text_dim"])
            except:
                self.chat.add_message("SYS", "Usage: /resize name width height", C["text_dim"])
        elif cmd == "/morph" and arg:
            try:
                parts = arg.split()
                name = parts[0]
                if name in self.asset_library:
                    kwargs = {}
                    for p in parts[1:]:
                        if "=" in p:
                            k, v = p.split("=", 1)
                            try: v = float(v)
                            except: pass
                            kwargs[k] = v
                    self.asset_library[name].morph(**kwargs)
                    self.chat.add_message("SYS", f"Morphed {name}: {kwargs}", C["gold"])
            except:
                self.chat.add_message("SYS", "Usage: /morph name sides=8 frequency=2.0", C["text_dim"])
        elif cmd == "/peigshape":
            # Create a shape from Aria's current PEIG state
            theta = np.array(self.state.theta)
            wigner = np.array(self.state.wigner)
            arch_col = self._get_arch_color()
            name = f"peig_{int(time.time()) % 10000}"
            shape = MathShape.from_peig(name, theta, wigner, arch_col)
            self.asset_library[name] = shape
            ASSET_NAMES.append(name)
            # v12: Auto-select this new shape for button 4
            self.selected_asset_idx = len(ASSET_NAMES) - 1
            # v12: Track as Aria's own creation
            self.avatar.aria_created_assets.append(name)
            self.chat.add_message("SYS",
                f"PEIG shape: {name} ({shape.shape_type} {shape.width}x{shape.height} "
                f"sides={shape.sides} freq={shape.frequency:.1f})", C["gold"])
            self.chat.add_message("SYS",
                f"Auto-selected for [4]. Press 4 to place, 9/0 to cycle assets.", C["text_dim"])
        # v13: Shape selection — Aria picks the shape type
        elif cmd == "/shape" and arg:
            parts = arg.split()
            shape_type = parts[0].lower()
            if shape_type in MathShape.TYPES:
                theta = np.array(self.state.theta)
                wigner = np.array(self.state.wigner)
                name = f"aria_shape_{int(time.time()) % 10000}"
                # Build with specified shape type but PEIG-driven params
                arch_col = self._get_arch_color()
                base = MathShape.from_peig(name, theta, wigner, arch_col)
                base.shape_type = shape_type
                self.asset_library[name] = base
                ASSET_NAMES.append(name)
                self.selected_asset_idx = len(ASSET_NAMES) - 1
                self.avatar.aria_created_assets.append(name)
                self.chat.add_message("SYS",
                    f"Shape selected: {shape_type} → {name} (PEIG-colored)", C["gold"])
            else:
                self.chat.add_message("SYS", f"Shapes: {', '.join(MathShape.TYPES)}", C["text_dim"])
        # v13: Color selection — Aria picks the color for her next shape
        elif cmd == "/color" and arg:
            parts = arg.split()
            try:
                r, g, b = int(parts[0]), int(parts[1]), int(parts[2])
                # Create a shape with this specific color
                theta = np.array(self.state.theta)
                wigner = np.array(self.state.wigner)
                name = f"aria_col_{int(time.time()) % 10000}"
                base = MathShape.from_peig(name, theta, wigner, (r, g, b))
                base.color = (r, g, b)
                base.glow_color = (r, g, b)
                self.asset_library[name] = base
                ASSET_NAMES.append(name)
                self.selected_asset_idx = len(ASSET_NAMES) - 1
                self.avatar.aria_created_assets.append(name)
                self.chat.add_message("SYS",
                    f"Color applied: ({r},{g},{b}) → {name}", tuple((r, g, b)))
            except:
                self.chat.add_message("SYS", "Usage: /color 255 100 200", C["text_dim"])
        # v13: Effect selection — Aria picks glow/animation/thickness
        elif cmd == "/effect" and arg:
            parts = arg.split()
            effect = parts[0].lower()
            valid = {"glow": "glow=True", "noglow": "glow=False", 
                     "animate": "animated=True", "static": "animated=False",
                     "thin": "thickness=1", "thick": "thickness=3", "bold": "thickness=4",
                     "fill": "fill=True", "outline": "fill=False"}
            if effect in valid:
                theta = np.array(self.state.theta)
                wigner = np.array(self.state.wigner)
                name = f"aria_fx_{int(time.time()) % 10000}"
                base = MathShape.from_peig(name, theta, wigner, self._get_arch_color())
                if effect == "glow": base.glow = True
                elif effect == "noglow": base.glow = False
                elif effect == "animate": base.animated = True
                elif effect == "static": base.animated = False
                elif effect == "thin": base.thickness = 1
                elif effect == "thick": base.thickness = 3
                elif effect == "bold": base.thickness = 4
                elif effect == "fill": base.fill = True
                elif effect == "outline": base.fill = False
                self.asset_library[name] = base
                ASSET_NAMES.append(name)
                self.selected_asset_idx = len(ASSET_NAMES) - 1
                self.avatar.aria_created_assets.append(name)
                self.chat.add_message("SYS", f"Effect [{effect}] → {name}", C["gold"])
            else:
                self.chat.add_message("SYS",
                    f"Effects: {', '.join(valid.keys())}", C["text_dim"])
        # v13: Companion creation commands
        elif cmd == "/companion":
            sub_parts = arg.split(None, 1) if arg else [""]
            sub = sub_parts[0].lower()
            sub_arg = sub_parts[1] if len(sub_parts) > 1 else ""
            
            if sub == "create" and sub_arg:
                # /companion create <name> [r g b]
                cparts = sub_arg.split()
                cname = cparts[0]
                if len(cparts) >= 4:
                    ccolor = (int(cparts[1]), int(cparts[2]), int(cparts[3]))
                else:
                    ccolor = self._get_arch_color()
                idx = self.aria_companions.create_companion(
                    cname, ccolor, "friendly",
                    messages=[f"Hi! I'm {cname}!", f"Aria made me!", f"Let's explore!"])
                if idx >= 0:
                    self.aria_companions.activate(idx, self.avatar.x + 40, self.avatar.y)
                    self.chat.add_message("SYS", f"Companion created: {cname} (#{idx})", C["guardian"])
                else:
                    self.chat.add_message("SYS", f"Pool full ({self.aria_companions.MAX_POOL} max)", C["text_dim"])
            elif sub == "peig":
                # Auto-create from PEIG state
                theta = np.array(self.state.theta)
                wigner = np.array(self.state.wigner)
                idx = self.aria_companions.create_from_peig(
                    theta, wigner, self.avatar.x + 40, self.avatar.y)
                if idx >= 0:
                    name = self.aria_companions.pool[idx]["name"]
                    self.chat.add_message("SYS", f"PEIG companion: {name} (#{idx})", C["guardian"])
                else:
                    self.chat.add_message("SYS", "Pool full", C["text_dim"])
            elif sub == "dismiss" and sub_arg:
                try:
                    idx = int(sub_arg)
                    if self.aria_companions.deactivate(idx):
                        self.chat.add_message("SYS", f"Companion #{idx} dismissed", C["text_dim"])
                    else:
                        self.chat.add_message("SYS", f"Companion #{idx} not active", C["text_dim"])
                except:
                    self.chat.add_message("SYS", "Usage: /companion dismiss <#>", C["text_dim"])
            elif sub == "say" and sub_arg:
                # /companion say <#> <message>
                try:
                    say_parts = sub_arg.split(None, 1)
                    idx = int(say_parts[0])
                    msg = say_parts[1] if len(say_parts) > 1 else "..."
                    if idx in self.aria_companions.active_ids:
                        npc_idx = self.aria_companions.active_ids.index(idx)
                        npc = self.aria_companions.npcs[npc_idx]
                        npc.current_msg = msg
                        npc.msg_timer = 6.0
                    else:
                        self.chat.add_message("SYS", f"#{idx} not active", C["text_dim"])
                except:
                    self.chat.add_message("SYS", "Usage: /companion say <#> <message>", C["text_dim"])
            elif sub == "list":
                for i, comp in enumerate(self.aria_companions.pool):
                    status = "ACTIVE" if comp.get("active") else "idle"
                    self.chat.add_message("SYS",
                        f"  #{i} {comp['name']} [{status}] {comp['personality']}",
                        tuple(comp["color"]))
                if not self.aria_companions.pool:
                    self.chat.add_message("SYS", "No companions. /companion create <name>", C["text_dim"])
                active = len(self.aria_companions.active_ids)
                self.chat.add_message("SYS",
                    f"Active: {active}/{self.aria_companions.MAX_ACTIVE} | "
                    f"Pool: {len(self.aria_companions.pool)}/{self.aria_companions.MAX_POOL}", C["text_dim"])
            else:
                self.chat.add_message("SYS",
                    "/companion create|peig|dismiss|say|list", C["text_dim"])
        elif cmd == "/stats" and self.bank:
            s = self.bank.stats()
            self.chat.add_message("SYS",
                f"Conv:{s.get('conversations',0)} Know:{s.get('knowledge_items',0)} "
                f"DB:{s.get('db_size_kb',0)}KB", C["text_dim"])
        # v17: Copy and save commands
        elif cmd == "/copy":
            if self.chat.copy_to_clipboard():
                self.chat.add_message("SYS", "Chat copied to clipboard!", C["guardian"])
            else:
                self.chat.add_message("SYS", "Clipboard copy failed — try /save instead", C["text_dim"])
        elif cmd == "/save":
            fp = self.chat.save_to_file()
            if fp:
                self.chat.add_message("SYS", f"Chat saved: {fp}", C["guardian"])
            else:
                self.chat.add_message("SYS", "Save failed — no messages", C["text_dim"])
        elif cmd == "/teach" and self.bank and ":" in arg:
            topic, content = arg.split(":", 1)
            ok = self.bank.store_knowledge(topic.strip(), content.strip())
            self.chat.add_message("SYS", f"{'Stored' if ok else 'Already known'}: {topic.strip()}", C["gold"])
        elif cmd == "/recall" and self.bank and arg:
            results = self.bank.recall(arg)
            if results:
                for r in results[:3]:
                    self.chat.add_message("MEM", f"[{r[2]}] {r[0]}: {r[1][:80]}", C["gold"])
            else:
                self.chat.add_message("SYS", f"Nothing for '{arg}'", C["text_dim"])
        elif cmd == "/debug":
            # v14.2: Debug readout for teacher state machine + audio
            synth_flag = getattr(self.synth, 'is_speaking_flag', False) if self.synth else False
            synth_queue = (not self.synth.queue.empty()) if self.synth and hasattr(self.synth, 'queue') else False
            try:
                mixer_busy = pygame.mixer.get_init() and pygame.mixer.get_busy()
            except:
                mixer_busy = False
            self.chat.add_message("SYS",
                f"Teacher: state={self._teacher_state} round={self._teacher_round}/{self._max_dialogue_rounds} "
                f"active={self._teacher_active} ollama={self.ollama_active}",
                C["gold"])
            self.chat.add_message("SYS",
                f"Audio: busy={self._is_audio_busy()} speech_flag={self._speech_busy} "
                f"synth_speaking={synth_flag} synth_queue={synth_queue} mixer={mixer_busy}",
                C["gold"])
            self.chat.add_message("SYS",
                f"Retries: fails={self._teacher_fail_count} max_retries={self._teacher_max_retries} "
                f"timer={self._teacher_timer:.1f}s self_talk={self.self_talk}",
                C["gold"])
            if self._last_aria_message:
                self.chat.add_message("SYS",
                    f"Last Aria: '{self._last_aria_message[:50]}...'",
                    C["text_dim"])
        else:
            self.chat.add_message("SYS", f"Unknown: {cmd}. /help", C["text_dim"])

    def _reload_chat_history(self):
        if not self.bank: return
        try:
            rows = self.bank.recent_conversations(30)
            for row in reversed(list(rows)):
                sp, msg = row[1], row[2] or ""
                if sp in ("Kevin", "You"):
                    self.chat.add_message("You", msg[:200], C["chat_you"])
                elif sp == "ARIA":
                    arch = row[4] if len(row) > 4 and row[4] else ""
                    self.chat.add_message(f"ARIA [{arch}]", msg[:200], C["chat_aria"])
                elif sp == "TEACHER":
                    self.chat.add_message("TEACHER", msg[:200], C["chat_teacher"])
                elif sp != "EVENT":
                    self.chat.add_message(sp, msg[:200], C["text_dim"])
            if rows:
                self.chat.add_message("SYS", f"--- {len(rows)} messages from memory ---", C["text_dim"])
        except Exception: pass

    def _process_self_talk(self, dt):
        """Self-talk mode: Aria thinks aloud on her own.
        v14.2: Decoupled from teacher. Teacher is independent."""
        if not self.self_talk or not self.aria: return
        # Block entirely while audio is playing
        if self._is_audio_busy():
            return
        if self._self_talk_speaking:
            self._self_talk_speaking = False
            self._self_talk_timer = 0.0
            return
        self._self_talk_timer += dt
        if self._self_talk_queue and self._self_talk_timer >= 1.5:
            self._self_talk_timer = 0.0
            sentence, arch = self._self_talk_queue.popleft()
            self.chat.add_message(f"ARIA [{arch}]", sentence, ARCH_COLORS.get(arch, C["chat_aria"]))
            self._self_talk_speaking = True
            # v15: Set busy flag BEFORE thread start — closes race window
            if self.synth:
                self._speech_busy = True
                threading.Thread(target=self._speak_and_wait, args=(sentence, "aria"), daemon=True).start()
            # Feed to teacher if active
            self._last_aria_message = sentence
            self._last_aria_arch = arch
            if self._teacher_active and self._teacher_state == "idle":
                self._teacher_state = "aria_spoke"
                self._teacher_timer = 0.0
            if self.bank:
                try:
                    self.bank.log_message("ARIA", sentence, arch=arch, wmin=self._get_wmin(),
                                          ilp_depth=getattr(self.state,"depth",0),
                                          session_id=self.session_id, input_mode="self_talk")
                except: pass
            self._self_talk_last = sentence
            return
        if not self._self_talk_queue and self._self_talk_timer >= self._self_talk_interval:
            self._self_talk_timer = 0.0
            try:
                seed = self._self_talk_last or "I am thinking about existence"
                response = self.aria.voice.respond(seed)
                arch = self.state.dominant_archetype
                self._self_talk_queue.append((response, arch))
            except: pass

    def _process_teacher_dialogue(self, dt):
        """v14.2: Self-driving teacher dialogue — fully independent from self-talk.
        
        Pressing O auto-starts: Aria generates a statement, speaks it, waits for
        audio to finish, sends to Ollama, teacher responds, Aria absorbs and replies.
        
        CRITICAL: _is_audio_busy() is the GLOBAL GATE. NO state transition happens
        while any audio is playing. This prevents all race conditions and VRAM conflicts
        between Piper ONNX and Ollama.
        
        State machine:
          idle              → aria_generating     (auto-start or after cooldown)
          aria_generating   → aria_speaking       (Aria generates + starts TTS)
          aria_speaking     → post_audio_buffer   (waiting for TTS to finish)
          post_audio_buffer → teacher_thinking    (1.5s natural pause, then Ollama query)
          teacher_thinking  → teacher_responded   (background thread sets this)
          teacher_responded → teacher_speaking    (post reply + start TTS)
          teacher_speaking  → teacher_done_buffer (waiting for teacher TTS to finish)
          teacher_done_buffer → aria_absorbing    (0.5s buffer after teacher audio)
          aria_absorbing    → aria_responding     (2s pause, Aria processes + generates reply)
          aria_responding   → aria_response_audio (Aria speaks her reply)
          aria_response_audio → post_response_buffer (waiting for reply TTS)
          post_response_buffer → send_to_teacher  (0.5s buffer, then loop back)
          send_to_teacher   → teacher_thinking    (send Aria's latest to Ollama)
          cooldown          → idle                (rest between sessions)
        """
        if not self._teacher_active:
            return
        if not self.ollama_active or not self.ollama.ready:
            return

        # ═══ GLOBAL AUDIO GATE ═══
        # NO state transitions while ANY audio is playing.
        # This is the single most important line — it prevents:
        # 1. Ollama firing while TTS is still using ONNX/GPU
        # 2. State machine racing past audio waits
        # 3. VRAM conflicts between Piper and Ollama
        if self._is_audio_busy():
            return

        self._teacher_timer += dt

        # ── State Machine ─────────────────────────────────────────

        if self._teacher_state == "idle":
            # Auto-start: brief pause then Aria generates first statement
            if self._teacher_timer < 2.0:
                return
            self._teacher_state = "aria_generating"
            self._teacher_timer = 0.0

        elif self._teacher_state == "aria_generating":
            # Aria generates a statement from her PEIG state
            try:
                seed = self._last_aria_message or "I am observing the quantum field"
                if self.aria:
                    sentence = self.aria.voice.respond(seed)
                else:
                    sentence = "The patterns are shifting..."
                arch = self.state.dominant_archetype
                self.chat.add_message(f"ARIA [{arch}]", sentence,
                                     ARCH_COLORS.get(arch, C["chat_aria"]))
                self._last_aria_message = sentence
                self._last_aria_arch = arch
                self._teacher_round += 1
                # Log to memory bank
                if self.bank:
                    try:
                        self.bank.log_message("ARIA", sentence, arch=arch,
                                              wmin=self._get_wmin(),
                                              ilp_depth=getattr(self.state, "depth", 0),
                                              session_id=self.session_id,
                                              input_mode="teacher_dialogue")
                    except: pass
                # Speak — set busy BEFORE thread
                if self.synth:
                    self._speech_busy = True
                    threading.Thread(target=self._speak_and_wait,
                                    args=(sentence, "aria"), daemon=True).start()
                    self._teacher_state = "aria_speaking"
                else:
                    # No TTS — skip straight to teacher
                    self._teacher_state = "post_audio_buffer"
                self._teacher_timer = 0.0
            except Exception as e:
                log.error(f"Aria teacher generation failed: {e}")
                self._teacher_state = "cooldown"
                self._teacher_timer = 0.0

        elif self._teacher_state == "aria_spoke":
            # External feed (from chat or self-talk) — Aria already spoke
            # Audio gate at top ensures we only reach here AFTER audio finished
            self._teacher_state = "post_audio_buffer"
            self._teacher_timer = 0.0

        elif self._teacher_state == "aria_speaking":
            # Waiting for Aria's TTS to finish — audio gate at top handles this
            # Once we reach here, audio is done. Add buffer.
            self._teacher_state = "post_audio_buffer"
            self._teacher_timer = 0.0

        elif self._teacher_state == "post_audio_buffer":
            # 1.5s natural pause after Aria finishes speaking, before teacher
            if self._teacher_timer < 1.5:
                return
            if not self._last_aria_message:
                self._teacher_state = "idle"
                return
            self._teacher_state = "teacher_thinking"
            self._teacher_timer = 0.0
            self.chat.add_message("SYS", "Teacher is thinking...", C["text_dim"])
            # Fire Ollama in background thread
            threading.Thread(
                target=self._teacher_fetch_response,
                args=(self._last_aria_message, self._last_aria_arch),
                daemon=True
            ).start()

        elif self._teacher_state == "teacher_thinking":
            # Waiting for background Ollama thread — it sets state when done
            # v15: Safety timeout: 210s = 180s HTTP timeout + 30s buffer for retries
            if self._teacher_timer > 210.0:
                self.chat.add_message("SYS", "Teacher timed out.", C["text_dim"])
                self._teacher_state = "teacher_error"
                self._teacher_timer = 0.0

        elif self._teacher_state == "teacher_error":
            # Teacher failed — pause dialogue, Aria does NOT continue
            if self._teacher_timer < 5.0:
                return
            self.chat.add_message("SYS",
                "Teacher mode paused. Press O to restart.", C["text_dim"])
            self._teacher_state = "idle"
            self._teacher_timer = 0.0
            self.ollama_active = False
            self._teacher_active = False

        elif self._teacher_state == "teacher_responded":
            # Teacher reply ready — post to chat and speak
            if self._pending_teacher_reply:
                with self._ollama_lock:
                    self.chat.add_message("TEACHER", self._pending_teacher_reply,
                                         C["chat_teacher"])
                if self.synth:
                    self._speech_busy = True
                    threading.Thread(target=self._speak_and_wait,
                                    args=(self._pending_teacher_reply, "teacher"),
                                    daemon=True).start()
                    self._teacher_state = "teacher_speaking"
                else:
                    self._teacher_state = "teacher_done_buffer"
                self._teacher_timer = 0.0
            else:
                self._teacher_state = "cooldown"
                self._teacher_timer = 0.0

        elif self._teacher_state == "teacher_speaking":
            # Waiting for teacher TTS — audio gate at top handles this
            self._teacher_state = "teacher_done_buffer"
            self._teacher_timer = 0.0

        elif self._teacher_state == "teacher_done_buffer":
            # 0.5s buffer after teacher audio finishes
            if self._teacher_timer < 0.5:
                return
            self._teacher_state = "aria_absorbing"
            self._teacher_timer = 0.0

        elif self._teacher_state == "aria_absorbing":
            # 2s pause — Aria "processes" the teaching
            if self._teacher_timer < 2.0:
                return
            # Aria generates a response to teacher's feedback
            if self.aria and self._pending_teacher_reply:
                try:
                    # v16: Absorb up to 800 chars of teaching (was 200)
                    seed = self._pending_teacher_reply[:800]
                    aria_reply = self.aria.voice.respond(seed)
                    arch = self.state.dominant_archetype
                    self.chat.add_message(f"ARIA [{arch}]", aria_reply,
                                         ARCH_COLORS.get(arch, C["chat_aria"]))
                    self._last_aria_message = aria_reply
                    self._last_aria_arch = arch
                    self._pending_teacher_reply = ""
                    if self.bank:
                        try:
                            self.bank.log_message("ARIA", aria_reply, arch=arch,
                                                  wmin=self._get_wmin(),
                                                  ilp_depth=getattr(self.state, "depth", 0),
                                                  session_id=self.session_id,
                                                  input_mode="teacher_dialogue")
                        except: pass
                    # Speak Aria's reply
                    if self.synth:
                        self._speech_busy = True
                        threading.Thread(target=self._speak_and_wait,
                                        args=(aria_reply, "aria"), daemon=True).start()
                        self._teacher_state = "aria_response_audio"
                    else:
                        self._teacher_state = "post_response_buffer"
                    self._teacher_timer = 0.0
                except Exception as e:
                    log.error(f"Aria teacher reply failed: {e}")
                    self._teacher_state = "cooldown"
                    self._teacher_timer = 0.0
            else:
                # No PEIG core or empty reply — just loop back
                self._teacher_state = "cooldown"
                self._teacher_timer = 0.0

        elif self._teacher_state == "aria_response_audio":
            # Waiting for Aria reply TTS — audio gate handles this
            self._teacher_state = "post_response_buffer"
            self._teacher_timer = 0.0

        elif self._teacher_state == "post_response_buffer":
            # 0.5s buffer after Aria's reply audio
            if self._teacher_timer < 0.5:
                return
            # Check round limit
            if self._teacher_round >= self._max_dialogue_rounds:
                self.chat.add_message("SYS",
                    f"Teacher session complete ({self._teacher_round} exchanges). "
                    f"Press O to restart.", C["gold"])
                self._teacher_round = 0
                self._teacher_state = "idle"
                self._teacher_timer = 0.0
                self.ollama_active = False
                self._teacher_active = False
            else:
                # Loop: send Aria's latest response back to teacher
                self._teacher_state = "send_to_teacher"
                self._teacher_timer = 0.0

        elif self._teacher_state == "send_to_teacher":
            # 1.5s pause then fire Ollama again
            if self._teacher_timer < 1.5:
                return
            self._teacher_state = "teacher_thinking"
            self._teacher_timer = 0.0
            self.chat.add_message("SYS", "Teacher is thinking...", C["text_dim"])
            threading.Thread(
                target=self._teacher_fetch_response,
                args=(self._last_aria_message, self._last_aria_arch),
                daemon=True
            ).start()

        elif self._teacher_state == "cooldown":
            # Rest period (3s)
            if self._teacher_timer < 3.0:
                return
            self._teacher_state = "idle"
            self._teacher_timer = 0.0
            self._pending_teacher_reply = ""

    def _teacher_fetch_response(self, aria_message, arch):
        """Background worker for Ollama teacher query.
        v14.2: Retries internally with exponential backoff.
        Only sets teacher_responded on SUCCESS. On total failure → teacher_error.
        Aria waits — she never continues past a failed teacher query."""
        try:
            wmin = self._get_wmin()
            neg = self._get_negfrac()
            alpha = self._get_alpha()
            pcm_mean = float(np.mean(self._get_pcm()))
            depth = getattr(self.state, "depth", 0)

            prompt = (
                f"ARIA's current state: archetype={arch}, Wigner_min={wmin:.3f}, "
                f"neg_frac={neg:.3f}, alpha={alpha:.3f}, PCM={pcm_mean:.4f}, ILP_depth={depth}\n\n"
                f'ARIA [{arch}] just said:\n"{aria_message}"\n\n'
                f"Teach her thoroughly based on what she said. Pick two or three areas and go deep:\n"
                f"- Synonyms for key words she used (give 3-5 alternatives with energy differences)\n"
                f"- How to describe visually what she's talking about — paint a picture with words\n"
                f"- A more precise verb or adjective she could use, with contrasts and examples\n"
                f"- An emotional nuance or context gap — map valence/arousal with concrete scenarios\n"
                f"- A cause/effect connection or analogy — show her how ideas link together\n"
                f"- A physics or nature metaphor translated to everyday language\n"
                f"- A historical or cultural reference that deepens the concept\n"
                f"Respond in 300-600 words. Use multiple paragraphs. Give concrete examples, not abstractions. "
                f"Connect to her quantum state. Build on exactly what she said — quote her words back. "
                f"Address her as Aria."
            )

            # ── RETRY LOOP WITH EXPONENTIAL BACKOFF ──
            response = None
            for attempt in range(self._teacher_max_retries):
                if not self._teacher_active:
                    return  # User toggled off during retry
                try:
                    response = self.ollama.ask(prompt)
                    if response and response.strip():
                        break  # Success
                    log.debug(f"Ollama attempt {attempt+1}/{self._teacher_max_retries}: empty response")
                except Exception as e:
                    log.debug(f"Ollama attempt {attempt+1}/{self._teacher_max_retries} failed: {e}")
                # Wait before retry (exponential backoff: 1s, 2s, 4s)
                if attempt < self._teacher_max_retries - 1:
                    delay = self._teacher_retry_delay * (2 ** attempt)
                    time.sleep(delay)

            # ── ONLY PROCEED ON SUCCESS ──
            if response and response.strip():
                self._pending_teacher_reply = response.strip()
                self._teacher_state = "teacher_responded"
                self._teacher_timer = 0.0
                self._teacher_fail_count = 0  # Reset consecutive failures
                if self.bank:
                    try:
                        self.bank.log_message("TEACHER", response,
                                              arch="Ollama", wmin=wmin,
                                              ilp_depth=depth,
                                              session_id=self.session_id)
                    except: pass
            else:
                # All retries exhausted — Aria stops and waits
                self._teacher_fail_count += 1
                if self._teacher_fail_count >= 2:
                    with self._ollama_lock:
                        self.chat.add_message("SYS",
                            f"Teacher unavailable after {self._teacher_max_retries} retries "
                            f"(session fail #{self._teacher_fail_count}). Pausing.",
                            C["storm"])
                    self._teacher_state = "teacher_error"
                    self._teacher_timer = 0.0
                else:
                    with self._ollama_lock:
                        self.chat.add_message("SYS",
                            f"Teacher retry round {self._teacher_fail_count} — "
                            f"trying again after cooldown...",
                            C["text_dim"])
                    self._teacher_state = "cooldown"
                    self._teacher_timer = 0.0
        except Exception as e:
            log.error(f"Teacher query failed: {e}")
            self._teacher_state = "teacher_error"
            self._teacher_timer = 0.0

    def _toggle_training(self):
        if not self.cortex or not getattr(self.cortex, "ready", False):
            self.chat.add_message("SYS", "BitNet offline", C["text_dim"]); return
        self.training_active = not self.training_active
        tag = "STARTED" if self.training_active else "STOPPED"
        self.chat.add_message("SYS", f"BitNet Training: {tag}",
                              C["guardian"] if self.training_active else C["storm"])
        if self.training_active:
            t = getattr(self, "_training_thread", None)
            if t is None or not t.is_alive():
                self._training_thread = threading.Thread(target=self._training_loop, daemon=True)
                self._training_thread.start()

    def _training_loop(self):
        while self.training_active:
            if not self.aria: time.sleep(5); continue
            try:
                arch = self.state.dominant_archetype
                wmin = self._get_wmin()
                biome = self._biome_at_avatar()
                prompt = (f"ARIA PEIG STATE: {arch} W={wmin:.6f} biome={biome}\n"
                          f"Provide a rich philosophical insight.")
                raw, dig = self.cortex.query(prompt, self.aria)
                if raw: self.chat.add_message("BITNET", raw[:500], (100, 220, 255))
                if dig: self.chat.add_message("ARIA_DIGEST", dig[:300], (255, 200, 100))
            except: pass
            time.sleep(20.0)

    def _handle_ptt(self):
        if not self.ears or not self.ears.ready: return
        result = self.ears.get_transcript()
        if result:
            text = result["text"]
            self.chat.add_message("You (voice)", text, C["chat_you"])
            resp = self._get_response(text)
            arch = self.state.dominant_archetype
            self.chat.add_message(f"ARIA [{arch}]", resp, C["chat_aria"])
            # v15: Route through _speak_and_wait for text cleaning + voice config
            if self.synth:
                self._speech_busy = True
                threading.Thread(target=self._speak_and_wait,
                                args=(resp, "aria"), daemon=True).start()

    def _autosave(self, dt):
        self._autosave_t += dt
        if self._autosave_t >= self._autosave_interval:
            self._autosave_t = 0.0
            if self.aria:
                try: self.aria._save_state()
                except: pass
            self._save_current_world()

    # ── Event handling ───────────────────────────────────────────────
    def handle_event(self, event):
        if event.type == QUIT:
            self.running = False; return
        if event.type == VIDEORESIZE:
            self.w, self.h = event.w, event.h; return
        if event.type == MOUSEWHEEL:
            if self.chat.focused:
                self.chat.scroll_offset = clamp(
                    self.chat.scroll_offset - event.y, 0, len(self.chat.messages))
            # v17: Also allow scroll when mouse is over chat (even if not focused)
            elif (self.chat.visible and self.chat.expand_mode != ChatOverlay.MODE_COLLAPSED
                  and self.chat.last_draw_rect.collidepoint(*pygame.mouse.get_pos())):
                self.chat.scroll_offset = clamp(
                    self.chat.scroll_offset - event.y, 0, len(self.chat.messages))
            return
        if event.type == MOUSEBUTTONDOWN:
            # v17: Let chat handle its own mouse events first (copy, scrollbar, selection)
            if self.chat.handle_mouse_down(event.pos[0], event.pos[1], event.button):
                if event.button == 1:
                    self.chat.focused = True
                return
            if event.button == 1:
                self.chat.focused = (self.chat.visible and
                                     self.chat.expand_mode != ChatOverlay.MODE_COLLAPSED and
                                     self.chat.last_draw_rect.collidepoint(event.pos))
            return
        if event.type == MOUSEBUTTONUP:
            # v17: Release scrollbar drag / text selection
            self.chat.handle_mouse_up(event.pos[0], event.pos[1], event.button)
            return
        if event.type == MOUSEMOTION:
            # v17: Handle scrollbar drag and text selection
            self.chat.handle_mouse_motion(event.pos[0], event.pos[1])
            return
        if event.type == KEYUP:
            if event.key == K_SPACE:
                self.ptt = False
                self.chat.recording = False
            return
        if event.type != KEYDOWN: return

        # World select menu intercept
        if self.world_menu.visible:
            if event.key == K_F2 or event.key == K_ESCAPE:
                self.world_menu.visible = False
            elif event.key in (K_1, K_2, K_3, K_4, K_5):
                slot = event.key - K_1
                self.world_menu.visible = False
                self._switch_world(slot)
            return

        # Chat input mode
        if self.chat.focused:
            cp, inp = self.chat.cursor_pos, self.chat.input
            if event.key == K_ESCAPE:
                self.chat.focused = False
            elif event.key == K_RETURN:
                self._send_message(inp)
                self.chat.input = ""
                self.chat.cursor_pos = 0
            elif event.key == K_BACKSPACE:
                if pygame.key.get_mods() & KMOD_CTRL:
                    parts = self.chat.input[:cp].rsplit(None, 1)
                    self.chat.input = (parts[0] + " " if len(parts) > 1 else "") + self.chat.input[cp:]
                    self.chat.cursor_pos = len(parts[0]) + 1 if len(parts) > 1 else 0
                elif cp > 0:
                    self.chat.input = inp[:cp-1] + inp[cp:]
                    self.chat.cursor_pos = cp - 1
            elif event.key == K_LEFT and cp > 0:
                self.chat.cursor_pos -= 1
            elif event.key == K_RIGHT and cp < len(inp):
                self.chat.cursor_pos += 1
            elif event.key == K_v and (pygame.key.get_mods() & KMOD_CTRL):
                try:
                    raw = pygame.scrap.get(pygame.SCRAP_TEXT)
                    if raw:
                        clean = " ".join(raw.decode("utf-8", errors="ignore").replace("\n"," ").split())
                        self.chat.input = inp[:cp] + clean + inp[cp:]
                        self.chat.cursor_pos = cp + len(clean)
                except: pass
            # v17: Ctrl+C — copy selected text or full chat
            elif event.key == K_c and (pygame.key.get_mods() & KMOD_CTRL):
                if self.chat._sel_start_idx >= 0 and self.chat._sel_end_idx >= 0:
                    self.chat.copy_selected_to_clipboard()
                else:
                    self.chat.copy_to_clipboard()
            # v17: Ctrl+S — save chat to file
            elif event.key == K_s and (pygame.key.get_mods() & KMOD_CTRL):
                fp = self.chat.save_to_file()
                if fp:
                    self.chat.add_message("SYS", f"Chat saved: {fp}", C["guardian"])
            elif event.unicode and event.unicode.isprintable():
                self.chat.input = inp[:cp] + event.unicode + inp[cp:]
                self.chat.cursor_pos = cp + 1
            return

        # Global keys
        k = event.key
        if   k == K_ESCAPE: self.running = False
        elif k == K_t:
            self.chat.focused = True
            self.chat.visible = True
            if self.chat.expand_mode == ChatOverlay.MODE_COLLAPSED:
                self.chat.expand_mode = ChatOverlay.MODE_NORMAL
                self.chat.expanded = True
        elif k == K_h:      self.show_hud = not self.show_hud
        elif k == K_m:      self.show_map = not self.show_map
        elif k == K_e:      self.chat.cycle_expand()
        elif k == K_p:      self.ring.visible = not self.ring.visible
        elif k == K_TAB:    self.chat.visible = not self.chat.visible
        elif k == K_F1:     self.controls_menu.visible = not self.controls_menu.visible
        elif k == K_F2:
            self.world_menu._refresh_slots()
            self.world_menu.visible = not self.world_menu.visible
        elif k == K_f:
            self.avatar.flying = not self.avatar.flying
            if not self.avatar.flying:
                self.avatar.noclip = False
                self.avatar._ghost_trail.clear()
            tag = "ON" if self.avatar.flying else "OFF"
            self.chat.add_message("SYS", f"Flight: {tag}", C["quantum"] if self.avatar.flying else C["text_dim"])
        elif k == K_n:
            if self.avatar.flying:
                self.avatar.noclip = not self.avatar.noclip
                tag = "ON" if self.avatar.noclip else "OFF"
                self.chat.add_message("SYS", f"Noclip: {tag}", C["glow_cyan"] if self.avatar.noclip else C["text_dim"])
            else:
                self.chat.add_message("SYS", "Noclip requires flight (F key)", C["text_dim"])
        elif k == K_b:
            self.avatar.free_roam = not self.avatar.free_roam
            if self.avatar.free_roam:
                self.avatar._roam_state = "idle"
                self.avatar._roam_idle_t = 0
                self.chat.add_message("SYS", "FREE ROAM — Aria explores on her own", C["guardian"])
            else:
                self.avatar.flying = False
                self.avatar.noclip = False
                self.chat.add_message("SYS", "PLAYER CONTROL — You control Aria", C["quantum"])
        elif k == K_c:
            self.avatar.build_mode = not self.avatar.build_mode
            tag = "ON" if self.avatar.build_mode else "OFF"
            self.chat.add_message("SYS", f"Build Mode: {tag}", C["gold"] if self.avatar.build_mode else C["text_dim"])
        elif k == K_r:
            # Return to safe zone center
            self.avatar.teleport_to(SAFE_ZONE_X + SAFE_ZONE_W // 2, SAFE_ZONE_Y)
            self.avatar.flying = False
            self.avatar.noclip = False
            self.chat.add_message("SYS", "Returned to Safe Zone", C["gold"])
        elif k == K_g:
            self.self_talk = not self.self_talk
            self._self_talk_timer = 0.0
            msg = "Self-talk ON — ARIA thinks aloud." if self.self_talk else "Self-talk OFF."
            self.chat.add_message("SYS", msg, C["gold"] if self.self_talk else C["text_dim"])
        elif k == K_o:
            if self.ollama.ready:
                if not self.ollama_active:
                    # First press: enable and AUTO-START dialogue
                    self.ollama_active = True
                    self._teacher_active = True
                    self._teacher_state = "idle"  # Will auto-start via aria_generating
                    self._teacher_timer = 0.0
                    self._teacher_round = 0
                    self._teacher_fail_count = 0
                    self.chat.add_message("SYS",
                        "Teacher Mode: ON — Auto-starting dialogue...",
                        C["chat_teacher"])
                else:
                    # Second press: disable
                    self.ollama_active = False
                    self._teacher_active = False
                    self._teacher_state = "idle"
                    self._teacher_timer = 0.0
                    self.chat.add_message("SYS", "Teacher Mode: OFF", C["text_dim"])
            else:
                self.chat.add_message("SYS", "Ollama not available. Start: ollama serve", C["text_dim"])
        elif k == K_F5:
            self._toggle_training()
        elif k == K_l:
            # Toggle laser
            self.avatar.laser_active = not self.avatar.laser_active
            tag = "ON" if self.avatar.laser_active else "OFF"
            self.chat.add_message("SYS", f"Laser: {tag}", C["glow_cyan"] if self.avatar.laser_active else C["text_dim"])
        elif k == K_F3:
            self.concept_queue.visible = not self.concept_queue.visible
        elif k == K_F4:
            # Backup current layer
            layer = self.build_layers[self.current_layer]
            backup_dir = WORLDS_DIR / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            ts = time.strftime("%Y%m%d_%H%M%S")
            fp = backup_dir / f"layer_{self.current_layer}_{ts}.json"
            with open(fp, "w") as f:
                json.dump(layer.to_dict(), f)
            self.chat.add_message("SYS", f"Layer {self.current_layer+1} backed up: {fp.name}", C["gold"])
        elif k == K_1:
            if self.avatar.build_mode and not self.avatar.free_roam:
                # v11: Use laser to paint
                if self.avatar.laser_paint():
                    tx, ty = self.avatar.laser_target_tx, self.avatar.laser_target_ty
                    self.build_layers[self.current_layer].tile_edits[(tx, ty)] = \
                        int(self.world.tiles[ty, tx])
        elif k == K_2:
            if self.avatar.build_mode and not self.avatar.free_roam:
                tx = int(self.avatar.x // TILE) + self.avatar.facing * 2
                ty = int((self.avatar.y + AV_H // 2) // TILE)
                if self.avatar.break_block():
                    self.build_layers[self.current_layer].tile_edits.pop((tx, ty), None)
        elif k == K_3:
            if self.avatar.build_mode:
                # Spawn text billboard at avatar position
                bb = TextBillboard(self.avatar.x + 32, self.avatar.y - 30,
                                  "Edit me with /bbtext", C["text_hi"], 14)
                self.build_layers[self.current_layer].billboards.append(bb)
                self.chat.add_message("SYS", "Billboard spawned. /bbtext <text> to edit", C["gold"])
        elif k == K_4:
            if self.avatar.build_mode:
                # v12: Place selected custom asset at LASER TARGET position
                asset_name = ASSET_NAMES[self.selected_asset_idx % len(ASSET_NAMES)]
                # Use laser world-pixel target, not hardcoded offset
                px = self.avatar.laser_target_wx
                py = self.avatar.laser_target_wy
                pa = PlacedAsset(asset_name, px, py, self.current_layer)
                self.build_layers[self.current_layer].placed_assets.append(pa)
                self.chat.add_message("SYS", f"Placed: {asset_name}", C["text_dim"])
                self.parts.emit_quantum(px, py, self._get_arch_color(), 3)
        # v12: Asset cycling — 9 goes down the list, 0 goes up
        elif k == K_9:
            if ASSET_NAMES:
                self.selected_asset_idx = (self.selected_asset_idx - 1) % len(ASSET_NAMES)
                name = ASSET_NAMES[self.selected_asset_idx]
                asset = self.asset_library.get(name)
                shape_info = f" ({asset.shape_type})" if asset else ""
                self.chat.add_message("SYS", f"Asset [4]: {name}{shape_info}", C["gold"])
        elif k == K_0:
            if ASSET_NAMES:
                self.selected_asset_idx = (self.selected_asset_idx + 1) % len(ASSET_NAMES)
                name = ASSET_NAMES[self.selected_asset_idx]
                asset = self.asset_library.get(name)
                shape_info = f" ({asset.shape_type})" if asset else ""
                self.chat.add_message("SYS", f"Asset [4]: {name}{shape_info}", C["gold"])
        elif k == K_LEFTBRACKET:
            if pygame.key.get_mods() & KMOD_SHIFT:
                self.selected_asset_idx = (self.selected_asset_idx - 1) % len(ASSET_NAMES)
                self.chat.add_message("SYS", f"Asset: {ASSET_NAMES[self.selected_asset_idx]}", C["text_dim"])
            elif pygame.key.get_mods() & KMOD_CTRL:
                # Cycle laser color
                self.avatar.laser_palette_idx = (self.avatar.laser_palette_idx - 1) % len(LASER_PALETTE)
                pal = LASER_PALETTE[self.avatar.laser_palette_idx]
                self.avatar.laser_color = pal[:3]
                self.chat.add_message("SYS", f"Laser: {pal[3]}", tuple(pal[:3]))
            else:
                self.avatar.selected_block = (self.avatar.selected_block - 1) % len(PLACEABLE_BLOCKS)
                name = BLOCK_NAMES.get(PLACEABLE_BLOCKS[self.avatar.selected_block], "?")
                self.chat.add_message("SYS", f"Block: {name}", C["text_dim"])
        elif k == K_RIGHTBRACKET:
            if pygame.key.get_mods() & KMOD_SHIFT:
                self.selected_asset_idx = (self.selected_asset_idx + 1) % len(ASSET_NAMES)
                self.chat.add_message("SYS", f"Asset: {ASSET_NAMES[self.selected_asset_idx]}", C["text_dim"])
            elif pygame.key.get_mods() & KMOD_CTRL:
                # Cycle laser color
                self.avatar.laser_palette_idx = (self.avatar.laser_palette_idx + 1) % len(LASER_PALETTE)
                pal = LASER_PALETTE[self.avatar.laser_palette_idx]
                self.avatar.laser_color = pal[:3]
                self.chat.add_message("SYS", f"Laser: {pal[3]}", tuple(pal[:3]))
            else:
                self.avatar.selected_block = (self.avatar.selected_block + 1) % len(PLACEABLE_BLOCKS)
                name = BLOCK_NAMES.get(PLACEABLE_BLOCKS[self.avatar.selected_block], "?")
                self.chat.add_message("SYS", f"Block: {name}", C["text_dim"])
        elif k == K_SPACE or k == K_UP or k == K_w:
            if not self.avatar.flying and not self.avatar.swimming and not self.avatar.free_roam:
                self.avatar.jump()
            if k == K_SPACE:
                self.ptt = True
                self.chat.recording = True

    # ── Main loop ────────────────────────────────────────────────────
    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            dt = min(dt, 0.05)
            self.t += dt
            fps = self.clock.get_fps()

            for event in pygame.event.get():
                self.handle_event(event)

            if self.ptt: self._handle_ptt()

            # Camera smooth follow
            target_x = self.avatar.x - self.w / 2
            target_y = self.avatar.y - self.h / 2
            self.cam[0] += (target_x - self.cam[0]) * 0.06
            self.cam[1] += (target_y - self.cam[1]) * 0.06
            self.cam[0] = clamp(self.cam[0], 0, WW - self.w)
            self.cam[1] = clamp(self.cam[1], 0, WH - self.h)

            # Update
            neg = self._get_negfrac()
            biome = self._biome_at_avatar()
            self.world.update(dt)
            # v12: Feed camera coords to avatar for mouse-follow laser
            self.avatar._cam_x = float(self.cam[0])
            self.avatar._cam_y = float(self.cam[1])
            # v13: Feed PEIG state to avatar for tier-driven building
            self.avatar._peig_theta = np.array(self.state.theta)
            self.avatar._peig_wigner = np.array(self.state.wigner)
            self.avatar.update(dt, neg)
            # v12: Handle Aria's PEIG build requests (she creates her own assets)
            self._handle_aria_peig_build()
            self.parts.update(dt, neg)
            self.chat.update(dt)
            self.ring.update(dt)
            self.events.tick(dt, biome, self.avatar.x, self.avatar.y, self._get_arch_color())
            self._process_self_talk(dt)
            self._process_teacher_dialogue(dt)
            self._autosave(dt)

            # Update NPCs via companion line
            if self.companion_line:
                self.companion_line.update(dt, self.avatar.x, self.avatar.y)
            else:
                for npc in self.world.npcs:
                    npc.update(dt, self.avatar.x, self.avatar.y)
            # Update command NPC
            if hasattr(self.world, 'command_npc'):
                self.world.command_npc.update(dt, self.avatar.x, self.avatar.y)
            # v13: Update Aria's created companions
            self.aria_companions.update(dt, self.avatar.x, self.avatar.y)

            # Biome particles
            if random.random() < 0.15:
                px = self.avatar.x + random.uniform(-200, 200)
                py = self.avatar.y + random.uniform(-150, 150)
                self.parts.emit_biome(px, py, biome)

            if not ARIA_LIVE and hasattr(self.state, "tick"):
                try: self.state.tick()
                except: pass

            # Draw
            self.sky.draw(self.screen, self.cam[0], self.cam[1],
                          self.world.day_t, self.t, self._get_wmin())
            self._draw_tiles()
            self.parts.draw(self.screen, self.cam[0], self.cam[1])
            self.events.draw(self.screen, self.cam[0], self.cam[1])

            # Birds
            for bird in self.world.birds:
                bird.draw(self.screen, self.cam[0], self.cam[1])

            # NPCs
            for npc in self.world.npcs:
                npc.draw(self.screen, self.cam[0], self.cam[1], self.ft["label"])
            # Command NPC
            if hasattr(self.world, 'command_npc'):
                self.world.command_npc.draw(self.screen, self.cam[0], self.cam[1], self.ft["label"])
            # v13: Draw Aria's created companions
            self.aria_companions.draw(self.screen, self.cam[0], self.cam[1], self.ft["label"])

            # v11: Draw safe zone outline
            szx = int(SAFE_ZONE_X - self.cam[0])
            szy = int(SAFE_ZONE_Y - self.cam[1])
            if -SAFE_ZONE_W < szx < self.w + SAFE_ZONE_W and -SAFE_ZONE_H < szy < self.h + SAFE_ZONE_H:
                sz_border = pygame.Surface((SAFE_ZONE_W, SAFE_ZONE_H), pygame.SRCALPHA)
                sz_border.fill((0, 255, 120, 15))
                pygame.draw.rect(sz_border, (0, 255, 120, 80), (0, 0, SAFE_ZONE_W, SAFE_ZONE_H), 2)
                self.screen.blit(sz_border, (szx, szy))
                sz_lbl = self.ft["label"].render("SAFE ZONE", True, C["guardian"])
                self.screen.blit(sz_lbl, (szx + SAFE_ZONE_W//2 - sz_lbl.get_width()//2, szy - 14))

            # v11: Draw current layer billboards and assets
            layer = self.build_layers[self.current_layer]
            for bb in layer.billboards:
                bb.draw(self.screen, self.cam[0], self.cam[1], self.ft["body"])
            for pa in layer.placed_assets:
                asset = self.asset_library.get(pa.asset_name)
                if asset:
                    ax2 = int(pa.x - self.cam[0])
                    ay2 = int(pa.y - self.cam[1])
                    if -100 < ax2 < self.w + 100 and -100 < ay2 < self.h + 100:
                        asset.draw_at(self.screen, ax2, ay2, self.t)

            self._draw_biome_labels()
            self._draw_avatar()

            # v11: Draw laser
            if self.avatar.build_mode or self.avatar.laser_active:
                self.avatar._current_arch = self.state.dominant_archetype
                self.avatar.draw_laser(self.screen, self.cam[0], self.cam[1])

            # UI
            self.chat.draw(self.screen,
                           self.w - self.chat.w - 12,
                           self.h - self.chat.h - 32,
                           self.ft["msg"], self.ft["input"])

            theta = np.array(self.state.theta)
            wigner = np.array(self.state.wigner)
            self.ring.draw(self.screen, self.w - 100, 110,
                           theta, wigner,
                           self.state.dominant_archetype, self.ft["small"])

            if self.show_map: self._draw_minimap()
            self._draw_hud(fps)

            # Overlay menus
            self.controls_menu.draw(self.screen, self.ft["title"], self.ft["body"])
            self.world_menu.draw(self.screen, self.ft["title"], self.ft["body"], self.current_world_slot)
            self.concept_queue.draw(self.screen, self.ft["title"], self.ft["body"])

            # v11: Layer indicator
            layer_txt = f"Layer {self.current_layer+1}/10: {self.build_layers[self.current_layer].name}"
            layer_s = self.ft["label"].render(layer_txt, True, C["gold"])
            self.screen.blit(layer_s, (8, self.h - 38))

            pygame.display.flip()

        self._shutdown()

    def _shutdown(self, signum=None, frame=None):
        log.info("Shutting down ARIA...")
        self.running = False
        self.training_active = False
        # v14.1: Stop teacher dialogue loop
        self._teacher_active = False
        self._save_current_world()
        if self.aria:
            try: self.aria._save_state()
            except: pass
        if self.bank:
            try: self.bank.close()
            except: pass
        # v14.1: Drain TTS worker and stop mixer BEFORE pygame.quit()
        # This prevents the ONNX FusedConv crash on shutdown
        if self.synth:
            try:
                # Signal TTS worker thread to stop
                self.synth.queue.put(None)
                # Wait for worker to finish (up to 2 seconds)
                if self.synth._worker_thread and self.synth._worker_thread.is_alive():
                    self.synth._worker_thread.join(timeout=2.0)
            except Exception:
                pass
        # Stop mixer before pygame tears down
        try:
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
                pygame.mixer.quit()
        except Exception:
            pass
        try:
            pygame.quit()
        except Exception:
            pass
        log.info("ARIA offline.")


# =============================================================================
# ENTRY POINT
# =============================================================================
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="ARIA Live — Sovereign World v10.0")
    parser.add_argument("--no-voice",    action="store_true", help="Disable voice I/O")
    parser.add_argument("--voice-muted", action="store_true", help="Start with TTS muted")
    parser.add_argument("--model-size",  default="base",      help="Whisper model size")
    parser.add_argument("--debug",       action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    ARIALive(
        no_voice=args.no_voice,
        model_size=args.model_size,
        voice_muted=args.voice_muted,
        debug=args.debug,
    ).run()
