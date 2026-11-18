# Project specification
# Site Runoff

## Purpose
Peak storm runoff from a small site with the rational method, and the
size of the storm drain pipe that carries it.

## Inputs
| Input | Units | Range or choices | Default | Control |
|---|---|---|---|---|
| Site areas | acres | Greater than 0 and within the displayed map area | No areas selected | Draw, edit, or delete polygons on the map |
| Surface type and runoff coefficient C | C is dimensionless | Roof, pavement/asphalt, lawn, or other; 0 ≤ C ≤ 1 | No surface selected; asphalt C = 0.90 per validation; other preset C values need definition | Surface-type dropdown; show the preset C and allow numeric override |
| Design storm | years | 2, 10, 25, or 100 | 10 years (provisional; matches validation) | Dropdown |
| Time of concentration Tc | minutes | Durations supported by the configured Provo rainfall table | None; require entry | Numeric input; reject durations outside the table range |
| Pipe slope | percent (%) | 0.1–10.0% (provisional) | 1% (matches validation) | Numeric input |
| Manning roughness n | Empirical coefficient in the U.S. customary equation | Fixed at 0.013 for the provisional smooth-concrete assumption | 0.013 | No user control; display the assumption |

Assume the map and rainfall lookup are for Provo; there is no location selector. Measure polygon area in UTM Zone 12N (EPSG:32612) and convert square meters to acres. If sites outside Provo are in scope, add a site-location input and location-specific rainfall data. Rainfall intensity i is derived from the selected storm and Tc using the Provo IDF table; supply the table source, values, units, and interpolation method. Do not extrapolate beyond its duration range. The standard pipe-size catalog must come from the applicable local standard; it is configuration rather than a user input.

The slope limits and smooth-concrete roughness assumption are provisional and need confirmation against the applicable design standard.

## Calculations
- Calculate each polygon's area in UTM Zone 12N, then convert it to acres: `A_acres = A_m2 / 4046.8564224`.
- Calculate the area-weighted runoff coefficient: `Cw = sum(Cj * Aj) / Atotal`, where `Aj` is each polygon's area in acres, `Cj` is its dimensionless runoff coefficient, and `Atotal = sum(Aj)`.
- Look up rainfall intensity `i` for the selected return period and `Tc` in the Provo IDF table. Use the table's stated interpolation method within its duration range only. `i` is in inches/hour.
- Calculate peak runoff using U.S. customary units: `Qpeak = 1.008 * Cw * i * Atotal`, where `Atotal` is in acres and `Qpeak` is in cubic feet/second (cfs).
- For each standard circular pipe candidate, calculate full-pipe capacity using Manning's equation: `Qpipe = (1.486 / n) * Apipe * R^(2/3) * S^(1/2)`. Use `n = 0.013`, `D` in feet, `Apipe = pi * D^2 / 4` in square feet, `R = D / 4` in feet, and `S = pipe_slope_percent / 100` in feet/foot; `Qpipe` is in cfs.
- Select the smallest catalog diameter whose `Qpipe` is at least `Qpeak`. If no catalog size meets the flow, report that no listed size is adequate.

## Outputs
- Areas on the map use stable IDs (A1, A2, A3, ...) assigned when drawn. IDs remain unchanged when an area is edited or reclassified; users may add an optional name. Match map labels to the results list.
- Color areas by surface type with a legend: roof `#0072B2` (blue), pavement/asphalt `#E69F00` (orange), lawn `#009E73` (green), and other `#CC79A7` (magenta). Use translucent fills and contrasting outlines so the satellite imagery remains visible and color is not the only distinction.
- An area table with each area's ID/name, surface type, C, and area in acres, followed by total area and weighted C.
- A runoff summary with design storm (years), Tc (minutes), rainfall intensity i (in/hr), and peak flow Qpeak (cfs).
- A pipe-sizing result with nominal diameter (in), full-pipe capacity (cfs), required Qpeak (cfs), slope (%), and Manning n. If no catalog size meets Qpeak, state that no listed size is adequate.
- A visible assumptions and sources note beneath the results with the Provo IDF table source, pipe-size catalog/standard, area projection (UTM Zone 12N), and Manning n assumption.
- Display calculated numeric values to two decimal places without rounding intermediate calculations; display positive areas that would round to 0.00 acres as `<0.01 ac`. Show nominal pipe sizes exactly as listed in the catalog.

## Look and feel
Clean and professional, with an original blend of retro rock-poster energy and colorful puppet-theater staging. Use warm cream (`#FFF4D6`), deep aubergine (`#2E193D`), gold (`#E7B63B`), and coral (`#D94F4F`) for the app's non-map chrome; keep the established surface-class colors reserved for map areas.

Use prominent abstract stage arches, spotlights, stars, or rhythm marks throughout the non-map chrome. Do not arrange the interface to depict a recognizable person or character, and do not obscure map features, controls, or results. On wide screens, keep the map as the large central canvas with controls and results in a right-side panel; on narrow screens, stack the map above the panel.

Use a readable, rounded sans-serif with clear numerals for the interface, labels, and results; keep decorative typography to headings.

## Validation
For the runoff arithmetic check, use 1.00 acre of asphalt (C = 0.90), a 10-year storm, `i = 3.0 in/hr`, and 1% slope. This gives `Qpeak = 2.72 cfs` with the 1.008 conversion factor. With `n = 0.013`, a full 12 in circular pipe has capacity of approximately 3.56 cfs. The selected size is the smallest catalog size that meets the peak flow; verifying that it is 12 in requires the configured pipe-size catalog. An end-to-end rainfall lookup test also requires the table duration/Tc that yields `i = 3.0 in/hr`.

## Out of scope
Detention ponds and inlet spacing.

## Build stages

Implement the application in the root `index.html` using vanilla HTML, CSS, and JavaScript with no build system. Keep reference datasets in `01_data/` and focused checks in `02_validation/`. Add a focused mapping library only if needed.

1. **Static layout mockup**
   - Create the header, map placeholder, controls, area table, runoff and pipe-result panels, and assumptions note. Use clearly labeled sample values; do not add map services, interactions, or real calculations.
   - **Check:** Open locally. Verify visual hierarchy, palette and legend distinction, readable sample values, and desktop/narrow layouts. Confirm values do not change based on inputs.
2. **Map and area interactions**
   - Use Esri World Imagery for the Provo map; support drawing/editing/deleting polygons, stable IDs, optional names, and surface selection. Keep acreage pending and runoff/pipe results mocked until later stages.
   - **Check:** Draw, edit, reclassify, name, and delete polygons. Verify IDs remain stable and map colors, legend, and table rows stay synchronized. Check map controls on narrow screens.
3. **Reference data and input validation**
   - Define surface-coefficient presets, authoritative Provo IDF data and interpolation, and the standard pipe-size catalog. Keep provisional Manning `n` and slope assumptions labeled.
   - **Check:** Verify valid storm/duration and catalog lookups. Confirm unsupported durations, invalid coefficients/slopes, and missing reference data produce visible messages.
4. **Area and runoff calculations**
   - Calculate polygon areas, total area, weighted `C`, rainfall intensity from storm and `Tc`, and peak flow with the 1.008 conversion.
   - **Check:** Verify hand-calculated polygon areas and weighted-`C` cases. Confirm the 1-acre asphalt case produces 2.72 cfs when `i = 3.0 in/hr`, and that rainfall lookup does not extrapolate.
5. **Pipe capacity and selection**
   - Calculate full-pipe Manning capacity for each catalog diameter and select the smallest size meeting `Qpeak`; report when no listed size is adequate.
   - **Check:** Verify the 12-inch, `n = 0.013`, 1% slope capacity is about 3.56 cfs. Test a smaller failing size, an exact-capacity boundary, and a case where no size is adequate.
6. **End-to-end integration and release checks**
   - Connect map edits, inputs, calculations, and outputs; finish accessibility, responsive behavior, and GitHub Pages loading.
   - **Check:** Complete the validation case from drawing through selected pipe size. Test empty/invalid states, keyboard operation, contrast, narrow screens, and direct loading of root `index.html` on GitHub Pages.

### Stage prerequisites

- Stage 2 uses the public Esri World Imagery tile service without an API key in the prototype. Include attribution, stream imagery only (do not export tiles), and review current Esri terms before publishing.
- Supply authoritative Provo rainfall data, surface `C` presets, and the applicable pipe-size catalog before stage 3.
- Confirm slope limits and the provisional `n = 0.013` assumption before treating results as design-ready.
