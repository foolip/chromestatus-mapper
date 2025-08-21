document.addEventListener("DOMContentLoaded", () => {
  const template = document.getElementById("feature-template");

  const chromestatusData = document.getElementById("chromestatus-data");
  const webFeaturesData = document.getElementById("web-features-data");
  const confidenceEl = document.getElementById("confidence");
  const notesEl = document.getElementById("notes");
  const progressEl = document.getElementById("progress");

  const acceptBtn = document.getElementById("accept-btn");
  const rejectBtn = document.getElementById("reject-btn");
  const prevBtn = document.getElementById("prev-btn");
  const nextBtn = document.getElementById("next-btn");

  let queue = [];
  let currentIndex = -1;

  async function init() {
    const response = await fetch("/api/queue");
    if (!response.ok) {
      throw new Error(`Failed to fetch review queue: ${response.status}`);
    }
    queue = await response.json();
    if (advanceIndex()) {
      loadMapping();
    } else {
      displayCompletion();
    }
  }

  // Advance currentIndex until review_status is "pending"
  function advanceIndex() {
    while (true) {
      currentIndex++;
      if (currentIndex >= queue.length) {
        return false;
      }
      if (queue[currentIndex].review_status == "pending") {
        return true;
      }
    }
  }

  function displayChromestatusData(feature) {
    if (!feature || feature.error) {
      chromestatusData.textContent = "Error loading feature data.";
      return;
    }

    const clone = template.content.cloneNode(true);

    const nameEl = clone.querySelector(".name a");
    nameEl.href = `https://chromestatus.com/feature/${feature.id}`;
    nameEl.textContent = feature.name;

    clone.querySelector(".desc").textContent = feature.summary;

    const specEl = clone.querySelector(".spec a");
    const specLink = feature.spec_link;
    if (specLink) {
        specEl.href = specLink;
        specEl.textContent = specLink;
    } else {
        specEl.textContent = 'N/A';
    }

    chromestatusData.innerHTML = "";
    chromestatusData.appendChild(clone);
  }

  function displayWebFeatureData(feature) {
    if (!feature || feature.error) {
      webFeaturesData.textContent = "Error loading feature data.";
      return;
    }

    const clone = template.content.cloneNode(true);

    const nameEl = clone.querySelector(".name a");
    nameEl.href = `https://github.com/web-platform-dx/web-features/blob/main/features/${feature.id}.yml`;
    nameEl.textContent = feature.name;

    // Assuming description_html is trusted. If not, this is an XSS risk.
    clone.querySelector(".desc").innerHTML = feature.description_html;

    // TODO: support displaying multiple spec links
    const specLink = Array.isArray(feature.spec) ? feature.spec[0] : feature.spec;
    const specEl = clone.querySelector(".spec a");
    specEl.href = specLink;
    specEl.textContent = specLink;

    webFeaturesData.innerHTML = "";
    webFeaturesData.appendChild(clone);
  }

  async function loadMapping() {
    const mapping = queue[currentIndex];

    // Fetch and display chromestatus data
    try {
      const response = await fetch(
        `/api/chromestatus/${mapping.chromestatus_id}`,
      );
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const featureData = await response.json();
      displayChromestatusData(featureData);
    } catch (e) {
      console.error("Failed to fetch chromestatus data", e);
      displayChromestatusData({ error: e.message });
    }

    // Fetch and display web-features data
    try {
      const response = await fetch(
        `/api/web-features/${mapping.web_features_id}`,
      );
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const featureData = await response.json();
      featureData.id = mapping.web_features_id;
      displayWebFeatureData(featureData);
    } catch (e) {
      console.error("Failed to fetch web-features data", e);
      displayWebFeatureData({ error: e.message });
    }

    confidenceEl.textContent = mapping.confidence;
    notesEl.textContent = mapping.notes || "N/A";

    updateProgress();
  }

  function updateProgress() {
    progressEl.textContent = `Reviewing ${currentIndex + 1} of ${queue.length}`;
  }

  function displayCompletion() {
    document.querySelector(".container").innerHTML =
      "<h1>Review Complete!</h1><p>All mappings have been reviewed. You can close this window.</p>";
  }

  function handleInput(action) {
    if (currentIndex >= queue.length) return;

    if (action == "accept" || action == "reject") {
      const mapping = queue[currentIndex];
      mapping.review_status = action;
      fetch("/api/save", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(mapping),
      }).then(
        (response) => {
          if (!response.ok) {
            console.error(`Error saving review: ${response.status}`);
          }
        },
        (error) => {
          console.error(`Error saving review: ${error}`);
        },
      );

      // Note: UI does not wait for review to be saved before moving on, and
      // errors are not surfaced at all...
      if (advanceIndex()) {
        loadMapping();
      } else {
        displayCompletion();
      }
      return;
    }

    if (action == "prev" && currentIndex > 0) {
      currentIndex--;
      loadMapping();
      return;
    }

    if (action == "next" && currentIndex < queue.length - 1) {
        currentIndex++;
        loadMapping();
        return;
    }
  }

  acceptBtn.addEventListener("click", () => handleInput("accept"));
  rejectBtn.addEventListener("click", () => handleInput("reject"));
  prevBtn.addEventListener("click", () => handleInput("prev"));
  nextBtn.addEventListener("click", () => handleInput("next"));

  document.addEventListener("keydown", (e) => {
    switch (e.key) {
      case "y":
        handleInput("accept");
        break;
      case "n":
        handleInput("reject");
        break;
      case "ArrowLeft":
        handleInput("prev");
        break;
      case "ArrowRight":
        handleInput("next");
        break;
    }
  });

  init();
});
