// src/utils/mockResponses.ts

import { CONFIG } from './constants';

/**
 * Generates mock responses for POC demonstration
 * In production, this would be replaced with actual RAG system responses
 */

const RESPONSE_TEMPLATES = [
    "Thank you for your query. In a production system, this would search our knowledge base for '{query}'.",
    "I've processed your request about '{query}'. Here's what I found in our knowledge base: This is a mock response demonstrating the complete user interaction flow.",
    "Based on your question '{query}', our system would retrieve relevant documents and provide a comprehensive answer with citations.",
    "Your query about '{query}' has been received. In the full system, this would trigger a RAG pipeline to search, rank, and synthesize information from our document store.",
    "Processing '{query}'... In production, this would involve semantic search across our knowledge base, followed by context-aware answer generation.",
];

// Simple keyword-based response variations for demo purposes
const KEYWORD_RESPONSES: Record<string, string> = {
    status: "I've checked the status based on your query '{query}'. In a production environment, this would show real-time system status.",
    help: "I'm here to help with '{query}'. This demo shows how voice input would work in our full RAG system.",
    search: "Searching for '{query}'... In production, this would perform semantic search across our indexed documents.",
    find: "Finding information about '{query}'... The full system would use vector embeddings to retrieve the most relevant content.",
    how: "To answer '{query}', our production system would analyze the question type and retrieve step-by-step information from our knowledge base.",
};

export function generateMockResponse(query: string): string {
    if (!query || query.trim().length === 0) {
        return "I didn't receive a query. Please try speaking or typing your question.";
    }

    const lowerQuery = query.toLowerCase();

    // Check for keyword matches
    for (const [keyword, template] of Object.entries(KEYWORD_RESPONSES)) {
        if (lowerQuery.includes(keyword)) {
            return template.replace('{query}', query);
        }
    }

    // Return random template response
    const randomIndex = Math.floor(Math.random() * RESPONSE_TEMPLATES.length);
    return RESPONSE_TEMPLATES[randomIndex].replace('{query}', query);
}

/**
 * Simulates processing delay for realistic UX
 * Returns a promise that resolves after configured delays
 */
export async function simulateProcessing(
    onProcessing?: () => void,
    onGenerating?: () => void
): Promise<void> {
    const { PROCESSING, GENERATING } = CONFIG.MOCK_RESPONSE_DELAY;

    // Stage 1: Processing
    if (onProcessing) onProcessing();
    await new Promise(resolve => setTimeout(resolve, PROCESSING));

    // Stage 2: Generating
    if (onGenerating) onGenerating();
    await new Promise(resolve => setTimeout(resolve, GENERATING));
}