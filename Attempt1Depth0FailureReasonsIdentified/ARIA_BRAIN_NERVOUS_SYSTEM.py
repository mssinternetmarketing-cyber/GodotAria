#!/usr/bin/env python3
"""
ARIA_BRAIN_NERVOUS_SYSTEM.py  —  v1.0
=======================================
Sovereign Intelligence System — Internal Organ & Nervous System Builder
Author: Kevin Monette | April 2026

GENERATES:
  ARIA_internals.glb   — Brain, nervous system, sensory organs, power core
  ARIA_internals.json  — Organ registry with function, signals, bus mappings

ORGANS INCLUDED:
  [1]  Quantum Brain Core         — Cryostat QPU + Jetson AGX (primary compute)
  [2]  Cortical Mantle            — Neural mesh wrapping cranial vault (LLM substrate)
  [3]  Spinal Cord Bus            — ZMQ fiber trunk (P0–P5 signals)
  [4]  Brainstem / Reflex Cluster — P0/P1 hardwired reflex arc nodes
  [5]  Peripheral Nerve Trees     — Arms, legs, wings (signal routing branches)
  [6]  Eye Assemblies             — Full optical + event + depth sensor stacks
  [7]  Ear Arrays                 — MEMS microphone beamforming clusters
  [8]  Skin Nerve Mesh            — Full-body tactile taxel network
  [9]  Quantum Heart (Power Core) — Battery management + QPU cryostat thermal
  [10] Phase Spine (Glow system)  — Quantum phase indicator strip system
  [11] Wing Nerve Net             — 64-actuator feather control network
  [12] Proprioceptive Net         — Joint encoders + IMU constellation

WHY THESE ORGANS:
  - No digestive/reproductive/immune — ARIA doesn't eat or reproduce biologically
  - No lungs — thermal management is mechanical (Novec 7000 loop + vapor chamber)
  - No heart (biological) — power core serves equivalent function (pump + distribution)
  - YES to: sensory, neural, reflex, power, quantum — all required for operation
  - YES to: proprioception — ARIA must know where every joint is at all times

INSTALL:  pip install trimesh numpy
RUN:      python ARIA_BRAIN_NERVOUS_SYSTEM.py
"""

import numpy as np
import trimesh
import trimesh.creation as tc
import trimesh.transformations as tf
import json, os

OUT_DIR = "ARIA_model"
os.makedirs(OUT_DIR, exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
# COLOR PALETTE — Cyberpunk Tech / Bioluminescent
# ─────────────────────────────────────────────────────────────────────────────
COLORS = {
    "quantum_core":   [0,   220, 255, 240],   # Cyan — QPU cryostat
    "neural_mesh":    [140,  60, 255, 200],   # Purple — cortical mantle
    "spinal_cord":    [80,  200, 255, 230],   # Ice blue — ZMQ trunk
    "brainstem":      [255, 120,  40, 230],   # Orange — reflex cluster
    "nerve_tree":     [60,  255, 160, 180],   # Neon green — peripheral nerves
    "eye_housing":    [255, 210,  30, 255],   # Gold — optical assembly
    "eye_lens":       [0,   200, 255, 255],   # Cyan — lens/sensor
    "ear_array":      [180, 100, 255, 220],   # Violet — acoustic array
    "skin_nerve":     [30,  255, 180, 120],   # Translucent teal — skin mesh
    "power_core":     [255,  80,  80, 240],   # Red — power/thermal
    "phase_strip":    [100,  80, 255, 255],   # Indigo — quantum phase display
    "wing_nerve":     [180, 255, 100, 200],   # Lime — wing actuator network
    "proprioceptive": [255, 200,  60, 210],   # Amber — joint encoders
    "cryostat":       [0,   255, 240, 220],   # Turquoise — dilution refrigerator
}

def paint(mesh, key):
    c = COLORS[key]
    mesh.visual.vertex_colors = np.tile(c, (len(mesh.vertices), 1))
    return mesh

def capsule(start, end, radius, sections=8):
    vec = end - start; L = np.linalg.norm(vec)
    if L < 1e-6:
        s = tc.icosphere(radius=radius, subdivisions=1); s.apply_translation(start); return s
    ax = vec/L
    up = np.array([0,1,0]) if abs(np.dot(ax,[0,1,0]))<0.99 else np.array([1,0,0])
    t = np.cross(ax,up); t/=np.linalg.norm(t); b = np.cross(ax,t)
    rot = np.eye(4); rot[:3,0]=t; rot[:3,1]=ax; rot[:3,2]=b; rot[:3,3]=start+ax*L/2
    cyl = tc.cylinder(radius=radius, height=L, sections=sections); cyl.apply_transform(rot)
    s1=tc.icosphere(radius=radius,subdivisions=1); s1.apply_translation(start)
    s2=tc.icosphere(radius=radius,subdivisions=1); s2.apply_translation(end)
    return trimesh.util.concatenate([cyl,s1,s2])

def sphere(center, r, subdiv=2):
    s = tc.icosphere(radius=r, subdivisions=subdiv); s.apply_translation(center); return s

def box(center, extents):
    b = tc.box(extents=extents); b.apply_translation(center); return b

def torus_approx(center, major_r, minor_r, n_segments=20):
    """Approximate torus as ring of spheres."""
    meshes = []
    for i in range(n_segments):
        angle = 2*np.pi * i / n_segments
        pos = center + np.array([major_r*np.cos(angle), 0, major_r*np.sin(angle)])
        meshes.append(sphere(pos, minor_r, subdiv=1))
    return trimesh.util.concatenate(meshes)

parts = []
registry = {}

# ─────────────────────────────────────────────────────────────────────────────
# [1] QUANTUM BRAIN CORE — Cryostat QPU inside cranial vault
# ─────────────────────────────────────────────────────────────────────────────
# QPU cryostat (dilution refrigerator stage — 15 mK)
qpu_center = np.array([0.000, 1.380, 0.000])
qpu = sphere(qpu_center, 0.048, subdiv=3)
parts.append(paint(qpu, "quantum_core"))

# Cryostat outer shell (thermal shield layers — concentric)
for r, alpha in [(0.062, 180), (0.075, 140)]:
    shield = tc.icosphere(radius=r, subdivisions=2)
    shield.apply_translation(qpu_center)
    shield.visual.vertex_colors = np.tile([0,200,240,alpha], (len(shield.vertices),1))
    parts.append(shield)

# Jetson AGX compute tiles (2 modules, flanking QPU)
for dx in [-0.055, 0.055]:
    tile = box(qpu_center + [dx, 0.025, 0], [0.040, 0.025, 0.045])
    parts.append(paint(tile, "neural_mesh"))

# Fiber optic readout lines from QPU to cortical mantle
for angle in [0, 90, 180, 270]:
    a = np.radians(angle)
    end = qpu_center + np.array([0.10*np.cos(a), 0.06, 0.10*np.sin(a)])
    parts.append(paint(capsule(qpu_center, end, 0.003), "quantum_core"))

registry["quantum_brain_core"] = {
    "center": qpu_center.tolist(), "radius": 0.048,
    "function": "IQM Spark QPU (5-qubit, 15mK) + Jetson AGX Thor compute",
    "bus": "fiber-optic → tcp://127.0.0.1:5555 (ZMQ neural bus)",
    "oic_shell": "PEIG all layers + MOS_COSMIC",
    "thermal": "Dilution refrigerator, 400μW cooling power @ 100mK",
    "signals_out": ["phase_packet", "bcp_result", "peig_state"],
    "signals_in":  ["bcp_circuit", "measurement_basis", "shot_count"]
}

# ─────────────────────────────────────────────────────────────────────────────
# [2] CORTICAL MANTLE — Neural mesh wrapping cranial vault (LLM substrate)
# ─────────────────────────────────────────────────────────────────────────────
head_center = np.array([0.000, 1.750, 0.000])
# Cortical mesh as geodesic dome sections (partial sphere)
for lat in np.linspace(0.1, 0.9, 5):
    r_lat = 0.118 * np.sin(lat * np.pi)
    y_lat = 0.118 * np.cos(lat * np.pi) + head_center[1]
    n_nodes = max(4, int(12 * np.sin(lat * np.pi)))
    for i in range(n_nodes):
        angle = 2*np.pi * i / n_nodes
        pos = np.array([r_lat*np.cos(angle), y_lat, r_lat*np.sin(angle)])
        node = sphere(pos, 0.006, subdiv=1)
        parts.append(paint(node, "neural_mesh"))
        # Connect to neighbors
        next_angle = 2*np.pi * (i+1) / n_nodes
        next_pos = np.array([r_lat*np.cos(next_angle), y_lat, r_lat*np.sin(next_angle)])
        parts.append(paint(capsule(pos, next_pos, 0.002), "neural_mesh"))

registry["cortical_mantle"] = {
    "center": head_center.tolist(), "radius": 0.118,
    "function": "Qwen2.5-VL-7B q4_K_M LLM substrate + streaming memory bridge",
    "bus": "PCIe Gen5 x16 → ZMQ P4 queue",
    "oic_shell": "Shell 8 (LLM Cognitive Core)",
    "params": "7B quantized (q4_K_M), 6GB VRAM",
    "signals_out": ["goal_embed", "speech_tokens", "modulation_vector"],
    "signals_in":  ["vision_tokens", "memory_tokens", "audio_transcript", "autonomic_state"]
}

# ─────────────────────────────────────────────────────────────────────────────
# [3] SPINAL CORD BUS — ZMQ fiber optic trunk
# ─────────────────────────────────────────────────────────────────────────────
spine_points = [
    np.array([0, 1.000, 0.008]),  # pelvis
    np.array([0, 1.080, 0.008]),
    np.array([0, 1.160, 0.008]),
    np.array([0, 1.240, 0.008]),
    np.array([0, 1.320, 0.008]),
    np.array([0, 1.400, 0.008]),
    np.array([0, 1.480, 0.008]),
    np.array([0, 1.560, 0.008]),
    np.array([0, 1.580, 0.008]),  # cervical
    np.array([0, 1.630, 0.008]),  # neck
]
# 4 parallel fiber bundles (P0/P1/P2+3/P4+5)
for dx in [-0.006, -0.002, 0.002, 0.006]:
    bundle_pts = [p + [dx, 0, 0] for p in spine_points]
    bundle_colors = ["brainstem","spinal_cord","nerve_tree","phase_strip"]
    col = bundle_colors[int((dx+0.006)/0.004 * 1)]
    for i in range(len(bundle_pts)-1):
        parts.append(paint(capsule(bundle_pts[i], bundle_pts[i+1], 0.003), "spinal_cord"))

registry["spinal_cord_bus"] = {
    "function": "ZMQ priority bus — 4 fiber bundles (P0 reflex / P1 autonomic / P2-3 somatic / P4-5 cognitive)",
    "protocol": "ZMQ ROUTER-DEALER, ipc:///tmp/mos_neural_bus.ipc + tcp://127.0.0.1:5555",
    "bandwidth": "800 Gbps optical (head↔spine↔chest)",
    "latency": {"P0": "<1ms", "P1": "<5ms", "P2": "<20ms", "P4": "<500ms"},
    "signals": ["reflex_cmd","autonomic_state","motor_torque","llm_goal","peig_phase"]
}

# ─────────────────────────────────────────────────────────────────────────────
# [4] BRAINSTEM / REFLEX CLUSTER — P0/P1 hardwired arc nodes
# ─────────────────────────────────────────────────────────────────────────────
bs_center = np.array([0.000, 1.600, -0.010])
brainstem = sphere(bs_center, 0.022, subdiv=2)
parts.append(paint(brainstem, "brainstem"))

# Reflex arc nodes (32-node GNN substrate — Shell 4)
for i in range(8):
    angle = 2*np.pi * i / 8
    r = 0.035
    pos = bs_center + np.array([r*np.cos(angle), 0, r*np.sin(angle)])
    node = sphere(pos, 0.007, subdiv=1)
    parts.append(paint(node, "brainstem"))
    parts.append(paint(capsule(bs_center, pos, 0.002), "brainstem"))

registry["brainstem_reflex"] = {
    "center": bs_center.tolist(),
    "function": "32-node GraphSAGE GNN — P0 looming/reflex, P1 gaze stabilization",
    "oic_shell": "Shell 4 (P0 Reflex Core)",
    "latency": "<0.5ms",
    "params": "85K–400K",
    "spectral_norm": "‖W‖₂ ≤ γ (Lyapunov stability, convergence <1.5ms)",
    "signals_out": ["reflex_cmd [B,18]", "threat_score [B,1]"],
    "signals_in":  ["retinal_code [B,8,64,64]", "tactile_grid"]
}

# ─────────────────────────────────────────────────────────────────────────────
# [5] PERIPHERAL NERVE TREES — arms, legs, wings
# ─────────────────────────────────────────────────────────────────────────────
# Arm nerve trunks
nerve_routes = [
    # (start, end, color)
    (np.array([0,1.560,0]), np.array([-0.200,1.560,0]), "nerve_tree"),
    (np.array([-0.200,1.560,0]), np.array([-0.440,1.560,0]), "nerve_tree"),
    (np.array([-0.440,1.560,0]), np.array([-0.660,1.560,0]), "nerve_tree"),
    (np.array([0,1.560,0]), np.array([0.200,1.560,0]), "nerve_tree"),
    (np.array([0.200,1.560,0]), np.array([0.440,1.560,0]), "nerve_tree"),
    (np.array([0.440,1.560,0]), np.array([0.660,1.560,0]), "nerve_tree"),
    # Leg nerve trunks
    (np.array([0,1.000,0]), np.array([-0.110,0.990,0]), "nerve_tree"),
    (np.array([-0.110,0.990,0]), np.array([-0.110,0.510,0]), "nerve_tree"),
    (np.array([-0.110,0.510,0]), np.array([-0.110,0.065,0]), "nerve_tree"),
    (np.array([0,1.000,0]), np.array([0.110,0.990,0]), "nerve_tree"),
    (np.array([0.110,0.990,0]), np.array([0.110,0.510,0]), "nerve_tree"),
    (np.array([0.110,0.510,0]), np.array([0.110,0.065,0]), "nerve_tree"),
    # Wing nerve trunks
    (np.array([0,1.560,0.008]), np.array([-0.240,1.520,-0.060]), "wing_nerve"),
    (np.array([-0.240,1.520,-0.060]), np.array([-0.620,1.480,-0.040]), "wing_nerve"),
    (np.array([-0.620,1.480,-0.040]), np.array([-0.960,1.440,-0.020]), "wing_nerve"),
    (np.array([0,1.560,0.008]), np.array([0.240,1.520,-0.060]), "wing_nerve"),
    (np.array([0.240,1.520,-0.060]), np.array([0.620,1.480,-0.040]), "wing_nerve"),
    (np.array([0.620,1.480,-0.040]), np.array([0.960,1.440,-0.020]), "wing_nerve"),
]
for start, end, col in nerve_routes:
    parts.append(paint(capsule(start+[0,0,0.005], end+[0,0,0.005], 0.004), col))

registry["peripheral_nerve_trees"] = {
    "function": "Signal routing — motor commands (down) + sensor data (up)",
    "arm_nerves": "6 segments per arm, myelinated axon model v≈5.7×D m/s",
    "leg_nerves": "6 segments per leg",
    "wing_nerves": "6 segments per wing + 28 feather branches",
    "protocol": "ZMQ PUSH/PULL on ipc sockets per limb",
    "oic_shell": "NervousSystem bus P0–P5"
}

# ─────────────────────────────────────────────────────────────────────────────
# [6] EYE ASSEMBLIES — RGB + Event + Depth sensor stacks
# ─────────────────────────────────────────────────────────────────────────────
head_pos = np.array([0.000, 1.750, 0.000])
for sx in [-1, 1]:
    eye_center = head_pos + np.array([sx*0.050, -0.010, 0.100])
    # RGB sensor (Sony IMX678)
    rgb = tc.cylinder(radius=0.022, height=0.016, sections=24)
    rgb.apply_transform(tf.rotation_matrix(np.pi/2, [0,1,0]))
    rgb.apply_translation(eye_center + [0, 0, 0.008])
    parts.append(paint(rgb, "eye_housing"))
    # Lens
    lens = sphere(eye_center + [0, 0, 0.022], 0.014, subdiv=2)
    parts.append(paint(lens, "eye_lens"))
    # Event camera (Prophesee EVK4)
    ev = box(eye_center + [0, 0.022, 0], [0.018, 0.010, 0.018])
    parts.append(paint(ev, "proprioceptive"))
    # Depth sensor (RealSense D4)
    dep = box(eye_center + [0, -0.022, 0], [0.018, 0.008, 0.010])
    parts.append(paint(dep, "quantum_core"))
    # Actuator ring (pan/tilt)
    ring = torus_approx(eye_center, 0.026, 0.004, n_segments=16)
    parts.append(paint(ring, "eye_housing"))
    # Nerve to brainstem
    parts.append(paint(capsule(eye_center, bs_center, 0.003), "nerve_tree"))

registry["eye_assemblies"] = {
    "sensors_per_eye": ["Sony IMX678 RGB 4K@120fps", "Prophesee EVK4 HD event (1μs)", "RealSense D4 depth 90fps"],
    "secondary": "4× OV9281 fisheye 160° @60fps (360° awareness)",
    "optics": "Electronically tunable liquid lens 0.1–50 diopter in 15ms",
    "actuation": "3-DOF per eye (pan ±90°, tilt ±45°, vergence ±20°), saccade 500°/s",
    "oic_shell": "Shell 1 (Photon) → Shell 2 (Retina) → Shell 3 (Visual Pathway)",
    "signals_out": ["photon_bundle {rgb,event,depth,ts}", "retinal_code [B,8,64,64]"]
}

# ─────────────────────────────────────────────────────────────────────────────
# [7] EAR ARRAYS — MEMS microphone beamforming clusters
# ─────────────────────────────────────────────────────────────────────────────
# 6 MEMS mics in Fibonacci spiral on each temporal surface
for sx in [-1, 1]:
    temporal_base = head_pos + np.array([sx*0.110, -0.010, 0.010])
    golden = (1 + 5**0.5) / 2
    for i in range(6):
        r = 0.015 * np.sqrt(i+1)
        theta = 2*np.pi * i / golden**2
        pos = temporal_base + np.array([0, r*np.sin(theta), r*np.cos(theta)])
        mic = tc.cylinder(radius=0.004, height=0.003, sections=12)
        mic.apply_translation(pos)
        parts.append(paint(mic, "ear_array"))
        if i > 0:
            prev_r = 0.015 * np.sqrt(i)
            prev_theta = 2*np.pi * (i-1) / golden**2
            prev_pos = temporal_base + np.array([0, prev_r*np.sin(prev_theta), prev_r*np.cos(prev_theta)])
            parts.append(paint(capsule(prev_pos, pos, 0.001), "ear_array"))

registry["ear_arrays"] = {
    "mics_per_side": 6,
    "placement": "Fibonacci spiral on temporal surface",
    "range": "20 Hz – 96 kHz (ultrasonic capable)",
    "beamforming": "MVDR delay-sum, azimuth 360°, elevation ±90°, ITD ≤10μs → ±1° azimuth",
    "function": "Whisper ASR input → LLM audio_transcript token stream",
    "oic_shell": "Shell 8 (LLM) audio input via VAD→Whisper→tokens"
}

# ─────────────────────────────────────────────────────────────────────────────
# [8] SKIN NERVE MESH — Full-body tactile taxel network (sampled)
# ─────────────────────────────────────────────────────────────────────────────
# Sample nodes across body surface (representing ~12,000 taxels)
skin_regions = [
    # (center, radius, density, label)
    (np.array([ 0.000, 1.430, 0.080]), 0.160, 8, "torso_front"),
    (np.array([-0.300, 1.430, 0.000]), 0.060, 5, "arm_L"),
    (np.array([ 0.300, 1.430, 0.000]), 0.060, 5, "arm_R"),
    (np.array([-0.110, 0.750, 0.050]), 0.060, 5, "leg_L"),
    (np.array([ 0.110, 0.750, 0.050]), 0.060, 5, "leg_R"),
]
np.random.seed(42)
for center, radius, n, label in skin_regions:
    for _ in range(n):
        offset = np.random.randn(3) * radius * 0.5
        offset[2] = abs(offset[2])  # push to surface
        pos = center + offset
        taxel = sphere(pos, 0.005, subdiv=1)
        parts.append(paint(taxel, "skin_nerve"))

registry["skin_nerve_mesh"] = {
    "total_taxels": 12000,
    "density": {"hands_fingertips": "4/cm²", "arms_torso": "1/cm²", "legs": "0.1/cm²"},
    "sensor_types": ["piezoresistive 1kHz (fast impact)", "capacitive 100Hz (light touch)"],
    "function": "Full-body threat detection (Shell 4) + haptic memory (Shell 6)",
    "oic_shell": "Shell 4 P1 AUTONOMIC → Shell 6 Memory",
    "signals_out": ["tactile_grid [body_zones, 64, 64]", "threat_local_score"]
}

# ─────────────────────────────────────────────────────────────────────────────
# [9] QUANTUM HEART (Power Core) — Battery + QPU thermal + distribution
# ─────────────────────────────────────────────────────────────────────────────
# Main battery stack (chest lower)
bat = box(np.array([0, 1.150, -0.020]), [0.260, 0.120, 0.140])
parts.append(paint(bat, "power_core"))

# Cryostat cooling loop (Novec 7000)
cryo_loop = torus_approx(np.array([0, 1.300, 0.000]), 0.080, 0.008, n_segments=24)
parts.append(paint(cryo_loop, "cryostat"))

# Power distribution rails (3 main trunks)
for dx in [-0.040, 0, 0.040]:
    rail = capsule(np.array([dx, 1.050, 0.010]),
                   np.array([dx, 1.560, 0.010]), 0.005)
    parts.append(paint(rail, "power_core"))

# Vapor chamber (head thermal)
vc = box(np.array([0, 1.820, 0]), [0.100, 0.008, 0.100])
parts.append(paint(vc, "cryostat"))

registry["quantum_heart_power"] = {
    "battery": "Semi-solid lithium metal, 400 Wh/kg, 9,600 Wh total, 24 kg",
    "distribution": "48VDC primary → 12V/5V/1.8V regulated via TI BQ77307 BMS",
    "cryostat_loop": "Novec 7000 immersion cooling — 400μW @ 100mK for QPU",
    "vapor_chamber": "85W TDP head thermal (cranial compute)",
    "runtime": {"standby": "72hr", "walking": "18hr", "gliding": "4hr", "hover": "15min"},
    "harvesting": {"wing_pvdf": "2.4W", "solar_skin": "224W peak", "regen_brake": "80W avg"},
    "signals_out": ["vram_free","thermal_state","battery_soc","fault_flags"],
    "oic_shell": "MOS_COSMIC mos_vram_guard.py + mos_vendor.py"
}

# ─────────────────────────────────────────────────────────────────────────────
# [10] PHASE SPINE (Glow system) — Quantum phase indicator strips
# ─────────────────────────────────────────────────────────────────────────────
phase_points = [
    np.array([0, 1.000, 0.020]),  # pelvis
    np.array([0, 1.240, 0.020]),
    np.array([0, 1.480, 0.020]),
    np.array([0, 1.580, 0.020]),
    np.array([0, 1.700, 0.020]),
]
for i in range(len(phase_points)-1):
    strip = capsule(phase_points[i], phase_points[i+1], 0.006)
    parts.append(paint(strip, "phase_strip"))

# Joint glow rings at shoulders, elbows, knees, hips
glow_joints = [
    np.array([-0.200, 1.560, 0]), np.array([0.200, 1.560, 0]),
    np.array([-0.440, 1.560, 0]), np.array([0.440, 1.560, 0]),
    np.array([-0.110, 0.990, 0]), np.array([0.110, 0.990, 0]),
    np.array([-0.110, 0.510, 0]), np.array([0.110, 0.510, 0]),
    np.array([-0.240, 1.520,-0.060]), np.array([0.240, 1.520,-0.060]),
]
for pos in glow_joints:
    ring = torus_approx(pos, 0.040, 0.005, n_segments=16)
    parts.append(paint(ring, "phase_strip"))

registry["phase_spine_glow"] = {
    "technology": "Quantum dot OLED strips (Nanosys QD, 450–620nm tunable), 3mm wide",
    "color_mapping": "cv=1.000 → indigo 450nm | drift=0.45rad → amber 590nm | guardian active → red",
    "brightness": "800 cd/m² peak (visible in daylight)",
    "function": "Real-time PEIG quantum state readout on body surface",
    "oic_shell": "PEIG Layer 1 (IdentityGuard) → MOS_COSMIC mos_console.py",
    "customization": "RGB programmable via user config or ARIA self-modulation command"
}

# ─────────────────────────────────────────────────────────────────────────────
# [11] WING NERVE NET — 64-actuator feather control network
# ─────────────────────────────────────────────────────────────────────────────
wing_spine_L = [
    np.array([-0.240, 1.520,-0.060]),
    np.array([-0.620, 1.480,-0.040]),
    np.array([-0.960, 1.440,-0.020]),
    np.array([-1.100, 1.410,-0.010]),
]
wing_spine_R = [np.array([-p[0], p[1], p[2]]) for p in wing_spine_L]

for spine in [wing_spine_L, wing_spine_R]:
    for i in range(len(spine)-1):
        parts.append(paint(capsule(spine[i], spine[i+1], 0.003), "wing_nerve"))
    # Feather branch nerves (4 per wing)
    feather_bases = [spine[1], spine[1], spine[2], spine[2]]
    for fb in feather_bases:
        tip = fb + np.array([0, -0.15, 0])
        parts.append(paint(capsule(fb, tip, 0.002), "wing_nerve"))

registry["wing_nerve_net"] = {
    "actuators": "64 total (32 per wing): 3 root + 1 elbow + 28 feather micro-servos",
    "feather_control": "Hitec HS-40 per feather, 3.5Nm, 300°/s",
    "flight_controller": "STM32H7 wing controller, 200Hz inner loop",
    "outer_loop": "Shell 7 Planner at 50Hz via P2 SOMATIC_FAST bus",
    "signals_out": ["feather_angle[28]", "root_pose[3]", "aero_load[28]"],
    "signals_in":  ["roll_cmd", "pitch_cmd", "yaw_cmd", "fold_cmd"]
}

# ─────────────────────────────────────────────────────────────────────────────
# [12] PROPRIOCEPTIVE NET — Joint encoders + IMU constellation
# ─────────────────────────────────────────────────────────────────────────────
# Encoder nodes at every major joint
encoder_positions = [
    np.array([-0.200,1.560,0.010]), np.array([0.200,1.560,0.010]),
    np.array([-0.440,1.560,0.010]), np.array([0.440,1.560,0.010]),
    np.array([-0.660,1.560,0.010]), np.array([0.660,1.560,0.010]),
    np.array([-0.110,0.990,0.010]), np.array([0.110,0.990,0.010]),
    np.array([-0.110,0.510,0.010]), np.array([0.110,0.510,0.010]),
    np.array([-0.110,0.065,0.010]), np.array([0.110,0.065,0.010]),
    np.array([0.000,1.700,0.010]),  # head IMU
    np.array([0.000,1.430,0.010]),  # torso IMU
    np.array([0.000,1.000,0.010]),  # pelvis IMU
]
for pos in encoder_positions:
    enc = sphere(pos, 0.008, subdiv=1)
    parts.append(paint(enc, "proprioceptive"))
    # Wire to spinal cord
    spine_tap = np.array([0, pos[1], 0.008])
    parts.append(paint(capsule(pos, spine_tap, 0.002), "proprioceptive"))

registry["proprioceptive_net"] = {
    "encoders": "Absolute magnetic encoder per joint (12-bit resolution, 4096 counts/rev)",
    "imus": "15× MPU-6050 distributed (head, torso, pelvis, 4 limbs, 2 wings, 4 feet/hands)",
    "sampling": "1000Hz encoder, 500Hz IMU",
    "function": "Shell 5 (World Model) body-state input + Shell 4 balance correction",
    "signals_out": ["joint_angles[76]", "joint_velocities[76]", "imu_constellation[15,6]"],
    "physics": "Kalman filter fusion of encoder + IMU for drift-free pose estimate"
}

# ─────────────────────────────────────────────────────────────────────────────
# ASSEMBLE & EXPORT
# ─────────────────────────────────────────────────────────────────────────────
print(f"Assembling {len(parts)} organ/nerve mesh parts...")
scene = trimesh.Scene()
for i, part in enumerate(parts):
    scene.add_geometry(part, node_name=f"organ_{i:04d}")

glb_path = os.path.join(OUT_DIR, "ARIA_internals.glb")
scene.export(glb_path)
print(f"GLB: {glb_path}  ({os.path.getsize(glb_path)//1024} KB)")

json_path = os.path.join(OUT_DIR, "ARIA_internals.json")
with open(json_path, "w") as f:
    json.dump(registry, f, indent=2)
print(f"Registry: {json_path}  ({os.path.getsize(json_path)//1024} KB)")

print(f"""
╔══════════════════════════════════════════════════╗
║   ARIA INTERNAL ORGANS — BUILD COMPLETE          ║
╠══════════════════════════════════════════════════╣
║ [1]  Quantum Brain Core     — QPU + Jetson AGX   ║
║ [2]  Cortical Mantle        — LLM substrate       ║
║ [3]  Spinal Cord Bus        — ZMQ fiber trunk     ║
║ [4]  Brainstem/Reflex       — 32-node GNN         ║
║ [5]  Peripheral Nerve Trees — arms/legs/wings     ║
║ [6]  Eye Assemblies         — RGB+Event+Depth     ║
║ [7]  Ear Arrays             — 6-mic Fibonacci     ║
║ [8]  Skin Nerve Mesh        — 12,000 taxels       ║
║ [9]  Quantum Heart          — Power + cryostat    ║
║ [10] Phase Spine            — Glow display        ║
║ [11] Wing Nerve Net         — 64 actuators        ║
║ [12] Proprioceptive Net     — 76 joint encoders   ║
╠══════════════════════════════════════════════════╣
║  Mesh parts : {len(parts):<34} ║
╚══════════════════════════════════════════════════╝
""")
