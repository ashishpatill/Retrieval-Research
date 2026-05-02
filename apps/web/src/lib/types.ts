export type DocumentProfile = {
  document_id: string;
  title: string;
  source_type: string;
  page_count: number;
  text_page_count: number;
  image_page_count: number;
  total_words: number;
  page_types: Record<string, number>;
  headings: string[];
  topics: string[];
  entities: string[];
  extraction_confidence: Record<string, unknown>;
  structured_reference_inventory?: Record<string, string[]>;
  created_at: string;
};

export type DocumentListItem = {
  id: string;
  title: string;
  source_path: string;
  created_at: string;
  page_count: number;
  source_type?: string;
  profile?: DocumentProfile | null;
};

export type RunSummary = {
  id: string;
  path: string;
  files: string[];
};

export type DocumentDetailResponse = {
  document: {
    id: string;
    title: string;
    source_path: string;
    created_at: string;
    pages: Array<{ id: string; number: number; text: string; image_path?: string | null }>;
    metadata: Record<string, unknown>;
  };
  profile: DocumentProfile | null;
  stats: {
    chunk_count: number;
    indexes: { bm25: boolean; dense: boolean; late?: boolean; visual: boolean; graph?: boolean };
    knowledge_graph?: {
      node_count?: number;
      edge_count?: number;
      section_count?: number;
      entity_count?: number;
      reference_count?: number;
      relation_counts?: Record<string, number>;
    } | null;
  };
  knowledge_graph?: {
    sections?: unknown[];
    entities?: unknown[];
    references?: unknown[];
    stats?: Record<string, unknown>;
  } | null;
};
