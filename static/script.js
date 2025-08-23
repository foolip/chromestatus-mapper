document.addEventListener("DOMContentLoaded", () => {
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
    advanceIndex();
    await loadMapping();
  }

  // Advance currentIndex until review_status is "pending"
  function advanceIndex() {
    while (true) {
      currentIndex++;
      if (currentIndex >= queue.length) {
        currentIndex = queue.length - 1;
        return;
      }
      if (queue[currentIndex].review_status == "pending") {
        return;
      }
    }
  }

  // Update el.innerHTML with HTML fragment from URL
  async function updateData(el, url) {
    try {
        const response = await fetch(url);
        if (response.ok) {
            const html = await response.text();
            el.innerHTML = html;
            return;
        }
    } catch {}

    el.textContent = 'Error';
  }

  async function loadMapping() {
    const mapping = queue[currentIndex];

    // Fetch and update the two views in parallel.
    await Promise.all([
        updateData(chromestatusData, `/fragment/chromestatus/${mapping.chromestatus_id}`),
        updateData(webFeaturesData, `/fragment/web-features/${mapping.web_features_id}`),
    ]);

    confidenceEl.textContent = mapping.confidence;
    notesEl.textContent = mapping.notes || "N/A";

    updateProgress();
  }

  function updateProgress() {
    const done = !queue.some((mapping) => mapping.review_status == "pending");
    if (done) {
      progressEl.textContent = `Reviewed all ${queue.length} 🎉`;
    } else {
      progressEl.textContent = `Reviewing ${currentIndex + 1} of ${queue.length}`;
    }
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
      advanceIndex();
      loadMapping();
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
