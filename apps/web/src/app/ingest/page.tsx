import { UploadForm } from "@/components/upload/upload-form";

export default function IngestPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <h1 className="page-title">Raw media</h1>
        <p className="mt-1.5 max-w-prose text-sm text-muted-foreground text-pretty">
          Stage raw images here (up to 100 MB each). They upload straight to
          Backblaze B2, and the &ldquo;raw&rdquo; dataset source packs them into
          WebDataset shards. Prefer a zero-upload demo? Create a dataset with the{" "}
          <span className="font-medium">synthetic</span> source instead.
        </p>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <UploadForm />
      </div>
    </div>
  );
}
