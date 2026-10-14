import { experimentCreateOptions } from "@/components/experiments/experiment-create-options";

const optionIds = experimentCreateOptions.map((option) => option.id);
const expectedIds = ["enterprise", "sample", "blank"] as const;
const primary = experimentCreateOptions.filter((option) => option.emphasis === "primary");

void optionIds;
void expectedIds;
void primary;
