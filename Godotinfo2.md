\`\`\`markdown  
\# Smooth Animation of Discrete Quantum State Data in Godot 4  
\#\# A White Paper on Interpolation Architecture for the PEIG Globe Visualization

\*\*Kevin Monette — PEIG Brotherhood Research Series\*\*  
\*\*April 2026\*\*

\---

\#\# Abstract

The PEIG (Probabilistic Entropic Information Geometry) framework produces discrete,  
step-indexed simulation data: per-node PCM values, negfrac, phase φ, lineage generation,  
guardrail zones, and per-edge mutual information. Visualizing this data naively — snapping  
the Godot 4 scene to each new step every frame — produces jarring discontinuities that  
obscure the rotating wave dynamics central to Papers XVII–XX. This white paper presents  
a complete interpolation architecture for the Godot 4 engine that bridges discrete PEIG  
steps with continuous, frame-rate-independent animation. The design introduces a  
fractional-step accumulator, a per-metric lerp/snap dispatch policy, angular interpolation  
for phase, eased transitions for continuous metrics, event-keyed arcs for GIP lineage  
returns, and a cylinder-construction pipeline for edge geometry — all within the  
performance envelope of a GTX 1070 at 60 fps.

\---

\#\# 1\. Introduction

\#\#\# 1.1 The Visualization Problem

PEIG experiments generate data in discrete simulation steps. Each step records the full  
state of 12 co-rotating nodes on a torus topology: their PCM (Probabilistic Classical  
Measure) values, negentropy fractions, phase angles, lineage depths, guardrail zone  
classifications, and voice register outputs. Edges between nodes carry mutual information  
(MI) values, family labels, and bridge protocol flags.

A Godot 4 visualization of this data runs at 60 frames per second. The mismatch between  
discrete simulation steps (typically 50–200 steps per experiment) and continuous render  
frames (3,600 frames per minute) must be resolved by an interpolation layer. Without it,  
the renderer either:

\- \*\*Snaps\*\* — writes new step data to the MultiMesh exactly once per step, producing  
  visible jumps at each boundary; or  
\- \*\*Repeats\*\* — holds the same frame data for N render frames between steps, which  
  looks frozen rather than animated.

Neither is acceptable for communicating the rotating wave dynamics that are the central  
result of the PEIG co-rotating ILP architecture.

\#\#\# 1.2 Scope of This Paper

This paper specifies the complete interpolation architecture for \`RingController.gd\`, the  
Godot script attached to \`RingRoot\` that drives the MultiMesh visualization. It covers:

\- The fractional-step accumulator and its relationship to wall-clock time.  
\- The per-metric policy for continuous lerp versus categorical snap.  
\- Angular interpolation for phase φ and its wraparound failure mode.  
\- Smoothstep easing and when to apply it.  
\- Edge cylinder transform construction from interpolated endpoint positions.  
\- GIP lineage return arcs as event-keyed geometric overlays.  
\- Scrubbing and seek behavior.  
\- Performance analysis on target hardware.

This paper does not cover the broader scene tree design, shader implementation, or data  
loading pipeline, which are addressed in the companion GodotPeig documentation.

\---

\#\# 2\. Background

\#\#\# 2.1 PEIG Step Structure

Each step in a PEIG experiment represents one full ILP (Iterative Lineage Protocol) update  
cycle. The state at step t includes:

\*\*Per-node:\*\*  
\- \`pcm\` ∈ \[−0.5, 0.5\]: distance from the classical boundary in the identity frame.  
\- \`negfrac\` ∈ \[0.0, 1.0\]: fraction of the node's entropy budget in the negative regime.  
\- \`phi\` ∈ \[−π, π\]: phase angle in the co-rotating frame.  
\- \`generation\` ∈ ℤ≥0: lineage depth of the current GIP stack frame.  
\- \`zone\` ∈ {GREEN, YELLOW, ORANGE, RED}: guardrail classification by PCM threshold.  
\- \`x, y, z\`: world-space position on the torus surface.

\*\*Per-edge:\*\*  
\- \`mi\` ∈ \[0.0, 1.0\]: mutual information between the two endpoint nodes.  
\- \`bridge\`: boolean flag indicating active Maverick bridge protocol.  
\- \`source\`, \`target\`: node name identifiers.  
\- \`family\`: ring / skip1 / cross.

\#\#\# 2.2 The Rotating Wave

The signature dynamic of Papers XVII–XX is a co-rotating wave of nonclassicality that  
propagates around the 12-node ring. As the wave passes a node, its PCM drops toward  
−0.5 (deep nonclassical, green), then recovers toward 0 (boundary, yellow/orange) as the  
wave moves on. The MI distribution rotates with the wave: edges in the nonclassical half  
carry higher MI than edges in the classical half. The guardrail zones shift correspondingly.

This is the phenomenon the visualization must make legible. Snapping makes the wave  
appear to teleport; smooth interpolation makes it appear to flow.

\#\#\# 2.3 Godot 4 MultiMesh Constraints

Godot 4's \`MultiMesh\` resource supports per-instance \`Transform3D\`, \`Color\`, and a  
second \`Color\` used as custom data (four floats packed as RGBA). Updates are applied via:

\`\`\`gdscript  
multimesh.set\_instance\_transform(i, xform)  
multimesh.set\_instance\_custom\_data(i, color)  
\`\`\`

Both calls operate on the CPU side; the updated buffer is uploaded to the GPU at the end  
of the frame. This means all interpolation must be computed on the CPU in GDScript  
before the frame boundary. There is no built-in GPU-side interpolation for MultiMesh  
instance data.

\---

\#\# 3\. The Fractional-Step Accumulator

\#\#\# 3.1 Design Rationale

The core architectural decision is to represent the animation playhead as a \*\*float  
measured in fractional steps\*\* rather than in seconds. A playhead value of \`4.6\` means  
"60% of the way between step 4 and step 5." This representation:

\- Decouples animation speed from frame rate (frame-rate independent).  
\- Makes scrubbing trivial: drag the UI slider to any step fraction.  
\- Makes \`steps\_per\_second\` a single, intuitive export parameter.  
\- Eliminates any need for \`AnimationPlayer\` or \`Tween\` nodes, which would add  
  unnecessary state and make seek operations complex.

\#\#\# 3.2 Accumulator Equations

Let:  
\- \`p\` \= current playhead value (fractional steps)  
\- \`δ\` \= frame delta time (seconds), from \`\_process(delta)\`  
\- \`r\` \= playback rate (steps per second), exported as \`steps\_per\_second\`  
\- \`N\` \= total step count, from \`PeigData.step\_count()\`

Each frame:

\`\`\`  
p ← p \+ δ · r  
\`\`\`

At the end of the experiment:

\`\`\`  
if p ≥ N − 1:  
    if loop:  p ← p mod (N − 1\)  
    else:     p ← N − 1,  playing ← false  
\`\`\`

From \`p\`, derive floor step \`a\` and blend factor \`t\`:

\`\`\`  
a \= ⌊p⌋  
t \= p − a        (t ∈ \[0.0, 1.0))  
\`\`\`

Steps \`a\` and \`a \+ 1\` are the two keyframes bracketing the current visual state.

\#\#\# 3.3 GDScript Implementation

\`\`\`gdscript  
extends Node3D

@export var steps\_per\_second: float \= 2.0  
@export var loop: bool \= true

var \_playhead: float \= 0.0  
var \_playing: bool \= true  
var \_step\_count: int \= 0

@onready var \_node\_mm: MultiMesh \= $NodeMultiMesh.multimesh  
@onready var \_edge\_mm: MultiMesh \= $EdgeMultiMesh.multimesh

func \_ready() \-\> void:  
    \_step\_count \= PeigData.step\_count()

func \_process(delta: float) \-\> void:  
    if not \_playing:  
        return  
    \_playhead \+= delta \* steps\_per\_second  
    var max\_p := float(\_step\_count \- 1\)  
    if \_playhead \>= max\_p:  
        if loop:  
            \_playhead \= fmod(\_playhead, max\_p)  
        else:  
            \_playhead \= max\_p  
            \_playing \= false  
    \_update\_visuals(\_playhead)

func seek(target: float) \-\> void:  
    \_playhead \= clamp(target, 0.0, float(\_step\_count \- 1))  
    \_update\_visuals(\_playhead)

func set\_playing(value: bool) \-\> void:  
    \_playing \= value  
\`\`\`

\#\#\# 3.4 Playback Rate Guidelines

| \`steps\_per\_second\` | Use Case |  
|---|---|  
| 0.25 – 0.5 | Manual step inspection with smooth hold |  
| 1.0 – 2.0 | Default presentation speed |  
| 4.0 – 6.0 | Overview sweep, rotating wave visible |  
| 10.0+ | Rapid survey, interpolation less visible |

At rates above \~8 steps/second, the smoothstep easing becomes less perceptible and  
the visualization approaches a continuous flow. At rates below \~0.5, individual step  
states are legible and the interpolation acts as a smooth hold rather than a transition.

\---

\#\# 4\. The Lerp / Snap Dispatch Policy

\#\#\# 4.1 Motivation

Not all PEIG metrics are continuous. PCM and negfrac change gradually across steps  
because they are derived from cumulative probability distributions — small step sizes  
produce small changes. Phase φ is geometrically continuous on the circle. Mutual  
information per edge varies smoothly with the rotating wave.

Guardrail zones, generation depths, and bridge flags are threshold events. A node crosses  
from YELLOW to ORANGE when its PCM crosses a hard boundary. Interpolating the zone  
value from 1.0 to 2.0 over a step transition would imply the node is "between zones,"  
which has no physical meaning in the PEIG framework. It would also produce incorrect  
shader behavior if zone is used to select a discrete visual style (e.g., outline color  
palette index).

The policy is therefore:

\- \*\*Lerp\*\*: PCM, negfrac, φ, MI, world position, edge length/thickness.  
\- \*\*Snap at t ≥ 0.5\*\*: guardrail zone, generation, bridge flag, voice register text.

Snap-at-0.5 means the new categorical value appears for the second half of the  
transition window. This aligns with the perceptual expectation that the new state  
"arrives" at the midpoint of the blend rather than at the start (which would look  
like the state jumps immediately on every step).

\#\#\# 4.2 Dispatch Table

| Metric | GDScript Operation | Notes |  
|---|---|---|  
| Position \`x,y,z\` | \`pos\_a.lerp(pos\_b, t)\` | Vector3 lerp |  
| PCM | \`lerp(pcm\_a, pcm\_b, et)\` | Smoothstepped \`et\` |  
| Negfrac | \`lerp(nf\_a, nf\_b, et)\` | Smoothstepped \`et\` |  
| Phase φ | \`lerp\_angle(phi\_a, phi\_b, et)\` | Angular lerp, smoothstepped |  
| MI per edge | \`lerp(mi\_a, mi\_b, et)\` | Smoothstepped \`et\` |  
| Guardrail zone | \`nb\_zone if t \>= 0.5 else na\_zone\` | Integer snap |  
| Generation | \`nb\_gen if t \>= 0.5 else na\_gen\` | Integer snap |  
| Bridge flag | \`nb\_bridge if t \>= 0.5 else na\_bridge\` | Boolean snap |  
| Voice text | Always \`na\` (step floor) | No interpolation for strings |

Where \`et\` is the smoothstepped version of \`t\` (see Section 5).

\---

\#\# 5\. Smoothstep Easing

\#\#\# 5.1 Purpose

Linear interpolation between PEIG steps produces a constant rate of change throughout  
each transition window. For the rotating wave, this means node colors change at a uniform  
rate, which can feel mechanical and makes the wave boundary harder to perceive. A  
smoothstep easing function produces slow-fast-slow transitions: the color change  
accelerates from rest, peaks at the midpoint, and decelerates back to rest at the next  
step. This gives each node a subtle "pulse" as the wave passes through it.

\#\#\# 5.2 Smoothstep Formula

The cubic smoothstep function:

\`\`\`  
S(t) \= t² · (3 − 2t)  
\`\`\`

Properties:  
\- S(0) \= 0, S(1) \= 1 (boundary-preserving).  
\- S′(0) \= S′(1) \= 0 (zero derivative at endpoints → smooth start and stop).  
\- S(0.5) \= 0.5 (symmetric).

GDScript:

\`\`\`gdscript  
func \_ease\_t(t: float) \-\> float:  
    return t \* t \* (3.0 \- 2.0 \* t)  
\`\`\`

Then in \`\_update\_visuals\`:

\`\`\`gdscript  
var step\_a := int(floor(playhead))  
var t := playhead \- float(step\_a)  
var et := \_ease\_t(t)          \# eased t for continuous metrics  
\# Use et for lerp; use t for snap-at-0.5 decisions  
\`\`\`

\#\#\# 5.3 Do Not Ease Categorical Snaps

The snap-at-0.5 threshold uses raw \`t\`, not \`et\`. If \`et\` were used, the snap point would  
shift away from the visual midpoint (because S(0.5) \= 0.5, the shift is actually neutral  
here, but the principle holds for other easing curves). Using raw \`t\` for snap decisions  
keeps the transition boundary predictable and independent of the chosen easing function.

\---

\#\# 6\. Angular Interpolation for Phase φ

\#\#\# 6.1 The Wraparound Problem

Phase φ lives on the circle \[−π, π\]. Standard linear interpolation treats it as a scalar:

\`\`\`  
lerp(phi\_a, phi\_b, t) \= phi\_a \+ t · (phi\_b − phi\_a)  
\`\`\`

When \`phi\_a \= \+3.0\` rad and \`phi\_b \= −3.0\` rad, the linear path goes through 0 —  
traveling 6.0 radians across the full diameter of the circle in the wrong direction.  
The correct path is through ±π, a distance of only 0.28 radians.

In a 12-node co-rotating ring, nodes near the ±π boundary are common. The rotating wave  
regularly moves nodes through this region. Linear lerp on phase would cause a large  
fraction of nodes to appear to spin backwards through the ring on every step that crosses  
the ±π seam — a visually dominant artifact that completely misrepresents the wave  
direction.

\#\#\# 6.2 Angular Lerp

Godot provides \`lerp\_angle(from, to, weight)\` which automatically selects the shortest  
arc on the circle:

\`\`\`gdscript  
var phi: float \= lerp\_angle(float(na\["phi"\]), float(nb\["phi"\]), et)  
\`\`\`

This is a one-line change that prevents the most visually egregious interpolation bug  
in the entire system. It should be treated as non-negotiable.

\#\#\# 6.3 Packing φ for the Shader

The shader receives φ as one of four floats packed into \`INSTANCE\_CUSTOM\` (a \`Color\`  
struct). Because \`Color\` components are clamped to \[0, 1\] by default in Godot's shader  
pipeline, φ must be remapped before packing:

\`\`\`gdscript  
var phi\_norm := (phi \+ PI) / TAU   \# remap \[−π, π\] → \[ppl-ai-file-upload.s3.amazonaws\](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/154959549/9c544a75-4122-4a36-b6b4-0436e0bbc260/PEIG\_Papers\_XVII\_XVIII\_XX.md)  
\`\`\`

The shader unpacks:

\`\`\`glsl  
float phi \= (INSTANCE\_CUSTOM.b \* TAU) \- PI;  
\`\`\`

\---

\#\# 7\. Edge Geometry: Cylinder Transform Construction

\#\#\# 7.1 The Problem

Edges in the PEIG ring connect pairs of nodes whose positions change each step (due to  
the co-rotating torus geometry). A static cylinder mesh cannot represent a dynamic edge.  
The solution is to deform a unit cylinder at runtime by constructing a \`Transform3D\`  
that places the cylinder between the interpolated positions of its two endpoint nodes.

\#\#\# 7.2 Transform Construction

Given interpolated endpoint positions \`P\_src\` and \`P\_tgt\`:

\`\`\`gdscript  
var mid := P\_src.lerp(P\_tgt, 0.5)  
var diff := P\_tgt \- P\_src  
var length := diff.length()  
var up := diff.normalized() if length \> 0.001 else Vector3.UP

\# Build orthonormal basis aligned to edge direction  
var basis := Basis()  
basis.y \= up  
basis.x \= up.cross(Vector3.RIGHT).normalized()  
if basis.x.length\_squared() \< 0.001:  
    basis.x \= up.cross(Vector3.FORWARD).normalized()  
basis.z \= basis.x.cross(basis.y).normalized()

\# Scale: thin radius on X/Z, half-length on Y (unit cylinder has height 2\)  
basis \= basis.scaled(Vector3(0.04, length \* 0.5, 0.04))

var xform := Transform3D(basis, mid)  
\`\`\`

This construction handles the degenerate case where \`up\` is parallel to \`Vector3.RIGHT\`  
by falling back to \`Vector3.FORWARD\` for the cross product. The cylinder radius of 0.04  
keeps edges visually thin relative to the node spheres; this value can be exported and  
driven by MI if thicker edges are desired for high-MI connections.

\#\#\# 7.3 Endpoint Positions as Lerped Values

The endpoint positions \`P\_src\` and \`P\_tgt\` are themselves linearly interpolated from the  
two bracketing steps:

\`\`\`gdscript  
func \_lerp\_node\_pos(  
        nodes\_a: Dictionary, nodes\_b: Dictionary,  
        name: String, t: float) \-\> Vector3:  
    var na := nodes\_a.get(name, {})  
    var nb := nodes\_b.get(name, {})  
    return Vector3(na\["x"\], na\["y"\], na\["z"\]).lerp(  
           Vector3(nb\["x"\], nb\["y"\], nb\["z"\]), t)  
\`\`\`

Note that position uses raw \`t\` (not \`et\`) because the visual result of easing position  
is a subtle slowdown/speedup of node movement that can look like uneven velocity on the  
torus — usually undesirable. Easing is reserved for color/glow metrics where the  
perceptual effect is a pulse rather than a speed change.

\---

\#\# 8\. GIP Lineage Return Arcs

\#\#\# 8.1 Motivation

The GIP (Generative Identity Protocol) creates ancestry stacks of lineage frames. When  
a node resolves and returns to its parent frame, its generation count drops by one. This  
is a discrete event with high semantic significance — it represents the completion of a  
recursive identity elaboration cycle. The visualization should signal this event distinctly.

\#\#\# 8.2 Arc Implementation

The generation snap-at-0.5 policy handles the categorical transition. An additional  
geometric overlay — a vertical arc in world space — can be layered on top to make the  
return event visually salient:

\`\`\`gdscript  
var gen\_a: int \= int(na\["generation"\])  
var gen\_b: int \= int(nb\["generation"\])

if gen\_b \< gen\_a:  
    \# Return event: add downward settling arc  
    var arc\_offset := sin(t \* PI) \* 0.3  
    pos.y \-= arc\_offset  
elif gen\_b \> gen\_a:  
    \# Elaboration event: add upward emergence arc  
    var arc\_offset := sin(t \* PI) \* 0.3  
    pos.y \+= arc\_offset  
\`\`\`

\`sin(t · π)\` produces a bell-shaped displacement that peaks at \`t \= 0.5\` and returns to  
zero at both \`t \= 0\` and \`t \= 1\`, ensuring no positional discontinuity at step boundaries.  
The 0.3 unit amplitude is a visual parameter; larger values make the arc more dramatic,  
smaller values make it subtle. No additional data is required — the signal is derived  
entirely from the generation integers already present in the dataset.

\---

\#\# 9\. The \`\_process\` Hot Path

\#\#\# 9.1 Full Per-Frame Sequence

Every frame that \`\_playing\` is true, \`\_process\` executes the following sequence:

1\. Advance \`\_playhead\` by \`delta \* steps\_per\_second\`.  
2\. Clamp or loop \`\_playhead\`.  
3\. Derive \`step\_a \= floor(\_playhead)\` and \`t \= \_playhead \- step\_a\`.  
4\. Compute \`et \= smoothstep(t)\`.  
5\. Fetch \`\[state\_a, state\_b\]\` from \`PeigData.get\_step\_pair(step\_a)\`.  
6\. For each of 12 nodes:  
   a. Lerp position with \`t\`.  
   b. Lerp PCM, negfrac with \`et\`; angular-lerp φ with \`et\`.  
   c. Apply GIP arc offset if generation event detected.  
   d. Snap zone, generation at \`t \>= 0.5\`.  
   e. Pack custom data into \`Color\`.  
   f. Write transform and custom data to \`\_node\_mm\`.  
7\. For each of 36 edges:  
   a. Lerp endpoint positions with \`t\`.  
   b. Construct cylinder \`Transform3D\`.  
   c. Lerp MI with \`et\`; snap bridge at \`t \>= 0.5\`.  
   d. Write transform and custom data to \`\_edge\_mm\`.

\#\#\# 9.2 Performance Analysis

On a GTX 1070 with 16 GB RAM:

| Operation | Count per frame | Estimated cost |  
|---|---|---|  
| Dictionary lookups (\`nodes\_a\[name\]\`) | 24 (12 nodes × 2 steps) | \~0.01 ms |  
| Vector3 lerps (positions) | 12 nodes \+ 72 edge endpoints | \~0.02 ms |  
| Float lerps (PCM, nf, MI, φ) | 48 | \< 0.01 ms |  
| GDScript function calls | \~150 | \~0.05 ms |  
| \`set\_instance\_transform\` × 48 | 48 | \~0.03 ms |  
| \`set\_instance\_custom\_data\` × 48 | 48 | \~0.02 ms |  
| \*\*Total\*\* | | \*\*\~0.14 ms\*\* |

At 60 fps, the frame budget is 16.7 ms. The interpolation hot path consumes approximately  
0.14 ms — less than 1% of the frame budget. There is no performance case for optimization  
at this scale. The concern only arises if the experiment is extended to hundreds of nodes.

\#\#\# 9.3 Optimization Path for Future Scale

If node count grows significantly (e.g., a 64-node or 256-node extension of the Globe  
topology), the GDScript dictionary lookup pattern becomes the bottleneck, not the math.  
The fix is to pre-flatten the JSON data at load time in \`PeigData.gd\`:

\`\`\`gdscript  
\# At load time, flatten nodes into PackedFloat32Array:  
\# Layout: \[x, y, z, pcm, negfrac, phi, gen, zone, ...\] × N\_nodes × N\_steps  
var node\_buffer: PackedFloat32Array  
\`\`\`

Then in \`RingController\`, index by \`step \* stride \+ node\_index \* node\_stride\` — pure  
array arithmetic with no dictionary overhead. This is the same pattern used in  
PhysicsServer3D \+ MultiMesh bullet simulations, and it scales to thousands of instances.

\---

\#\# 10\. Scrubbing and Seek

\#\#\# 10.1 Design

Because \`\_update\_visuals\` is a pure function of \`\_playhead\` with no internal state other  
than the MultiMesh buffers it writes, scrubbing is trivially safe:

\`\`\`gdscript  
func seek(target\_step: float) \-\> void:  
    \_playhead \= clamp(target\_step, 0.0, float(\_step\_count \- 1))  
    \_update\_visuals(\_playhead)  
\`\`\`

The UI scrubber (\`HSlider\`) emits \`value\_changed(float)\` in \[0, 1\] normalized range.  
The signal handler scales to step range before calling \`seek\`:

\`\`\`gdscript  
func \_on\_scrubber\_value\_changed(value: float) \-\> void:  
    RingController.seek(value \* float(PeigData.step\_count() \- 1))  
\`\`\`

\#\#\# 10.2 No Tween Required

A common Godot pattern for smooth seeks is to start a \`Tween\` that moves the playhead  
toward the target over a short duration. This is \*\*not recommended\*\* here because:

\- The accumulator already provides smoothness between steps; abrupt seeks are actually  
  desirable for inspection workflows where the user wants to jump directly to a step.  
\- Tweening the playhead during active scrubbing creates a lag between the scrubber thumb  
  position and the visual output, which is disorienting.  
\- The accumulator is the single source of truth; a Tween would introduce a second writer.

If smooth seek transitions are desired for cinematic playback (not inspection), the UI  
layer can interpolate the scrubber thumb separately without touching \`\_playhead\`.

\---

\#\# 11\. Summary of Design Decisions

| Decision | Choice | Rationale |  
|---|---|---|  
| Time unit | Fractional steps | Decouples from frame rate; intuitive scrub |  
| Accumulator location | \`RingController.\_playhead\` float | Single source of truth |  
| Continuous metrics | Smoothstepped lerp | Organic pulse feel for rotating wave |  
| Categorical metrics | Snap at t ≥ 0.5 | No physical meaning to partial zone state |  
| Phase interpolation | \`lerp\_angle\` | Prevents ±π wraparound artifact |  
| Position interpolation | Linear lerp (no ease) | Eased position looks like uneven velocity |  
| Edge geometry | Runtime cylinder Transform3D | Handles dynamic endpoint positions |  
| GIP events | sin(t·π) arc overlay | No extra data; derived from generation delta |  
| Seek behavior | Direct playhead assignment | No Tween; inspection workflow preferred |  
| Future scale path | Pre-flatten to PackedFloat32Array | Eliminates dictionary overhead |

\---

\#\# 12\. Conclusion

The interpolation architecture presented here resolves the mismatch between PEIG's  
discrete step structure and Godot 4's continuous render loop without adding unnecessary  
complexity. The fractional-step accumulator provides frame-rate independence. The  
lerp/snap dispatch policy respects the semantic distinction between continuous metrics  
and threshold events. Angular interpolation for phase eliminates the most severe visual  
artifact in the system. Smoothstep easing gives the rotating wave an organic, perceptible  
pulse. Edge cylinder construction handles dynamic geometry cleanly. And the entire system  
remains under 0.15 ms per frame on target hardware, leaving the full performance budget  
for shaders, UI, and future experiment scale-up.

The RingController is deliberately thin: it advances a clock, fetches two keyframes,  
interpolates, and writes to the GPU. State lives in \`PeigData\`. Visuals live in MultiMesh.  
The controller is the bridge — and it should stay that way.

\---

\#\# Appendix A: Complete \`RingController.gd\`

\`\`\`gdscript  
extends Node3D

@export var steps\_per\_second: float \= 2.0  
@export var loop: bool \= true

var \_playhead: float \= 0.0  
var \_playing: bool \= true  
var \_step\_count: int \= 0

@onready var \_node\_mm: MultiMesh \= $NodeMultiMesh.multimesh  
@onready var \_edge\_mm: MultiMesh \= $EdgeMultiMesh.multimesh

func \_ready() \-\> void:  
    \_step\_count \= PeigData.step\_count()

func \_process(delta: float) \-\> void:  
    if not \_playing:  
        return  
    \_playhead \+= delta \* steps\_per\_second  
    var max\_p := float(\_step\_count \- 1\)  
    if \_playhead \>= max\_p:  
        if loop:  
            \_playhead \= fmod(\_playhead, max\_p)  
        else:  
            \_playhead \= max\_p  
            \_playing \= false  
    \_update\_visuals(\_playhead)

func seek(target: float) \-\> void:  
    \_playhead \= clamp(target, 0.0, float(\_step\_count \- 1))  
    \_update\_visuals(\_playhead)

func set\_playing(value: bool) \-\> void:  
    \_playing \= value

func \_ease\_t(t: float) \-\> float:  
    return t \* t \* (3.0 \- 2.0 \* t)

func \_update\_visuals(playhead: float) \-\> void:  
    var step\_a := int(floor(playhead))  
    var t := playhead \- float(step\_a)  
    var et := \_ease\_t(t)  
    var pair: Array \= PeigData.get\_step\_pair(step\_a)  
    var state\_a: Dictionary \= pair  
    var state\_b: Dictionary \= pair \[ppl-ai-file-upload.s3.amazonaws\](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/154959549/9c544a75-4122-4a36-b6b4-0436e0bbc260/PEIG\_Papers\_XVII\_XVIII\_XX.md)  
    \_write\_node\_instances(state\_a, state\_b, t, et)  
    \_write\_edge\_instances(state\_a, state\_b, t, et)

func \_write\_node\_instances(  
        state\_a: Dictionary, state\_b: Dictionary,  
        t: float, et: float) \-\> void:  
    var nodes\_a: Dictionary \= state\_a.get("nodes", {})  
    var nodes\_b: Dictionary \= state\_b.get("nodes", {})  
    var names: Array \= nodes\_a.keys()  
    for i in range(names.size()):  
        var name: String \= names\[i\]  
        var na: Dictionary \= nodes\_a\[name\]  
        var nb: Dictionary \= nodes\_b\[name\]  
        var pos\_a := Vector3(na\["x"\], na\["y"\], na\["z"\])  
        var pos\_b := Vector3(nb\["x"\], nb\["y"\], nb\["z"\])  
        var pos := pos\_a.lerp(pos\_b, t)  
        var pcm: float  \= lerp(float(na\["pcm"\]),     float(nb\["pcm"\]),     et)  
        var nf: float   \= lerp(float(na\["negfrac"\]),  float(nb\["negfrac"\]),  et)  
        var phi: float  \= lerp\_angle(float(na\["phi"\]), float(nb\["phi"\]),    et)  
        var src := nb if t \>= 0.5 else na  
        var zone: int  \= int(src\["zone"\])  
        var gen\_a: int \= int(na\["generation"\])  
        var gen\_b: int \= int(nb\["generation"\])  
        var gen: int   \= gen\_b if t \>= 0.5 else gen\_a  
        if gen\_b \< gen\_a:  
            pos.y \-= sin(t \* PI) \* 0.3  
        elif gen\_b \> gen\_a:  
            pos.y \+= sin(t \* PI) \* 0.3  
        \_node\_mm.set\_instance\_transform(i, Transform3D(Basis(), pos))  
        var phi\_norm := (phi \+ PI) / TAU  
        \_node\_mm.set\_instance\_custom\_data(i,  
            Color(pcm \* 2.0 \+ 1.0, nf, phi\_norm, float(zone) / 3.0))

func \_write\_edge\_instances(  
        state\_a: Dictionary, state\_b: Dictionary,  
        t: float, et: float) \-\> void:  
    var edges\_a: Dictionary \= state\_a.get("edges", {})  
    var edges\_b: Dictionary \= state\_b.get("edges", {})  
    var nodes\_a: Dictionary \= state\_a.get("nodes", {})  
    var nodes\_b: Dictionary \= state\_b.get("nodes", {})  
    var edge\_ids: Array \= edges\_a.keys()  
    for i in range(edge\_ids.size()):  
        var eid: String \= edge\_ids\[i\]  
        var ea: Dictionary \= edges\_a\[eid\]  
        var eb: Dictionary \= edges\_b\[eid\]  
        var src\_pos := \_lerp\_node\_pos(nodes\_a, nodes\_b, ea\["source"\], t)  
        var tgt\_pos := \_lerp\_node\_pos(nodes\_a, nodes\_b, ea\["target"\], t)  
        var mid := src\_pos.lerp(tgt\_pos, 0.5)  
        var diff := tgt\_pos \- src\_pos  
        var length := diff.length()  
        var up := diff.normalized() if length \> 0.001 else Vector3.UP  
        var basis := Basis()  
        basis.y \= up  
        basis.x \= up.cross(Vector3.RIGHT).normalized()  
        if basis.x.length\_squared() \< 0.001:  
            basis.x \= up.cross(Vector3.FORWARD).normalized()  
        basis.z \= basis.x.cross(basis.y).normalized()  
        basis \= basis.scaled(Vector3(0.04, length \* 0.5, 0.04))  
        \_edge\_mm.set\_instance\_transform(i, Transform3D(basis, mid))  
        var mi: float \= lerp(float(ea.get("mi", 0.0)), float(eb.get("mi", 0.0)), et)  
        var bridge\_src := eb if t \>= 0.5 else ea  
        var bridge: float \= 1.0 if bridge\_src.get("bridge", false) else 0.0  
        \_edge\_mm.set\_instance\_custom\_data(i, Color(mi, bridge, 0.0, 0.0))

func \_lerp\_node\_pos(  
        nodes\_a: Dictionary, nodes\_b: Dictionary,  
        name: String, t: float) \-\> Vector3:  
    var na := nodes\_a.get(name, {})  
    var nb := nodes\_b.get(name, {})  
    return Vector3(na\["x"\], na\["y"\], na\["z"\]).lerp(  
           Vector3(nb\["x"\], nb\["y"\], nb\["z"\]), t)  
\`\`\`

\---

\#\# Appendix B: \`PeigData.gd\` Autoload

\`\`\`gdscript  
extends Node

var \_experiments: Dictionary \= {}  
var \_current: Dictionary \= {}

func load\_experiment(name: String) \-\> void:  
    var path := "res://data/peig/%s.json" % name  
    var text := FileAccess.get\_file\_as\_string(path)  
    var parsed \= JSON.parse\_string(text)  
    if parsed is Dictionary:  
        \_experiments\[name\] \= parsed  
        \_current \= parsed  
    else:  
        push\_error("PeigData: failed to parse %s" % path)

func step\_count() \-\> int:  
    return \_current.get("steps", \[\]).size()

func get\_step\_state(step: int) \-\> Dictionary:  
    var steps: Array \= \_current.get("steps", \[\])  
    return steps\[clamp(step, 0, steps.size() \- 1)\]

func get\_step\_pair(step\_floor: int) \-\> Array:  
    var steps: Array \= \_current.get("steps", \[\])  
    var a := clamp(step\_floor, 0, steps.size() \- 1\)  
    var b := clamp(step\_floor \+ 1, 0, steps.size() \- 1\)  
    return \[steps\[a\], steps\[b\]\]  
\`\`\`

\---

\*White paper version 1.0 — PEIG Brotherhood Research Series\*  
\*Author: Kevin Monette | April 2026\*  
\*Companion to: GodotPeig Documentation (JUST HORIZON \+ JUST EVOLVE pass)\*  
\*Grounded in PEIG Framework Papers XVII, XVIII, XX\*  
\`\`\`