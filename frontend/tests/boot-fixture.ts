import * as fs from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';

export const BOOT_FIXTURE_COUNTS = Object.freeze({
    models: 500,
    entities: 500,
    columnsPerModel: 20,
    relationships: 750,
});

export const BOOT_FIXTURE_TIMESTAMP = '2026-01-01T00:00:00.000Z';
export const BOOT_FIXTURE_SEED = 'trellis-frontend-boot';

export type BootFixture = {
    rootDir: string;
    projectDir: string;
    manifestPath: string;
    catalogPath: string;
    dataModelPath: string;
    layoutPath: string;
    schemaPath: string;
    counts: typeof BOOT_FIXTURE_COUNTS;
};

export type BootFixtureOptions = {
    seed?: string;
    rootDir?: string;
};

function seedOffset(seed: string): number {
    let hash = 2166136261;
    for (const character of seed) {
        hash ^= character.charCodeAt(0);
        hash = Math.imul(hash, 16777619);
    }
    return Math.abs(hash >>> 0) % 97;
}

function writeJsonYaml(filePath: string, value: unknown): void {
    fs.writeFileSync(filePath, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
}

export function buildBootFixture(options: BootFixtureOptions = {}): BootFixture {
    const seed = options.seed ?? BOOT_FIXTURE_SEED;
    const rootDir = options.rootDir ?? fs.mkdtempSync(path.join(os.tmpdir(), 'trellis-boot-'));
    const projectDir = path.join(rootDir, 'dbt_boot_fixture');
    const targetDir = path.join(projectDir, 'target');
    const modelDir = path.join(projectDir, 'models', 'boot_fixture');

    fs.mkdirSync(targetDir, { recursive: true });
    fs.mkdirSync(modelDir, { recursive: true });

    const offset = seedOffset(seed);
    const modelEntries = Array.from({ length: BOOT_FIXTURE_COUNTS.models }, (_, index) => {
        const number = String(index).padStart(4, '0');
        const name = `model_${number}`;
        const uniqueId = `model.boot_fixture.${name}`;
        const columns = Object.fromEntries(
            Array.from({ length: BOOT_FIXTURE_COUNTS.columnsPerModel }, (_, columnIndex) => {
                const columnNumber = String(columnIndex).padStart(2, '0');
                const columnName = `column_${columnNumber}`;
                return [
                    columnName,
                    {
                        name: columnName,
                        description: '',
                        data_type: columnIndex === 0 ? 'INTEGER' : 'VARCHAR',
                    },
                ];
            }),
        );
        // Keep the large model set reference-resolvable without creating a 500-deep
        // lineage walk for every bound entity during the pre-optimization boot.
        const dependency: string[] = [];

        return {
            number,
            name,
            uniqueId,
            columns,
            dependency,
            originalFilePath: `models/boot_fixture/${name}.sql`,
        };
    });

    const nodes: Record<string, Record<string, unknown>> = {};
    const catalogNodes: Record<string, Record<string, unknown>> = {};
    const parentMap: Record<string, string[]> = {};
    const childMap: Record<string, string[]> = {};
    const schemaModels: Array<Record<string, unknown>> = [];

    for (const model of modelEntries) {
        nodes[model.uniqueId] = {
            unique_id: model.uniqueId,
            resource_type: 'model',
            name: model.name,
            package_name: 'boot_fixture',
            // Do not point every model at one large shared schema file: the
            // pre-optimization model index reparses that file once per entity.
            original_file_path: model.originalFilePath,
            config: { materialized: 'table' },
            tags: ['trellis_boot_fixture'],
            columns: model.columns,
            depends_on: { macros: [], nodes: model.dependency },
        };
        parentMap[model.uniqueId] = [...model.dependency];
        childMap[model.uniqueId] = [];

        for (const dependency of model.dependency) {
            childMap[dependency].push(model.uniqueId);
        }

        catalogNodes[model.uniqueId] = {
            unique_id: model.uniqueId,
            metadata: {
                type: 'BASE TABLE',
                name: model.name,
            },
            columns: Object.fromEntries(
                Object.keys(model.columns).map((columnName, columnIndex) => [
                    columnName,
                    {
                        name: columnName.toUpperCase(),
                        type: columnIndex === 0 ? 'INTEGER' : 'VARCHAR',
                        index: columnIndex,
                    },
                ]),
            ),
        };

        schemaModels.push({
            name: model.name,
            description: `Deterministic boot fixture model ${model.number}`,
            columns: Object.keys(model.columns).map((columnName, columnIndex) => ({
                name: columnName,
                description: `Deterministic column ${String(columnIndex).padStart(2, '0')}`,
                data_type: columnIndex === 0 ? 'INTEGER' : 'VARCHAR',
            })),
        });
    }

    const entities = modelEntries.map((model) => ({
        id: model.name,
        label: `Boot Model ${model.number}`,
        description: `Deterministic boot fixture entity ${model.number}`,
        model_ref: model.uniqueId,
        entity_type: Number(model.number) % 5 === 0 ? 'fact' : 'dimension',
        framework_tags: ['trellis_boot_fixture'],
        drafted_fields: Object.entries(model.columns).map(([name, column], index) => ({
            name,
            datatype: index === 0 ? 'int' : 'text',
            source: 'dbt',
            physical_datatype: column.data_type,
            description: column.description,
        })),
    }));

    const relationships = Array.from({ length: BOOT_FIXTURE_COUNTS.relationships }, (_, index) => {
        const sourceIndex = index % BOOT_FIXTURE_COUNTS.entities;
        const targetIndex = (index * 17 + offset + 1) % BOOT_FIXTURE_COUNTS.entities;
        return {
            source: modelEntries[sourceIndex].name,
            target: modelEntries[targetIndex].name,
            label: `relationship_${String(index).padStart(4, '0')}`,
            type: 'one_to_many',
            source_field: 'column_00',
            target_field: 'column_00',
        };
    });

    const layoutEntities = Object.fromEntries(
        modelEntries.map((model, index) => [
            model.name,
            {
                position: {
                    x: ((index + offset) % 25) * 360,
                    y: Math.floor(index / 25) * 240,
                },
                width: 280,
                panel_height: 200,
                collapsed: false,
            },
        ]),
    );
    const layoutRelationships = Object.fromEntries(
        relationships.map((relationship, index) => [
            `${relationship.source}-${relationship.target}-${index}`,
            { label_dx: 0, label_dy: 0 },
        ]),
    );

    const manifestPath = path.join(targetDir, 'manifest.json');
    const catalogPath = path.join(targetDir, 'catalog.json');
    const dataModelPath = path.join(projectDir, 'data_model.yml');
    const layoutPath = path.join(projectDir, 'canvas_layout.yml');
    const schemaPath = path.join(modelDir, 'schema.yml');

    writeJsonYaml(manifestPath, {
        metadata: {
            dbt_schema_version: 'https://schemas.getdbt.com/dbt/manifest/v12.json',
            dbt_version: '1.8.2',
            generated_at: BOOT_FIXTURE_TIMESTAMP,
            invocation_id: `boot-fixture-${seed}`,
            project_name: 'boot_fixture',
        },
        nodes,
        sources: {},
        parent_map: parentMap,
        child_map: childMap,
    });
    writeJsonYaml(catalogPath, {
        metadata: {
            dbt_schema_version: 'https://schemas.getdbt.com/dbt/catalog/v1.json',
            dbt_version: '1.8.2',
            generated_at: BOOT_FIXTURE_TIMESTAMP,
            project_name: 'boot_fixture',
        },
        nodes: catalogNodes,
        sources: {},
    });
    writeJsonYaml(dataModelPath, {
        version: 0.1,
        entities,
        relationships,
    });
    writeJsonYaml(layoutPath, {
        version: 0.1,
        entities: layoutEntities,
        relationships: layoutRelationships,
    });
    writeJsonYaml(schemaPath, {
        version: 2,
        models: schemaModels,
    });

    fs.writeFileSync(
        path.join(projectDir, 'dbt_project.yml'),
        'name: boot_fixture\nversion: 1.0.0\nconfig-version: 2\nprofile: boot_fixture\nmodel-paths: ["models"]\n',
        'utf8',
    );

    return {
        rootDir,
        projectDir,
        manifestPath,
        catalogPath,
        dataModelPath,
        layoutPath,
        schemaPath,
        counts: BOOT_FIXTURE_COUNTS,
    };
}
