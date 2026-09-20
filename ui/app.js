const nodes = ["news_search", "market_data", "universe", "fundamental", "technical", "scoring"];
const form = document.querySelector("#researchForm");
const button = form.querySelector("button");
const message = document.querySelector("#formMessage");
const log = document.querySelector("#activityLog span:last-child");
const state = document.querySelector("#runState");
const connectionLabel = document.querySelector("#connectionLabel");
const resultsTable = document.querySelector("#resultsTable");
const resultsEmpty = document.querySelector("#resultsEmpty");
const resultCount = document.querySelector("#resultCount");
const agentOutput = document.querySelector("#agentOutput");
let socket;

function setNode(stage, mode) {
  const node = document.querySelector(`[data-node="${stage}"]`);
  if (!node) return;
  node.classList.remove("active", "done");
  if (mode) node.classList.add(mode);
  const index = nodes.indexOf(stage);
  nodes.slice(0, index).forEach(name => document.querySelector(`[data-node="${name}"]`)?.classList.add("done"));
}

function renderResults(data) {
  const ranking = data.ranking || [];
  resultCount.textContent = `${ranking.length} candidate${ranking.length === 1 ? "" : "s"}`;
  if (!ranking.length) {
    resultsEmpty.classList.remove("hidden");
    resultsTable.classList.add("hidden");
    return;
  }
  resultsEmpty.classList.add("hidden");
  resultsTable.classList.remove("hidden");
  resultsTable.innerHTML = ranking.map((item, index) => {
    const score = Number(item.final_score || 0).toFixed(1);
    const catalyst = item.catalysts?.[0] || "Signal review complete";
    return `<div class="result-row"><span class="rank">0${index + 1}</span><span><span class="ticker">${item.ticker || "--"}</span><br><span class="signal">${catalyst}</span></span><span><span class="score">${score}</span><br><span class="score-label">final score</span></span><span class="signal"><b>${Number(item.technical_score || 0).toFixed(0)}</b> technical<br><b>${Number(item.fundamental_score || 0).toFixed(0)}</b> fundamental</span></div>`;
  }).join("") + (data.errors?.length ? `<div class="error-row">${data.errors.length} source note${data.errors.length === 1 ? "" : "s"}: ${data.errors[0]}</div>` : "");
}

function renderAgent(stage, data) {
  if (!data) return;
  agentOutput.querySelector(".empty-state")?.remove();
  const labels = { news_search: "News search", market_data: "Market data", universe: "Universe", fundamental: "Fundamental", technical: "Technical", scoring: "Scoring" };
  let content = "";
  if (stage === "research") content = `<div class="agent-value">${(data.candidate_symbols || []).length}</div><div class="agent-meta">symbols found<br>${data.sources || 0} sources scanned<br>${(data.candidate_symbols || []).join(" · ") || "No symbols"}</div>`;
  if (stage === "universe") content = `<div class="agent-value">${(data.candidates || []).length}</div><div class="agent-meta">candidates selected<br>${(data.candidates || []).join(" · ") || "No candidates"}</div>`;
  if (stage === "news_search") content = `<div class="agent-value">${(data.results || []).reduce((count, item) => count + (item.events || []).length, 0)}</div><div class="agent-meta">events found<br>${(data.results || []).map(item => `${item.symbol}: ${item.material_catalyst_found ? "catalyst" : "no material catalyst"}`).join("<br>") || "No news output"}</div>`;
  if (stage === "fundamental") content = `<div class="agent-meta">${(data.analysis || []).map(item => `${item.ticker}: local price <b>${item.metrics?.current_price != null ? Number(item.metrics.current_price).toFixed(2) : "unavailable"}</b>`).join("<br>") || "No fundamental output"}</div>`;
  if (stage === "technical") content = `<div class="agent-meta">${(data.analysis || []).map(item => `${item.ticker}: close ${Number(item.indicators?.latest_close || 0).toFixed(2)}<br>score ${Number(item.score || 0).toFixed(0)}`).join("<br><br>") || "No technical output"}</div>`;
  if (stage === "scoring") content = `<div class="agent-meta">${(data.ranking || []).slice(0, 5).map((item, index) => `${index + 1}. ${item.ticker} <b>${Number(item.final_score || 0).toFixed(1)}</b>`).join("<br>") || "No ranking"}</div>`;
  let card = document.querySelector(`[data-agent="${stage}"]`);
  if (!card) {
    card = document.createElement("div"); card.className = "agent-card"; card.dataset.agent = stage;
    agentOutput.appendChild(card);
  }
  card.classList.remove("active"); card.classList.add("complete");
  card.innerHTML = `<span class="section-kicker">${stage}</span><h3>${labels[stage]}</h3>${content}`;
}

function connect() {
  socket = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/api/ws`);
  socket.onopen = () => { connectionLabel.textContent = "Socket connected"; };
  socket.onmessage = event => {
    const payload = JSON.parse(event.data);
    if (payload.type === "started") {
      state.textContent = "RUNNING"; state.className = "run-state live"; message.textContent = "The graph is moving through its nodes."; log.textContent = "Workflow started.";
    } else if (payload.type === "stage") {
      setNode(payload.stage, "active"); log.textContent = payload.message; message.textContent = `${payload.stage} node is active.`; renderAgent(payload.stage, payload.data);
    } else if (payload.type === "keepalive") {
      log.textContent = "Still working — waiting on external market sources.";
    } else if (payload.type === "complete") {
      nodes.forEach(node => setNode(node, "done")); state.textContent = "COMPLETE"; state.className = "run-state done"; message.textContent = "Research graph completed."; log.textContent = "Ranked output is ready."; renderResults(payload.data);
      button.disabled = false; button.querySelector("span").textContent = "Run research graph";
    } else if (payload.type === "error") {
      state.textContent = "ERROR"; state.className = "run-state done"; message.textContent = payload.message; log.textContent = "The graph could not start."; button.disabled = false;
    }
  };
  socket.onerror = () => { connectionLabel.textContent = "Socket unavailable"; message.textContent = "Could not reach the API. Is Uvicorn running?"; button.disabled = false; };
  socket.onclose = () => { if (connectionLabel.textContent !== "Socket unavailable") connectionLabel.textContent = "API ready"; };
}

form.addEventListener("submit", event => {
  event.preventDefault();
  if (socket && socket.readyState === WebSocket.OPEN) socket.close();
  nodes.forEach(node => setNode(node, null));
  agentOutput.innerHTML = '<div class="empty-state"><span class="empty-number">--</span><span>Waiting for agent output.</span></div>';
  resultsTable.classList.add("hidden"); resultsEmpty.classList.remove("hidden"); resultCount.textContent = "0 candidates";
  button.disabled = true; button.querySelector("span").textContent = "Running graph..."; state.textContent = "CONNECTING"; state.className = "run-state live";
  connect();
  socket.addEventListener("open", () => socket.send(JSON.stringify({ objective: document.querySelector("#objective").value, market: document.querySelector("#market").value, universe: "equity", research_urls: [], max_candidates: Number(document.querySelector("#limit").value) })), { once: true });
});

connect();
