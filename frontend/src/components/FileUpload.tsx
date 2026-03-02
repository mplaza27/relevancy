import { useCallback, useState } from "react";
import { useDropzone, type FileRejection } from "react-dropzone";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";

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

interface Props {
  onUploadComplete: (sessionId: string) => void;
  apiUrl: string;
}

export function FileUpload({ onUploadComplete, apiUrl }: Props) {
  const [fileStatuses, setFileStatuses] = useState<FileStatus[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

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
        onUploadComplete(data.session_id);
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

    xhr.open("POST", `${apiUrl}/api/upload`);
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
          ${isDragActive ? "border-primary bg-primary/5" : "border-border hover:border-primary/50"}
          ${uploading ? "opacity-50 cursor-not-allowed" : ""}
        `}
      >
        <input {...getInputProps()} />
        <div className="space-y-2">
          <div className="text-4xl">📄</div>
          {isDragActive ? (
            <p className="text-primary font-medium">Drop files here</p>
          ) : (
            <>
              <p className="font-medium">Drag &amp; drop lecture files here, or click to browse</p>
              <p className="text-sm text-muted-foreground">PDF, PPTX, DOCX, TXT, MD · max 50MB · up to 5 files</p>
            </>
          )}
        </div>
      </div>

      {/* File list */}
      {fileStatuses.length > 0 && (
        <div className="space-y-2">
          {fileStatuses.map((s, i) => (
            <div key={i} className="flex items-center gap-3 text-sm">
              <span className="truncate flex-1 font-mono">{s.file.name}</span>
              <div className="w-32">
                <Progress value={s.progress} className="h-2" />
              </div>
              <span className="w-8 text-right">{s.progress}%</span>
              <span>
                {s.status === "done" && "✓"}
                {s.status === "error" && "✗"}
                {s.status === "uploading" && "⏳"}
                {s.status === "pending" && "○"}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Error message */}
      {uploadError && (
        <p className="text-sm text-destructive">{uploadError}</p>
      )}

      {/* Action buttons */}
      <div className="flex gap-2">
        {pendingCount > 0 && (
          <Button onClick={handleUpload} disabled={uploading}>
            {uploading ? "Uploading…" : `Upload & Find Relevant Cards (${pendingCount} file${pendingCount > 1 ? "s" : ""})`}
          </Button>
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
