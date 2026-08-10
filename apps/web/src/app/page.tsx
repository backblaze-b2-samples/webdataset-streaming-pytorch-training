import Link from "next/link";
import { Boxes } from "lucide-react";

import { Button } from "@/components/ui/button";
import { StatsCards } from "@/components/dashboard/stats-cards";
import { RecentDatasetsTable } from "@/components/dashboard/recent-datasets-table";
import { LastRunCard } from "@/components/dashboard/last-run-card";

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="text-sm text-muted-foreground mt-1.5">
            WebDataset shard collections on Backblaze B2, and how fast they
            stream into PyTorch.
          </p>
        </div>
        <Button asChild size="sm" className="h-8">
          <Link href="/datasets">
            <Boxes className="h-3.5 w-3.5" />
            New dataset
          </Link>
        </Button>
      </div>
      <StatsCards />
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="animate-fade-in-up stagger-3 lg:col-span-2">
          <RecentDatasetsTable />
        </div>
        <div className="animate-fade-in-up stagger-4">
          <LastRunCard />
        </div>
      </div>
    </div>
  );
}
