"use client";

import Link from "next/link";
import { ArrowLeft, Boxes } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/error-state";
import { EmptyState } from "@/components/ui/empty-state";
import { useDataset } from "@/lib/queries";
import { EditDatasetDialog } from "./edit-dataset-dialog";
import { DeleteDatasetDialog } from "./delete-dataset-dialog";
import { ShardExplorer } from "./shard-explorer";
import { StreamPanel } from "./stream-panel";

function ManifestSummary({
  rows,
}: {
  rows: { label: string; value: string }[];
}) {
  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title">Manifest</CardTitle>
      </CardHeader>
      <CardContent className="p-5">
        <dl className="grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-3">
          {rows.map((r) => (
            <div key={r.label}>
              <dt className="text-xs uppercase tracking-wider text-muted-foreground">
                {r.label}
              </dt>
              <dd className="mt-0.5 font-mono text-sm tabular-nums">{r.value}</dd>
            </div>
          ))}
        </dl>
      </CardContent>
    </Card>
  );
}

export function DatasetDetail({ slug }: { slug: string }) {
  const { data: dataset, isLoading, error, refetch } = useDataset(slug);

  const back = (
    <Link
      href="/datasets"
      className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
    >
      <ArrowLeft className="h-4 w-4" />
      All datasets
    </Link>
  );

  if (isLoading) {
    return (
      <div className="space-y-6">
        {back}
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        {back}
        {error.isNotFound ? (
          <Card>
            <CardContent className="p-0">
              <EmptyState
                icon={Boxes}
                title="Dataset not found"
                description={`No dataset with slug "${slug}" exists in this bucket.`}
              />
            </CardContent>
          </Card>
        ) : (
          <ErrorState error={error} onRetry={() => refetch()} />
        )}
      </div>
    );
  }

  if (!dataset) return null;

  const manifestRows = [
    { label: "Slug", value: dataset.slug },
    { label: "Modality", value: dataset.modality },
    { label: "Image size", value: `${dataset.image_size}px` },
    { label: "Samples", value: `${dataset.sample_count}` },
    { label: "Shards", value: `${dataset.shard_count}` },
    { label: "Size", value: dataset.size_human },
    { label: "Seed", value: `${dataset.seed}` },
    { label: "Train / Val", value: `${dataset.splits.train ?? 0} / ${dataset.splits.val ?? 0}` },
  ];

  return (
    <div className="space-y-6">
      {back}
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-border pb-5">
        <div className="min-w-0">
          <h1 className="page-title flex items-center gap-2">
            <Boxes className="h-6 w-6 text-muted-foreground" />
            {dataset.display_name}
          </h1>
          <p className="mt-1.5 max-w-prose text-sm text-muted-foreground">
            {dataset.description || "No description."}
          </p>
          <p className="mt-2 font-mono text-xs text-muted-foreground">
            datasets/{dataset.slug}/
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="secondary">{dataset.shard_count} shards</Badge>
          <EditDatasetDialog dataset={dataset} />
          <DeleteDatasetDialog slug={dataset.slug} />
        </div>
      </div>

      <ManifestSummary rows={manifestRows} />
      <StreamPanel slug={dataset.slug} />
      <ShardExplorer slug={dataset.slug} />
    </div>
  );
}
