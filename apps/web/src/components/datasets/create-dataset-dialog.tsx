"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { Plus, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
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
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { useCreateDataset } from "@/lib/queries";

// Finite option sets render as selectors (never free text); the API re-validates
// against the same sets. Defaults match the plan's fast, offline demo run.
const NUM_SAMPLES = ["128", "256", "512", "1024"] as const;
const SAMPLES_PER_SHARD = ["64", "128", "256"] as const;
const IMAGE_SIZE = ["32", "64"] as const;

const schema = z.object({
  name: z
    .string()
    .min(2, "Name must be at least 2 characters")
    .max(50, "Name must be 50 characters or fewer"),
  description: z.string().max(500).optional(),
  source: z.enum(["synthetic", "raw"]),
  num_samples: z.enum(NUM_SAMPLES),
  samples_per_shard: z.enum(SAMPLES_PER_SHARD),
  image_size: z.enum(IMAGE_SIZE),
});

type Values = z.infer<typeof schema>;

const DEFAULTS: Values = {
  name: "",
  description: "",
  source: "synthetic",
  num_samples: "512",
  samples_per_shard: "128",
  image_size: "32",
};

export function CreateDatasetDialog() {
  const [open, setOpen] = useState(false);
  const router = useRouter();
  const create = useCreateDataset();
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: DEFAULTS,
  });

  // useWatch (not form.watch) is the memo-safe subscription for values read
  // during render — it avoids the React Compiler "cannot be memoized" warning.
  const source = useWatch({ control: form.control, name: "source" });
  const samples = Number(useWatch({ control: form.control, name: "num_samples" }));
  const perShard = Number(
    useWatch({ control: form.control, name: "samples_per_shard" })
  );
  const shardCount = Math.max(1, Math.ceil(samples / perShard));

  // Packing is a single synchronous POST — tick a live elapsed counter while it
  // is pending so the disabled button visibly advances instead of looking hung.
  // (Reset happens in onSubmit — setState in an effect body is disallowed.)
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    if (!create.isPending) return;
    const started = Date.now();
    const id = setInterval(
      () => setElapsed(Math.floor((Date.now() - started) / 1000)),
      1000
    );
    return () => clearInterval(id);
  }, [create.isPending]);

  const onSubmit = (values: Values) => {
    setElapsed(0);
    create.mutate(
      {
        name: values.name,
        description: values.description || undefined,
        source: values.source,
        num_samples: Number(values.num_samples),
        samples_per_shard: Number(values.samples_per_shard),
        image_size: Number(values.image_size),
      },
      {
        onSuccess: (dataset) => {
          toast.success(`Dataset "${dataset.display_name}" created`, {
            description: `${dataset.sample_count} ${
              dataset.sample_count === 1 ? "sample" : "samples"
            } across ${dataset.shard_count} ${
              dataset.shard_count === 1 ? "shard" : "shards"
            } on B2.`,
          });
          form.reset(DEFAULTS);
          setOpen(false);
          // Chain into the goal's next step: the "Start run" control lives on the
          // dataset detail page, so land the user there instead of the list.
          router.push(`/datasets/${dataset.slug}`);
        },
        onError: (error) =>
          toast.error("Could not create dataset", {
            description: error.message,
          }),
      }
    );
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm" className="h-8">
          <Plus className="h-3.5 w-3.5" />
          New dataset
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Create dataset</DialogTitle>
          <DialogDescription>
            Pack images into WebDataset shards and write them straight to
            Backblaze B2.
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Name</FormLabel>
                  <FormControl>
                    {/* Placeholder is guidance only — never an autofill button. */}
                    <Input placeholder="e.g. cifar-demo" {...field} />
                  </FormControl>
                  <FormDescription>
                    Slugified for the B2 prefix{" "}
                    <code>datasets/&lt;slug&gt;/</code>. 2&ndash;50 characters.
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Description</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder="Optional. What is this training corpus?"
                      className="resize-none"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="grid gap-4 sm:grid-cols-2">
              <FormField
                control={form.control}
                name="source"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Source</FormLabel>
                    <Select onValueChange={field.onChange} value={field.value}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="synthetic">Synthetic</SelectItem>
                        <SelectItem value="raw">Raw media</SelectItem>
                      </SelectContent>
                    </Select>
                    <FormDescription>
                      Synthetic needs no upload; Raw packs images from the Raw
                      media page.
                    </FormDescription>
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="image_size"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Image size (px)</FormLabel>
                    <Select onValueChange={field.onChange} value={field.value}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {IMAGE_SIZE.map((v) => (
                          <SelectItem key={v} value={v}>
                            {v} &times; {v}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </FormItem>
                )}
              />

              {/* Samples is a synthetic-generation count. For the raw source the
                  packer uses whatever images already exist under uploads/ and
                  num_samples would only cap them — hiding it avoids the "picked
                  512, got fewer" mismatch. The field keeps its default value in
                  form state, so the submitted payload stays valid for raw. */}
              {source !== "raw" && (
                <FormField
                  control={form.control}
                  name="num_samples"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Samples</FormLabel>
                      <Select onValueChange={field.onChange} value={field.value}>
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {NUM_SAMPLES.map((v) => (
                            <SelectItem key={v} value={v}>
                              {v}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </FormItem>
                  )}
                />
              )}

              <FormField
                control={form.control}
                name="samples_per_shard"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Samples per shard</FormLabel>
                    <Select onValueChange={field.onChange} value={field.value}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {SAMPLES_PER_SHARD.map((v) => (
                          <SelectItem key={v} value={v}>
                            {v}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </FormItem>
                )}
              />
            </div>

            <p className="rounded-md bg-muted/50 px-3 py-2 text-xs text-muted-foreground">
              {source === "raw" ? (
                "Packs the raw media already uploaded to your bucket into WebDataset shards on B2."
              ) : (
                <>
                  The default 512 synthetic samples at 32&nbsp;px pack into{" "}
                  <span className="font-medium text-foreground">
                    {shardCount} shard{shardCount === 1 ? "" : "s"}
                  </span>{" "}
                  &mdash; a fast, offline demo run.
                </>
              )}
            </p>

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setOpen(false)}
                disabled={create.isPending}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={create.isPending}>
                {create.isPending && (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
                )}
                {create.isPending ? `Packing shards… ${elapsed}s` : "Create dataset"}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
