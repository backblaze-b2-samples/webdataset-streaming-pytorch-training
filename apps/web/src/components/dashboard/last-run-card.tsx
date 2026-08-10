"use client";

import { Activity, Cpu } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { Badge } from "@/components/ui/badge";
import { useDatasetStats } from "@/lib/queries";

export function LastRunCard() {
  const { data: stats, isLoading } = useDatasetStats();
  const throughput = stats?.last_run_samples_per_s ?? null;

  return (
    <Card className="h-full">
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title">Last streaming run</CardTitle>
      </CardHeader>
      <CardContent className="p-5">
        {isLoading ? (
          <Skeleton className="h-24 w-full" />
        ) : throughput === null ? (
          <EmptyState
            icon={Activity}
            title="No runs yet"
            description="Open a dataset and start a streaming run to see live throughput here."
          />
        ) : (
          <div className="space-y-4">
            <div>
              <div className="stat-value">{throughput.toLocaleString()}</div>
              <p className="text-sm text-muted-foreground mt-1">
                samples / second streamed straight from B2 into PyTorch
              </p>
            </div>
            {stats?.last_run_device && (
              <Badge variant="secondary" className="gap-1.5">
                <Cpu className="h-3 w-3" />
                device: {stats.last_run_device}
              </Badge>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
