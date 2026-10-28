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

**Metric**:
A named quantity the business measures, carrying a description and a SQL expression, and joined to other metrics by influence.
_Avoid_: KPI, measure, field

**Draft Metric**:
A metric authored on the metric canvas that has no definition in the project's semantic model.
_Avoid_: Unbound metric, custom metric

**Bound Metric**:
A metric whose definition lives in the project's Ossie semantic model and is referenced from the metric canvas rather than restated there.
_Avoid_: Linked metric, imported metric

**Influence**:
A directed claim that one metric drives another, stored from cause to effect and carrying no arithmetic.
_Avoid_: Dependency, derivation, formula

**Metric Tree**:
A named grouping of metrics and the influences between them. Trees may overlap, so one metric can appear in more than one.
_Avoid_: Metric hierarchy, metric tree diagram, lineage graph

