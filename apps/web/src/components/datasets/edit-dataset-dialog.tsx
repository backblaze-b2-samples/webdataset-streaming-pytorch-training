"use client";

import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { Pencil } from "lucide-react";

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
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { useEditDataset } from "@/lib/queries";
import type { Dataset } from "@webdataset-streaming-pytorch-training/shared";

const schema = z.object({
  display_name: z
    .string()
    .min(2, "Name must be at least 2 characters")
    .max(80, "Name must be 80 characters or fewer"),
  description: z.string().max(500).optional(),
});

type Values = z.infer<typeof schema>;

export function EditDatasetDialog({ dataset }: { dataset: Dataset }) {
  const [open, setOpen] = useState(false);
  const edit = useEditDataset(dataset.slug);
  // Edit opens PRE-FILLED with the real manifest — no default hints needed.
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: {
      display_name: dataset.display_name,
      description: dataset.description ?? "",
    },
  });

  useEffect(() => {
    if (open) {
      form.reset({
        display_name: dataset.display_name,
        description: dataset.description ?? "",
      });
    }
  }, [open, dataset, form]);

  const onSubmit = (values: Values) => {
    edit.mutate(
      { display_name: values.display_name, description: values.description ?? "" },
      {
        onSuccess: () => {
          toast.success("Dataset updated");
          setOpen(false);
        },
        onError: (error) =>
          toast.error("Could not update dataset", { description: error.message }),
      }
    );
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          <Pencil className="h-3.5 w-3.5" />
          Edit
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit dataset</DialogTitle>
          <DialogDescription>
            Update the display name and description. The slug{" "}
            <code>{dataset.slug}</code> and shards are immutable.
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="display_name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Display name</FormLabel>
                  <FormControl>
                    <Input {...field} />
                  </FormControl>
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
                    <Textarea className="resize-none" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setOpen(false)}
                disabled={edit.isPending}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={edit.isPending}>
                {edit.isPending ? "Saving..." : "Save changes"}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
