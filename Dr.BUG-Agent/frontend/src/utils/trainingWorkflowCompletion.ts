/**
 * Detect whether the chat session already shows a terminal training task result card
 * (avoids duplicate inserts after release / refresh).
 */

export type ChatResultMessageLike = {
  resultData?: {
    variant?: string;
    jobType?: string;
    jobId?: string;
  } | null;
};

export function sessionChatHasTrainCompletionResult(msgs: ChatResultMessageLike[] | undefined, jobId: string): boolean {
  const jid = String(jobId || "").trim();
  if (!jid || !msgs?.length) return false;
  for (const m of msgs) {
    const rd = m.resultData;
    if (!rd || rd.variant !== "completed") continue;
    if (String(rd.jobType || "") !== "train_model") continue;
    if (String(rd.jobId || "").trim() === jid) return true;
  }
  return false;
}

export function sessionChatHasTrainFailureResult(msgs: ChatResultMessageLike[] | undefined, jobId: string): boolean {
  const jid = String(jobId || "").trim();
  if (!jid || !msgs?.length) return false;
  for (const m of msgs) {
    const rd = m.resultData;
    if (!rd || rd.variant !== "failed") continue;
    if (String(rd.jobType || "") !== "train_model") continue;
    if (String(rd.jobId || "").trim() === jid) return true;
  }
  return false;
}
