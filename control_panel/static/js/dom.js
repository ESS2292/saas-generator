export function $(selector, root = document) {
  return root.querySelector(selector);
}


export function showError(errorBox, message) {
  if (!errorBox) {
    return;
  }
  errorBox.style.display = message ? "block" : "none";
  errorBox.textContent = message || "";
}


export function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}


export function plainStatusLabel(status) {
  const labels = {
    queued: "Getting ready",
    running: "Building now",
    deploying: "Publishing online",
    completed: "Finished",
    failed: "Needs attention",
  };
  return labels[String(status || "").toLowerCase()] || "In progress";
}


export function currentStage(payload) {
  const stages = payload.stages || [];
  const active = stages.find((stage) => stage.state === "current" || stage.state === "failed");
  if (active) {
    return active;
  }
  if (String(payload.status || "").toLowerCase() === "completed") {
    return { key: "completed", label: "Completed", state: "done" };
  }
  return { key: "queued", label: "Queued", state: "pending" };
}


export function stageProgress(stage) {
  const order = {
    queued: 8,
    planning: 22,
    generating: 40,
    validating: 62,
    repairing: 76,
    deploying: 90,
    completed: 100,
  };
  return order[String(stage.key || "").toLowerCase()] || 8;
}


export function statusIcon(status) {
  const icons = { queued: "○", running: "◔", deploying: "↗", completed: "✓", failed: "!" };
  return icons[String(status || "").toLowerCase()] || "•";
}


export function renderStageMarkup(stage) {
  const stageLabel = stage.state === "failed" ? "Failed" : stage.label;
  return `<div class="stage-track-wrap"><span class="stage-pill stage-${escapeHtml(stage.state)}">${escapeHtml(stageLabel)}</span><div class="stage-track"><span class="stage-fill stage-${escapeHtml(stage.state)}" style="width:${stageProgress(stage)}%;"></span></div></div>`;
}
