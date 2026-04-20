# trellis Data

<p align="center">
  <img src="resources/trellis_with_text.png" alt="trellis Data" width="420" />
</p>

**trellis** is a lightweight, local-first app that connects **conceptual** and **logical** data modeling with how you actually build the warehouse today—**dbt-core** first, with a live canvas that stays aligned to your project.

## Why trellis

**Typical pain**

- ERDs live in separate tools and go stale on real projects.
- Transformations drift from the story the business understands.
- Stakeholders can’t see structure without wading through SQL and YAML.
- “All-in-one” warehouse designers rarely meet teams where they are (dbt, git, the modern stack).

**What you get with trellis**

- **Small PyPI install, local web app** — run it beside your dbt project; the canvas and model files (`data_model.yml`, dbt YAML) stay **in version control**, so names, relationships, and descriptions evolve like the rest of your code—not a one-off diagram export.
- One place to **see** entities, fields, relationships, and descriptions—tied to your repo, not a dead export.
- **Conceptual** view for names and meaning; **Logical** view for columns, types, and materialization detail—switch without losing context.
- **Greenfield**: sketch entities and attributes, then push structured artifacts into dbt.
- **Brownfield**: load what you already modeled in dbt, infer links from relationship tests, and push descriptions and tags back into the project.

## What you can do

- **Visualize your data model** — canvas layout, conceptual vs logical views, less manual “diagram maintenance.”
- **Work with your dbt project** — point at `manifest.json` / `catalog.json`, keep the diagram honest, round-trip descriptions and tags, and generate **relationship** tests from drawn links.
- **Optional — Kimball-style modeling** — classify facts and dimensions, sensible default placement, and a **Bus Matrix** when your team thinks in stars/snowflakes; you can stay on plain entities if you prefer.
- **Optional — business events & processes** — capture events with 7W-style annotations and group them into processes; most useful for **greenfield** and **dimensional** workflows. Skip this entirely if it’s not your methodology.

## Getting started

**Install**

```bash
pip install trellis-datamodel
# or: uv pip install trellis-datamodel
```

**Run next to your dbt project**

1. `cd /path/to/your/dbt-project`
2. `trellis init` — creates `trellis.yml` (point it at your dbt paths and artifacts).
3. `trellis run` — opens **http://localhost:8089** (use `trellis run --help` for port and config path).

Generate **`manifest.json`** and **`catalog.json`** with `dbt docs generate` in your dbt project so trellis can load models; without them, the UI may start but show no dbt-backed entities.

Install from source or hack on the app: see [CONTRIBUTING.md](CONTRIBUTING.md).

## Examples & walkthroughs

Short video walkthroughs:

| | |
| --- | --- |
| [Getting started](examples/1%20-%20Getting%20Started.md) | Init, settings in the UI, conceptual vs logical, relationships, push to dbt. |
| [dbt integration](examples/3%20-%20dbt%20integration.md) | Link a project, mock data, bind entities to models, stay in sync with artifacts. |
| [Documenting business processes](examples/2%20-%20Documenting%20Business%20Processes.md) | **Optional / experimental:** events, 7Ws, processes—enable in config or UI first. |

More narrative walkthroughs and context: [full tutorial](https://app.capacities.io/home/667ad256-ca68-4dfd-8231-e77d83127dcf) · [general information](https://app.capacities.io/home/8b7546f6-9028-4209-a383-c4a9ba9be42a).

## Configuration

After `trellis init`, edit **`trellis.yml`**. Annotated options and defaults live in **[trellis.yml.example](trellis.yml.example)** (paths, modeling style, optional lineage/exposures, entity guidance, prefixes, etc.).

You can also open **`/config`** in the app to edit settings in the browser (validated saves; see example file for field meanings).

## Vision

trellis is built and tested around **dbt-core** today. The longer-term idea is to stay **tool-agnostic**—concepts outlive any one framework. Possible directions include dbt Fusion, Pydantic-flavored exports, or adapters for tools like [SQLMesh](https://github.com/TobikoData/sqlmesh) or [Bruin](https://github.com/bruin-data/bruin) where it makes sense. For now, the focus is a great experience with dbt-core.

## Contributing

Contributions welcome. Workflow, local dev, tests, and packaging: **[CONTRIBUTING.md](CONTRIBUTING.md)**. All contributors sign the CLA once per GitHub account—see **[CLA.md](CLA.md)** and the bot on your PR.

## Acknowledgments

- [dbt-colibri](https://github.com/dbt-labs/dbt-colibri) for lineage-related capabilities that support trellis visualization.

## License

trellis Datamodel is licensed under the **[GNU Affero General Public License v3.0](LICENSE)**. See **[NOTICE](NOTICE)** for a short summary of copyright and licensing.
