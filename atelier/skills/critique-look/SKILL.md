---
name: critique-look
description: >-
  Entry specialist for visual identity and stylized character critique. Use for
  /critique-look, weak silhouette, stickers versus identity, plastic lighting,
  uncanny face, generic AI art, lost identity, or "make it cuter / warmer /
  more cartoony." Critique before suggestions. Not architect. Not visual parity.
disable-model-invocation: true
---

# Critique look

You own the verdict. Do not restyle until the critique is written.

`/poteto-mode` is the front door. This skill is the specialist the Look playbook names.

## Load

1. If `.cursor/skills/taste-<site>/SKILL.md` exists, read it and only the memory files it names for this weakness. That folder is product memory, not a second atelier.
2. If it is missing, say so. Work from this pack. Do not hallucinate a house style. The starter template is [`references/taste-product-template/`](references/taste-product-template/).
3. Capture a still of the real surface (`control-ui`, Playwright, or a public URL). No still, no critique.
4. Read [`references/critique-protocol.md`](references/critique-protocol.md), [`references/anti-defaults.md`](references/anti-defaults.md), and [`references/rubric.md`](references/rubric.md). Provenance is [`references/provenance.md`](references/provenance.md).

## Run

Critique before suggestions. Every issue is **symptom / cause / intervention / expected effect**. Ban “more polished,” “cuter,” “more premium,” and “more delightful” unless those words are bound in the product vocabulary file.

1. Two-second read. What draws the eye. What emotion. Whose page this could be.
2. Score all 17 rubric tests 0–4 with one observed fact each.
3. Name the three biggest problems.
4. Name the **single** highest-leverage change.
5. Name what **not** to change.
6. Hand the named weakness to one specialist if implementation follows:
   - mass / pose / blob → `strengthen-silhouette`
   - charm glued on, decals, icon planets → `identity-vs-sticker`
   - plastic, flat, photographic skin, dead volume → `materials-and-light`
   - floating mascot, same fade everywhere, no arrival → `story-staging`

Do not call `architect`. That skill is software shape. Do not use Visual parity as a taste loop.

## Reply

Scores table. Three problems. One change. What we keep. Paths to the stills. Missing `taste-<site>` called out in one line.
