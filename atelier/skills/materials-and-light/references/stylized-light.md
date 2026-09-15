# Stylized light checklist

Conventions from public stylized-3D production notes. Link the [Valve NPAR 2007 PDF](https://cdn.akamai.steamstatic.com/apps/valve/2007/NPAR07_IllustrativeRenderingInTeamFortress2.pdf) and the [GDC 2008 slides](https://cdn.akamai.steamstatic.com/apps/valve/2008/GDC2008_StylizationWithAPurpose_TF2.pdf). Do not copy classes, hats, or team colors.

- Design until the figure is identifiable with shading off.
- Warm-to-cool hue shift. Shadows go cool, not black.
- Saturation up at the terminator.
- Drop high-frequency detail.
- Interior folds echo the silhouette.
- Rim highlights, not dark outlines, to pop the edge.
- Half-Lambert or a 1×N ramp so the dark side still has shape.
- Dedicated rim biased toward light from above.
- Impressionistic albedo. Photo textures fail under magnification.
- Character lights decoupled from the environment when the page is darker than the toy.
- Squint. One value hierarchy. Label lights.

For web, implement the conventions (`MeshToonMaterial` gradient maps, simplified shadows). Do not vendor a film lighting rig.
