"use client";

import { useRouter } from "next/navigation";
import { Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Button, buttonVariants } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { useDeleteDataset } from "@/lib/queries";

export function DeleteDatasetDialog({ slug }: { slug: string }) {
  const router = useRouter();
  const del = useDeleteDataset();

  const onConfirm = () => {
    del.mutate(slug, {
      onSuccess: (result) => {
        toast.success("Dataset deleted", {
          description: `Removed ${result.objects} object(s) under datasets/${slug}/.`,
        });
        router.push("/datasets");
      },
      onError: (error) =>
        toast.error("Could not delete dataset", { description: error.message }),
    });
  };

  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <Button variant="outline" size="sm" className="text-destructive">
          <Trash2 className="h-3.5 w-3.5" />
          Delete
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete this dataset?</AlertDialogTitle>
          <AlertDialogDescription>
            This permanently removes every object under{" "}
            <code>datasets/{slug}/</code> in B2 — shards, manifest, and run
            history. The delete is scoped to this prefix only. There is no undo.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={del.isPending}>Cancel</AlertDialogCancel>
          <AlertDialogAction
            onClick={onConfirm}
            disabled={del.isPending}
            className={buttonVariants({ variant: "destructive" })}
          >
            {del.isPending ? "Deleting..." : "Yes, delete it"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
