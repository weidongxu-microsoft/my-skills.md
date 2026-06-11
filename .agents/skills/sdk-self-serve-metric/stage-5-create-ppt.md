# Stage 5 - Create presentation deck

## Goal

Create a PowerPoint summary deck from the persisted stage 3 metrics and charts.

Run this stage only when the user explicitly asks for a PPT, PowerPoint deck, or `.pptx` output.

## Inputs

- `progress\period.json`
- `result\language-summary-metrics.json`
- `result\language-pr-count-and-average-human-communication-bar.png` or `.svg`
- `result\language-teams-post-count-bar.png` or `.svg`
- per-language `result\<language-key>\metrics.json`
- per-language `result\<language-key>\pr-communication-bar.png` or `.svg`
- per-language `result\<language-key>\report.md`

## Outputs

- `result\self-serve-sdk-generation-review-metrics-<yyyymm>.pptx`
- optional `progress\stage-5.md`

## Checklist

```text
Stage 5 progress
- [ ] Load the stage 3 metrics and charts
- [ ] Build a title slide
- [ ] Add a cross-language summary slide
- [ ] Add per-language slides
- [ ] Add a metric definitions / notes slide
- [ ] Save the PPTX to result\
- [ ] Write progress\stage-5.md if useful
```

## Workflow

1. Load `progress\period.json` and the stage 3 result files.
2. Build the deck around the current reporting period and current language set from `sdk-source.md`.
3. Use the title:
   - `Metrics for self-serve, on SDK generation and review`
4. Add at least:
   - a title slide
   - an executive summary or cross-language summary slide
   - a slide containing the cross-language charts
   - one slide per language with key metrics and the per-language PR communication chart
   - a final slide with metric definitions or assumptions
5. Save the deck under `result\`.

## Recommended file name

```text
result\self-serve-sdk-generation-review-metrics-<yyyymm>.pptx
```

## Content guidance

- Keep the deck concise and presentation-ready.
- Use the persisted charts instead of regenerating data inside the deck builder whenever possible.
- Preserve the current metric definitions:
  - AutoPR counts use the filtered created-period cohort
  - human communication counts include issue comments and review comments only
  - review submission events are excluded
  - SDK generation related Teams posts include retained AutoPR discussion and SDK validation / generation-failure triage threads under the current filtering rules

## Error handling

- If stage 3 artifacts are missing, stop and document that stage 3 must be rerun first.
- If PPT generation fails, preserve the existing result files and document the failure in `progress\stage-5.md`.
- Do not create a placeholder or empty deck just to satisfy the stage.
