const $ = (id) => document.getElementById(id);

const fmtJSON = (v) => {
  try {
    return JSON.stringify(v, null, 2);
  } catch (e) {
    return String(v);
  }
};

const setText = (id, text) => { $(id).textContent = text; };

const showError = (msg) => {
  const e = $("error");
  e.textContent = msg;
  e.classList.remove("hidden");
};
const clearError = () => $("error").classList.add("hidden");

const runOptimization = async () => {
  clearError();
  const btn = $("run-btn");
  const prompt = $("prompt").value.trim();
  const schemaRaw = $("schema").value.trim();
  const method = $("method").value;

  if (!prompt) {
    showError("Prompt is required.");
    return;
  }

  let schema;
  try {
    schema = JSON.parse(schemaRaw);
  } catch (e) {
    showError("Schema is not valid JSON: " + e.message);
    return;
  }

  btn.disabled = true;
  btn.textContent = "Running…";

  try {
    const resp = await fetch("/api/optimize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt, schema, method }),
    });
    const data = await resp.json();
    if (!resp.ok) {
      showError(data.error || ("HTTP " + resp.status));
      return;
    }
    renderResult(data);
  } catch (e) {
    showError("Network error: " + e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = "Run optimization";
  }
};

const renderResult = (data) => {
  $("empty").classList.add("hidden");
  $("result").classList.remove("hidden");

  setText("tokens-before", data.tokens_before);
  setText("tokens-after",  data.tokens_after);

  const savings = data.token_savings_pct;
  const sign = savings > 0 ? "−" : savings < 0 ? "+" : "";
  setText("savings", `${sign}${Math.abs(savings).toFixed(1)}%`);

  const methodLabel = data.method_requested === "auto"
    ? `${data.method_used} (auto)`
    : data.method_used;
  setText("method-used", methodLabel);
  setText("status",  data.status);
  setText("elapsed", data.elapsed_s + "s");

  setText("decoded", fmtJSON(data.decoded_output));
  setText("toon",    data.toon_output || "—");
  setText("key-map", fmtJSON(data.key_map));
  setText("raw",     data.raw_output || "—");
};

document.addEventListener("DOMContentLoaded", () => {
  $("run-btn").addEventListener("click", runOptimization);
  $("prompt").addEventListener("keydown", (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      runOptimization();
    }
  });
});
