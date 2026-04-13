# Getting Started with Trellis

Video tutorials demonstrating core Trellis workflows.

## Initialize Project

Start Trellis in a file-based setup with `trellis init` and create the initial config with the optional wizard.  
Launch the UI with `trellis run`; modeled entities are stored in `data_model.yml`, which works well for version control and machine-readable workflows.

<video src="https://github.com/user-attachments/assets/b5690e96-3ed0-4988-a576-5471e48096f2" controls></video>

## Configure in UI

Edit Trellis settings directly in the UI instead of managing everything by hand in YAML.  
You can also disable the Entity Creation Wizard.

<video src="https://github.com/user-attachments/assets/a27de46c-a909-4e90-af4e-7e68e6f52d98" controls></video>

## Add Entity Attributes

Use the **Conceptual View** for a high-level business overview. Switch to the **Logical View** to add entity attributes and metadata such as descriptions and data types.

<video src="https://github.com/user-attachments/assets/e24322c0-8631-458c-8359-67e0d4d5e624" controls></video>

## Create Relationships & Push to dbt

Connect entities visually at the entity or field level and push the resulting artifacts to dbt.  
Trellis writes per-entity `schema.yml` files with descriptions and, for field-level links, relationship tests.

<video src="https://github.com/user-attachments/assets/d30406c2-13e0-46aa-9288-a0414c6688cf" controls></video>

## Entity Details & Export

The **Entity List** page gives you an overview of all entities, which is especially useful in larger projects. The **Entity Detail** page lets you refine metadata, including retrieval context for individual fields.  
You can export a single Entity Specification as Markdown or `.xlsx`, and export the full data model as `.xlsx` as well.

<video src="https://github.com/user-attachments/assets/518c497a-564e-488d-8b94-ddca51d0e3c6" controls></video>

## Dimensional Model & Bus Matrix

When you switch to **Dimensional Model** mode, features like `entity_type` (dimension vs. fact) and the Bus Matrix are enabled and kept in sync automatically.

<video src="https://github.com/user-attachments/assets/d4187b27-18f5-44f6-bbef-d13dfb619085" controls></video>
