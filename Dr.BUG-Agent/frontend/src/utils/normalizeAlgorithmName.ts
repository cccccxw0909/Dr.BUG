/**
 * Normalize heterogeneous training / artifact model names into stable canonical keys for UI grouping.
 * Used by SHAP screening plot parsing so equivalently named learners are not duplicated or dropped.
 */

function compactAlnum(raw: string): string {
  return String(raw || "")
    .trim()
    .toLowerCase()
    .replace(/[\s_-]+/g, "")
    .replace(/[^a-z0-9]/g, "");
}

function stripLearnerSuffixes(compact: string): string {
  let c = compact;
  for (;;) {
    if (c.endsWith("classifier")) {
      c = c.slice(0, -"classifier".length);
      continue;
    }
    if (c.endsWith("regressor")) {
      c = c.slice(0, -"regressor".length);
      continue;
    }
    break;
  }
  return c;
}

type Canonical = "CatBoost" | "RandomForest" | "XGBoost" | "LightGBM";

const CANONICAL_BY_BODY: Record<string, Canonical> = {
  catboost: "CatBoost",
  randomforest: "RandomForest",
  rf: "RandomForest",
  xgboost: "XGBoost",
  xgb: "XGBoost",
  lightgbm: "LightGBM",
  lgbm: "LightGBM",
  lgb: "LightGBM",
};

function mapBodyToCanonical(body: string): Canonical | null {
  if (!body) return null;
  const direct = CANONICAL_BY_BODY[body];
  if (direct) return direct;
  if (body.startsWith("catboost")) return "CatBoost";
  if (body.startsWith("randomforest")) return "RandomForest";
  if (body.startsWith("xgboost") || body === "xgb") return "XGBoost";
  if (body.startsWith("lightgbm") || body.startsWith("lgbm")) return "LightGBM";
  return null;
}

/**
 * Maps names such as CatBoostClassifier, random_forest, xg-boost → canonical tree learner key.
 * Unknown names return a readable fallback (never empty when raw is non-empty).
 */
export function normalizeAlgorithmName(raw: string): string {
  const t = String(raw || "").trim();
  if (!t) return "";

  const compact = compactAlnum(t);
  if (!compact) return "";

  const body = stripLearnerSuffixes(compact);
  const canonical = mapBodyToCanonical(body);
  if (canonical) return canonical;

  const spaced = raw.replace(/_/g, " ").replace(/-/g, " ").trim();
  if (/\s/.test(spaced)) {
    return spaced
      .split(/\s+/)
      .map((w) => (w ? w.charAt(0).toUpperCase() + w.slice(1).toLowerCase() : ""))
      .filter(Boolean)
      .join("");
  }

  const fall = spaced || raw.trim();
  if (!fall.length) return "";
  return fall.charAt(0).toUpperCase() + fall.slice(1).toLowerCase();
}
