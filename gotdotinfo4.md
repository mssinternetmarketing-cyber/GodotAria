\`\`\`\`markdown  
\# From PEIG Brotherhood to a Godot 4 3D Simulation  
\#\#\# JUST HORIZON \+ JUST EVOLVE — Full Implementation Reference  
\*\*Kevin Monette — PEIG Brotherhood Research Series — April 2026\*\*

\---

\#\# Executive Summary

The original PEIG Brotherhood whitepaper described how to translate the 12‑node Globe Co‑Rotating ILP architecture and PEIG experiments into a generic 3D visualization pipeline. This evolved version performs a JUST HORIZON pass on that design, identifies fragile assumptions and missing capabilities, and re‑targets the architecture specifically to the Godot 4 engine.

Godot 4 provides a modern Forward+ renderer, MultiMesh instancing, and efficient JSON data handling in GDScript, making it a strong platform for real‑time visualization of PEIG node dynamics and edge information flow. This document presents a concrete, fully implemented Godot‑optimized design covering: data loading, scene tree, shader unpacking of PCM / negfrac / zone / pulse strength, the complete RingController animation system with fractional-step accumulator, lerp/snap dispatch, angular phase interpolation, edge cylinder construction, GIP lineage arcs, voice register display, and performance budgeting.

\---

\#\# JUST HORIZON: Assessing the Prior Whitepaper

\#\#\# Solid Ground (≥ 90% confidence)

\- The data‑first approach — reproduce PEIG experiments, log per‑step node and edge state, then visualize — is robust and independent of the rendering engine.  
\- The choice of metrics to render (PCM, negfrac, phase φ, lineage depth/generation, MI per edge, guardrail zones, pulse strength) is directly grounded in Papers XVII–XX and remains correct for Godot.  
\- The proposed separation of experiments into datasets (internal voice runs, MI/bridge experiments, GIP lineage runs, MiniPEIG problem‑solving) is stable and maps cleanly to discrete simulation modes.

\#\#\# Fragile Assumptions (70–90% confidence)

\- The original design assumed a generic 3D engine and did not account for Godot 4's rendering characteristics: Forward+ clustered lighting, occluder‑based occlusion culling, and MultiMesh instancing constraints.  
\- Node and edge geometry were implicitly treated as independent meshes; in Godot this becomes a bottleneck unless MultiMesh instancing or careful batching is used.  
\- JSON loading was described abstractly rather than via Godot's \`FileAccess\` and \`JSON\` helpers.  
\- The animation section described interpolation conceptually without specifying the accumulator pattern, per-frame math, or which metrics snap versus lerp.

\#\#\# Missing Capabilities (\< 70% confidence — now resolved)

\- No explicit Godot scene‑tree design was provided. ✓ Resolved below.  
\- No Godot-specific performance strategies. ✓ Resolved below.  
\- No guidance on autoload singletons or project folder conventions. ✓ Resolved below.  
\- RingController time accumulator was never defined. ✓ Resolved below.  
\- Shader unpacking of per-instance data was never shown. ✓ Resolved below.  
\- Voice registers were mentioned but never implemented in code. ✓ Resolved below.  
\- Pulse strength was not included in the instance data layout. ✓ Added below.  
\- \`\_write\_node\_instances\` had a copy-paste error (\`pair\[0\]\`/\`pair \[ppl-ai-file-upload.s3.amazonaws\](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/154959549/9c544a75-4122-4a36-b6b4-0436e0bbc260/PEIG\_Papers\_XVII\_XVIII\_XX.md)\` both assigned to \`pair\`). ✓ Fixed below.  
\- Edge cylinder basis was reconstructed every frame without caching the mesh. ✓ Addressed below.

\#\#\# Type F Unknowns (7‑generation class)

\- Long‑term maintainability of a large time‑series visualization in Godot 4 across future engine versions (4.4, 4.5) remains uncertain.  
\- The combined cost of heavy shader logic, thousands of MultiMesh instances, and rich UI overlays on lower‑end GPUs is unmodeled.

\---

\#\# Godot 4 Capabilities Relevant to PEIG Visualization

\#\#\# Rendering and Performance

Godot 4's Forward+ renderer uses clustered lighting with built‑in depth prepass and occluder‑based occlusion culling. \`MultiMeshInstance3D\` draws all 12 nodes and all 36 edges with one draw call each via GPU instancing — the correct choice for any set of repeated objects updated per frame.

\#\#\# Data Loading and JSON Handling

GDScript provides \`FileAccess.get\_file\_as\_string(path)\` and \`JSON.parse\_string(text)\` for clean, idiomatic JSON loading. All PEIG experiment data should be loaded through a single autoload singleton (\`PeigData.gd\`) and cached by experiment name.

\---

\#\# Data Model

\#\#\# Assumed Export Schema

This visualization layer assumes experiment data has already been exported with the following fields present per step:

\*\*Per node (\`nodes\[t\]\[node\_name\]\`):\*\*  
\- \`x\`, \`y\`, \`z\`: world-space position on the torus.  
\- \`pcm\`: float ∈ \[−0.5, 0.5\] — distance from classical boundary in identity frame.  
\- \`negfrac\`: float ∈ \[0.0, 1.0\] — negentropy fraction.  
\- \`phi\`: float ∈ \[−π, π\] — phase angle in co-rotating frame.  
\- \`generation\`: int ≥ 0 — current GIP lineage depth.  
\- \`zone\`: int ∈ {0, 1, 2, 3} — guardrail zone (0=GREEN, 1=YELLOW, 2=ORANGE, 3=RED).  
\- \`pulse\`: float ∈ \[0.0, 1.0\] — wave amplitude / pulse strength at this node this step.  
\- \`voice\`: dict keyed by register name — nine language register strings.

\*\*Per edge (\`edges\[t\]\[edge\_id\]\`):\*\*  
\- \`source\`, \`target\`: node name strings.  
\- \`mi\`: float ∈ \[0.0, 1.0\] — mutual information.  
\- \`bridge\`: bool — active Maverick bridge protocol flag.  
\- \`family\`: string — \`"ring"\`, \`"skip1"\`, or \`"cross"\`.

\*\*Meta (\`meta\`):\*\*  
\- \`experiment\`, \`paper\`, \`alpha\`, \`beta1\`, \`negfrac\_ceiling\`.

\#\#\# The Nine Voice Registers

Paper XVII defines nine internal language registers per node per step. The visualization surfaces these in the UI on node selection. The register keys are:

\`\`\`  
"self"     — identity and state summary  
"gen"      — generational frame PCM, anchor chain  
"know"     — knowledge accumulation and drift  
"inherit"  — inheritance chain across generations  
"ring"     — ring-level negfrac and CV metrics  
"guard"    — guardrail zone interpretation  
"math"     — mathematical register (eigenvalues, PCM formula)  
"thermo"   — thermodynamic register (entropy, negentropy)  
"holo"     — holographic register (boundary/bulk encoding)  
\`\`\`

The voice dict in the JSON must contain at least these nine keys at each step where voice data was captured. Steps without voice data simply omit the \`voice\` key; the UI panel shows "No voice data at this step."

\#\#\# File Organization

\`\`\`  
res://  
├── data/  
│   └── peig/  
│       ├── internal\_voice\_run.json  
│       ├── mi\_bridge\_exp.json  
│       ├── gip\_lineage\_run.json  
│       └── minipeig\_solve.json  
├── scenes/  
│   ├── Main.tscn  
│   ├── RingRoot.tscn  
│   └── UIRoot.tscn  
├── scripts/  
│   ├── PeigData.gd          ← autoload singleton  
│   ├── RingController.gd    ← attached to RingRoot  
│   └── VoicePanel.gd        ← attached to UIRoot/VoicePanel  
└── shaders/  
    ├── node\_surface.gdshader  
    └── edge\_surface.gdshader  
\`\`\`

\---

\#\# Godot Scene Tree Architecture

\`\`\`  
Main.tscn  (Node)  
├── EnvironmentRoot  (Node3D)  
│   ├── WorldEnvironment  
│   ├── DirectionalLight3D  
│   └── Camera3D  
├── RingRoot  (Node3D)   ← RingController.gd attached here  
│   ├── NodeMultiMesh  (MultiMeshInstance3D)  
│   └── EdgeMultiMesh  (MultiMeshInstance3D)  
└── UIRoot  (CanvasLayer)  
    ├── HUDPanel  (PanelContainer)  
    │   ├── PlayPauseButton  (Button)  
    │   ├── Scrubber  (HSlider)  
    │   └── StepLabel  (Label)  
    └── VoicePanel  (PanelContainer)   ← VoicePanel.gd attached here  
        ├── NodeNameLabel  (Label)  
        ├── RegisterTabBar  (TabBar)  
        └── RegisterContent  (RichTextLabel)  
\`\`\`

\#\#\# MultiMesh Configuration

\*\*NodeMultiMesh:\*\*  
\- \`mesh\`: \`SphereMesh\` (radius 0.15, radial\_segments 16, rings 8\) — pre-authored once in the editor, never scaled at runtime.  
\- \`instance\_count\`: 12  
\- \`transform\_format\`: \`TRANSFORM\_3D\`  
\- \`color\_format\`: \`COLOR\_NONE\`  
\- \`custom\_data\_format\`: \`CUSTOM\_DATA\_FLOAT\` (two \`Color\` slots \= 8 floats per instance)

\*\*EdgeMultiMesh:\*\*  
\- \`mesh\`: \`CylinderMesh\` (top\_radius 0.04, bottom\_radius 0.04, height 1.0, radial\_segments 6\) — \*\*unit height, unit radius; all scaling done via Transform3D at runtime\*\*. Cached once; never rebuilt.  
\- \`instance\_count\`: 36  
\- \`transform\_format\`: \`TRANSFORM\_3D\`  
\- \`color\_format\`: \`COLOR\_NONE\`  
\- \`custom\_data\_format\`: \`CUSTOM\_DATA\_FLOAT\`

Caching the unit \`CylinderMesh\` in the editor and deforming it via \`Transform3D\` each frame eliminates per-frame mesh allocation. The basis construction encodes both length and orientation; the mesh itself is never touched after scene load.

\---

\#\# Instance Data Layout

Each node instance carries \*\*two \`Color\` slots\*\* (8 floats total) via \`INSTANCE\_CUSTOM\`. The layout is fixed and must match exactly between GDScript and the shader.

\#\#\# Node Instance Custom Data

| Slot | Component | GDScript Name | Range in Color | Unpacked Range | Meaning |  
|---|---|---|---|---|---|  
| \`CUSTOM0\` | \`.r\` | \`pcm\_packed\` | \[0.0, 1.0\] | \[−0.5, 0.5\] | PCM value |  
| \`CUSTOM0\` | \`.g\` | \`nf\_packed\` | \[0.0, 1.0\] | \[0.0, 1.0\] | Negfrac |  
| \`CUSTOM0\` | \`.b\` | \`phi\_packed\` | \[0.0, 1.0\] | \[−π, π\] | Phase φ |  
| \`CUSTOM0\` | \`.a\` | \`pulse\_packed\` | \[0.0, 1.0\] | \[0.0, 1.0\] | Pulse strength |  
| \`CUSTOM1\` | \`.r\` | \`zone\_packed\` | \[0.0, 1.0\] | {0,1,2,3} | Guardrail zone |  
| \`CUSTOM1\` | \`.g\` | \*(reserved)\* | 0.0 | — | Future use |  
| \`CUSTOM1\` | \`.b\` | \*(reserved)\* | 0.0 | — | Future use |  
| \`CUSTOM1\` | \`.a\` | \*(reserved)\* | 0.0 | — | Future use |

\*\*Packing conventions:\*\*  
\- PCM: \`(pcm \+ 0.5)\` maps \[−0.5, 0.5\] → \[0.0, 1.0\]  
\- φ: \`(phi \+ PI) / TAU\` maps \[−π, π\] → \[0.0, 1.0\]  
\- Zone: \`zone / 3.0\` maps {0,1,2,3} → {0.0, 0.333, 0.667, 1.0}  
\- Pulse, negfrac: already in \[0.0, 1.0\], pass through directly

\#\#\# Edge Instance Custom Data

| Slot | Component | Meaning |  
|---|---|---|  
| \`CUSTOM0\` | \`.r\` | MI value \[0.0, 1.0\] |  
| \`CUSTOM0\` | \`.g\` | Bridge flag (0.0 or 1.0) |  
| \`CUSTOM0\` | \`.b\` | \*(reserved)\* |  
| \`CUSTOM0\` | \`.a\` | \*(reserved)\* |

\---

\#\# Shaders

\#\#\# Node Surface Shader (\`node\_surface.gdshader\`)

\`\`\`glsl  
shader\_type spatial;  
render\_mode blend\_mix, depth\_draw\_opaque, cull\_back, diffuse\_lambert, specular\_schlick\_ggx;

uniform float emission\_scale : hint\_range(0.0, 8.0) \= 3.0;  
uniform float pulse\_emission\_scale : hint\_range(0.0, 6.0) \= 2.0;  
uniform float zone\_outline\_width : hint\_range(0.0, 0.1) \= 0.03;

// Color palette for guardrail zones  
const vec3 COLOR\_GREEN  \= vec3(0.0,  0.9,  0.3);  
const vec3 COLOR\_YELLOW \= vec3(0.9,  0.85, 0.0);  
const vec3 COLOR\_ORANGE \= vec3(1.0,  0.45, 0.0);  
const vec3 COLOR\_RED    \= vec3(0.95, 0.05, 0.05);

// Deep nonclassical → classical color ramp  
const vec3 PCM\_DEEP\_NC  \= vec3(0.0,  0.95, 0.4);   // PCM ≈ \-0.5  green  
const vec3 PCM\_BOUNDARY \= vec3(1.0,  0.85, 0.0);   // PCM ≈  0.0  yellow/orange  
const vec3 PCM\_CLASSICAL= vec3(0.95, 0.05, 0.05);  // PCM \>  0.05 red

void vertex() {  
    // Standard instanced vertex — no per-vertex logic needed.  
}

void fragment() {  
    // \--- Unpack CUSTOM0 \---  
    float pcm   \= INSTANCE\_CUSTOM.r \* 1.0 \- 0.5;        //  → \[-0.5, 0.5\] \[ppl-ai-file-upload.s3.amazonaws\](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/154959549/9c544a75-4122-4a36-b6b4-0436e0bbc260/PEIG\_Papers\_XVII\_XVIII\_XX.md)  
    float nf    \= INSTANCE\_CUSTOM.g;                     //  negfrac, pass through \[ppl-ai-file-upload.s3.amazonaws\](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/154959549/9c544a75-4122-4a36-b6b4-0436e0bbc260/PEIG\_Papers\_XVII\_XVIII\_XX.md)  
    float phi   \= INSTANCE\_CUSTOM.b \* 6.28318 \- 3.14159; //  → \[-π, π\] \[ppl-ai-file-upload.s3.amazonaws\](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/154959549/9c544a75-4122-4a36-b6b4-0436e0bbc260/PEIG\_Papers\_XVII\_XVIII\_XX.md)  
    float pulse \= INSTANCE\_CUSTOM.a;                     //  pass through \[ppl-ai-file-upload.s3.amazonaws\](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/154959549/9c544a75-4122-4a36-b6b4-0436e0bbc260/PEIG\_Papers\_XVII\_XVIII\_XX.md)

    // \--- Unpack CUSTOM1 \---  
    float zone\_f \= INSTANCE\_CUSTOM2.r;                   // {0, 0.333, 0.667, 1.0}  
    int   zone   \= int(round(zone\_f \* 3.0));             // → {0, 1, 2, 3}

    // \--- PCM → base color \---  
    // Remap PCM: \-0.5 → 0.0 (deep NC), 0.0 → 0.5 (boundary), 0.05+ → 1.0 (classical)  
    float pcm\_t \= clamp((pcm \+ 0.5) / 0.55, 0.0, 1.0);  
    vec3 base\_color;  
    if (pcm\_t \< 0.5) {  
        base\_color \= mix(PCM\_DEEP\_NC, PCM\_BOUNDARY, pcm\_t \* 2.0);  
    } else {  
        base\_color \= mix(PCM\_BOUNDARY, PCM\_CLASSICAL, (pcm\_t \- 0.5) \* 2.0);  
    }

    // \--- Zone → outline/rim color \---  
    vec3 zone\_color;  
    if      (zone \== 0\) zone\_color \= COLOR\_GREEN;  
    else if (zone \== 1\) zone\_color \= COLOR\_YELLOW;  
    else if (zone \== 2\) zone\_color \= COLOR\_ORANGE;  
    else                zone\_color \= COLOR\_RED;

    // \--- Emission: negfrac drives base glow, pulse adds sharp crest \---  
    // nf  → sustained background glow (the node's quantum budget)  
    // pulse → sharp wave-crest brightness (momentary wave peak passing through)  
    float base\_emission  \= nf    \* emission\_scale;  
    float pulse\_emission \= pulse \* pulse\_emission\_scale;  
    vec3  emission\_color \= base\_color \* (base\_emission \+ pulse\_emission);

    // \--- Fresnel rim: zone color bleeds to edge at glancing angles \---  
    float fresnel \= pow(1.0 \- clamp(dot(NORMAL, VIEW), 0.0, 1.0), 3.0);  
    vec3  rim     \= zone\_color \* fresnel \* 2.0;

    // \--- Output \---  
    ALBEDO     \= base\_color;  
    EMISSION   \= emission\_color \+ rim;  
    ROUGHNESS  \= 0.35;  
    METALLIC   \= 0.0;  
    SPECULAR   \= 0.5;

    // \--- Optional: zone outline via UV proximity to sphere edge \---  
    // This gives a visible colored ring at the silhouette  
    // float edge \= smoothstep(1.0 \- zone\_outline\_width, 1.0, fresnel);  
    // ALBEDO \= mix(base\_color, zone\_color, edge);  
}  
\`\`\`

\*\*Key unpacking details:\*\*  
\- \`INSTANCE\_CUSTOM\` is CUSTOM0 (\`Color\` slot 0).  
\- \`INSTANCE\_CUSTOM2\` is CUSTOM1 (\`Color\` slot 1). Godot names these \`INSTANCE\_CUSTOM\`, \`INSTANCE\_CUSTOM2\`, \`INSTANCE\_CUSTOM3\`, \`INSTANCE\_CUSTOM4\` in the shader.  
\- PCM unpacking: \`r \* 1.0 \- 0.5\` reverses the \`(pcm \+ 0.5)\` pack. Multiply-then-subtract preserves GPU precision better than subtract-then-multiply for this range.  
\- Zone is nearest-integer decoded via \`round(zone\_f \* 3.0)\` — robust to float precision drift at the four discrete values.  
\- Pulse and negfrac drive separate emission terms. \`nf\` represents the node's sustained nonentropy budget (background glow that persists as long as the node is nonclassical). \`pulse\` represents the momentary wave crest passing through the node — a sharp, transient brightness spike that travels around the ring with the rotating wave.

\#\#\# Edge Surface Shader (\`edge\_surface.gdshader\`)

\`\`\`glsl  
shader\_type spatial;  
render\_mode blend\_mix, depth\_draw\_opaque, cull\_back, diffuse\_lambert, specular\_disabled;

uniform float mi\_emission\_scale : hint\_range(0.0, 5.0) \= 2.5;

const vec3 EDGE\_BASE    \= vec3(0.3, 0.35, 0.4);  
const vec3 EDGE\_BRIDGE  \= vec3(0.9, 0.5,  1.0);  // magenta/violet for bridge edges  
const vec3 EDGE\_HIGH\_MI \= vec3(0.0, 0.9,  0.5);  // bright teal for top-MI edges

void fragment() {  
    float mi     \= INSTANCE\_CUSTOM.r;   // \[ppl-ai-file-upload.s3.amazonaws\](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/154959549/9c544a75-4122-4a36-b6b4-0436e0bbc260/PEIG\_Papers\_XVII\_XVIII\_XX.md)  
    float bridge \= INSTANCE\_CUSTOM.g;   // 0.0 or 1.0

    // MI drives color blend: low-MI edges stay base gray, high-MI shift to teal  
    vec3 edge\_color \= mix(EDGE\_BASE, EDGE\_HIGH\_MI, mi);

    // Bridge override: active Maverick bridge edges glow violet  
    edge\_color \= mix(edge\_color, EDGE\_BRIDGE, bridge);

    ALBEDO    \= edge\_color;  
    EMISSION  \= edge\_color \* mi \* mi\_emission\_scale;  
    ROUGHNESS \= 0.7;  
    METALLIC  \= 0.0;  
}  
\`\`\`

\---

\#\# \`PeigData.gd\` — Autoload Singleton

\`\`\`gdscript  
\# PeigData.gd  
\# Autoload singleton. Project Settings → AutoLoad → add this as "PeigData".  
extends Node

var \_experiments: Dictionary \= {}  
var \_current:     Dictionary \= {}  
var \_step\_cache:  Array      \= \[\]   \# flattened steps array for O(1) access

func load\_experiment(name: String) \-\> bool:  
    var path := "res://data/peig/%s.json" % name  
    var text := FileAccess.get\_file\_as\_string(path)  
    if text.is\_empty():  
        push\_error("PeigData: cannot read %s" % path)  
        return false  
    var parsed \= JSON.parse\_string(text)  
    if not parsed is Dictionary:  
        push\_error("PeigData: JSON parse failed for %s" % path)  
        return false  
    \_experiments\[name\] \= parsed  
    \_activate(parsed)  
    return true

func \_activate(exp: Dictionary) \-\> void:  
    \_current    \= exp  
    \_step\_cache \= exp.get("steps", \[\])

func switch\_experiment(name: String) \-\> bool:  
    if not \_experiments.has(name):  
        return load\_experiment(name)  
    \_activate(\_experiments\[name\])  
    return true

func step\_count() \-\> int:  
    return \_step\_cache.size()

func get\_step\_state(step: int) \-\> Dictionary:  
    return \_step\_cache\[clampi(step, 0, \_step\_cache.size() \- 1)\]

func get\_step\_pair(step\_floor: int) \-\> Array:  
    \# Returns \[state\_a, state\_b\] for the two keyframes bracketing a fractional playhead.  
    \# Both indices are clamped so the last step safely returns \[last, last\].  
    var a := clampi(step\_floor,     0, \_step\_cache.size() \- 1\)  
    var b := clampi(step\_floor \+ 1, 0, \_step\_cache.size() \- 1\)  
    return \[\_step\_cache\[a\], \_step\_cache\[b\]\]

func get\_meta() \-\> Dictionary:  
    return \_current.get("meta", {})

func get\_node\_names() \-\> Array:  
    \# Returns node names from the first step. Assumes consistent names across steps.  
    if \_step\_cache.is\_empty():  
        return \[\]  
    return \_step\_cache.get("nodes", {}).keys()  
\`\`\`

\---

\#\# \`RingController.gd\` — Complete Implementation

\`\`\`gdscript  
\# RingController.gd  
\# Attach to RingRoot (Node3D).  
extends Node3D

\# ── Exports ──────────────────────────────────────────────────────────────────  
@export var steps\_per\_second: float \= 2.0  
@export var loop:             bool  \= true  
@export var experiment\_name:  String \= "internal\_voice\_run"

\# ── Signals ──────────────────────────────────────────────────────────────────  
signal step\_changed(step\_floor: int, t: float)  
signal experiment\_ended

\# ── Internal state ────────────────────────────────────────────────────────────  
var \_playhead:   float \= 0.0  
var \_playing:    bool  \= true  
var \_step\_count: int   \= 0

\# ── Scene refs ────────────────────────────────────────────────────────────────  
@onready var \_node\_mm: MultiMesh \= $NodeMultiMesh.multimesh  
@onready var \_edge\_mm: MultiMesh \= $EdgeMultiMesh.multimesh

\# ── Lifecycle ─────────────────────────────────────────────────────────────────  
func \_ready() \-\> void:  
    if not PeigData.load\_experiment(experiment\_name):  
        push\_error("RingController: failed to load experiment '%s'" % experiment\_name)  
        return  
    \_step\_count \= PeigData.step\_count()  
    \_update\_visuals(0.0)

func \_process(delta: float) \-\> void:  
    if not \_playing or \_step\_count \== 0:  
        return

    \_playhead \+= delta \* steps\_per\_second  
    var max\_p := float(\_step\_count \- 1\)

    if \_playhead \>= max\_p:  
        if loop:  
            \_playhead \= fmod(\_playhead, max\_p)  
        else:  
            \_playhead \= max\_p  
            \_playing  \= false  
            experiment\_ended.emit()

    \_update\_visuals(\_playhead)

\# ── Public API ────────────────────────────────────────────────────────────────  
func seek(target: float) \-\> void:  
    \_playhead \= clampf(target, 0.0, float(maxf(\_step\_count \- 1, 0)))  
    \_update\_visuals(\_playhead)

func set\_playing(value: bool) \-\> void:  
    \_playing \= value

func get\_playhead() \-\> float:  
    return \_playhead

func get\_step\_count() \-\> int:  
    return \_step\_count

\# ── Core animation ────────────────────────────────────────────────────────────  
func \_update\_visuals(playhead: float) \-\> void:  
    var step\_a := int(floor(playhead))  
    var t      := playhead \- float(step\_a)   \# raw blend factor ∈ \[0, 1\)  
    var et     := \_ease\_t(t)                 \# smoothstepped t for continuous metrics

    var pair: Array     \= PeigData.get\_step\_pair(step\_a)  
    var state\_a: Dictionary \= pair        \# ← FIXED: was pair in both slots  
    var state\_b: Dictionary \= pair        \# ← FIXED: was pair duplicate \[ppl-ai-file-upload.s3.amazonaws\](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/154959549/9c544a75-4122-4a36-b6b4-0436e0bbc260/PEIG\_Papers\_XVII\_XVIII\_XX.md)

    \_write\_node\_instances(state\_a, state\_b, t, et)  
    \_write\_edge\_instances(state\_a, state\_b, t, et)

    step\_changed.emit(step\_a, t)

\# S(t) \= t²(3 − 2t)  —  slow-fast-slow easing for continuous metrics  
func \_ease\_t(t: float) \-\> float:  
    return t \* t \* (3.0 \- 2.0 \* t)

\# ── Node instances ────────────────────────────────────────────────────────────  
func \_write\_node\_instances(  
        state\_a: Dictionary, state\_b: Dictionary,  
        t: float, et: float) \-\> void:

    var nodes\_a: Dictionary \= state\_a.get("nodes", {})  
    var nodes\_b: Dictionary \= state\_b.get("nodes", {})  
    var names: Array \= nodes\_a.keys()

    for i in range(names.size()):  
        var name: String     \= names\[i\]  
        var na:   Dictionary \= nodes\_a\[name\]  
        var nb:   Dictionary \= nodes\_b\[name\]

        \# ── Position: linear lerp (no easing — eased position looks like  
        \#    uneven velocity on the torus, which is incorrect)  
        var pos := Vector3(na\["x"\], na\["y"\], na\["z"\]).lerp(  
                   Vector3(nb\["x"\], nb\["y"\], nb\["z"\]), t)

        \# ── Continuous metrics: smoothstepped  
        var pcm:   float \= lerpf(float(na\["pcm"\]),     float(nb\["pcm"\]),     et)  
        var nf:    float \= lerpf(float(na\["negfrac"\]),  float(nb\["negfrac"\]),  et)  
        var pulse: float \= lerpf(float(na.get("pulse", 0.0)),  
                                 float(nb.get("pulse", 0.0)), et)

        \# ── Phase: angular lerp to avoid ±π wraparound (non-negotiable)  
        var phi: float \= lerp\_angle(float(na\["phi"\]), float(nb\["phi"\]), et)

        \# ── Categorical: snap at t ≥ 0.5  
        \#    Zone and generation are threshold states — no physical meaning to  
        \#    a value "between" zones.  
        var src    := nb if t \>= 0.5 else na  
        var zone:   int \= int(src.get("zone", 0))  
        var gen\_a:  int \= int(na.get("generation", 0))  
        var gen\_b:  int \= int(nb.get("generation", 0))

        \# ── GIP lineage arc: sin(t·π) bell with zero at both step boundaries  
        \#    Return event  → node settles downward (dipping arc)  
        \#    Extend event  → node rises upward (emergence arc)  
        \#    No extra data needed — signal derived purely from generation delta  
        if gen\_b \< gen\_a:  
            pos.y \-= sin(t \* PI) \* 0.3  
        elif gen\_b \> gen\_a:  
            pos.y \+= sin(t \* PI) \* 0.3

        \# ── Write transform (position only; sphere mesh needs no rotation/scale)  
        \_node\_mm.set\_instance\_transform(i, Transform3D(Basis(), pos))

        \# ── Pack CUSTOM0: pcm, nf, phi, pulse  
        \_node\_mm.set\_instance\_custom\_data(i, Color(  
            (pcm \+ 0.5),               \# pcm: \[-0.5,0.5\] → \[ppl-ai-file-upload.s3.amazonaws\](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/154959549/9c544a75-4122-4a36-b6b4-0436e0bbc260/PEIG\_Papers\_XVII\_XVIII\_XX.md)  
            nf,                        \# negfrac:  pass through \[ppl-ai-file-upload.s3.amazonaws\](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/154959549/9c544a75-4122-4a36-b6b4-0436e0bbc260/PEIG\_Papers\_XVII\_XVIII\_XX.md)  
            (phi \+ PI) / TAU,          \# phi: \[-π,π\] → \[ppl-ai-file-upload.s3.amazonaws\](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/154959549/9c544a75-4122-4a36-b6b4-0436e0bbc260/PEIG\_Papers\_XVII\_XVIII\_XX.md)  
            pulse                      \# pulse:  pass through \[ppl-ai-file-upload.s3.amazonaws\](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/154959549/9c544a75-4122-4a36-b6b4-0436e0bbc260/PEIG\_Papers\_XVII\_XVIII\_XX.md)  
        ))

        \# ── Pack CUSTOM1: zone (r), reserved (g,b,a \= 0\)  
        \_node\_mm.set\_instance\_custom\_data2(i, Color(  
            float(zone) / 3.0,         \# zone: {0,1,2,3} → {0,0.333,0.667,1}  
            0.0, 0.0, 0.0  
        ))

\# ── Edge instances ────────────────────────────────────────────────────────────  
func \_write\_edge\_instances(  
        state\_a: Dictionary, state\_b: Dictionary,  
        t: float, et: float) \-\> void:

    var edges\_a: Dictionary \= state\_a.get("edges", {})  
    var edges\_b: Dictionary \= state\_b.get("edges", {})  
    var nodes\_a: Dictionary \= state\_a.get("nodes", {})  
    var nodes\_b: Dictionary \= state\_b.get("nodes", {})  
    var edge\_ids: Array \= edges\_a.keys()

    for i in range(edge\_ids.size()):  
        var eid: String      \= edge\_ids\[i\]  
        var ea:  Dictionary  \= edges\_a\[eid\]  
        var eb:  Dictionary  \= edges\_b\[eid\]

        \# Interpolate endpoint positions  
        var src\_pos := \_lerp\_node\_pos(nodes\_a, nodes\_b, ea\["source"\], t)  
        var tgt\_pos := \_lerp\_node\_pos(nodes\_a, nodes\_b, ea\["target"\], t)

        \# Build cylinder transform from the pre-cached unit CylinderMesh (height=1).  
        \# The mesh is NEVER rebuilt — only its Transform3D changes each frame.  
        \# Basis.y aligns to the edge direction; X/Z scale sets the radius.  
        var mid:    Vector3 \= src\_pos.lerp(tgt\_pos, 0.5)  
        var diff:   Vector3 \= tgt\_pos \- src\_pos  
        var length: float   \= diff.length()  
        var up:     Vector3 \= diff.normalized() if length \> 0.001 else Vector3.UP

        var basis := Basis()  
        basis.y \= up  
        basis.x \= up.cross(Vector3.RIGHT).normalized()  
        if basis.x.length\_squared() \< 0.001:  
            \# Degenerate case: edge is parallel to Vector3.RIGHT  
            basis.x \= up.cross(Vector3.FORWARD).normalized()  
        basis.z \= basis.x.cross(basis.y).normalized()

        \# Scale: radius 0.04 on X/Z, half-length on Y  
        \# (unit CylinderMesh has height 1.0, so Y scale \= length directly)  
        basis \= basis.scaled(Vector3(0.04, length, 0.04))

        \_edge\_mm.set\_instance\_transform(i, Transform3D(basis, mid))

        \# Continuous metric: MI smoothstepped  
        var mi: float \= lerpf(  
            float(ea.get("mi", 0.0)),  
            float(eb.get("mi", 0.0)), et)

        \# Categorical: bridge snap at t ≥ 0.5  
        var bridge\_src := eb if t \>= 0.5 else ea  
        var bridge: float \= 1.0 if bridge\_src.get("bridge", false) else 0.0

        \_edge\_mm.set\_instance\_custom\_data(i, Color(mi, bridge, 0.0, 0.0))

\# ── Helper ────────────────────────────────────────────────────────────────────  
func \_lerp\_node\_pos(  
        nodes\_a: Dictionary, nodes\_b: Dictionary,  
        name:    String, t: float) \-\> Vector3:  
    var na := nodes\_a.get(name, {})  
    var nb := nodes\_b.get(name, {})  
    return Vector3(float(na.get("x", 0.0)),  
                   float(na.get("y", 0.0)),  
                   float(na.get("z", 0.0))).lerp(  
           Vector3(float(nb.get("x", 0.0)),  
                   float(nb.get("y", 0.0)),  
                   float(nb.get("z", 0.0))), t)  
\`\`\`

\---

\#\# Lerp / Snap Dispatch Policy

| Metric | Type | Strategy | t used | Reason |  
|---|---|---|---|---|  
| Position (x, y, z) | Continuous | \`Vector3.lerp(…, t)\` | Raw \`t\` | No easing — eased position implies uneven velocity |  
| PCM | Continuous | \`lerpf(…, et)\` | Eased \`et\` | Drives color gradient; smoothstep gives organic pulse |  
| Negfrac | Continuous | \`lerpf(…, et)\` | Eased \`et\` | Drives glow; smooth looks correct |  
| Phase φ | Angular | \`lerp\_angle(…, et)\` | Eased \`et\` | \*\*Must use angular lerp\*\* — ±π wraparound causes backwards spin |  
| Pulse strength | Continuous | \`lerpf(…, et)\` | Eased \`et\` | Wave crest travels continuously around ring |  
| MI per edge | Continuous | \`lerpf(…, et)\` | Eased \`et\` | Edge brightness; smooth |  
| Guardrail zone | Categorical | Snap at \`t ≥ 0.5\` | Raw \`t\` | Zone is a threshold event, not a gradient |  
| Generation | Integer | Snap at \`t ≥ 0.5\` | Raw \`t\` | Lineage depth is discrete |  
| Bridge flag | Boolean | Snap at \`t ≥ 0.5\` | Raw \`t\` | Bridge either exists or it doesn't |  
| Voice register text | String | Always \`state\_a\` | — | No interpolation for strings; show floor-step text |

\*\*Rule:\*\* Use \`et\` (smoothstepped) for every continuous lerp. Use raw \`t\` for every snap-at-0.5 categorical decision. Never apply easing to threshold logic.

\---

\#\# \`VoicePanel.gd\` — Nine Register Implementation

\`\`\`gdscript  
\# VoicePanel.gd  
\# Attach to UIRoot/VoicePanel (PanelContainer).  
extends PanelContainer

\# ── Register display order ────────────────────────────────────────────────────  
const REGISTER\_ORDER: Array \= \[  
    "self", "gen", "know", "inherit",  
    "ring", "guard", "math", "thermo", "holo"  
\]

const REGISTER\_LABELS: Dictionary \= {  
    "self":    "Self",  
    "gen":     "Generational",  
    "know":    "Knowledge",  
    "inherit": "Inheritance",  
    "ring":    "Ring",  
    "guard":   "Guardrail",  
    "math":    "Mathematical",  
    "thermo":  "Thermodynamic",  
    "holo":    "Holographic",  
}

\# ── Scene refs ────────────────────────────────────────────────────────────────  
@onready var \_name\_label:   Label         \= $VBox/NodeNameLabel  
@onready var \_tab\_bar:      TabBar        \= $VBox/RegisterTabBar  
@onready var \_content:      RichTextLabel \= $VBox/RegisterContent

\# ── Internal state ────────────────────────────────────────────────────────────  
var \_selected\_node: String \= ""  
var \_current\_step:  int    \= 0  
var \_active\_register\_idx: int \= 0

\# ── Lifecycle ─────────────────────────────────────────────────────────────────  
func \_ready() \-\> void:  
    \# Populate tab bar with register names  
    for reg in REGISTER\_ORDER:  
        \_tab\_bar.add\_tab(REGISTER\_LABELS\[reg\])  
    \_tab\_bar.tab\_changed.connect(\_on\_tab\_changed)  
    hide()  \# hidden until a node is selected

\# ── Public API ────────────────────────────────────────────────────────────────  
func show\_node(node\_name: String, step\_floor: int) \-\> void:  
    \_selected\_node \= node\_name  
    \_current\_step  \= step\_floor  
    \_name\_label.text \= "%s — Step %d" % \[node\_name, step\_floor\]  
    \_refresh\_content()  
    show()

func update\_step(step\_floor: int) \-\> void:  
    if not visible or \_selected\_node.is\_empty():  
        return  
    \_current\_step \= step\_floor  
    \_name\_label.text \= "%s — Step %d" % \[\_selected\_node, step\_floor\]  
    \_refresh\_content()

func dismiss() \-\> void:  
    \_selected\_node \= ""  
    hide()

\# ── Internals ─────────────────────────────────────────────────────────────────  
func \_on\_tab\_changed(tab\_idx: int) \-\> void:  
    \_active\_register\_idx \= tab\_idx  
    \_refresh\_content()

func \_refresh\_content() \-\> void:  
    if \_selected\_node.is\_empty():  
        return

    var state := PeigData.get\_step\_state(\_current\_step)  
    var nodes  := state.get("nodes", {})  
    var node\_data: Dictionary \= nodes.get(\_selected\_node, {})  
    var voice: Dictionary     \= node\_data.get("voice", {})

    var reg\_key: String \= REGISTER\_ORDER\[\_active\_register\_idx\]

    if voice.is\_empty():  
        \_content.text \= "\[i\]No voice data at step %d.\[/i\]" % \_current\_step  
        return

    var text: String \= voice.get(reg\_key, "")  
    if text.is\_empty():  
        text \= "\[i\]Register '%s' not present at step %d.\[/i\]" % \[reg\_key, \_current\_step\]

    \# RichTextLabel with BBCode for readable multi-line voice output  
    \_content.bbcode\_enabled \= true  
    \_content.text \= "\[color=\#d0d0d0\]%s\[/color\]" % text  
\`\`\`

\#\#\# Connecting VoicePanel to RingController

In \`Main.tscn\`'s attached script (or \`UIRoot\`):

\`\`\`gdscript  
\# Wire up in \_ready() of Main.gd or UIRoot.gd  
func \_ready() \-\> void:  
    \# Connect RingController's step\_changed signal → update VoicePanel step  
    $RingRoot.step\_changed.connect(\_on\_step\_changed)  
    \# Scrubber  
    $UIRoot/HUDPanel/Scrubber.value\_changed.connect(\_on\_scrubber\_changed)  
    \# Play/pause  
    $UIRoot/HUDPanel/PlayPauseButton.pressed.connect(\_on\_play\_pause)

func \_on\_step\_changed(step\_floor: int, \_t: float) \-\> void:  
    var ring := $RingRoot  
    var ui   := $UIRoot

    \# Update scrubber position without re-triggering its signal  
    var scrub: HSlider \= ui.get\_node("HUDPanel/Scrubber")  
    scrub.set\_block\_signals(true)  
    scrub.value \= float(step\_floor) / float(maxf(ring.get\_step\_count() \- 1, 1))  
    scrub.set\_block\_signals(false)

    \# Update step label  
    ui.get\_node("HUDPanel/StepLabel").text \= \\  
        "Step %d / %d" % \[step\_floor, ring.get\_step\_count() \- 1\]

    \# Update voice panel if visible  
    ui.get\_node("VoicePanel").update\_step(step\_floor)

func \_on\_scrubber\_changed(value: float) \-\> void:  
    var ring := $RingRoot  
    ring.seek(value \* float(maxf(ring.get\_step\_count() \- 1, 1)))

func \_on\_play\_pause() \-\> void:  
    var ring := $RingRoot  
    ring.set\_playing(not ring.\_playing)  
    $UIRoot/HUDPanel/PlayPauseButton.text \= "⏸" if ring.\_playing else "▶"  
\`\`\`

\---

\#\# Scrubbing and Seek

Because \`\_update\_visuals\` is a pure function of \`\_playhead\` with no internal state, scrubbing is trivially safe. \`seek()\` clamps the target, writes \`\_playhead\`, and calls \`\_update\_visuals\` immediately. The scrubber sees the result on the same frame. No \`Tween\`, no \`AnimationPlayer\`, no secondary writer to \`\_playhead\`. Pausing sets \`\_playing \= false\`; the playhead holds exactly where it stopped and resumes from there.

\---

\#\# Performance Budget (GTX 1070\)

| Operation | Count per frame | Estimated cost |  
|---|---|---|  
| \`get\_step\_pair\` array index | 2 | \< 0.01 ms |  
| Node dictionary lookups | 24 (12 × 2\) | \~0.01 ms |  
| Vector3 lerps (positions) | 12 \+ 72 edge endpoints | \~0.02 ms |  
| Float lerps (pcm, nf, phi, pulse, MI) | 60 | \~0.01 ms |  
| \`lerp\_angle\` calls | 12 | \~0.01 ms |  
| \`sin(t·π)\` GIP arc checks | 12 | \~0.01 ms |  
| Basis construction (edges) | 36 | \~0.04 ms |  
| \`set\_instance\_transform\` × 48 | 48 | \~0.03 ms |  
| \`set\_instance\_custom\_data\` × 48 | 48 | \~0.02 ms |  
| \`set\_instance\_custom\_data2\` × 12 | 12 (nodes only) | \~0.01 ms |  
| \*\*Total\*\* | | \*\*\~0.17 ms\*\* |

At 60 fps the frame budget is 16.7 ms. The full hot path consumes \~1% of it. The concern only arises if the experiment is extended to hundreds of nodes. The optimization path for that scale is to pre-flatten JSON into \`PackedFloat32Array\` buffers at load time in \`PeigData.gd\`, replacing dictionary lookups with direct index arithmetic — the same pattern used in PhysicsServer3D \+ MultiMesh bullet simulations.

\---

\#\# Godot‑Specific Performance Considerations

\#\#\# MultiMesh and Instancing

Using \`MultiMesh\` for node glyphs and edges minimizes draw calls and exploits GPU instancing. The unit \`CylinderMesh\` for edges is authored once in the editor and never rebuilt at runtime — only its \`Transform3D\` changes each frame. This eliminates per-frame mesh allocation entirely.

\#\#\# Occlusion Culling and LOD

Although the Globe scene is compact, adding environments may benefit from occluder nodes and LOD. Reduce transparent surfaces where possible — they require back-to-front sorting and cannot benefit from the same batching as opaque meshes. Both node and edge shaders are configured \`blend\_mix, depth\_draw\_opaque\` for this reason.

\---

\#\# Implementation Roadmap

1\. \*\*Create the Godot project\*\*: set up \`Main.tscn\`, \`EnvironmentRoot\`, \`RingRoot\`, and \`UIRoot\` scenes; configure Forward+ renderer and basic lighting.  
2\. \*\*Author MultiMesh assets\*\*: create a \`SphereMesh\` for \`NodeMultiMesh\` and a unit \`CylinderMesh\` (height=1, radius=0.04) for \`EdgeMultiMesh\` in the editor. Set \`instance\_count\` to 12 and 36 respectively. Set \`custom\_data\_format\` to \`CUSTOM\_DATA\_FLOAT\`.  
3\. \*\*Assign shaders\*\*: apply \`node\_surface.gdshader\` to the node mesh material and \`edge\_surface.gdshader\` to the edge mesh material.  
4\. \*\*Implement \`PeigData.gd\` autoload\*\*: register in Project Settings → AutoLoad. Verify \`load\_experiment\` and \`get\_step\_pair\` work correctly against a test JSON file.  
5\. \*\*Implement \`RingController.gd\`\*\*: attach to \`RingRoot\`. Verify the accumulator advances correctly and \`\_update\_visuals\` writes correct transforms at step boundaries.  
6\. \*\*Implement \`VoicePanel.gd\`\*\*: attach to \`UIRoot/VoicePanel\`. Test all nine registers display correctly. Wire node-click signals from a raycast or area detection script.  
7\. \*\*Wire HUD signals\*\*: connect \`Scrubber\`, \`PlayPauseButton\`, and \`StepLabel\` per the connection code above.  
8\. \*\*Optimize and profile\*\*: use Godot's built-in profiler to verify \`\_update\_visuals\` stays under 1 ms. If node count grows significantly, pre-flatten JSON to \`PackedFloat32Array\` at load time.

\---

\#\# JUST EVOLVE: What Changed From the Prior Version

| Area | Prior State | Evolved State |  
|---|---|---|  
| Animation model | "interpolate between steps" (vague) | Explicit \`\_playhead\` float accumulator in fractional steps; full GDScript implementation |  
| \`pair\[0\]\`/\`pair \[ppl-ai-file-upload.s3.amazonaws\](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/154959549/9c544a75-4122-4a36-b6b4-0436e0bbc260/PEIG\_Papers\_XVII\_XVIII\_XX.md)\` bug | Both assigned to \`pair\[0\]\` (copy-paste error) | Fixed: \`state\_a \= pair\[0\]\`, \`state\_b \= pair \[ppl-ai-file-upload.s3.amazonaws\](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/154959549/9c544a75-4122-4a36-b6b4-0436e0bbc260/PEIG\_Papers\_XVII\_XVIII\_XX.md)\` |  
| Lerp vs. snap | Not addressed | Full per-metric dispatch table with justification for each decision |  
| Phase handling | Not addressed | \`lerp\_angle\` required and explained; ±π wraparound failure mode documented |  
| Edge geometry | Described abstractly | Full \`Transform3D\` cylinder construction; unit mesh cached in editor, never rebuilt |  
| Step easing | Not addressed | \`smoothstep\` on \`et\` for continuous metrics; position deliberately un-eased |  
| GIP events | "vertical motion" (vague) | \`sin(t·π)\` arc keyed on generation delta; zero discontinuity at boundaries |  
| Shader unpacking | Not addressed | Full \`node\_surface.gdshader\` showing PCM, negfrac, zone, pulse unpacking with comments |  
| Pulse strength | Not included | Added as 4th float in CUSTOM0; drives separate \`pulse\_emission\` term in shader |  
| Instance data layout | Not specified | Full 8-float layout table with packing conventions for both CUSTOM0 and CUSTOM1 |  
| Voice registers | Mentioned but not implemented | Full \`VoicePanel.gd\` with nine registers, tab bar, BBCode display, step tracking |  
| Scrubbing | Not addressed | \`seek(float)\` — direct playhead assignment, no Tween, no side effects |  
| Performance budget | Not addressed | GTX 1070 frame budget with per-operation breakdown; pre-flatten path identified |  
| \`PeigData\` API | Single \`get\_step\_state(int)\` | Added \`get\_step\_pair(int)\`, \`get\_node\_names()\`, \`get\_meta()\`, caching via \`\_step\_cache\` |  
| Roadmap framing | "ensure experiments log X" | Softened: "assumes data has already been exported with the following fields" |  
| Hardware reference | GTX 1070¹ (typo) | Corrected to GTX 1070 throughout |

\---

\*Document version: JUST HORIZON \+ JUST EVOLVE — Full Implementation\*  
\*Kevin Monette — PEIG Brotherhood Research Series — April 2026\*  
\*Grounded in PEIG Framework Papers XVII, XVIII, XIX, XX\*  
\`\`\`\`