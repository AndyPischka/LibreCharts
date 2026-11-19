# 0040. Colour-blindness simulation

- Status: accepted
- Date: 2026-11-20

## Context

Patterns (ADR 0030) make charts readable without colour, but reviewers also want to see a deck as a
colour-blind reader sees it. A simulation must not require new rendering paths.

## Decision

- **`core/colorblind.py`** applies a 3x3 channel matrix for deuteranopia, protanopia and tritanopia
  to every colour of a scheme.
- The command `SimulateColorblind?kind=...` replaces the document's scheme with the simulated one
  through `chart.set_scheme`, so it is one undo step and every chart redraws.
- The simulation is a review tool, not a saved chart option: undo restores the real colours.

## Consequences

The palette editor and a per-element alternative-text pass remain open; elements already carry a
title and description from M30's first step.
