### Look

**You own the visual identity verdict. architect stays software.**

Match this playbook when the user talks about look, cute, warm, cartoony, silhouette, stickers, identity, plastic lighting, uncanny face, or generic AI art. Do not match Feature. Do not match Visual parity unless they handed a frozen still as the truth.

1. Load project `.cursor/skills/taste-<site>/` if present. If missing, say so and work from atelier rubrics only. Do not invent a house style.
2. `how` only over where the mesh, CSS, or scene lives. Not a type redesign.
3. Capture a still of the real surface (`control-ui` or the repo's verify skill). Do not argue from CSS.
4. Run atelier `critique-look`. Score the shared 17-test rubric. Critique before suggestions. Symptom / cause / intervention / expected effect. Name the three biggest problems, the single highest-leverage change, and what not to change.
5. Open the one specialist that matches the named weakness (`strengthen-silhouette`, `identity-vs-sticker`, `materials-and-light`, `story-staging`).
6. If the look is undecided, hand variants to **Prototype**, then return here to judge the stills.
7. If one metric is named, **Hillclimb** with a frozen still or score. Do not edit a Visual parity baseline to pass taste.
8. If the look is decided and needs shipping code, **Feature** with `architect skipped: look already chosen` unless the change crosses a real software boundary.
9. Contested look: `arena` with the atelier rubric, not `architect/references/design-red-flags.md`.

No PR. Feature and Hillclimb already open one. Critique-only is an answer, not a diff.

**Reply:** the scores, the three problems, the one change, what you kept, and the still paths.
