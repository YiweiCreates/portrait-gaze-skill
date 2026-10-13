# Integrating the result

The generated HTML is self-contained: a raster image embedded as a data URI, two SVG `clipPath` masks, two `[data-iris]` groups, and plain JavaScript. Open it via `file://` or a static web server. It does not fetch remote assets or use a camera.

To use the portrait in another page, copy its SVG, include `assets/gaze.js` once, and call:

```js
const controller = PortraitGaze.mount(svgElement, {
  eyes: [
    {center: [leftX, leftY], max_offset: [horizontal, vertical]},
    {center: [rightX, rightY], max_offset: [horizontal, vertical]}
  ]
});
// On component removal:
controller.destroy();
```

Take the values from the generated page's configuration. Keep each iris inside its original clipping group and preserve the `viewBox`. When duplicating the same portrait SVG on one page, give its clip-path IDs unique instance prefixes and update their `url(#...)` references. Different image/measurement pairs get distinct IDs at build time.

The runtime uses inverse SVG screen transforms so coordinates survive resizing and scrolling. Both eyes receive the same offset to avoid accidental cross-eye motion. A dead zone around the eye midpoint returns a nearly centered gaze. Offsets are bounded; the mask remains fixed.

Mouse movement works across the window. Touch movement begins only on the portrait and returns to neutral on release. Apply `touch-action: none` to the SVG, not the entire page; page scrolling outside it remains available. The supplied template includes this rule. `prefers-reduced-motion: reduce` keeps eyes still. An optional button `[data-toggle-motion]` inside `[data-gaze-demo]` pauses/resumes following.

The template has inline scripts/styles and an embedded data URI. If the target site uses a strict Content Security Policy, move scripts/styles into permitted local files and serve the image from an allowed source; do not weaken the whole site's policy. For a framework component, mount after rendering and destroy during cleanup.
