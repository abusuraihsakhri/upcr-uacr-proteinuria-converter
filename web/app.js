"use strict";

// Standalone browser implementation mirrors upcr_uacr.py; no backend required.
const RatioConverter = (() => {
  const CREATININE_G_PER_MMOL = 0.11312;

  function numeric(value, name, positive = false) {
    if (value === null || value === undefined || value === "") return null;
    if (typeof value === "boolean") throw new Error(name + " must be a number.");
    const result = Number(value);
    if (!Number.isFinite(result) || result < 0 || (positive && result === 0)) {
      throw new Error(name + " must be a finite " + (positive ? "positive" : "non-negative") + " number.");
    }
    return result;
  }

  function toMgG(value, unit) {
    if (unit === "mg/g") return value;
    if (unit === "mg/mmol") return value / CREATININE_G_PER_MMOL;
    throw new Error("Unsupported ratio unit.");
  }

  function calculate(values) {
    const protein = numeric(values.protein_mg_dl, "Urine total protein");
    const albumin = numeric(values.albumin_mg_dl, "Urine albumin");
    const creatinine = numeric(values.creatinine_mg_dl, "Urine creatinine");
    const daily = numeric(values.creatinine_g_day, "Daily creatinine excretion", true);
    let upcr = numeric(values.upcr_mg_g, "UPCR");
    let uacr = numeric(values.uacr_mg_g, "UACR");
    if (protein !== null && upcr !== null) throw new Error("Choose a protein concentration or UPCR, not both.");
    if (albumin !== null && uacr !== null) throw new Error("Choose an albumin concentration or UACR, not both.");
    if ([protein, albumin, upcr, uacr].every(v => v === null)) throw new Error("Enter protein, albumin, UPCR, or UACR.");
    if ((protein !== null || albumin !== null) && (creatinine === null || creatinine === 0)) {
      throw new Error("A positive urine creatinine concentration is required.");
    }

    if (protein !== null) upcr = protein / creatinine * 1000;
    if (albumin !== null) uacr = albumin / creatinine * 1000;
    if ([upcr, uacr].some(v => v !== null && !Number.isFinite(v))) throw new Error("Result is out of numeric range.");

    const warnings = [];
    let fraction = null;
    if (upcr !== null && uacr !== null) {
      if (upcr > 0) fraction = uacr / upcr * 100;
      if (uacr > upcr + Math.max(1e-9, upcr * 1e-10)) {
        warnings.push("UACR exceeds UPCR; check specimen comparability, units and assays.");
      }
    }
    const category = uacr === null ? null : uacr < 30 ?
      "A1 — normal to mildly increased" : uacr < 300 ?
      "A2 — moderately increased" : "A3 — severely increased";

    if (daily !== null) {
      warnings.push("24-hour excretion is an estimate based on supplied daily creatinine excretion, not a measured 24-hour collection.");
    }
    return {
      upcr_mg_g: upcr,
      upcr_mg_mmol: upcr === null ? null : upcr * CREATININE_G_PER_MMOL,
      uacr_mg_g: uacr,
      uacr_mg_mmol: uacr === null ? null : uacr * CREATININE_G_PER_MMOL,
      albuminuria_category: category,
      albumin_fraction_percent: fraction,
      estimated_protein_mg_day: upcr === null || daily === null ? null : upcr * daily,
      estimated_albumin_mg_day: uacr === null || daily === null ? null : uacr * daily,
      warnings
    };
  }

  return { calculate, toMgG, CREATININE_G_PER_MMOL };
})();

if (typeof module !== "undefined" && module.exports) module.exports = RatioConverter;

if (typeof document !== "undefined") {
  const $ = id => document.getElementById(id);
  const form = $("calculator");
  const mode = $("mode");
  let lastResult = null;

  function updateMode() {
    const direct = mode.value === "ratio";
    $("concentration-fields").hidden = direct;
    $("ratio-fields").hidden = !direct;
    $("error").hidden = true;
  }
  mode.addEventListener("change", updateMode);
  updateMode();

  function input(id) {
    return $(id).value.trim() === "" ? null : $(id).value.trim();
  }
  function display(value, unit) {
    return value === null ? "Not available" : new Intl.NumberFormat("en", { maximumSignificantDigits: 6 }).format(value) + " " + unit;
  }

  function render(result) {
    $("result").hidden = false;
    $("error").hidden = true;
    $("upcr-result").textContent = display(result.upcr_mg_g, "mg/g");
    $("upcr-other").textContent = display(result.upcr_mg_mmol, "mg/mmol");
    $("uacr-result").textContent = display(result.uacr_mg_g, "mg/g");
    $("uacr-other").textContent = display(result.uacr_mg_mmol, "mg/mmol");
    $("classification").textContent = result.albuminuria_category || "UACR not provided";
    $("fraction").textContent = display(result.albumin_fraction_percent, "%");
    $("daily-protein").textContent = display(result.estimated_protein_mg_day, "mg/day");
    $("daily-albumin").textContent = display(result.estimated_albumin_mg_day, "mg/day");
    const alerts = $("warnings");
    alerts.replaceChildren();
    for (const warning of result.warnings) {
      const li = document.createElement("li");
      li.textContent = warning;
      alerts.appendChild(li);
    }
    $("warnings-panel").hidden = !result.warnings.length;
    $("export").disabled = false;
  }

  form.addEventListener("submit", e => {
    e.preventDefault();
    lastResult = null;
    $("export").disabled = true;
    try {
      const data = { creatinine_g_day: input("daily-creatinine") };
      if (mode.value === "concentration") {
        data.protein_mg_dl = input("protein");
        data.albumin_mg_dl = input("albumin");
        data.creatinine_mg_dl = input("creatinine");
      } else {
        const unit = $("ratio-unit").value;
        const protein = input("upcr");
        const albumin = input("uacr");
        data.upcr_mg_g = protein === null ? null : RatioConverter.toMgG(Number(protein), unit);
        data.uacr_mg_g = albumin === null ? null : RatioConverter.toMgG(Number(albumin), unit);
        // Check text first; Number("") and Number(non-finite) must not bypass validation.
        if ((protein !== null && !Number.isFinite(Number(protein))) ||
            (albumin !== null && !Number.isFinite(Number(albumin)))) {
          throw new Error("Enter finite ratio measurements.");
        }
      }
      lastResult = RatioConverter.calculate(data);
      render(lastResult);
    } catch (error) {
      $("result").hidden = true;
      $("error").textContent = error.message;
      $("error").hidden = false;
    }
  });

  $("export").addEventListener("click", () => {
    if (!lastResult) return;
    const keys = Object.keys(lastResult);
    const csv = keys.join(",") + "\r\n" +
      keys.map(k => {
        const value = Array.isArray(lastResult[k]) ? lastResult[k].join("; ") :
          lastResult[k] === null ? "" : String(lastResult[k]);
        return '"' + value.replace(/"/g, '""') + '"';
      }).join(",") + "\r\n";
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = "urine-ratio-results.csv";
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
}
