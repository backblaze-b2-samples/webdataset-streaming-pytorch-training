"use client";

import { ExternalLink, Package } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { useDatasetShards } from "@/lib/queries";

/**
 * Scoped shard explorer: lists ONLY this dataset's `.tar` shards under
 * `datasets/<slug>/`, with size, sample count, and a presigned inline preview.
 * The bucket-wide explorer lives at /files; this is the per-dataset counterpart.
 */
export function ShardExplorer({ slug }: { slug: string }) {
  const { data: shards = [], isLoading, error, refetch } = useDatasetShards(slug);

  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title flex items-center gap-2">
          <Package className="h-4 w-4 text-muted-foreground" />
          Shards
        </CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        {isLoading ? (
          <div className="p-4 space-y-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        ) : error ? (
          <ErrorState error={error} onRetry={() => refetch()} />
        ) : shards.length === 0 ? (
          <EmptyState icon={Package} title="No shards" description="This dataset has no shards." />
        ) : (
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/40 hover:bg-muted/40">
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Shard
                </TableHead>
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Samples
                </TableHead>
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Size
                </TableHead>
                <TableHead className="text-right text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Preview
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {shards.map((shard) => (
                <TableRow key={shard.key} className="table-row-hover">
                  <TableCell className="font-mono text-xs">{shard.filename}</TableCell>
                  <TableCell className="font-mono text-xs tabular-nums text-muted-foreground">
                    {shard.count}
                  </TableCell>
                  <TableCell className="font-mono text-xs tabular-nums text-muted-foreground whitespace-nowrap">
                    {shard.size_human}
                  </TableCell>
                  <TableCell className="text-right">
                    {shard.preview_url ? (
                      <a
                        href={shard.preview_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
                        title="Download this .tar shard from B2"
                      >
                        .tar
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    ) : (
                      <span className="text-xs text-muted-foreground">&mdash;</span>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}
