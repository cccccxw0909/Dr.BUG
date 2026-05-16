/** Stable display order for dataset available-task lists (chips / rows). */
export const DATASET_TASK_DISPLAY_ORDER = [
  "clinical_efficacy",
  "mortality_28d",
  "polymyxin_resistance",
  "treatment_duration",
] as const;

export function sortDatasetTasksForDisplay(tasks: string[]): string[] {
  const incoming = tasks.filter(Boolean);
  const known = new Set<string>([...DATASET_TASK_DISPLAY_ORDER]);
  const ordered = DATASET_TASK_DISPLAY_ORDER.filter((k) => incoming.includes(k));
  const rest = incoming.filter((t) => !known.has(t));
  rest.sort();
  return [...ordered, ...rest];
}
