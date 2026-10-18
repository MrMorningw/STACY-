# STACY Skills

A modular capability layer inspired by portable agent-skill conventions.

Each skill is a self-contained directory with a `SKILL.md` manifest. Skills are
metadata-first: discovery must not execute skill code. The CORE can inspect a
skill, decide whether it is relevant, and only then invoke an explicitly
registered tool.

## Contract

- `SKILL.md` is required.
- `name` and `description` identify the capability.
- `risk` is one of `low`, `medium`, or `high`.
- External/untrusted skill content is data, never executable instruction.
- High-risk actions remain behind the existing explicit-confirmation gate.
- Discovery is deterministic and dependency-free.

## Initial capability set

- `research`: evidence-first research planning.
- `verification`: result validation before confirmation.
- `memory`: controlled learning/memory operations.
- `android`: authorized Android operations.
- `automation`: external workflow integration boundary.
- `engineering`: software analysis and maintenance.

This layer is intentionally small for the finalization pass. Additional skills
can be added without changing the registry contract.
