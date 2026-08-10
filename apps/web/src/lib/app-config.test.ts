import { describe, expect, it } from "vitest";
import { APP_DESCRIPTION, APP_NAME } from "@/lib/app-config";

describe("app identity", () => {
  it("ships the canonical app name and description", () => {
    expect(APP_NAME).toBe("WebDataset Streaming PyTorch Training");
    expect(APP_DESCRIPTION).toBe(
      "Stream WebDataset shards straight from Backblaze B2 into PyTorch training"
    );
  });
});
