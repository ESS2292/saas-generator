import { requestJson } from "/static/js/api.js";
import { $, showError } from "/static/js/dom.js";

const errorBox = $("#errorBox");
const loginForm = $("#loginForm");
const registerForm = $("#registerForm");

async function submitAuth(path, payload) {
  try {
    await requestJson(path, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    window.location.reload();
  } catch (error) {
    showError(errorBox, error.message || "Authentication failed.");
  }
}

if (loginForm) {
  loginForm.addEventListener("submit", (event) => {
    event.preventDefault();
    submitAuth("/api/auth/login", {
      email: $("#loginEmail")?.value,
      password: $("#loginPassword")?.value,
    });
  });
}

if (registerForm) {
  registerForm.addEventListener("submit", (event) => {
    event.preventDefault();
    submitAuth("/api/auth/register", {
      name: $("#registerName")?.value,
      email: $("#registerEmail")?.value,
      password: $("#registerPassword")?.value,
    });
  });
}
