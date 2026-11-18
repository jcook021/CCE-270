# Prompt log

- **Asked:** Set up the project folders for a single-file web app, document the layout, and do not build the app.
- **Changed:** Added the numbered folders and their READMEs, documented file placement in `AGENTS.md`, and created top-level `spec.md` and an empty HTML shell.
- **Worked:** Yes; the requested layout is in place and no app behavior was implemented.

- **Asked:** Commit the project changes.
- **Changed:** Checked `spec.md`; it was already included in the previous project-layout commit, with no pending changes.
- **Worked:** No additional project commit was needed.

- **Asked:** Add the staged build plan to the end of the spec.
- **Changed:** Appended six incremental build stages with checks and prerequisites to `spec.md`; wrote no code.
- **Worked:** Yes; the staged plan is recorded at the end of the spec.

- **Asked:** Build stage 1 as a single-file static mockup with all specified inputs and outputs, but no calculations.
- **Changed:** Replaced `index.html` with a responsive mockup, illustrative SVG map, sample controls/results, and explicit placeholder/source notes.
- **Worked:** Yes; browser checks confirmed desktop and narrow layouts render without horizontal overflow, and changing controls leaves the example outputs unchanged.

- **Asked:** Build only stage 2 with map/area interactions, keeping calculations separate from drawing code.
- **Changed:** Replaced the placeholder map with Provo Esri World Imagery; added polygon draw/edit/delete, sequential area IDs, editable names, surface colors, a C-value control, and a synchronized area schedule. Recorded the provider and usage caveat in `spec.md`; kept acreage pending until stage 4 and runoff/pipe results mocked.
- **Worked:** Yes; browser checks confirmed imagery loads, drawing/editing/deleting and area controls work, result values remain fixed, and the narrow layout has no horizontal overflow. No calculations were added because acreage was deferred to stage 4.
