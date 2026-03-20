import { $, currentStage, escapeHtml, plainStatusLabel, renderStageMarkup } from "/static/js/dom.js";

const shell = $(".shell[data-run-id]");
const runId = shell?.dataset?.runId;

if (runId) {
  // The run detail page is live-updated over SSE so users can stay on one page
  // while the worker moves through planning, generation, validation, and deploy.
  const runStream = new EventSource(`/api/runs/${runId}/stream`);

  runStream.onmessage = (event) => {
    const payload = JSON.parse(event.data);
    const result = payload.result || {};
    $("#runTitle").textContent = result.app_name || "Run Details";
    $("#runStatus").textContent = plainStatusLabel(payload.status);
    $("#runPrompt").textContent = payload.prompt || "";
    $("#runError").textContent = payload.friendly_error || "None";
    $("#runFamily").textContent = result.closest_family || "pending";
    $("#runSupport").textContent = result.support_tier || "pending";
    $("#runVerification").textContent = result.tests_passed ? "Passed" : "Not passed";
    $("#runDeployed").textContent = result.deployed ? "Yes" : "No";

    const outcomeTitle = $("#outcomeTitle");
    const outcomeText = $("#outcomeText");
    const banner = $(".outcome-banner");
    if (payload.status === "completed" && result.tests_passed) {
      outcomeTitle.textContent = "Your app is ready";
      outcomeText.textContent = "The build finished and the quality check passed. You can download it now.";
      banner.classList.remove("outcome-progress", "outcome-failed");
      banner.classList.add("outcome-ready");
    } else if (payload.status === "failed") {
      outcomeTitle.textContent = "This build needs attention";
      outcomeText.textContent = payload.friendly_error || "Something went wrong during the build.";
      banner.classList.remove("outcome-progress", "outcome-ready");
      banner.classList.add("outcome-failed");
    } else {
      outcomeTitle.textContent = "Your app is being built";
      outcomeText.textContent = "Stay on this page to watch the progress update live.";
      banner.classList.remove("outcome-ready", "outcome-failed");
      banner.classList.add("outcome-progress");
    }

    $("#stageTimeline").innerHTML = renderStageMarkup(currentStage(payload));
    $("#artifactList").innerHTML =
      (payload.artifacts || [])
        .map((item) => `<li><strong>${escapeHtml(item.label)}</strong><br />${escapeHtml(item.path)}</li>`)
        .join("") || "<li>No artifacts yet.</li>";
    $("#logOutput").textContent =
      (payload.logs || [])
        .map((entry) => `[${entry.created_at}] ${String(entry.level || "").toUpperCase()}: ${entry.message}`)
        .join("\n") || "No logs yet.";

    if (payload.status === "completed" || payload.status === "failed") {
      runStream.close();
    }
  };
}
