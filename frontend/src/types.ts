export interface MatchedCard {
  note_id: number;
  text: string;
  extra: string;
  tags: string[];
  notetype: string;
  similarity: number;
  raw_fields: Record<string, string>;
}

export interface MatchResults {
  session_id: string;
  status: string;
  keywords: string[];
  cards: MatchedCard[];
}

export interface UploadResponse {
  session_id: string;
  file_count: number;
  total_chunks: number;
  match_count: number;
  keywords: string[];
  status: string;
}
