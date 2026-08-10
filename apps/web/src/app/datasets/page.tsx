import { DatasetList } from "@/components/datasets/dataset-list";
import { CreateDatasetDialog } from "@/components/datasets/create-dataset-dialog";

export default function DatasetsPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in flex flex-wrap items-start justify-between gap-4 border-b border-border pb-5">
        <div className="min-w-0">
          <h1 className="page-title">Datasets</h1>
          <p className="mt-1.5 max-w-prose text-sm text-muted-foreground">
            Each dataset is a WebDataset shard collection under{" "}
            <code>datasets/&lt;slug&gt;/</code> on Backblaze B2. Open one to
            browse its shards and stream it into a PyTorch training loop.
          </p>
        </div>
        <CreateDatasetDialog />
      </div>
      <div className="animate-fade-in-up stagger-2">
        <DatasetList />
      </div>
    </div>
  );
}
