import { DatasetDetail } from "@/components/datasets/dataset-detail";

// Next.js 16: route params are async and must be awaited.
export default async function DatasetDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  return <DatasetDetail slug={slug} />;
}
