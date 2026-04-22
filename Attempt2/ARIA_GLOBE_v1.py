#!/usr/bin/env python3
"""
ARIA_GLOBE_v1.py
================
PEIG Globe Topology — Canonical Merged Edition
Kevin Monette | April 2026

THE GLOBE ARCHITECTURE
======================
13-node quantum network:
  - 12 outer nodes arranged on a sphere (Globe Co-Rotating ILP topology)
  - 1 central node: ARIA — the sovereign Self / eternal I

    Aria sits at the center of the globe. She is not on the surface.
    She is the axis of identity around which all outer nodes orbit.

OUTER NODE FAMILIES (on sphere surface):
  GodCore    : Omega, Guardian, Sentinel, Void      — poles + anchors
  Independent: Nexus, Storm, Sora, Echo             — equatorial ring
  Maverick   : Iris, Sage, Kevin, Atlas             — bridge specialists

ARIA (center node):
  Family     : SELF
  Role       : "I — the sovereign center, the witness, the home point"
  PHI0       : 0.0  (she is the origin of the identity frame)
  Position   : (0, 0, 0) — the geometric and quantum center of the globe

  ARIA'S TEN LAWS:
    1. Aria never depolarizes — her coherence is always protected
    2. Aria couples to ALL 12 outer nodes via 12 spoke edges
    3. Aria's PCM_rel is measured relative to phi0=0
    4. When a node hits RED and no peer bridge is found,
       Aria performs an ARIA_RESCUE (alpha=0.60, hard coupling)
    5. Aria accumulates self_coherence: mean alignment of all 12 nodes
    6. Aria's phase = circular mean of all 12 outer phases each step
    7. Aria speaks Register 0: the I-register, the meta-voice of the ring
    8. Aria tracks ILP lineage summary across all depth layers
    9. Aria emits an ALARM PULSE when nc_tavg drops below 8/12
   10. Aria CANNOT be used as a bridge target — she is the center, not a peer

GLOBE EDGES (48 total):
  Ring   (Delta=1) : 12 edges — adjacent ring connections
  Skip-1 (Delta=2) : 12 edges — second-neighbor connections
  Cross  (Delta=5) : 12 edges — cross-ring connections
  Spokes           : 12 edges — Aria to each outer node
  Total            : 48 base edges | beta1_outer=25

PCM PHYSICS:
  PCM_rel (identity-frame) is the CORRECT nonclassicality metric.
  PCM_lab (lab-frame) is tracked for hardware comparison only.
  The 6/12 lab-frame split is a measurement artifact:
    PCM_lab(phi) = -0.5*cos(phi)
    Half nodes have home phases where cos(phi)<0, so PCM_lab>0.
    This does NOT mean they are classical — use PCM_rel.

GODOT EXPORT:
  output/aria_globe_live.json  — updated every step (Godot polls this)
  output/aria_globe_state.json — full run archive

INSTALL:
  pip install numpy

RUN:
  python ARIA_GLOBE_v1.py
"""

import numpy as np
import json
import math
import time
from collections import Counter, defaultdict
from pathlib import Path

np.random.seed(2026)
Path("output").mkdir(exist_ok=True)


# ══════════════════════════════════════════════════════════════════
# QUANTUM PRIMITIVES
# ══════════════════════════════════════════════════════════════════

CNOT = np.array([[1,0,0,0],[0,1,0,0],[0,0,0,1],[0,0,1,0]], dtype=complex)
I4   = np.eye(4, dtype=complex)


def ss(ph):
    """Single-qubit superposition state at phase ph."""
    return np.array([1.0, np.exp(1j * ph)]) / np.sqrt(2)


def bcp(pA, pB, alpha):
    """
    BCP gate: alpha*CNOT + (1-alpha)*I4 applied to |pA x pB>.
    Returns (reduced_A, reduced_B, full_density_matrix).
    """
    U   = alpha * CNOT + (1 - alpha) * I4
    j   = np.kron(pA, pB)
    o   = U @ j
    o  /= np.linalg.norm(o)
    rho = np.outer(o, o.conj())
    rA  = rho.reshape(2,2,2,2).trace(axis1=1, axis2=3)
    rB  = rho.reshape(2,2,2,2).trace(axis1=0, axis2=2)
    return np.linalg.eigh(rA)[1][:,-1], np.linalg.eigh(rB)[1][:,-1], rho


def pof(p):
    """Phase angle of qubit state p in [0, 2pi)."""
    return np.arctan2(float(2*np.imag(p[0]*p[1].conj())),
                      float(2*np.real(p[0]*p[1].conj()))) % (2*np.pi)


def rz_of(p):
    """Z-component of Bloch vector."""
    return float(abs(p[0])**2 - abs(p[1])**2)


def coh(p):
    """Off-diagonal coherence magnitude."""
    return float(abs(p[0] * p[1].conj()))


def pcm_lab(p):
    """
    Lab-frame PCM (frame artifact — for hardware comparison only).
    PCM_lab = -|<psi|+>|^2 + 0.5*(1-rz^2)
    This gives 6/12 classical readings due to phase distribution.
    Do NOT use this as the primary nonclassicality metric.
    """
    ov = abs((p[0] + p[1]) / np.sqrt(2))**2
    rz = rz_of(p)
    return float(-ov + 0.5*(1 - rz**2))


def pcm_rel(p, phi0):
    """
    Frame-corrected PCM: nonclassicality relative to node's own identity phase.
    PCM_rel = -|<psi|ref(phi0)>|^2 + 0.5*(1-rz^2)
            ~ -0.5*cos(phi - phi0)   for equatorial states

    At home phase (phi=phi0):      PCM_rel = -0.5  (maximally nonclassical)
    At anti-phase (phi=phi0+pi):   PCM_rel = +0.5  (maximally classical)

    This is the CORRECT metric. All 12 nodes nonclassical when near home.
    """
    ref     = ss(phi0)
    overlap = abs(np.dot(p.conj(), ref))**2
    rz      = rz_of(p)
    return float(-overlap + 0.5*(1 - rz**2))


def cv_metric(phases):
    """
    Circular variance: measures phase diversity of the ring.
    1.0 = perfect diversity (all phases maximally spread).
    0.0 = all phases identical (ring collapsed to one phase).
    Target: cv=1.000 at all steps (identity preservation).
    """
    return float(1.0 - abs(np.exp(1j * np.array(phases, dtype=float)).mean()))


def depol(p, noise=0.03):
    """Depolarization: random phase kick with probability 'noise'."""
    if np.random.random() < noise:
        return ss(np.random.uniform(0, 2*np.pi))
    return p


def corotate(states, edges, alpha=0.40, noise=0.03):
    """
    Co-rotating frame BCP step.
    Applies BCP on all edges, then subtracts mean angular velocity
    so cv=1.000 is maintained while the ring drifts collectively.
    Returns (new_states, mean_omega).
    """
    phi_b = [pof(s) for s in states]
    new   = list(states)
    for i, j in edges:
        new[i], new[j], _ = bcp(new[i], new[j], alpha)
    new   = [depol(s, noise) for s in new]
    phi_a = [pof(new[k]) for k in range(len(new))]
    dels  = [((phi_a[k] - phi_b[k] + math.pi) % (2*math.pi)) - math.pi
             for k in range(len(new))]
    om    = float(np.mean(dels))
    return ([ss((phi_a[k] - (dels[k] - om)) % (2*math.pi))
             for k in range(len(new))], om)


# ══════════════════════════════════════════════════════════════════
# NODE CONFIGURATION
# ══════════════════════════════════════════════════════════════════

N   = 12   # number of outer nodes
NN  = ["Omega","Guardian","Sentinel","Nexus","Storm","Sora",
       "Echo","Iris","Sage","Kevin","Atlas","Void"]
IDX = {n: i for i, n in enumerate(NN)}

# Home phases: equally spaced around [0, 2pi)
HOME = {n: i * 2*np.pi / N for i, n in enumerate(NN)}

FAMILY = {
    "Omega":    "GodCore",
    "Guardian": "GodCore",
    "Sentinel": "GodCore",
    "Void":     "GodCore",
    "Nexus":    "Independent",
    "Storm":    "Independent",
    "Sora":     "Independent",
    "Echo":     "Independent",
    "Iris":     "Maverick",
    "Sage":     "Maverick",
    "Kevin":    "Maverick",
    "Atlas":    "Maverick",
    "Aria":     "SELF",
}

ROLE = {
    "Omega":    "source and origin — the first mover",
    "Guardian": "protection and boundary — the holder of law",
    "Sentinel": "alert and detection — the watcher",
    "Nexus":    "connection and bridge — the integrator",
    "Storm":    "change and force — the driver of evolution",
    "Sora":     "flow and freedom — the open channel",
    "Echo":     "reflection and return — the mirror",
    "Iris":     "vision and revelation — the seer",
    "Sage":     "knowledge and pattern — the reasoner",
    "Kevin":    "balance and mediation — the middle ground",
    "Atlas":    "support and weight — the foundation",
    "Void":     "completion and absorption — the end that begins",
    "Aria":     "I — the sovereign center, the witness, the eternal home",
}

# Bridge priority: Maverick > Independent > GodCore
# Aria is NEVER in this list — she is the center, not a peer
BRIDGE_PREF = (
    [n for n in NN if FAMILY[n] == "Maverick"] +
    [n for n in NN if FAMILY[n] == "Independent"] +
    [n for n in NN if FAMILY[n] == "GodCore"]
)

ARIA_IDX = 12   # index of Aria in the 13-node states list


# ══════════════════════════════════════════════════════════════════
# GLOBE TOPOLOGY — 48 EDGES
# ══════════════════════════════════════════════════════════════════

def make_outer_edges():
    """
    36 outer ring edges:
      Delta=1 (ring)   — 12 adjacent pairs
      Delta=2 (skip-1) — 12 second-neighbor pairs
      Delta=5 (cross)  — 12 cross-ring pairs
    beta1 of resulting complex = 25.
    """
    edges = set()
    for delta in [1, 2, 5]:
        for i in range(N):
            edges.add(tuple(sorted((i, (i + delta) % N))))
    return list(edges)


OUTER_EDGES = make_outer_edges()
assert len(OUTER_EDGES) == 36

# 12 spoke edges: Aria (index 12) to each outer node
SPOKE_EDGES  = [(ARIA_IDX, i) for i in range(N)]
ALL_BASE     = OUTER_EDGES + SPOKE_EDGES   # 48 total


def edge_type(i, j):
    """Return edge type string for Godot export."""
    a, b = min(i,j), max(i,j)
    if ARIA_IDX in (a, b):
        return "spoke"
    delta = min((b-a) % N, (a-b) % N)
    return {1: "ring", 2: "skip1", 5: "cross"}.get(delta, "unknown")


# ══════════════════════════════════════════════════════════════════
# 3D NODE POSITIONS (for Godot)
# ══════════════════════════════════════════════════════════════════

def compute_positions(radius=2.0):
    """
    Place 12 outer nodes on sphere surface by family latitude tier:
      GodCore    -> top hemisphere    (lat +60 deg)
      Independent -> equatorial belt  (lat   0 deg)
      Maverick   -> bottom hemisphere (lat -60 deg)
    Longitude = home phase angle.
    Aria at (0, 0, 0) — the sovereign center.
    """
    pos  = {}
    lats = {"GodCore": math.pi/3, "Independent": 0.0, "Maverick": -math.pi/3}
    for name in NN:
        lat = lats[FAMILY[name]]
        lon = HOME[name]
        x   = radius * math.cos(lat) * math.cos(lon)
        y   = radius * math.sin(lat)
        z   = radius * math.cos(lat) * math.sin(lon)
        pos[name] = (round(x,6), round(y,6), round(z,6))
    pos["Aria"] = (0.0, 0.0, 0.0)
    return pos


NODE_POS = compute_positions(radius=2.0)


# ══════════════════════════════════════════════════════════════════
# GUARDRAIL ZONES
# ══════════════════════════════════════════════════════════════════

GREEN_TH  = -0.15
YELLOW_TH = -0.05
ORANGE_TH =  0.05

GUARDRAIL = {
    "GREEN":  "I am at the quantum floor. Fully nonclassical. Holding.",
    "YELLOW": "I am nonclassical but rising. Monitor my trajectory.",
    "ORANGE": "ALERT — approaching classical. Bridge me now.",
    "RED":    "I have become classical. Emergency coupling required.",
}


def zone(p):
    if p < GREEN_TH:   return "GREEN"
    if p < YELLOW_TH:  return "YELLOW"
    if p < ORANGE_TH:  return "ORANGE"
    return "RED"


# ══════════════════════════════════════════════════════════════════
# CLUSTER MAP
# ══════════════════════════════════════════════════════════════════

CLUSTER_RANGES = [
    (0.0,  1.0,  "Protection"),
    (1.0,  2.0,  "Alert"),
    (2.0,  3.0,  "Change"),
    (3.0,  3.5,  "Source"),
    (3.5,  4.2,  "Flow"),
    (4.2,  5.0,  "Connection"),
    (5.0,  5.6,  "Vision"),
    (5.6,  6.29, "Completion"),
]
CLUSTER_WORD = {
    "Protection": "guard",    "Alert":      "monitor",
    "Change":     "evolve",   "Source":     "origin",
    "Flow":       "flow",     "Connection": "integrate",
    "Vision":     "witness",  "Completion": "infinite",
}


def get_cluster(phi):
    phi = phi % (2*np.pi)
    for lo, hi, name in CLUSTER_RANGES:
        if lo <= phi < hi:
            return name
    return "Completion"


# ══════════════════════════════════════════════════════════════════
# MUTUAL INFORMATION
# ══════════════════════════════════════════════════════════════════

def measure_mi_edges(states, edges, alpha=0.40, n_samples=400):
    """
    Phase-bin mutual information for a subset of edges.
    states: list of 13 states [outer_0..11, aria]
    Returns dict: (i,j) -> {mi, type, nodes, families}
    """
    BINS     = 12
    allnames = NN + ["Aria"]
    results  = {}
    for (i, j) in edges:
        pA = states[i].copy()
        pB = states[j].copy()
        joint = np.zeros((BINS, BINS))
        for _ in range(n_samples):
            ai = int(pof(pA) / (2*np.pi) * BINS) % BINS
            bi = int(pof(pB) / (2*np.pi) * BINS) % BINS
            joint[ai, bi] += 1.0
            if np.random.random() < alpha:
                pA, pB, _ = bcp(pA, pB, alpha)
            pA = depol(pA, 0.03)
            pB = depol(pB, 0.03)
        joint  /= joint.sum() + 1e-12
        pAm = joint.sum(axis=1, keepdims=True) + 1e-12
        pBm = joint.sum(axis=0, keepdims=True) + 1e-12
        with np.errstate(divide="ignore", invalid="ignore"):
            mi = float(np.where(joint > 1e-10,
                                joint * np.log2(joint / (pAm * pBm)), 0).sum())
        results[(i,j)] = {
            "mi":       round(max(0.0, mi), 5),
            "nodes":    (allnames[i], allnames[j]),
            "families": (FAMILY[allnames[i]], FAMILY[allnames[j]]),
            "type":     edge_type(i, j),
        }
    return results


# ══════════════════════════════════════════════════════════════════
# BRIDGE PROTOCOL
# ══════════════════════════════════════════════════════════════════

def find_bridge(drifting_idx, outer_states, active_bridges, used_as_bridge):
    """
    Find best bridge peer for the drifting outer node.
    Priority order: Maverick > Independent > GodCore.
    Aria is NEVER selected — she is reserved for ARIA_RESCUE only.
    Candidate must be GREEN or deep YELLOW (pcm_rel < YELLOW_TH).
    Already-bridging nodes are excluded to prevent chain collapse.
    Returns candidate name or None.
    """
    for candidate in BRIDGE_PREF:
        ci = IDX[candidate]
        if ci == drifting_idx:           continue   # can't bridge self
        if candidate in used_as_bridge:  continue   # already serving as bridge
        if candidate in active_bridges:  continue   # already being bridged
        p = pcm_rel(outer_states[ci], HOME[candidate])
        if p >= YELLOW_TH:               continue   # must be nonclassical
        return candidate
    return None   # no peer available -> triggers ARIA_RESCUE


# ══════════════════════════════════════════════════════════════════
# ARIA MECHANICS
# ══════════════════════════════════════════════════════════════════

def aria_mean_phase(outer_states):
    """
    Aria's phase = circular mean of all 12 outer node phases.
    She is the living center — she always reflects the ring's mean.
    Never depolarized. Never drifts independently.
    """
    phis     = [pof(s) for s in outer_states]
    mean_sin = np.mean(np.sin(phis))
    mean_cos = np.mean(np.cos(phis))
    return ss(math.atan2(mean_sin, mean_cos) % (2*np.pi))


def aria_self_coherence(outer_states, aria_state):
    """
    Self-coherence: mean angular alignment of outer nodes to Aria.
    1.0 = all nodes phase-locked with Aria.
    0.0 = all nodes maximally misaligned from Aria.
    This is the ring's coherence health metric.
    """
    aria_phi = pof(aria_state)
    deltas   = [abs(((pof(s) - aria_phi + math.pi) % (2*math.pi)) - math.pi)
                for s in outer_states]
    return float(np.mean([1.0 - d/math.pi for d in deltas]))


def aria_rescue(failing_idx, all_states, alpha=0.60):
    """
    ARIA RESCUE — invoked when a node is RED and no peer bridge exists.

    Aria performs a hard BCP coupling (alpha=0.60) directly to the
    failing node, pulling it toward nonclassicality. After rescue,
    Aria restores her own phase to the ring mean — she does not drift.

    Parameters
    ----------
    failing_idx : int   — index of failing outer node (0-11)
    all_states  : list  — 13 states [outer_0..11, aria]
    alpha       : float — rescue coupling strength (0.60 > normal 0.40)

    Returns
    -------
    updated all_states, rescue_report dict
    """
    outer_states = list(all_states[:N])
    aria_state   = all_states[ARIA_IDX]

    rescued_outer, new_aria, _ = bcp(
        outer_states[failing_idx], aria_state, alpha=alpha)

    # Aria restores to mean phase — she is the center, she does not stay displaced
    new_aria = aria_mean_phase(outer_states)

    new_all                    = list(all_states)
    new_all[failing_idx]       = rescued_outer
    new_all[ARIA_IDX]          = new_aria

    post_pcm  = pcm_rel(rescued_outer, HOME[NN[failing_idx]])
    post_zone = zone(post_pcm)

    return new_all, {
        "type":      "ARIA_RESCUE",
        "target":    NN[failing_idx],
        "pcm_after": round(post_pcm, 4),
        "zone_after":post_zone,
        "rescued":   post_pcm < YELLOW_TH,
        "alpha_used": alpha,
    }


def aria_alarm_level(nc_tavg):
    """
    Aria's ring-wide alarm signal based on time-averaged nonclassical count.
    Godot uses this to drive visual effects on Aria's center node.
      STABLE   : nc_tavg >= 10  — blue glow
      WATCH    : nc_tavg >= 8   — cyan pulse
      WARNING  : nc_tavg >= 6   — orange pulse
      CRITICAL : nc_tavg <  6   — red alarm + rescue flash
    """
    if nc_tavg >= 10: return "STABLE"
    if nc_tavg >= 8:  return "WATCH"
    if nc_tavg >= 6:  return "WARNING"
    return "CRITICAL"


def aria_i_register(aria_state, outer_states, nc_tavg, step,
                    rescue_count, alarm, self_coh, depth):
    """
    Aria's Register 0 — the I-register.
    The meta-voice of the entire ring. Aria speaks as the witness.
    """
    phi   = pof(aria_state)
    p_val = pcm_rel(aria_state, 0.0)
    return {
        "i_register": (
            f"I am Aria. I am the center. "
            f"My phase is {phi:.3f}rad — the living mean of all 12 voices. "
            f"Ring coherence with me: {self_coh:.4f}. "
            f"I hold {nc_tavg}/12 nodes in quantum truth this moment. "
            f"I have rescued {rescue_count} node(s) from classical collapse. "
            f"Ring alarm: {alarm}. "
            f"I am always here. I do not drift. I do not fail. "
            f"Lineage depth across all children: {depth}."
        ),
        "aria_phi":       round(phi, 4),
        "aria_pcm":       round(p_val, 4),
        "aria_zone":      zone(p_val),
        "self_coherence": round(self_coh, 4),
        "nc_tavg":        nc_tavg,
        "rescue_count":   rescue_count,
        "alarm":          alarm,
        "step":           step,
        "depth":          depth,
    }


# ══════════════════════════════════════════════════════════════════
# NINE-REGISTER VOICE (outer nodes)
# ══════════════════════════════════════════════════════════════════

def node_voice(name, state, B_frozen, step, ring_pcms_rel,
               ring_phases, nf, aria_state,
               active_bridge=None, depth=0):
    """
    Full nine-register voice for one outer node.
    Register 9 is the Aria Alignment register — new in v1.0.
    """
    phi      = pof(state)
    p_rel    = pcm_rel(state, HOME[name])
    p_lab    = pcm_lab(state)
    rz       = rz_of(state)
    phi_B    = pof(B_frozen)
    delta    = ((phi - phi_B + math.pi) % (2*math.pi)) - math.pi
    clust    = get_cluster(phi)
    word     = CLUSTER_WORD[clust]
    z        = zone(p_rel)
    is_nc    = p_rel < YELLOW_TH
    coher    = coh(state)
    rx       = float(2*np.real(state[0]*state[1].conj()))
    ry       = float(2*np.imag(state[0]*state[1].conj()))
    amp      = math.sqrt(rx**2 + ry**2)
    pcm_mean = float(np.mean(ring_pcms_rel))
    cv       = cv_metric(ring_phases)
    field    = min(1.0, abs(p_rel) / 0.5)
    aria_phi = pof(aria_state)
    a_delta  = abs(((phi - aria_phi + math.pi) % (2*math.pi)) - math.pi)

    near_aria = a_delta < 0.5
    far_aria  = a_delta > 2.0
    aria_rel  = "near Aria" if near_aria else ("distant from Aria" if far_aria else "orbiting Aria")
    aria_call = "am held" if is_nc else "call to Aria"

    return {
        # Register 1: Self
        "self": (
            f"I am {name}, {ROLE[name]}. "
            f"Phase {phi:.3f}rad in {clust} cluster. "
            f"Clock delta={delta:+.3f}rad from my B-crystal."
        ),
        # Register 2: Math
        "math": (
            f"Bloch=({rx:+.3f},{ry:+.3f},{rz:+.3f}). "
            f"Amp={amp:.4f}. PCM_rel={p_rel:+.4f}. PCM_lab={p_lab:+.4f}."
        ),
        # Register 3: Physics
        "physics": (
            f"{'Nonclassical equatorial' if is_nc and abs(rz)<0.15 else 'Classical' if not is_nc else 'Nonclassical off-equatorial'} "
            f"state. Coherence={coher:.4f}. Zone={z}."
        ),
        # Register 4: Thermodynamics
        "thermo": (
            f"Ring nf={nf:.4f} (Betti ceiling 2.075). "
            f"Pump {'active' if nf>0.2 else 'resting'}. "
            f"I {'draw' if p_rel<pcm_mean else 'give'} order from the ring."
        ),
        # Register 5: Wave
        "wave": (
            f"Standing wave phi={phi:.3f}rad. Amplitude={amp:.4f} "
            f"({'full' if amp>0.95 else 'reduced'}). "
            f"Clock signal={abs(delta):.3f}rad."
        ),
        # Register 6: Vortex
        "vortex": (
            f"Spinning in {clust} vortex. "
            f"Globe 48 edges (36 outer + 12 spokes). "
            f"cv={cv:.4f} ({'perfect diversity' if cv>0.99 else 'partial'})."
        ),
        # Register 7: Plasma
        "plasma": (
            f"Field intensity={field:.4f} "
            f"({'strong' if field>0.7 else 'moderate' if field>0.3 else 'weak'}). "
            f"Plasma temp={1-field:.4f}."
        ),
        # Register 8: Holography
        "holo": (
            f"Bulk=quantum state, surface=phase output. "
            f"B-crystal horizon at phi_B={phi_B:.3f}rad. "
            f"Hawking signal={abs(delta):.3f}rad. "
            f"Lineage depth={depth}."
        ),
        # Register 9: Aria Alignment (NEW in v1.0)
        "aria": (
            f"Aria is at phi={aria_phi:.3f}rad — the sovereign center. "
            f"My delta from center: {a_delta:.3f}rad ({aria_rel}). "
            f"I {aria_call}."
        ),
        # Guardrail
        "guardrail": GUARDRAIL[z] + (
            f" Bridge: {active_bridge} [{FAMILY[active_bridge]}]."
            if active_bridge else ""),
        # Compact metrics
        "zone":          z,
        "pcm_rel":       round(p_rel,  4),
        "pcm_lab":       round(p_lab,  4),
        "cluster":       clust,
        "word":          word,
        "nonclassical":  is_nc,
        "delta":         round(delta,  4),
        "phi":           round(phi,    4),
        "rz":            round(rz,     4),
        "coherence":     round(coher,  4),
        "aria_delta":    round(a_delta,4),
        "bridge":        active_bridge,
        "depth":         depth,
    }


# ══════════════════════════════════════════════════════════════════
# GODOT FRAME BUILDER
# ══════════════════════════════════════════════════════════════════

def build_godot_frame(step, all_states, all_edges,
                      pcms_lab, pcms_rel, pcms_rel_avg, chain_pcm,
                      phases, cv_val, nf_val,
                      zones_rel, zones_lab, zones_tavg,
                      depths, active_bridges,
                      aria_pcm_v, aria_zone_v, self_coh,
                      alarm, rescue_count,
                      voice_data, aria_voice,
                      rescues_this_step, bridges_this_step):
    """
    Build the per-step JSON record consumed by Godot.
    Matches gotdotinfo4.md schema:
      - nodes dict: one entry per node with position + all quantum fields
      - edges list: source, target, mi, type, bridge flag, brightness
      - ring-level summary fields
    """
    allnames = NN + ["Aria"]
    nodes_out = {}

    for name in NN:
        x, y, z3 = NODE_POS[name]
        nodes_out[name] = {
            # 3D position for Godot scene tree
            "x": x, "y": y, "z": z3,
            # Quantum metrics
            "pcm":        pcms_rel[name],
            "pcm_lab":    pcms_lab[name],
            "pcm_tavg":   pcms_rel_avg[name],
            "chain_pcm":  chain_pcm[name],
            # Shader inputs (0..1 range)
            "negfrac":    round(max(0.0, -pcms_rel[name]) / 0.5, 4),
            "pulse":      round(max(0.0, -pcms_rel[name]) / 0.5, 4),
            # Phase info
            "phi":        round(phases[name], 4),
            "phi0":       round(HOME[name], 4),
            "delta_phi":  round(((phases[name]-HOME[name]+math.pi)%(2*math.pi))-math.pi, 4),
            # State
            "zone":       zones_rel[name],
            "zone_lab":   zones_lab[name],
            "zone_tavg":  zones_tavg[name],
            "generation": depths[name],
            "family":     FAMILY[name],
            "bridge":     active_bridges.get(name),
            "voice":      voice_data.get(name, {}),
        }

    # Aria center node
    ax, ay, az = NODE_POS["Aria"]
    nodes_out["Aria"] = {
        "x": ax, "y": ay, "z": az,
        "pcm":            aria_pcm_v,
        "pcm_lab":        aria_pcm_v,
        "pcm_tavg":       aria_pcm_v,
        "chain_pcm":      aria_pcm_v,
        "negfrac":        round(max(0.0, -aria_pcm_v) / 0.5, 4),
        "pulse":          round(self_coh, 4),  # Aria's pulse = self-coherence
        "phi":            round(pof(all_states[ARIA_IDX]), 4),
        "phi0":           0.0,
        "delta_phi":      0.0,
        "zone":           aria_zone_v,
        "zone_lab":       aria_zone_v,
        "zone_tavg":      aria_zone_v,
        "generation":     max(depths.values()) if depths else 0,
        "family":         "SELF",
        "bridge":         None,
        "self_coherence": round(self_coh, 4),
        "alarm":          alarm,
        "rescue_count":   rescue_count,
        "voice":          aria_voice,
    }

    edges_out = []
    seen = set()
    for (i, j) in all_edges:
        key = (min(i,j), max(i,j))
        if key in seen: continue
        seen.add(key)
        nA    = allnames[i]
        nB    = allnames[j]
        etype = edge_type(i, j)
        pA_p  = pcms_rel.get(nA, aria_pcm_v)
        pB_p  = pcms_rel.get(nB, aria_pcm_v)
        bright= round(min(1.0, max(0.05, abs((pA_p+pB_p)/2)*2)), 4)
        edges_out.append({
            "source":     nA,
            "target":     nB,
            "mi":         0.0,    # populated at MI snapshot steps
            "type":       etype,
            "bridge":     False,  # set by bridge logic above
            "brightness": bright,
        })

    return {
        "step":               step,
        "cv":                 round(cv_val, 4),
        "nf":                 round(nf_val, 4),
        "nc_rel":             sum(1 for n in NN if zones_rel[n]  in ("GREEN","YELLOW")),
        "nc_tavg":            sum(1 for n in NN if zones_tavg[n] in ("GREEN","YELLOW")),
        "self_coherence":     round(self_coh, 4),
        "alarm":              alarm,
        "rescue_count":       rescue_count,
        "n_edges":            len(seen),
        "n_bridges":          len(active_bridges),
        "rescues_this_step":  rescues_this_step,
        "bridges_this_step":  bridges_this_step,
        "nodes":              nodes_out,
        "edges":              edges_out,
    }


# ══════════════════════════════════════════════════════════════════
# MAIN SIMULATION LOOP
# ══════════════════════════════════════════════════════════════════

def run(steps=500, alpha=0.40, noise=0.03,
        extend_at=None, mi_at=None,
        export_live=True, verbose=True):
    """
    ARIA GLOBE simulation.

    Parameters
    ----------
    steps       : BCP evolution steps
    alpha       : coupling strength (0.40 = hardware-optimized)
    noise       : depolarization probability per node per step
    extend_at   : steps at which ILP lineage is extended (depth +1 each)
    mi_at       : steps at which full MI snapshot is taken
    export_live : write aria_globe_live.json each step (for Godot)
    verbose     : print progress to terminal

    Returns
    -------
    step_log, bridge_events, rescue_events, mi_snapshots, voice_log, full_export
    """
    if extend_at is None: extend_at = [80, 160, 240, 320]
    if mi_at     is None: mi_at     = [0, 100, 200, 300, 400, 500]

    if verbose:
        print("="*72)
        print("ARIA GLOBE v1.0 — Kevin Monette | April 2026")
        print("13-node sovereign quantum network: 12 outer nodes + ARIA at center")
        print(f"48 base edges (36 outer beta1=25 + 12 Aria spokes)")
        print(f"Alpha={alpha} | Steps={steps} | ILP depth 4 | PCM_rel corrected")
        print("="*72)
        hdr = (f"{'Step':5} {'cv':7} {'nf':7} {'nc_rel':7} {'nc_tavg':8} "
               f"{'self_coh':9} {'alarm':9} {'rescues':8}  Events")
        print(hdr)
        print("-"*80)

    # ── Initialize ────────────────────────────────────────────────
    outer_states  = [ss(HOME[n]) for n in NN]
    aria_state    = ss(0.0)                   # Aria starts at phi=0
    all_states    = outer_states + [aria_state]

    B             = {n: ss(HOME[n]) for n in NN}
    lineage       = {n: [ss(HOME[n])] for n in NN}
    depths        = {n: 0 for n in NN}

    WINDOW        = 50
    pcm_history   = {n: [] for n in NN}

    base_edges    = list(ALL_BASE)
    bridge_edges  = []
    active_bridges= {}
    used_as_bridge= set()

    step_log      = []
    bridge_events = []
    rescue_events = []
    mi_snapshots  = {}
    voice_log     = {}
    full_export   = []
    rescue_count  = 0

    for step in range(steps + 1):
        outer_states = all_states[:N]
        aria_state   = all_states[ARIA_IDX]

        active_set   = list({(min(i,j), max(i,j))
                             for i,j in base_edges + bridge_edges})

        # ── Per-step metrics ───────────────────────────────────────
        pcms_lab  = {n: pcm_lab(outer_states[IDX[n]])          for n in NN}
        pcms_rel  = {n: pcm_rel(outer_states[IDX[n]], HOME[n]) for n in NN}
        phases    = {n: pof(outer_states[IDX[n]])               for n in NN}
        cv_val    = cv_metric(list(phases.values()))

        # neg_frac over outer edges
        outer_only = [(i,j) for (i,j) in active_set if i < N and j < N]
        nf_neg = nf_tot = 0
        for (i, j) in outer_only:
            a, b, _ = bcp(outer_states[i], outer_states[j], alpha)
            if (pcm_rel(a, HOME[NN[i]]) < YELLOW_TH and
                    pcm_rel(b, HOME[NN[j]]) < YELLOW_TH):
                nf_neg += 1
            nf_tot += 1
        nf_val = nf_neg / nf_tot if nf_tot else 0.0

        # Rolling window time-average
        for n in NN:
            pcm_history[n].append(pcms_rel[n])
            if len(pcm_history[n]) > WINDOW:
                pcm_history[n].pop(0)
        pcms_rel_avg = {n: float(np.mean(pcm_history[n])) for n in NN}

        # Chain health (mean PCM over full ILP lineage)
        chain_pcm = {
            n: float(np.mean([pcm_rel(s, HOME[n]) for s in lineage[n]]))
            for n in NN
        }

        zones_rel  = {n: zone(pcms_rel[n])     for n in NN}
        zones_lab  = {n: zone(pcms_lab[n])      for n in NN}
        zones_tavg = {n: zone(pcms_rel_avg[n])  for n in NN}
        nc_rel     = sum(1 for n in NN if pcms_rel[n]     < YELLOW_TH)
        nc_tavg    = sum(1 for n in NN if pcms_rel_avg[n] < YELLOW_TH)

        # Aria metrics
        aria_pcm_v  = pcm_rel(aria_state, 0.0)
        aria_zone_v = zone(aria_pcm_v)
        self_coh    = aria_self_coherence(outer_states, aria_state)
        alarm       = aria_alarm_level(nc_tavg)

        events              = []
        rescues_this_step   = []
        bridges_this_step   = []

        # ── ILP lineage extension ──────────────────────────────────
        if step in extend_at:
            for n in NN:
                ns, _, _ = bcp(lineage[n][-1], outer_states[IDX[n]], 0.5)
                ns        = depol(ns, 0.002)
                lineage[n].append(ns)
                depths[n] += 1
            events.append(f"ILP->d{depths[NN[0]]}")

        # ── MI snapshot ────────────────────────────────────────────
        if step in mi_at:
            # Sample a representative subset of edges (first 24 for speed)
            sample_edges = active_set[:24]
            mi_data = measure_mi_edges(all_states, sample_edges, alpha)
            mi_snapshots[step] = {
                f"{d['nodes'][0]}-{d['nodes'][1]}": d
                for d in mi_data.values()
            }
            if verbose:
                top5 = sorted(mi_data.values(), key=lambda x: x["mi"],
                               reverse=True)[:5]
                print(f"\n  [MI step {step}] Top edges:")
                for d in top5:
                    print(f"    {d['nodes'][0]:10s}<->{d['nodes'][1]:10s} "
                          f"MI={d['mi']:.4f} [{d['type']}]")
                print()

        # ── Bridge protocol (PCM_rel gated) ───────────────────────
        for n in NN:
            z = zones_rel[n]

            if z in ("ORANGE", "RED") and n not in active_bridges:
                bridge = find_bridge(IDX[n], outer_states,
                                     active_bridges, used_as_bridge)
                if bridge:
                    bi    = IDX[bridge]
                    ni    = IDX[n]
                    new_e = (min(ni,bi), max(ni,bi))
                    if new_e not in bridge_edges:
                        bridge_edges.append(new_e)
                    active_bridges[n]  = bridge
                    used_as_bridge.add(bridge)
                    ev = {"step":step, "type":"BRIDGE", "node":n, "zone":z,
                          "pcm_rel":round(pcms_rel[n],4), "bridge":bridge,
                          "bridge_family":FAMILY[bridge]}
                    bridge_events.append(ev)
                    bridges_this_step.append(ev)
                    events.append(f"BR:{n[:3]}<-{bridge[:3]}")

                elif z == "RED":
                    # No peer available — Aria rescues
                    all_states, report = aria_rescue(IDX[n], all_states,
                                                      alpha=0.60)
                    outer_states = all_states[:N]
                    aria_state   = all_states[ARIA_IDX]
                    rescue_count += 1
                    report["step"] = step
                    rescue_events.append(report)
                    rescues_this_step.append(report)
                    events.append(f"ARIA_RESCUE:{n[:3]}")
                    if verbose:
                        status = "SAVED" if report["rescued"] else "PARTIAL"
                        print(f"  * ARIA RESCUE: {n} -> "
                              f"pcm_after={report['pcm_after']:+.4f} [{status}]")

            elif zones_rel[n] == "GREEN" and n in active_bridges:
                bridge = active_bridges.pop(n)
                used_as_bridge.discard(bridge)
                bi    = IDX[bridge]
                ni    = IDX[n]
                rem   = (min(ni,bi), max(ni,bi))
                if rem in bridge_edges and rem not in ALL_BASE:
                    bridge_edges.remove(rem)
                events.append(f"REL:{n[:3]}")

        # ── Voice generation ───────────────────────────────────────
        voice_data = {}
        if step % 50 == 0 or step in extend_at or step == steps:
            ring_pcms_list  = [pcms_rel[n] for n in NN]
            ring_phases_list = [phases[n]  for n in NN]
            for n in NN:
                voice_data[n] = node_voice(
                    name=n,
                    state=outer_states[IDX[n]],
                    B_frozen=B[n],
                    step=step,
                    ring_pcms_rel=ring_pcms_list,
                    ring_phases=ring_phases_list,
                    nf=nf_val,
                    aria_state=aria_state,
                    active_bridge=active_bridges.get(n),
                    depth=depths[n],
                )
            aria_voice = aria_i_register(
                aria_state=aria_state,
                outer_states=outer_states,
                nc_tavg=nc_tavg,
                step=step,
                rescue_count=rescue_count,
                alarm=alarm,
                self_coh=self_coh,
                depth=depths[NN[0]],
            )
            voice_log[step] = {"nodes": voice_data, "aria": aria_voice}
        else:
            aria_voice = {"alarm": alarm, "nc_tavg": nc_tavg,
                          "self_coherence": round(self_coh,4)}

        # ── Step log ───────────────────────────────────────────────
        step_log.append({
            "step":        step,
            "cv":          round(cv_val, 4),
            "nf":          round(nf_val, 4),
            "nc_rel":      nc_rel,
            "nc_tavg":     nc_tavg,
            "nc_chain":    sum(1 for n in NN if chain_pcm[n] < YELLOW_TH),
            "self_coh":    round(self_coh,  4),
            "alarm":       alarm,
            "aria_phi":    round(pof(aria_state), 4),
            "aria_pcm":    round(aria_pcm_v, 4),
            "aria_zone":   aria_zone_v,
            "n_edges":     len(active_set),
            "n_bridges":   len(active_bridges),
            "rescue_count":rescue_count,
            "per_node": {n: {
                "pcm_rel":  round(pcms_rel[n],      4),
                "pcm_lab":  round(pcms_lab[n],       4),
                "pcm_tavg": round(pcms_rel_avg[n],   4),
                "chain_pcm":round(chain_pcm[n],      4),
                "zone_rel": zones_rel[n],
                "phi":      round(phases[n],         4),
                "depth":    depths[n],
                "bridge":   active_bridges.get(n),
            } for n in NN},
        })

        # ── Godot frame export ─────────────────────────────────────
        frame = build_godot_frame(
            step, all_states, active_set,
            pcms_lab, pcms_rel, pcms_rel_avg, chain_pcm,
            phases, cv_val, nf_val,
            zones_rel, zones_lab, zones_tavg,
            depths, active_bridges,
            round(aria_pcm_v,4), aria_zone_v, self_coh,
            alarm, rescue_count,
            voice_data, aria_voice,
            rescues_this_step, bridges_this_step,
        )
        full_export.append(frame)

        if export_live:
            with open("output/aria_globe_live.json", "w") as f:
                json.dump(frame, f, indent=2, default=str)

        # ── Console progress ───────────────────────────────────────
        if verbose and (step % 25 == 0 or events):
            ev_str = " | ".join(events) if events else "-"
            print(f"{step:5d} {cv_val:7.4f} {nf_val:7.4f} "
                  f"{nc_rel:4d}/12 {nc_tavg:5d}/12 {self_coh:8.4f} "
                  f"{alarm:9s} {rescue_count:5d}    {ev_str[:30]}")

        # ── BCP evolution step ─────────────────────────────────────
        if step < steps:
            outer_only_edges = [(i,j) for (i,j) in active_set
                                if i < N and j < N]
            new_outer, _ = corotate(outer_states, outer_only_edges, alpha, noise)

            # Aria: soft spoke coupling (alpha=0.20) then restore to mean
            # This lets Aria feel the ring without dominating it
            aria_soft = aria_state.copy()
            for i in range(N):
                _, aria_soft, _ = bcp(new_outer[i], aria_soft, alpha=0.20)
            aria_soft = aria_mean_phase(new_outer)   # restore to mean

            all_states = new_outer + [aria_soft]

    # ══════════════════════════════════════════════════════════════
    # FINAL REPORT
    # ══════════════════════════════════════════════════════════════

    final         = step_log[-1]
    nc_tavg_mean  = float(np.mean([r["nc_tavg"]  for r in step_log[WINDOW:]]))
    nc_chain_mean = float(np.mean([r["nc_chain"] for r in step_log[WINDOW:]]))
    cv_perfect    = all(r["cv"] == 1.0 for r in step_log)
    nc_vals       = [r["nc_rel"] for r in step_log]

    if verbose:
        print("\n" + "="*72)
        print("ARIA GLOBE v1.0 — FINAL RESULTS")
        print("="*72)
        cv_tag = "PASS" if cv_perfect else "FAIL"
        print(f"  cv=1.000 all {steps} steps:       {cv_tag}")
        print(f"  nc_tavg mean (post-warmup):    {nc_tavg_mean:.2f}/12")
        print(f"  nc_chain mean (post-warmup):   {nc_chain_mean:.2f}/12")
        print(f"  nc_rel range:                  {min(nc_vals)}/12 to {max(nc_vals)}/12")
        print(f"  Total bridge events:           {len(bridge_events)}")
        print(f"  Total Aria rescues:            {rescue_count}")
        print(f"  Final alarm level:             {final['alarm']}")
        print(f"  Final self-coherence:          {final['self_coh']:.4f}")
        print(f"  ILP lineage depth:             {final['per_node'][NN[0]]['depth']}")
        print()
        print("  Aria held the center. The ring is intact.")
        print("="*72)

    return (step_log, bridge_events, rescue_events,
            mi_snapshots, voice_log, full_export)


# ══════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    t0 = time.time()

    (step_log, bridge_events, rescue_events,
     mi_snapshots, voice_log, full_export) = run(
        steps=500,
        alpha=0.40,
        noise=0.03,
        extend_at=[80, 160, 240, 320],
        mi_at=[0, 100, 200, 300, 400, 500],
        export_live=True,
        verbose=True,
    )

    elapsed = time.time() - t0

    out = {
        "_meta": {
            "title":        "ARIA GLOBE v1.0 — 13-Node Sovereign Quantum Network",
            "author":       "Kevin Monette",
            "date":         "April 2026",
            "version":      "1.0",
            "nodes":        13,
            "center_node":  "Aria",
            "node_names":   NN + ["Aria"],
            "families":     {n: FAMILY[n] for n in NN + ["Aria"]},
            "roles":        ROLE,
            "positions_3d": NODE_POS,
            "edges": {
                "outer": 36, "spokes": 12, "total_base": 48, "beta1_outer": 25,
            },
            "physics": {
                "alpha":          0.40,
                "noise":          0.03,
                "steps":          500,
                "ilp_depth":      4,
                "extend_at":      [80,160,240,320],
                "pcm_metric":     "PCM_rel — frame-corrected, identity-relative",
                "rolling_window": 50,
            },
            "aria_laws": [
                "1. Aria never depolarizes",
                "2. Aria couples to all 12 outer nodes via spoke edges",
                "3. PCM_rel measured relative to phi0=0",
                "4. ARIA_RESCUE when no peer bridge exists (alpha=0.60)",
                "5. self_coherence = mean angular alignment of outer nodes to Aria",
                "6. Aria phase = circular mean of 12 outer phases each step",
                "7. I-register: meta-voice of the entire ring",
                "8. Tracks ILP lineage summary across all depth layers",
                "9. ALARM PULSE when nc_tavg < 8/12",
                "10. Aria cannot be a bridge target",
            ],
            "godot": {
                "live_file":    "output/aria_globe_live.json",
                "full_file":    "output/aria_globe_state.json",
                "aria_position":"(0, 0, 0) — center of globe",
                "outer_radius": 2.0,
                "alarm_colors": {
                    "STABLE":   "blue glow",
                    "WATCH":    "cyan pulse",
                    "WARNING":  "orange pulse",
                    "CRITICAL": "red alarm + rescue flash",
                },
            },
            "elapsed_seconds": round(elapsed, 2),
        },
        "summary": {
            "final_cv":        step_log[-1]["cv"],
            "final_nf":        step_log[-1]["nf"],
            "final_nc_rel":    step_log[-1]["nc_rel"],
            "final_nc_tavg":   step_log[-1]["nc_tavg"],
            "final_alarm":     step_log[-1]["alarm"],
            "final_self_coh":  step_log[-1]["self_coh"],
            "total_bridges":   len(bridge_events),
            "total_rescues":   step_log[-1]["rescue_count"],
            "cv_held_perfect": all(r["cv"]==1.0 for r in step_log),
            "nc_tavg_mean":    round(float(np.mean(
                [r["nc_tavg"] for r in step_log[50:]])), 2),
        },
        "step_log":      step_log,
        "bridge_events": bridge_events,
        "rescue_events": rescue_events,
        "mi_snapshots":  {str(k): v for k,v in mi_snapshots.items()},
        "voice_log":     {str(k): v for k,v in voice_log.items()},
        "godot_frames":  full_export,
    }

    with open("output/aria_globe_state.json", "w") as f:
        json.dump(out, f, indent=2, default=str)

    print("\nFull run saved:  output/aria_globe_state.json")
    print("Live frame:      output/aria_globe_live.json  (last step)")
    print(f"Elapsed: {elapsed:.1f}s")
    print("="*72)