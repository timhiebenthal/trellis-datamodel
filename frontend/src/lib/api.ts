import type { DbtModel, Ontology } from './types';

const API_BASE = 'http://localhost:8000/api';

export async function getManifest(): Promise<DbtModel[]> {
    try {
        const res = await fetch(`${API_BASE}/manifest`);
        if (!res.ok) {
            if (res.status === 404) return []; // Handle missing manifest gracefully
            throw new Error(`Status: ${res.status}`);
        }
        const data = await res.json();
        return data.models;
    } catch (e) {
        console.error("Error fetching manifest:", e);
        return [];
    }
}

export async function getOntology(): Promise<Ontology> {
    try {
        const res = await fetch(`${API_BASE}/ontology`);
        if (!res.ok) throw new Error(`Status: ${res.status}`);
        return await res.json();
    } catch (e) {
        console.error("Error fetching ontology:", e);
        // Return empty default
        return { version: 0.1, entities: [], relationships: [] };
    }
}

export async function saveOntology(ontology: Ontology): Promise<void> {
    const res = await fetch(`${API_BASE}/ontology`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(ontology)
    });
    if (!res.ok) throw new Error(`Failed to save ontology: ${res.status}`);
}

export async function getConfigStatus(): Promise<any> {
    try {
        const res = await fetch(`${API_BASE}/config-status`);
        if (!res.ok) throw new Error(`Status: ${res.status}`);
        return await res.json();
    } catch (e) {
        console.error("Error fetching config status:", e);
        return {
            config_present: false,
            error: "Failed to connect to backend"
        };
    }
}

