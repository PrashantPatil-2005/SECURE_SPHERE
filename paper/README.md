# SecuriSphere IEEE Paper

## Main file

`securisphere.tex` — complete IEEE conference draft (~5–6 pages when compiled).

## Compile locally

```bash
cd paper
pdflatex securisphere.tex
pdflatex securisphere.tex
```

Requires a LaTeX distribution with `IEEEtran` (TeX Live, MiKTeX, or Overleaf).

## Overleaf

1. Create project from **IEEE Conference Template**
2. Replace `main.tex` body with `securisphere.tex` contents
3. Upload figures to `figures/` when ready and replace `\figplaceholder{...}` with `\includegraphics`

## Figures to add later

| Figure | File (suggested) | Section |
|--------|------------------|---------|
| Fig. 1 — Architecture | `figures/architecture.pdf` | §III-B |
| Fig. 2 — Workflow | `figures/workflow.pdf` | §III-C |
| Fig. 3 — SICA pipeline | `figures/sica_pipeline.pdf` | §IV-D |
| Fig. 4 — Completeness chart | `figures/completeness.pdf` | §V |

## Results

Tables III–IV use `--` placeholders. After running evaluation:

```bash
make run-evaluation   # when implemented
```

Replace placeholder cells in `securisphere.tex` with measured values.

## References

22 IEEE-style references are embedded in `\begin{thebibliography}`. No external `.bib` required for this draft.
