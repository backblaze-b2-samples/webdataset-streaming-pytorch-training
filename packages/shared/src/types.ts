export type FileStatus = "uploading" | "complete" | "error";

export interface FileMetadata {
  key: string;
  filename: string;
  folder: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
}

export interface FileMetadataDetail {
  filename: string;
  size_bytes: number;
  size_human: string;
  mime_type: string;
  extension: string;
  md5: string;
  sha256: string;
  uploaded_at: string;
  /** Set when a format-specific extractor was skipped or failed (e.g. an image
   *  above the decompression-bomb decode limit). Core fields stay exact. */
  metadata_warning: string | null;
  // Image-specific
  image_width: number | null;
  image_height: number | null;
  exif: Record<string, string> | null;
  // PDF-specific
  pdf_pages: number | null;
  pdf_author: string | null;
  pdf_title: string | null;
  // Audio/Video
  duration_seconds: number | null;
  codec: string | null;
  bitrate: number | null;
}

export interface FileUploadResponse {
  key: string;
  filename: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
  metadata: FileMetadataDetail | null;
}

/** A short-lived presigned PUT the browser uploads a file directly to B2 with.
 *  `headers` are signed into the URL, so the browser must send them verbatim. */
export interface PresignUploadResponse {
  key: string;
  url: string;
  method: string;
  content_type: string;
  headers: Record<string, string>;
  expires_in: number;
}

export interface DailyUploadCount {
  date: string;
  uploads: number;
}

export interface UploadStats {
  total_files: number;
  total_size_bytes: number;
  total_size_human: string;
  uploads_today: number;
  total_downloads: number;
}

// --- Datasets (WebDataset shard collections on B2) -----------------------

export interface ShardEntry {
  key: string;
  size_bytes: number;
  count: number;
}

export interface Dataset {
  slug: string;
  display_name: string;
  description: string;
  modality: "image";
  image_size: number;
  seed: number;
  created_at: string;
  sample_count: number;
  shard_count: number;
  total_size_bytes: number;
  size_human: string;
  shards: ShardEntry[];
  splits: Record<string, number>;
}

export interface CreateDatasetRequest {
  name: string;
  description?: string;
  source: "synthetic" | "raw";
  num_samples: number;
  samples_per_shard: number;
  image_size: number;
}

export interface EditDatasetRequest {
  display_name?: string;
  description?: string;
}

export interface ShardListEntry {
  key: string;
  filename: string;
  size_bytes: number;
  size_human: string;
  count: number;
  preview_url: string | null;
}

export interface DatasetStats {
  total_datasets: number;
  total_shards: number;
  total_samples: number;
  total_size_bytes: number;
  total_size_human: string;
  last_run_samples_per_s: number | null;
  last_run_device: string | null;
}

export interface StreamRequest {
  num_workers: number;
  num_nodes: number;
  batch_size: number;
  max_batches: number;
  shuffle_buffer: number;
}

export interface ShardAssignment {
  rank: number;
  world_size: number;
  shard_indices: number[];
}

export interface StreamResult {
  device: string;
  elapsed_s: number;
  samples: number;
  batches: number;
  bytes_read: number;
  samples_per_s: number;
  mb_per_s: number;
  loss_curve: number[];
  worker_plan: ShardAssignment[];
  node_plan: ShardAssignment[];
  num_workers: number;
  num_nodes: number;
  batch_size: number;
  created_at: string;
}
