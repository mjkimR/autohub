---
id: UX-sdd-workflow-request
title: Retired native workflow request
summary: "This former native evaluator control is retired; repository documents and ordinary PR questions remain available independently."
area: sdd
element: panel
status: deprecated
usecases: []
capabilities:
  - CAP-SDD-native-delivery
---

# [UX-sdd-workflow-request] Retired native workflow request

## 1. Purpose

This panel is no longer an active product control.

## 2. Content

No live readiness, workflow-choice or execution-selection content is rendered. Historical records are inspected through `UX-sdd-run` or `UX-sdd-batch`; repository documents remain in `UX-repository`.

## 3. States

- **retired**: no live control exists; open the ordinary repository or Run view.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Open repository | global: leave the retired control | retired | populated | `UX-repository` | `CAP-DOC-repository-viewer` | Read-only documents open without evaluation. |
