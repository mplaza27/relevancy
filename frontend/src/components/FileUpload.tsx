import { useCallback, useState } from "react";
import { useDropzone, type FileRejection } from "react-dropzone";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Upload, FileText, CheckCircle, XCircle, Clock, Circle } from "lucide-react";

const ACCEPTED_TYPES = {
  "application/pdf": [".pdf"],
  "application/vnd.openxmlformats-officedocument.presentationml.presentation": [".pptx"],
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
  "text/plain": [".txt"],
  "text/markdown": [".md"],
};

const MAX_SIZE = 50 * 1024 * 1024; // 50MB
const MAX_FILES = 5;

interface FileStatus {
  file: File;
  progress: number;
  status: "pending" | "uploading" | "done" | "error";
  error?: string;
}

const MAX_RESULTS_OPTIONS = [50, 100, 250, 500, 1000];

interface Props {
  onUploadComplete: (sessionId: string, keywords: string[]) => void;
  apiUrl: string;
}

export function FileUpload({ onUploadComplete, apiUrl }: Props) {
  const [fileStatuses, setFileStatuses] = useState<FileStatus[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [maxResults, setMaxResults] = useState(100);

  const onDrop = useCallback((accepted: File[], rejected: FileRejection[]) => {
    setUploadError(null);

    if (rejected.length > 0) {
      const msgs = rejected.flatMap(r => r.errors.map(e => e.message));
      setUploadError(msgs[0] || "Some files were rejected");
    }

    const newStatuses: FileStatus[] = accepted.map(f => ({
      file: f,
      progress: 0,
      status: "pending",
    }));
    setFileStatuses(prev => [...prev, ...newStatuses].slice(0, MAX_FILES));
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED_TYPES,
    maxSize: MAX_SIZE,
    maxFiles: MAX_FILES,
    disabled: uploading,
  });

  const handleUpload = () => {
    const pendingFiles = fileStatuses.filter(s => s.status === "pending").map(s => s.file);
    if (pendingFiles.length === 0) return;

    setUploading(true);
    setUploadError(null);

    const formData = new FormData();
    pendingFiles.forEach(f => formData.append("files", f));

    // Mark all as uploading
    setFileStatuses(prev =>
      prev.map(s => s.status === "pending" ? { ...s, status: "uploading" as const } : s)
    );

    const xhr = new XMLHttpRequest();

    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable) {
        const pct = Math.round((e.loaded / e.total) * 100);
        setFileStatuses(prev =>
          prev.map(s => s.status === "uploading" ? { ...s, progress: pct } : s)
        );
      }
    });

    xhr.addEventListener("load", () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        const data = JSON.parse(xhr.responseText);
        setFileStatuses(prev =>
          prev.map(s => s.status === "uploading" ? { ...s, status: "done" as const, progress: 100 } : s)
        );
        setUploading(false);
        onUploadComplete(data.session_id, data.keywords ?? []);
      } else {
        let msg = "Upload failed";
        try {
          msg = JSON.parse(xhr.responseText).detail || msg;
        } catch {}
        setFileStatuses(prev =>
          prev.map(s => s.status === "uploading" ? { ...s, status: "error" as const, error: msg } : s)
        );
        setUploadError(msg);
        setUploading(false);
      }
    });

    xhr.addEventListener("error", () => {
      setUploadError("Network error — is the backend running?");
      setFileStatuses(prev =>
        prev.map(s => s.status === "uploading" ? { ...s, status: "error" as const } : s)
      );
      setUploading(false);
    });

    xhr.open("POST", `${apiUrl}/api/upload?max_results=${maxResults}`);
    xhr.send(formData);
  };

  const clearFiles = () => {
    setFileStatuses([]);
    setUploadError(null);
  };

  const pendingCount = fileStatuses.filter(s => s.status === "pending").length;

  return (
    <div className="space-y-4">
      {/* Drop zone */}
      <div
        {...getRootProps()}
        className={`
          border-2 border-dashed rounded-lg p-10 text-center cursor-pointer
          transition-colors duration-200
          ${isDragActive
            ? "border-[#3172ae] bg-[#eff5fb]"
            : "border-[#83aace] hover:border-[#3172ae] hover:bg-[#eff5fb]/50"
          }
          ${uploading ? "opacity-50 cursor-not-allowed" : ""}
        `}
      >
        <input {...getInputProps()} />
        <div className="space-y-2">
          <Upload className="mx-auto h-10 w-10 text-[#3172ae]" />
          {isDragActive ? (
            <p className="text-[#3172ae] font-medium">Drop files here</p>
          ) : (
            <>
              <p className="font-medium">Drag & drop lecture files here, or click to browse</p>
              <p className="text-sm text-[#646469]">PDF, PPTX, DOCX, TXT, MD · max 50MB · up to 5 files</p>
            </>
          )}
        </div>
      </div>

      {/* File list */}
      {fileStatuses.length > 0 && (
        <div className="space-y-2">
          {fileStatuses.map((s, i) => (
            <div key={i} className="flex items-center gap-3 text-sm">
              <FileText className="h-4 w-4 shrink-0 text-[#3172ae]" />
              <span className="truncate flex-1 font-mono">{s.file.name}</span>
              <div className="w-32">
                <Progress value={s.progress} className="h-2" />
              </div>
              <span className="w-8 text-right font-mono text-xs">{s.progress}%</span>
              <span className="w-5 flex justify-center">
                {s.status === "done" && <CheckCircle className="h-4 w-4 text-[#62a60a]" />}
                {s.status === "error" && <XCircle className="h-4 w-4 text-[#cb333b]" />}
                {s.status === "uploading" && <Clock className="h-4 w-4 text-[#d45d00] animate-pulse" />}
                {s.status === "pending" && <Circle className="h-4 w-4 text-[#646469]" />}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Error message */}
      {uploadError && (
        <p className="text-sm text-[#cb333b]">{uploadError}</p>
      )}

      {/* Max results selector + action buttons */}
      <div className="flex items-center gap-3">
        {pendingCount > 0 && (
          <>
            <div className="flex items-center gap-2">
              <label className="text-xs font-mono text-[#646469]">Max cards:</label>
              <select
                value={maxResults}
                onChange={(e) => setMaxResults(Number(e.target.value))}
                disabled={uploading}
                className="border border-[#d1d5db] rounded px-2 py-1.5 text-sm font-mono bg-white focus:outline-none focus:ring-1 focus:ring-[#3172ae]"
              >
                {MAX_RESULTS_OPTIONS.map((n) => (
                  <option key={n} value={n}>{n}</option>
                ))}
              </select>
            </div>
            <Button onClick={handleUpload} disabled={uploading}>
              {uploading ? "Uploading…" : `Upload & Find Relevant Cards (${pendingCount} file${pendingCount > 1 ? "s" : ""})`}
            </Button>
          </>
        )}
        {fileStatuses.length > 0 && !uploading && (
          <Button variant="outline" onClick={clearFiles}>
            Clear
          </Button>
        )}
      </div>
    </div>
  );
}
