export interface User {
  id: number;
  username: string;
  role: 'admin' | 'user';
  avatar_seed: string;
  signup_status: 'pending' | 'approved' | 'rejected';
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  role: string;
  username: string;
  user_id: number;
}

export interface FBILRate {
  id: number;
  date: string;
  time: string;
  currency_pair: string;
  rate: number;
  comments: string;
}

export interface RatesResponse {
  data: FBILRate[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface ProcessedFile {
  id: number;
  original_filename: string;
  processed_filename: string;
  total_rows: number;
  matched_rows: number;
  unmatched_rows: number;
  status: string;
  created_at: string;
  r2_processed_key: string;
}

export interface ProcessingProgress {
  stage: string;
  progress: number;
  message: string;
  done: boolean;
  error: string | null;
  stats?: any;
  file_id?: number;
  download_url?: string;
}

export interface Toast {
  id: number;
  type: 'success' | 'error' | 'warning' | 'info';
  message: string;
}
