"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { Play, Cpu, Gauge, Timer, Network } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
} from "@/components/ui/form";
import { useStreamDataset } from "@/lib/queries";
import type { ShardAssignment, StreamResult } from "@webdataset-streaming-pytorch-training/shared";

// Run knobs are all finite → selectors. Defaults match the plan's fast, safe run.
const NUM_WORKERS = ["0", "2", "4"] as const;
const NUM_NODES = ["1", "2", "4"] as const;
const BATCH_SIZE = ["16", "32", "64"] as const;
const MAX_BATCHES = ["10", "20", "50"] as const;
const SHUFFLE_BUFFER = ["0", "100", "1000"] as const;

const schema = z.object({
  num_workers: z.enum(NUM_WORKERS),
  num_nodes: z.enum(NUM_NODES),
  batch_size: z.enum(BATCH_SIZE),
  max_batches: z.enum(MAX_BATCHES),
  shuffle_buffer: z.enum(SHUFFLE_BUFFER),
});

type Values = z.infer<typeof schema>;

const DEFAULTS: Values = {
  num_workers: "0",
  num_nodes: "1",
  batch_size: "32",
  max_batches: "20",
  shuffle_buffer: "100",
};

const SELECTS: { name: keyof Values; label: string; options: readonly string[] }[] = [
  { name: "num_workers", label: "Workers", options: NUM_WORKERS },
  { name: "num_nodes", label: "Nodes", options: NUM_NODES },
  { name: "batch_size", label: "Batch size", options: BATCH_SIZE },
  { name: "max_batches", label: "Max batches", options: MAX_BATCHES },
  { name: "shuffle_buffer", label: "Shuffle buffer", options: SHUFFLE_BUFFER },
];

function LossSparkline({ values }: { values: number[] }) {
  if (values.length < 2) return null;
  const max = Math.max(...values);
  const min = Math.min(...values);
  const span = max - min || 1;
  const points = values
    .map((v, i) => {
      const x = (i / (values.length - 1)) * 100;
      const y = 30 - ((v - min) / span) * 28 - 1;
      return `${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");
  return (
    <svg viewBox="0 0 100 30" preserveAspectRatio="none" className="h-16 w-full">
      <polyline
        points={points}
        fill="none"
        stroke="var(--primary)"
        strokeWidth="1"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}

function SplitPlan({ title, plan }: { title: string; plan: ShardAssignment[] }) {
  return (
    <div className="space-y-2">
      <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        {title}
      </p>
      <div className="space-y-1.5">
        {plan.map((a) => (
          <div key={a.rank} className="flex items-center gap-2 text-xs">
            <span className="font-mono text-muted-foreground w-16 shrink-0">
              rank {a.rank}
            </span>
            <div className="flex flex-wrap gap-1">
              {a.shard_indices.length === 0 ? (
                <span className="text-muted-foreground">(no shards)</span>
              ) : (
                a.shard_indices.map((idx) => (
                  <Badge key={idx} variant="secondary" className="font-mono">
                    #{idx}
                  </Badge>
                ))
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function Metrics({ result }: { result: StreamResult }) {
  const cells = [
    { icon: Cpu, label: "device", value: result.device },
    { icon: Gauge, label: "samples/s", value: result.samples_per_s.toLocaleString() },
    { icon: Gauge, label: "MB/s", value: result.mb_per_s.toFixed(2) },
    { icon: Timer, label: "elapsed", value: `${result.elapsed_s.toFixed(2)}s` },
    { icon: Network, label: "batches", value: `${result.batches}` },
    { icon: Network, label: "samples", value: `${result.samples}` },
  ];
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
      {cells.map((c) => (
        <div key={c.label} className="rounded-md border border-border p-3">
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <c.icon className="h-3 w-3" />
            {c.label}
          </div>
          <div className="mt-1 font-mono text-lg font-semibold tabular-nums">
            {c.value}
          </div>
        </div>
      ))}
    </div>
  );
}

export function StreamPanel({ slug }: { slug: string }) {
  const stream = useStreamDataset(slug);
  const form = useForm<Values>({ resolver: zodResolver(schema), defaultValues: DEFAULTS });
  const result = stream.data;

  const onSubmit = (values: Values) => {
    stream.mutate(
      {
        num_workers: Number(values.num_workers),
        num_nodes: Number(values.num_nodes),
        batch_size: Number(values.batch_size),
        max_batches: Number(values.max_batches),
        shuffle_buffer: Number(values.shuffle_buffer),
      },
      {
        onSuccess: (r) =>
          toast.success("Streaming run complete", {
            description: `${r.samples_per_s.toLocaleString()} samples/s on ${r.device}.`,
          }),
        onError: (error) =>
          toast.error("Run failed", { description: error.message }),
      }
    );
  };

  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title flex items-center gap-2">
          <Play className="h-4 w-4 text-muted-foreground" />
          Stream &amp; train
        </CardTitle>
      </CardHeader>
      <CardContent className="p-5 space-y-5">
        <p className="text-sm text-muted-foreground">
          Shards stream from B2 straight into a bounded PyTorch loop (tiny CNN,
          device auto-detected CUDA&nbsp;&rarr;&nbsp;MPS&nbsp;&rarr;&nbsp;CPU) —
          no local staging disk. Defaults run in seconds.
        </p>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
              {SELECTS.map((s) => (
                <FormField
                  key={s.name}
                  control={form.control}
                  name={s.name}
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-xs">{s.label}</FormLabel>
                      <Select onValueChange={field.onChange} value={field.value}>
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {s.options.map((o) => (
                            <SelectItem key={o} value={o}>
                              {o}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </FormItem>
                  )}
                />
              ))}
            </div>
            <div className="flex items-center justify-between gap-3">
              <p className="text-xs text-muted-foreground">
                Detected device:{" "}
                <span className="font-mono">
                  {result?.device ?? "auto (CUDA → MPS → CPU)"}
                </span>
              </p>
              <Button type="submit" disabled={stream.isPending}>
                <Play className="h-3.5 w-3.5" />
                {stream.isPending ? "Streaming..." : "Start run"}
              </Button>
            </div>
          </form>
        </Form>

        {result && (
          <div className="space-y-5 border-t border-border pt-5">
            <Metrics result={result} />
            {result.loss_curve.length > 1 && (
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Loss ({result.loss_curve.length} steps)
                </p>
                <LossSparkline values={result.loss_curve} />
              </div>
            )}
            <div className="grid gap-5 sm:grid-cols-2">
              <SplitPlan
                title={`Node split (world size ${result.num_nodes})`}
                plan={result.node_plan}
              />
              <SplitPlan
                title={`Worker split (${result.num_workers || 1} reader${
                  (result.num_workers || 1) === 1 ? "" : "s"
                })`}
                plan={result.worker_plan}
              />
            </div>
            <p className="text-xs text-muted-foreground">
              Each rank reads a non-overlapping shard range via WebDataset&rsquo;s
              round-robin split — the same rule scales a real multi-GPU /
              multi-node run reading one bucket.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
