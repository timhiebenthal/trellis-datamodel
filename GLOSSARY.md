# Trellis Data Model

Conceptual and physical data modeling context for defining entities, relationships, business events, and semantic models across transformation frameworks.

## Language

**Entity**:
A business concept on the data model canvas representing a distinct domain object, classified as a dimension, a fact, or unclassified.
_Avoid_: Node, table, model

**Bound Entity**:
An entity linked to a physical model or asset in the underlying transformation framework.
_Avoid_: Linked node, synced entity, mapped table

**Draft Entity**:
A conceptual entity on the canvas that has no link to a physical transformation model yet.
_Avoid_: Unbound model, stub table

**Dataset**:
A logical table representation in an exported semantic model backed by a bound entity's physical table and fields.
_Avoid_: Semantic table, view

**Semantic Model**:
A standalone Apache Ossie document describing datasets, fields, relationships, and metrics derived from bound entities in the data model.
_Avoid_: Ossie profile, schema bundle

**Grain**:
The business statement of what one row of an entity represents, such as "one row per order line".
_Avoid_: Primary key, uniqueness rule

**Primary Key**:
The field or fields that uniquely identify a row of a dataset, taken from framework metadata or framework tests.
_Avoid_: Grain, unique key

