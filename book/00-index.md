---
title: prealpha; Formal Verification Agent Recipes
site:
  hide_outline: false
  hide_toc: false
  hide_title_block: false
---

```{epigraph}
In distant land, unreachable by your steps, there stands a castle known as Monsalvat

-- Lohengrin, *Lohengrin* Act III, Scene 3
```

# TODO: this is an ALPHA. This is not released yet.

Please don't send it around to your friends yet.

+++ {"kind": "centered"}

# Formal Verification Agent Recipes

Agents, evals, and RL environments for the working proof engineer.

[Get Started](/introduction/ch0)

```{figure} ./static/img/lean-agent-helix.png
:name: lean-agent-helix
:width: 60%

MVP: the loop between LLM (◉) and a verifier (∀)
```

+++ {"kind": "left"}

## Table of contents at a glance (PLANNED)

1. Introduction. Setting scope, defining terms.
2. DafnyBench (Dafny) with `inspect-ai`. Quickest MVP with free agents and logging/dashboards
3. DafnyBench no-framework. Dispell any suspicions about the complicated framework by feeling the purepython and anthropic SDK under your fingernails.
4. FVAPPS (Lean) with `pydantic-ai`, more flexible than `inspect-ai`
5. From evals to RL envs. How much SFT do you need to bootstrap, and how to get those tokens. Curricula design.
6. Outlook. Please measure verification burden

Chapters 2-4 will have code in the repo in the `./evals` subdir, maybe 5 as well. 
