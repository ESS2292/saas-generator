import { requestJson } from "/static/js/api.js";
import { $, currentStage, escapeHtml, plainStatusLabel, renderStageMarkup, showError, statusIcon } from "/static/js/dom.js";

// Dashboard behavior lives here so the template only needs markup and page data.
const runList = $("#runList");
const errorBox = $("#errorBox");
const secretList = $("#secretList");
const generatorForm = $("#generatorForm");
const secretSaveButton = $("#secretSaveButton");
const refreshRuns = $("#refreshRuns");
const logoutButton = $("#logoutButton");
const advancedMode = $("#advancedMode");
const advancedFields = $("#advancedFields");

function renderRun(run) {
  const result = run.result || {};
  const latestError = run.friendly_error || result.latest_error || "None";
  const stage = currentStage(run);
  const deployButton =
    run.status === "completed" && result.tests_passed && !result.deployed
      ? `<button class="secondary-button" data-deploy-run="${escapeHtml(run.id)}">Deploy App</button>`
      : "";
  return `<article class="run-card" data-run-id="${escapeHtml(run.id)}"><div class="run-header"><div><p class="eyebrow">App Request</p><h3>${escapeHtml(result.app_name || "New App")}</h3></div><span class="status-pill status-${escapeHtml(run.status)}"><span class="status-icon">${escapeHtml(statusIcon(run.status))}</span>${escapeHtml(plainStatusLabel(run.status))}</span></div><p class="prompt-copy">${escapeHtml(run.prompt)}</p><div class="stage-row"><strong>Current step:</strong> ${renderStageMarkup(stage)}</div><div class="metric-grid"><div class="metric"><span>App type</span><strong>${escapeHtml(String(result.closest_family || "in progress").replaceAll("_", " "))}</strong></div><div class="metric"><span>Status</span><strong>${escapeHtml(plainStatusLabel(run.status))}</strong></div><div class="metric"><span>Ready to download</span><strong>${result.saved_files_count ? "Yes" : "Not yet"}</strong></div><div class="metric"><span>Quality check</span><strong>${result.tests_passed ? "Passed" : "In progress"}</strong></div></div><div class="detail-grid"><div class="panel"><h4>Main parts</h4><p><strong>For:</strong> ${escapeHtml((result.primary_users || []).join(", ") || "Still deciding")}</p><p><strong>Includes:</strong> ${escapeHtml((result.core_entities || []).join(", ") || "Still deciding")}</p><p><strong>Key actions:</strong> ${escapeHtml((result.core_workflows || []).join(", ") || "Still deciding")}</p></div><div class="panel"><h4>Progress</h4><p><strong>Quality check:</strong> ${result.tests_passed ? "Passed" : "Not finished yet"}</p><p><strong>Published online:</strong> ${result.deployed ? "Yes" : "No"}</p><p><strong>Need attention:</strong> ${escapeHtml(latestError)}</p></div></div><div class="button-row"><a class="ghost-link" href="/runs/${escapeHtml(run.id)}">Open details</a>${deployButton}</div></article>`;
}

function renderSecrets(secrets) {
  if (!secretList) {
    return;
  }
  secretList.innerHTML = secrets.length
    ? secrets
        .map(
          (secret) =>
            `<div class="secret-row"><strong>${escapeHtml(secret.name)}</strong><span>${escapeHtml(secret.updated_at)}</span><button class="ghost-button" data-delete-secret="${escapeHtml(secret.name)}">Delete</button></div>`,
        )
        .join("")
    : "<p class='empty-state'>No saved account keys yet.</p>";
}

async function loadRuns() {
  try {
    const payload = await requestJson("/api/runs");
    runList.innerHTML = payload.runs.length
      ? payload.runs.map(renderRun).join("")
      : "<p class='empty-state'>Your apps will show up here after you start your first build.</p>";
  } catch (error) {
    if (error.status === 401) {
      window.location.reload();
      return;
    }
    showError(errorBox, error.message || "Unable to load runs.");
  }
}

async function loadSecrets() {
  try {
    const payload = await requestJson("/api/secrets");
    renderSecrets(payload.secrets || []);
  } catch (error) {
    showError(errorBox, error.message || "Unable to load saved account keys.");
  }
}

async function startRun(event) {
  event.preventDefault();
  showError(errorBox, "");
  const prompt = $("#prompt")?.value?.trim();
  if (!prompt) {
    showError(errorBox, "Prompt is required.");
    return;
  }

  try {
    const payload = await requestJson("/api/runs", {
      method: "POST",
      body: JSON.stringify({
        prompt,
        run_verification: $("#runVerification")?.checked,
        auto_deploy: $("#autoDeploy")?.checked,
        mode: advancedMode?.checked ? "advanced" : "starter",
        app_name: $("#appName")?.value || "",
        target_users: $("#targetUsers")?.value || "",
        core_entities: $("#coreEntities")?.value || "",
        core_workflows: $("#coreWorkflows")?.value || "",
      }),
    });
    window.location.href = `/runs/${payload.id}`;
  } catch (error) {
    showError(errorBox, error.message || "Unable to queue run.");
  }
}

async function deployRun(runId) {
  try {
    await requestJson(`/api/runs/${runId}/deploy`, { method: "POST" });
    await loadRuns();
  } catch (error) {
    showError(errorBox, error.message || "Unable to deploy app.");
  }
}

async function saveSecret() {
  try {
    await requestJson("/api/secrets", {
      method: "POST",
      body: JSON.stringify({
        name: $("#secretName")?.value?.trim() || "",
        value: $("#secretValue")?.value || "",
      }),
    });
    $("#secretName").value = "";
    $("#secretValue").value = "";
    await loadSecrets();
  } catch (error) {
    showError(errorBox, error.message || "Unable to store secret.");
  }
}

async function deleteSecretByName(name) {
  try {
    await requestJson(`/api/secrets/${encodeURIComponent(name)}`, { method: "DELETE" });
    await loadSecrets();
  } catch (error) {
    showError(errorBox, error.message || "Unable to delete secret.");
  }
}

generatorForm?.addEventListener("submit", startRun);
secretSaveButton?.addEventListener("click", saveSecret);
refreshRuns?.addEventListener("click", loadRuns);
logoutButton?.addEventListener("click", async () => {
  await requestJson("/api/auth/logout", { method: "POST" });
  window.location.reload();
});
advancedMode?.addEventListener("change", (event) => {
  advancedFields?.classList.toggle("active", event.target.checked);
});
document.addEventListener("click", (event) => {
  const templateButton = event.target.closest(".template-button");
  if (templateButton) {
    event.preventDefault();
    const prompt = $("#prompt");
    prompt.value = templateButton.getAttribute("data-template") || "";
    prompt.focus();
    return;
  }

  const deployButton = event.target.closest("[data-deploy-run]");
  if (deployButton) {
    deployRun(deployButton.getAttribute("data-deploy-run"));
    return;
  }

  const deleteButton = event.target.closest("[data-delete-secret]");
  if (deleteButton) {
    deleteSecretByName(deleteButton.getAttribute("data-delete-secret"));
  }
});

// Keep the dashboard fresh without requiring manual reloads while a build is running.
setInterval(loadRuns, 5000);
setInterval(loadSecrets, 15000);
