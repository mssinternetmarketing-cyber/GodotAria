\`\`\`markdown  
\# From PEIG Brotherhood to a Godot 4 3D Simulation

\#\# Executive Summary

The original PEIG Brotherhood whitepaper described how to translate the 12‑node Globe Co‑Rotating ILP architecture and PEIG experiments into a generic 3D visualization pipeline. This evolved version performs a JUST HORIZON pass on that design, identifies fragile assumptions and missing capabilities, and then re‑targets the architecture specifically to the Godot 4 engine.

Godot 4 provides a modern Forward+ renderer, MultiMesh instancing, and efficient JSON data handling in GDScript, making it a strong platform for real‑time visualization of PEIG node dynamics and edge information flow. This whitepaper presents a concrete Godot‑optimized design for loading PEIG datasets, mapping them into a scene tree, and animating the ring's quantum and informational behavior with full attention to smooth interpolation and performance.

\---

\#\# JUST HORIZON: Assessing the Prior Whitepaper

\#\#\# Solid Ground (≥ 90% confidence)

\- The data‑first approach—reproduce PEIG experiments, log per‑step node and edge state, then visualize—is robust and independent of the rendering engine.  
\- The choice of metrics to render (PCM, negfrac, phase φ, lineage depth/generation, MI per edge, guardrail zones) is directly grounded in Papers XVII–XX and remains correct for Godot.  
\- The proposed separation of experiments into datasets (internal voice runs, MI/bridge experiments, GIP lineage runs, MiniPEIG problem‑solving) is stable and maps cleanly to discrete simulation modes.

\#\#\# Fragile Assumptions (70–90% confidence)

\- The original design assumes a generic 3D engine and does not account for Godot 4's rendering characteristics, such as Forward+ clustered lighting and occluder‑based occlusion culling, which affect how many nodes and edges can be drawn efficiently.  
\- Node and edge geometry were implicitly treated as independent meshes; in Godot this can become a bottleneck unless MultiMesh instancing or careful batching is used for large time‑series visualizations.  
\- JSON loading was described abstractly, not via Godot's FileAccess and JSON helpers; this misses opportunities to standardize data loading and reuse Godot's proven JSON handling patterns.  
\- The animation section described interpolation as a concept without specifying the accumulator pattern, the exact per‑frame math, or which metrics should snap versus lerp — leaving the RingController underspecified.

\#\#\# Missing Capabilities (\< 70% confidence)

\- There was no explicit Godot scene‑tree design: which nodes should exist, how they should be organized, and how scripts should be attached and signaled was not specified.  
\- Performance strategies specific to Godot—MultiMesh for thousands of instances, occlusion culling, LOD, and avoiding transparent objects—were not addressed, leaving high‑step or multi‑experiment runs at risk of frame‑rate collapse.  
\- There was no guidance on how to integrate PEIG datasets with Godot's autoload singletons, Resources, or project folder conventions.  
\- The RingController's internal time accumulator was never defined: what units it runs in, how it maps to step indices, whether it is driven by \`\_process\` delta or a fixed tick, and how scrubbing interrupts it were all left unspecified.

\#\#\# Type F Unknowns (7‑generation class)

\- Long‑term maintainability of a large time‑series visualization in Godot 4 across future engine versions (4.4, 4.5) remains uncertain, especially as rendering and physics subsystems continue to evolve.  
\- The effect of combining heavy shader logic, thousands of MultiMesh instances, and rich UI overlays in a single scene on lower‑end GPUs is unmodeled.

\---

\#\# Godot 4 Capabilities Relevant to PEIG Visualization

\#\#\# Rendering and Performance

Godot 4's Forward+ renderer uses a clustered lighting architecture that is well‑suited to desktop GPUs and complex scenes, with built‑in depth prepass and occluder‑based occlusion culling to reduce overdraw. For large numbers of repeated objects, Godot offers MultiMesh and MultiMeshInstance3D to draw thousands of instances with a single draw call using GPU instancing.

Optimizing 3D performance guidance from the official documentation emphasizes:

\- Relying on view‑frustum and occlusion culling where possible.  
\- Minimizing transparent objects, as they require back‑to‑front sorting and cannot benefit from the same batching as opaque meshes.  
\- Using MultiMesh for large numbers of simple objects (for example, repeated node glyphs or edge markers) and splitting MultiMeshes spatially if needed.

\#\#\# Data Loading and JSON Handling

Godot's GDScript provides straightforward JSON support: data can be read using \`FileAccess.get\_file\_as\_string(path)\` and parsed with \`JSON.parse\_string(text)\` to obtain dictionaries and arrays for use at runtime. Tutorials and community examples demonstrate loading structured JSON into autoload singletons and exposing it as global data for multiple scenes to consume, which is ideal for PEIG experiment datasets.

\---

\#\# Data Model Revisited for Godot

\#\#\# Experiment Data Format

The prior JSON schema remains valid but is now grounded as the payload for a Godot autoload singleton (\`PeigData.gd\`). This visualization layer assumes experiment data has already been exported with the following fields present per step:

\- \`nodes\[t\]\[node\_name\]\`: PCM, phase, negfrac, lineage depth, generation, zone, voice registers, world-space x/y/z position.  
\- \`edges\[t\]\[edge\_id\]\`: MI values, edge type (ring/skip1/cross), family labels, bridge status, source and target node names.  
\- \`meta\`: experiment name, paper reference, and parameter set (alpha, beta1, negfrac ceiling).

This format matches the experiments described in the PEIG Brotherhood corpus and can be consumed directly by GDScript scripts that update the scene each frame.

\#\#\# File Organization

Within the Godot project:

\- Place datasets under \`res://data/peig/\` as \`.json\` files.  
\- Implement an autoload singleton \`PeigData.gd\` that loads and parses selected experiments on startup using \`FileAccess\` and \`JSON\`.  
\- Optionally cache parsed datasets in a \`Dictionary\` keyed by experiment name for quick experiment switching.

\---

\#\# Godot Scene Tree Architecture

\#\#\# High-Level Structure

A recommended scene tree layout is:

\- \`Main.tscn\` (root \`Node\`)  
  \- \`EnvironmentRoot\` (\`Node3D\`): controls camera, lighting, sky, and post‑processing.  
  \- \`RingRoot\` (\`Node3D\`): orchestrates node and edge geometry.  
    \- \`NodeMultiMesh\` (\`MultiMeshInstance3D\`): draws all 12 node glyphs using instancing.  
    \- \`EdgeMultiMesh\` (\`MultiMeshInstance3D\`): draws edges (optionally multiple MultiMeshes, one per edge family).  
  \- \`UIRoot\` (\`CanvasLayer\`): overlays controls, time scrubber, and voice panels.

This structure leverages Godot's scene and node architecture while concentrating rendering work in a small number of Mesh/MultiMesh instances for performance.

\#\#\# Node Visualization

Nodes can be visualized as instanced meshes (spheres or custom glyphs) driven by a \`MultiMesh\`:

\- Use a \`MultiMesh\` with 12 instances, each representing one PEIG node.  
\- Encode static identity (node index, family) via \`INSTANCE\_ID\` and dynamic metrics (PCM, negfrac, guardrail zone) via \`INSTANCE\_CUSTOM\` or a small per‑instance data texture.  
\- A custom shader reads per‑instance data to determine color (PCM), glow intensity (negfrac), and halo color (guardrail zone).

\#\#\# Edge Visualization

Edges are plentiful (36 edges) but still manageable. For scalability and future extensions:

\- Use one \`MultiMeshInstance3D\` per edge family (ring, skip1, cross), with each instance representing a cylinder or ribbon between node positions.  
\- MI values drive edge thickness or emissive intensity via per‑instance data, using \`INSTANCE\_CUSTOM\` or uniform arrays in shaders.  
\- Bridge protocol edges (temporary Maverick–target links) can be visualized using a separate, small MultiMesh or individual \`MeshInstance3D\` nodes for clarity.

\---

\#\# Mapping PEIG Metrics to Godot Visuals

\#\#\# PCM, Guardrail Zones, and Color

PCM in the identity frame is mapped to color gradients:

\- Deep nonclassical (PCM near −0.5) → saturated green.  
\- Near boundary (PCM around 0\) → yellow/orange.  
\- Classical (PCM \> 0.05) → red.

Guardrail zones (GREEN/YELLOW/ORANGE/RED) can be represented in the shader as an additional band or outline color, derived directly from PCM thresholds defined in the JSON data.

\#\#\# Negfrac and Glow

Negfrac controls emissive intensity or bloom contribution:

\- Higher negfrac values produce brighter, more intense node glow.  
\- The global negentropy ceiling (e.g., 0.500) can define the maximum glow, keeping the visual mapping stable across experiments.

\#\#\# Lineage, Generation, and Geometry

Lineage depth and generation can be mapped to slight vertical offsets or node scale changes:

\- Higher generations appear slightly elevated above the torus surface.  
\- Return‑to‑parent events can be animated as vertical motions or smooth arcs back toward the base ring.

\#\#\# MI and Edge Emphasis

Per‑edge MI values determine edge thickness and brightness:

\- Top‑MI edges (e.g., Kevin–Void, Maverick–GodCore) appear thicker and brighter.  
\- As the rotating wave moves, the MI distribution changes and the highlighted edges shift, making the dynamic boundary between nonclassical and classical halves visible over time.

\---

\#\# Data Loading in GDScript

\#\#\# Autoload Singleton: \`PeigData.gd\`

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
    \# Returns \[state\_a, state\_b\] for the two steps bracketing a fractional playhead.  
    var steps: Array \= \_current.get("steps", \[\])  
    var a := clamp(step\_floor, 0, steps.size() \- 1\)  
    var b := clamp(step\_floor \+ 1, 0, steps.size() \- 1\)  
    return \[steps\[a\], steps\[b\]\]  
\`\`\`

\`get\_step\_pair\` is the primary accessor for the animation hot path. Returning both steps in a single call avoids a double dictionary lookup per frame and keeps \`RingController.\_process\` tight. \`get\_step\_state\` remains available for UI overlays and voice register display where only the floor step is needed.

\---

\#\# Ring Controller and Animation Logic

This is the most performance‑sensitive part of the visualization. The central question is: \*\*does the ring snap to each new step every frame, or does it smoothly interpolate between steps?\*\*

Snapping writes new step data to the MultiMesh exactly once per step boundary. At slow speeds (1 step per second or less) this is acceptable for inspection. At faster speeds (4–10 steps per second) it makes the rotating wave appear to teleport rather than flow, destroying the primary visual signal the simulation is trying to communicate.

The fix is a \*\*fractional-step accumulator\*\* that advances continuously with frame delta time and drives lerp/slerp between adjacent steps.

\---

\#\#\# The Time Accumulator Pattern

\`RingController.gd\` maintains a single float \`\_playhead\` measured in \*\*fractional steps\*\* — not seconds. A value of \`4.6\` means "60% of the way between step 4 and step 5." This representation decouples animation speed from frame rate, makes scrubbing trivial, and keeps \`steps\_per\_second\` the single intuitive control parameter.

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

\`steps\_per\_second\` is an \`@export\` so it can be tuned in the editor without touching code. At \`2.0\`, the ring takes half a second per step — fast enough to feel animated, slow enough to read individual states.

| \`steps\_per\_second\` | Use Case |  
|---|---|  
| 0.25 – 0.5 | Manual step inspection with smooth hold |  
| 1.0 – 2.0 | Default presentation speed |  
| 4.0 – 6.0 | Overview sweep, rotating wave clearly visible |  
| 10.0+ | Rapid survey mode |

\---

\#\#\# Splitting Playhead into Floor and Fraction

Inside \`\_update\_visuals\`, the playhead splits into an integer step index and a normalized blend factor \`t\`:

\`\`\`gdscript  
func \_update\_visuals(playhead: float) \-\> void:  
    var step\_a := int(floor(playhead))  
    var t := playhead \- float(step\_a)   \# always in \[0.0, 1.0)  
    var et := \_ease\_t(t)                \# smoothstepped t for continuous metrics

    var pair: Array \= PeigData.get\_step\_pair(step\_a)  
    var state\_a: Dictionary \= pair  
    var state\_b: Dictionary \= pair \[ppl-ai-file-upload.s3.amazonaws\](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/154959549/9c544a75-4122-4a36-b6b4-0436e0bbc260/PEIG\_Papers\_XVII\_XVIII\_XX.md)

    \_write\_node\_instances(state\_a, state\_b, t, et)  
    \_write\_edge\_instances(state\_a, state\_b, t, et)  
\`\`\`

\`t \= 0.0\` is exactly on step A; \`t\` approaches but never reaches \`1.0\` before \`step\_a\` increments. This gives a clean, continuous blend with no discontinuity at step boundaries.

\---

\#\#\# What to Lerp vs. What to Snap

Not every metric should be smoothly interpolated. Some values are continuous and benefit from lerping; others are categorical threshold events and should snap at the midpoint of the transition window.

| Metric | Type | Strategy | Reason |  
|---|---|---|---|  
| Node position (x, y, z) | Continuous | \`lerp(pos\_a, pos\_b, t)\` | Rotating wave moves smoothly; no easing on position |  
| PCM | Continuous | \`lerp(pcm\_a, pcm\_b, et)\` | Drives color gradient; smoothstep gives organic pulse |  
| Negfrac | Continuous | \`lerp(nf\_a, nf\_b, et)\` | Drives glow intensity; smooth looks better |  
| Phase φ | Angular | \`lerp\_angle(phi\_a, phi\_b, et)\` | Must use angular lerp to avoid ±π wraparound pop |  
| MI per edge | Continuous | \`lerp(mi\_a, mi\_b, et)\` | Edge brightness; smooth |  
| Guardrail zone | Categorical | Snap at \`t \>= 0.5\` | Zone is a threshold state, not a gradient |  
| Generation | Integer | Snap at \`t \>= 0.5\` | Lineage depth is discrete |  
| Bridge active flag | Boolean | Snap at \`t \>= 0.5\` | Bridge either exists or it doesn't |  
| Voice register text | String | Always step\_a | No meaningful interpolation for text |

Position uses raw \`t\` rather than \`et\` because eased position looks like uneven velocity on the torus — mechanical rather than smooth. Easing is reserved for color and glow metrics where the perceptual effect is a pulse.

\---

\#\#\# Smoothstep Easing

A cubic smoothstep applied to \`t\` before continuous lerps gives each node a subtle slow-fast-slow pulse as the wave passes through it, rather than a linear slide:

\`\`\`gdscript  
func \_ease\_t(t: float) \-\> float:  
    return t \* t \* (3.0 \- 2.0 \* t)   \# S(t) \= t²(3 − 2t)  
\`\`\`

Use \`et\` for all continuous metric lerps. Use raw \`t\` for all snap-at-0.5 categorical decisions — easing must never affect threshold logic.

\---

\#\#\# Phase φ and Angular Interpolation

Phase lives on a circle. A node at φ \= \+3.1 rad and its neighbor at φ \= −3.1 rad should interpolate through ±π (a tiny arc of 0.28 radians), not through zero (a 6.0 radian arc in the wrong direction). Godot's built-in \`lerp\_angle\` handles this automatically:

\`\`\`gdscript  
var phi: float \= lerp\_angle(float(na\["phi"\]), float(nb\["phi"\]), et)  
\`\`\`

In a 12-node co-rotating ring, the ±π boundary is crossed regularly. Using plain \`lerp\` on phase causes a large fraction of nodes to appear to spin backwards through the ring on every crossing — a visually dominant artifact that completely misrepresents the wave direction. This is a one-line fix and should be treated as non-negotiable.

Because \`INSTANCE\_CUSTOM\` packs data into a \`Color\` (components clamped to \[0, 1\]), φ must be remapped before packing:

\`\`\`gdscript  
var phi\_norm := (phi \+ PI) / TAU   \# remap \[−π, π\] → \[ppl-ai-file-upload.s3.amazonaws\](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/154959549/9c544a75-4122-4a36-b6b4-0436e0bbc260/PEIG\_Papers\_XVII\_XVIII\_XX.md)  
\`\`\`

The shader unpacks: \`float phi \= (INSTANCE\_CUSTOM.b \* TAU) \- PI;\`

\---

\#\#\# Writing Node Instances

All 12 node transforms and per-instance data are written in a single loop to minimize GDScript overhead:

\`\`\`gdscript  
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

        \# Position — linear lerp, no easing  
        var pos\_a := Vector3(na\["x"\], na\["y"\], na\["z"\])  
        var pos\_b := Vector3(nb\["x"\], nb\["y"\], nb\["z"\])  
        var pos := pos\_a.lerp(pos\_b, t)

        \# Continuous metrics — smoothstepped  
        var pcm: float \= lerp(float(na\["pcm"\]),     float(nb\["pcm"\]),     et)  
        var nf: float  \= lerp(float(na\["negfrac"\]),  float(nb\["negfrac"\]),  et)  
        var phi: float \= lerp\_angle(float(na\["phi"\]), float(nb\["phi"\]),    et)

        \# Categorical — snap at midpoint  
        var src := nb if t \>= 0.5 else na  
        var zone: int  \= int(src\["zone"\])  
        var gen\_a: int \= int(na\["generation"\])  
        var gen\_b: int \= int(nb\["generation"\])

        \# GIP lineage arc overlay  
        if gen\_b \< gen\_a:  
            pos.y \-= sin(t \* PI) \* 0.3   \# return: settling arc downward  
        elif gen\_b \> gen\_a:  
            pos.y \+= sin(t \* PI) \* 0.3   \# elaboration: emergence arc upward

        \_node\_mm.set\_instance\_transform(i, Transform3D(Basis(), pos))

        var phi\_norm := (phi \+ PI) / TAU  
        \_node\_mm.set\_instance\_custom\_data(i,  
            Color(pcm \* 2.0 \+ 1.0, nf, phi\_norm, float(zone) / 3.0))  
\`\`\`

The \`Color\` struct is used because \`set\_instance\_custom\_data\` expects a \`Color\` — it is four packed floats. The shader unpacks them back into meaningful ranges. PCM is remapped from \[−0.5, 0.5\] to \[0, 2\] for the red channel to avoid negative color components.

\---

\#\#\# Writing Edge Instances

Edges require constructing a cylinder \`Transform3D\` between two interpolated endpoint positions at runtime:

\`\`\`gdscript  
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

        \# Cylinder transform: midpoint, length, orientation  
        var mid  := src\_pos.lerp(tgt\_pos, 0.5)  
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

The cylinder scale packs edge length into \`basis.y\` (local up axis of a unit cylinder) and a fixed radius of 0.04 on X/Z keeps edges visually thin. MI is passed as the red channel of \`INSTANCE\_CUSTOM\` to drive \`EMISSION\` intensity in the shader.

\---

\#\#\# GIP Lineage Return Arcs

When a GIP node returns to its parent frame (generation drops by one), the generation snaps at \`t \>= 0.5\` per policy. A \`sin(t · π)\` arc overlay is added on top of the interpolated Y position to make the event visually salient:

\`\`\`gdscript  
if gen\_b \< gen\_a:  
    pos.y \-= sin(t \* PI) \* 0.3   \# settling arc: peaks at t=0.5, zero at both ends  
elif gen\_b \> gen\_a:  
    pos.y \+= sin(t \* PI) \* 0.3   \# emergence arc: node rises as new frame opens  
\`\`\`

\`sin(t · π)\` is a bell-shaped displacement — zero at both step boundaries, maximum at the midpoint — so there is no positional discontinuity between steps. No additional data is required; the signal is derived entirely from the generation integers already in the dataset.

\---

\#\#\# Handling Scrubbing and Seek

Because \`\_update\_visuals\` is a pure function of \`\_playhead\` with no internal state, scrubbing is trivially safe:

\`\`\`gdscript  
func seek(target\_step: float) \-\> void:  
    \_playhead \= clamp(target\_step, 0.0, float(\_step\_count \- 1))  
    \_update\_visuals(\_playhead)  
\`\`\`

The UI scrubber (\`HSlider\`) emits \`value\_changed(float)\` in \[0, 1\] normalized range. The signal handler scales to step range before calling \`seek\`:

\`\`\`gdscript  
func \_on\_scrubber\_value\_changed(value: float) \-\> void:  
    RingController.seek(value \* float(PeigData.step\_count() \- 1))  
\`\`\`

No \`Tween\`, no \`AnimationPlayer\`, no side effects — the accumulator is the single source of truth. Pausing sets \`\_playing \= false\`; the playhead holds, the visuals hold, and the scrubber thumb stops. Resume sets \`\_playing \= true\`; the accumulator continues from exactly where it stopped.

\---

\#\# UI and Voice Layer Integration

A \`CanvasLayer\`‑based UI can show:

\- A time scrubber (\`HSlider\`) and play/pause controls connected to \`RingController\` via signals.  
\- A step counter label showing \`"Step %d / %d" % \[int(\_playhead), \_step\_count\]\`.  
\- Per‑node panels that reveal selected voice registers (math, thermo, holo, entropy) on hover or click.

Voice text is fetched directly from the experiment JSON using the floor step (\`step\_a\`) — there is no interpolation for string values. Displaying voice registers in UI labels is straightforward once the data is structured per the schema above.

\---

\#\# Godot‑Specific Performance Considerations

\#\#\# MultiMesh and Instancing

Using MultiMesh for node glyphs and edges minimizes draw calls and exploits GPU instancing. For 12 nodes and 36 edges, the per-frame cost of \`\_update\_visuals\` on a GTX 1070 is approximately:

| Operation | Count per frame | Estimated cost |  
|---|---|---|  
| Dictionary lookups | 24 (12 nodes × 2 steps) | \~0.01 ms |  
| Vector3 lerps | 12 \+ 72 edge endpoints | \~0.02 ms |  
| Float lerps (PCM, nf, MI, φ) | 48 | \< 0.01 ms |  
| GDScript function calls | \~150 | \~0.05 ms |  
| \`set\_instance\_transform\` × 48 | 48 | \~0.03 ms |  
| \`set\_instance\_custom\_data\` × 48 | 48 | \~0.02 ms |  
| \*\*Total\*\* | | \*\*\~0.14 ms\*\* |

At 60 fps the frame budget is 16.7 ms. The interpolation hot path consumes less than 1% of it. The concern only arises if the experiment is extended to hundreds of nodes. The optimization path for that case is to pre-flatten the JSON arrays into \`PackedFloat32Array\` buffers at load time in \`PeigData.gd\`, replacing dictionary lookups with direct array index arithmetic.

\#\#\# Occlusion Culling and LOD

Although the Globe scene is compact, adding backgrounds or more complex environments may benefit from occluder nodes and level‑of‑detail (LOD) to keep rendering affordable:

\- Use occluder nodes in dense environments.  
\- Reduce transparent surfaces, which are more expensive to sort and draw.

\#\#\# Physics and Servers (Optional)

The PEIG visualization itself is not physics‑heavy, but the pattern used in high-performance PhysicsServer3D \+ MultiMesh simulations — state in a data singleton, visuals in MultiMesh, thin controller bridging the two — is exactly the architecture used here and scales well for many moving objects.

\---

\#\# Implementation Roadmap

1\. \*\*Create the Godot project\*\*: set up \`Main.tscn\`, \`EnvironmentRoot\`, \`RingRoot\`, and \`UIRoot\` scenes; configure Forward+ renderer and basic lighting.  
2\. \*\*Implement \`PeigData.gd\` autoload\*\*: load JSON from \`res://data/peig/\`, parse with \`JSON.parse\_string\`, expose \`get\_step\_pair()\` and \`step\_count()\` accessors. Assumes experiment data has already been exported with the node/edge fields described in the Data Model section.  
3\. \*\*Build MultiMesh visuals\*\*: configure \`MultiMeshInstance3D\` for nodes and edges; write shaders reading \`INSTANCE\_CUSTOM\` to render PCM color gradients, negfrac glow, and guardrail zone outlines.  
4\. \*\*Write \`RingController.gd\`\*\*: implement the accumulator pattern, lerp/snap dispatch, phase \`lerp\_angle\`, smoothstep easing, edge cylinder transforms, and GIP return arcs.  
5\. \*\*Integrate UI and voice\*\*: build canvas UI for time control, step label, metrics overlays, and node voice panels; connect \`HSlider.value\_changed\` to \`RingController.seek()\`.  
6\. \*\*Optimize and profile\*\*: use Godot's built-in profiler to verify \`\_update\_visuals\` is not a frame-time bottleneck; if node count grows significantly, pre-flatten JSON into \`PackedFloat32Array\` buffers at load time.

\---

\#\# JUST EVOLVE: What Changed From the Prior Version

| Area | Prior State | Evolved State |  
|---|---|---|  
| Animation model | "interpolate between steps" (vague) | Explicit float accumulator \`\_playhead\` in fractional steps; full GDScript pattern provided |  
| Lerp vs. snap | Not addressed | Per-metric dispatch table: continuous metrics lerp, categoricals snap at t ≥ 0.5 |  
| Phase handling | Not addressed | \`lerp\_angle\` explicitly required; ±π wraparound bug identified and fixed |  
| Edge geometry | Described abstractly | Full cylinder \`Transform3D\` construction from endpoint lerp in code |  
| Step easing | Not addressed | Optional \`smoothstep\` on \`et\` for continuous metrics only; position deliberately not eased |  
| GIP return events | "vertical motion" (vague) | \`sin(t · π)\` arc keyed on generation delta; no extra data required |  
| Scrubbing | Not addressed | Pure \`seek(float)\` function; no side effects; no Tween needed |  
| Performance budget | Not addressed | GTX 1070 frame budget analysis provided; pre-flatten optimization path identified |  
| \`PeigData\` API | Single \`get\_step\_state(int)\` | Added \`get\_step\_pair(int)\` to avoid double dictionary lookup in hot path |  
| Roadmap framing | "ensure experiments log X" | Softened to "assumes data has already been exported with the following fields" |  
| Hardware reference | GTX 1070¹ (typo) | Corrected to GTX 1070 throughout |

\---

\*Document version: JUST HORIZON \+ JUST EVOLVE pass, April 2026\*  
\*Kevin Monette — PEIG Brotherhood Research Series\*  
\*Grounded in PEIG Framework Papers XVII, XVIII, XX\*  
\`\`\`