/**
 * Resolve SHAP beeswarm PNG artifacts against the final trained/published model display name.
 * Used by training completion receipt and narrative copy so we never substitute another model's plot.
 */

export function modelSlugFromShapBeeswarmArtifactName(artifactKey: string): string | null {
  const base = artifactKey.replace(/\\/g, "/").split("/").pop() || artifactKey;
  const stem = base.replace(/\.png$/i, "");
  const m = stem.match(/^shap[_-]?beeswarm[_-]+(.+)$/i);
  const raw = m?.[1]?.trim();
  return raw || null;
}

export function normalizedModelToken(s: string): string {
  return s.toLowerCase().replace(/[^a-z0-9]+/g, "");
}

export function shapArtifactMatchesFinalModel(artifactKey: string, finalModelDisplay: string): boolean {
  const slug = modelSlugFromShapBeeswarmArtifactName(artifactKey);
  if (!slug || !finalModelDisplay.trim()) return false;
  const fileTok = normalizedModelToken(slug);
  const finalTok = normalizedModelToken(finalModelDisplay);
  if (!fileTok || !finalTok) return false;
  return finalTok.includes(fileTok) || fileTok.includes(finalTok);
}

export function listShapBeeswarmPngKeys(artifacts: Record<string, string> | undefined): string[] {
  if (!artifacts) return [];
  return Object.keys(artifacts).filter((name) => {
    if (!/\.png$/i.test(name)) return false;
    const lower = name.toLowerCase();
    return lower.includes("shap") && lower.includes("beeswarm");
  });
}

export function anyShapBeeswarmInArtifacts(artifacts: Record<string, string> | undefined): boolean {
  return listShapBeeswarmPngKeys(artifacts).length > 0;
}

/** Pick the best beeswarm PNG whose filename matches `finalModelDisplay`; otherwise null. */
export function pickFinalModelShapBeeswarmFromArtifacts(
  artifacts: Record<string, string> | undefined,
  finalModelDisplay: string,
): { artifactKey: string; url: string } | null {
  if (!artifacts || !finalModelDisplay.trim()) return null;
  const scored: { artifactKey: string; url: string; score: number }[] = [];
  for (const name of listShapBeeswarmPngKeys(artifacts)) {
    if (!shapArtifactMatchesFinalModel(name, finalModelDisplay)) continue;
    const lower = name.toLowerCase();
    let score = 4;
    if (lower.includes("shap_beeswarm")) score += 2;
    scored.push({ artifactKey: name, url: String(artifacts[name]), score });
  }
  if (scored.length === 0) return null;
  scored.sort((a, b) => b.score - a.score || a.artifactKey.localeCompare(b.artifactKey));
  const top = scored[0]!;
  return { artifactKey: top.artifactKey, url: top.url };
}
