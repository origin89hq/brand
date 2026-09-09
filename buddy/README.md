# Buddy / shared moose character

The canonical Origin89 Buddy is a warm brown, upright moose. This folder owns the editable model, construction modules, validation and character review. Every identity illustration and website image derives from this source.

Open [buddy.blend](blender/buddy.blend). Choose a view layer in Blender:

1. **Skeleton** — renderable bones, separate jaw, teeth, nasal cartilage and a translucent skin envelope.
2. **Organs** — simplified internal volume guides.
3. **Muscles** — major muscle envelopes over the shared skeletal landmarks.
4. **Skin** — one connected torso, shoulders, arms and legs; shaped head, independently closing lower jaw, cupped ears, throat bell and recessed side nostrils.
5. **Fur** — editable, UV-attached native hair curves following the skin.

The `Buddy | pose rig` has stored tests at frame **1** (standing), **40** (explaining), and **80** (step study). These are static pose studies; the interval between them is not a finished walk cycle.

## Facial expressions

Select **Buddy | pose rig**, then open **Object Properties → Custom Properties**. The 26 numeric `face_` controls are keyframeable:

| Control | Movement |
| --- | --- |
| `face_jaw_open` | Opens the mandible with its teeth, gums and tongue |
| `face_smile`, `face_smile_L/R` | Raise or lower both mouth corners or either corner independently |
| `face_lip_raise`, `face_lip_lower` | Reveal or cover the tooth crowns |
| `face_lip_press`, `face_lip_pucker` | Press the soft lips together or purse them forward |
| `face_cheek_raise_L/R`, `face_muzzle_scrunch` | Lift either cheek and compress the soft muzzle |
| `face_tongue_out`, `face_tongue_curl` | Extend the tongue and curl its tip up or down |
| `face_tongue_side`, `face_tongue_twist`, `face_tongue_widen` | Bend, twist and change the width of the tongue |
| `face_blink_L`, `face_blink_R` | Close either eye independently |
| `face_upper_lid_L/R`, `face_lower_lid_L/R` | Adjust the upper and lower lids for squinting |
| `face_brow_raise_L/R`, `face_brow_tilt_L/R` | Lift a brow or tilt its inner corner |

The fitted eyelid surfaces wrap the corneas. A fine upper lid margin remains visible when closed. Skin shape keys move the lips and feathered brows; UV-attached hair follows the deformation. The oral chamber and furred cheek tissue stretch between the head and lower jaw. The lower-lip roll moves its cross sections together to preserve thickness in profile. The lower mouth lining has a rounded front edge tucked under the gum and a gradual transition into the inner lip. The throat bell follows the jaw, keeping its beard below the mouth floor when the jaw opens. The resting lips conceal the teeth, which remain rigidly attached to their respective bones.

Saved expression frames are **1 neutral**, **110 smile**, **140 delighted**, **170 surprised**, **200 concerned**, **230 wink**, **260 blink**, **290 playful lick**, **320 skeptical**, and **350 tongue peek**. The [expression sheet](expression-study.png), [eyelid sheet](eyelid-study.png), and [mouth sheet](mouth-study.png) show these controls in the finished coat. The [tongue sheet](tongue-study.png) shows the long tongue curling under the muzzle from three angles. The tongue-peek preset holds a small mouth opening with a gently downturned tip. The public `playful` avatar uses this preset and the shared front-facing avatar camera. Open the jaw before extending the tongue; its five controls can be combined and keyframed. These are editable expression studies; speech shapes and a timed performance have not been authored.

To experiment, stop on a preset frame, adjust the rig's custom properties, and insert a keyframe on the changed property to keep it. Scrubbing the timeline reloads the stored keys. The embedded **MOOSE | Facial controls** text block lists the same controls and frames.

The lower incisors, gum ridge and mandibular support use the same curved guide in `blender/dental.py`. Outer crowns turn with the arch and become slightly smaller toward the corners. The teeth stay rigid while the surrounding lips deform.

## Design

Buddy's short, sturdy legs support his [Lac Mac character story](story.md). The shared height map in `blender/proportions.py` reduces the hip-to-ankle interval by 40%, easing into the unchanged hoof base and torso shape. Bones, tissue guides and skin use the same map; grooming converts back to the original design coordinates. Rounded pasterns seat inside the upper hoof walls, with a close ankle coat at the transition.

The eyebrows use a separate dark, feathered groom swept upward and outward. A broad, softly blended short forehead coat leaves room for their movement without a shaved strip above each brow. Brow hair follows the existing independent shape keys.

Each upper eyelid carries four gently curled, tapered lashes toward its outer corner. The native curves attach to the eyelid surface, so they follow blinking and squinting together with the lid fur.

The character uses a deliberately adapted biped pelvis, spine, shoulders and legs, with a long moose muzzle, lateral eyes, leaf-shaped ears, broad palmate antlers and cloven hooves. The nose includes a soft-tissue/cartilage support volume extending beyond the shortened bony nasal roof. It is not a black button attached to the face.

The anatomy layers are modeling guides, not measured specimen meshes or a physiological simulation. Ruminant organ layout is simplified and adapted to the upright torso. The antlers and youthful proportions are an intentional mascot combination, not newborn calf anatomy.

The lower belly and hips are rounded, with narrow shoulders and light arms. Cross sections shape a continuous head and torso silhouette. The chest-to-belly coat is lighter, with a broad oval fade into the surrounding coat. Shorter underside hair follows the rounded arch between the thighs. A darker throat bell carries longer downward hair. The body coat has fine directional strands and sparse longer guard hairs. Shared shoulder, elbow and wrist weights are checked in standing, raised-arm and step poses; a production animation pass would still need joint topology and deformation refinement.

The ears have continuous cupped surfaces with warm inner shading, fine interior hair and softer furry rims. The cloven hooves have rounded walls, matte horn and flat soles. The antlers follow the supplied rack reference with tall broad palms, a swept lower beam, forward brow tines and smaller crown points. The outer points share the blade's continuous perimeter, and the lower beam extends directly into its final tip. The webs curve in depth, with tapered edges, lengthwise growth grooves, fine pores and a dry bone surface.

The feet and hands use paired half-hooves with tapered, gently pointed toes and angled outer walls. The feet retain broad heels and flat weight-bearing soles. The hand cleft narrows into a common furry wrist, with the hoof crowns seated inside the arm surface. The wrist skin blends between forearm and hand bones, and its coat shortens toward the horn. The explaining pose turns the hand upward to show its front. A [hand and wrist close-up](renders/brown-hands.png) shows that connection in the raised pose.

The arms and torso share one continuous skin mesh. Deforming shoulder tissue guides bridge the chest, back and upper arm beneath it. Gradual skin weights spread the arm's movement across that shoulder transition while keeping the lower belly still. The forearms sit clear of the belly, and one attached groom follows the connected skin without a separate shoulder cap seam.

Longer, finer shoulder hair blends into the dorsal coat, with a soft lifted curve and a gradual taper down each upper arm. Its grooming mask is independent of the joint weights, so the fuller coat follows the same skin in standing and raised-arm poses while the wrist stays close-coated.

[finish.py](blender/finish.py) preserves the authored smooth, directional shoulder and beard coat, materials and studio lighting. It sets the shared render quality at the end of model construction and for every export. Fur exports use up to 192 adaptive samples with denoising and a 64-sample floor to retain a soft, clean finish. Anatomy layers use a smaller sample floor. Responsive image sizes preserve detail in large illustrations. Small avatars use a front-facing close-up on green without changing the character's large-view finish.

The nostrils follow the supplied front/side references and nasal cross-sections: broad lateral pockets beneath a fleshy fold near the end of the hanging muzzle, tapering into an upper rear crease. The terminal muzzle has softly joined pads with a shallow central cleft. The lower jaw tapers toward a thin closing lip and widens back into the throat. The face study shows matching front, three-quarter and profile views.

Brown and navy are renderable color studies of the same geometry. `render_buddy.py --palette brown` changes only the coat/ear/lid palette for that render. The `.blend` opens in brown. In Scene Custom Properties, `coat_brown` switches the skin and fur together: **0 = navy**, **1 = brown**.

The muzzle is deep brown in the brown study and dark navy in the navy study, fading into the bridge and cheeks. Its short hair, underlying skin and inner-lip transition share the darker palette. Fine muzzle pores, tonal mottling and varied roughness are procedural nodes in `blender/surface_detail.py`. Their coordinates are stored on the skin so the detail follows facial deformation. The texture fades toward the furred bridge and cheek rather than forming a separate nose patch.

Muted chestnut markings blend through the forehead, bridge and cheeks in both coat studies. A shared mask colors the underlying skin and mixes warm native hair into the groom, with soft, uneven boundaries. The markings fade out before the dark nose and jaw seam and follow the face when it moves.

A small tapered tuft grows from the existing lower-belly surface as native hair curves. It blends into the coat and follows the pelvis deformation; there is no separate anatomical mesh beneath it.

## Rebuild and extend

From the repository root:

```sh
pnpm brand:rebuild
pnpm brand:check
```

The first command validates the saved `buddy.blend`, renders the character reviews, identity cutouts and expressions, then refreshes the sheets, guide, Reserve illustration and website WebP assets. It resumes matching completed renders. The second command checks source and output hashes without rendering.

Edit geometry, materials, fur and poses together in [buddy.blend](blender/buddy.blend). Ordinary image rebuilding preserves those edits. To explicitly regenerate the model from its Python construction modules, use `pnpm brand:model`, then `pnpm brand:rebuild`. The model command saves the previous file in ignored `.build/` before replacing it.

The construction source is [build_buddy.py](blender/build_buddy.py). [studio.py](blender/studio.py) owns cameras and application expression mappings; [review_jobs.py](blender/review_jobs.py) owns the 32 anatomy and expression views. The identity export inventory is [library_jobs.py](../source/library_jobs.py).

Small website avatars and Buddy app icons use front-facing green circles exported by [avatar/build_avatar.py](avatar/build_avatar.py). [presentation/render_face.py](presentation/render_face.py) renders seven expressions with the approved close camera and gentle default smile. [presentation/face-front.blend](presentation/face-front.blend) is the render input: saved camera, light, material, and greeting edits are preserved by `pnpm brand:avatars`. The same face, fur and lighting connect these small avatars and the seven wider transparent expressions in [presentation/](presentation/). The full-body cutout is ready for compositing; composed studio backgrounds remain optional. Run `pnpm brand:export` after changing avatar composition, `pnpm brand:avatars` after changing the front camera or expression controls, or `pnpm brand:presentation` after changing all presentation settings. The saved character geometry and soft coat stay shared. Navy remains an optional material study.

The character has 39 native checks covering anatomy, attached hair, fur roots in three poses, deformation, floor contact, hoof seating and facial controls. Every render sidecar records the source hash, frame, palette, camera, size, sampling, denoising and transparency. See the [interactive review](index.html) and [shared build instructions](../README.md).

## References and interpretation

- [DigiMorph / Ohio University: moose nasal anatomy](https://www.digimorph.org/specimens/Alces_alces/) — shortened bony nasal support, expanded nasal cartilage and soft tissue, lateral nostrils. Guides the head construction rather than exact proportions.
- [Oregon State University mammal collection](https://courses.ecampus.oregonstate.edu/wildlife/species.php?id=335) — long narrow rostrum, large ears, drooping nose, shoulder rise and short tail.
- [Alaska Department of Fish and Game: Moose](https://www.adfg.alaska.gov/static/education/wns/moose.pdf) — the throat bell is a fold of skin covered with hair. The broad light front patch is an art-directed choice from the supplied cartoon reference.
- [University of Minnesota large-animal anatomy: ruminant abdomen](https://pressbooks.umn.edu/largeanimalanatomy/chapter/abdomen-2/) — comparative guide for stomach compartment placement. This is bovine teaching material, not a moose-specific organ reconstruction.
- [Disney Animation: Flesh, Flab, and Fascia Simulation on Zootopia](https://www.disneyanimation.com/publications/flesh-flab-and-fascia-simulation-on-zootopia/) — published example of art-directed biped animals and layered anatomy. The present concept uses a simpler armature and skin workflow, not Disney's simulation system.

User-supplied moose pictures guide the soft face, smaller shoulders, expressive upright stance and broad antlers. No stock illustration was used as model geometry or texture.
