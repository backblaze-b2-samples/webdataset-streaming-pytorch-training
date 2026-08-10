"use client";

import Link from "next/link";
import { Boxes, Package, Images, HardDrive } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { LoadingNotice } from "@/components/common/loading-notice";
import { useDatasets } from "@/lib/queries";

export function DatasetList() {
  const { data: datasets = [], isLoading, error, refetch } = useDatasets();

  if (error) {
    return (
      <Card>
        <CardContent className="p-0">
          <ErrorState error={error} onRetry={() => refetch()} />
        </CardContent>
      </Card>
    );
  }

  if (isLoading) {
    return (
      <div className="space-y-3">
        <LoadingNotice subject="datasets" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-40 w-full" />
          ))}
        </div>
      </div>
    );
  }

  if (datasets.length === 0) {
    return (
      <Card>
        <CardContent className="p-0">
          <EmptyState
            icon={Boxes}
            title="No datasets yet"
            description="Create your first dataset — synthetic images need no upload."
          />
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {datasets.map((d, i) => (
        <Link key={d.slug} href={`/datasets/${d.slug}`} className="group">
          <Card className={`card-hover h-full animate-fade-in-up stagger-${(i % 4) + 1}`}>
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-base">
                <Boxes className="h-4 w-4 text-muted-foreground" />
                <span className="truncate group-hover:underline underline-offset-4">
                  {d.display_name}
                </span>
              </CardTitle>
              <p className="text-xs text-muted-foreground line-clamp-2 min-h-[2rem]">
                {d.description || "No description."}
              </p>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex flex-wrap gap-2 text-xs">
                <Badge variant="secondary" className="gap-1">
                  <Package className="h-3 w-3" /> {d.shard_count} shards
                </Badge>
                <Badge variant="secondary" className="gap-1">
                  <Images className="h-3 w-3" /> {d.sample_count} samples
                </Badge>
                <Badge variant="secondary" className="gap-1">
                  <HardDrive className="h-3 w-3" /> {d.size_human}
                </Badge>
              </div>
              <p className="font-mono text-[11px] text-muted-foreground">
                datasets/{d.slug}/ &middot; {d.image_size}px
              </p>
            </CardContent>
          </Card>
        </Link>
      ))}
    </div>
  );
}
