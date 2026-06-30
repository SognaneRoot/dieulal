const urlInput = document.getElementById("url");
const pasteBtn = document.getElementById("paste-btn");
const fetchBtn = document.getElementById("fetch-btn");
const statusEl = document.getElementById("status");
const stub = document.getElementById("stub");
const stubFilename = document.getElementById("stub-filename");
const stubLink = document.getElementById("stub-link");

function setStatus(message, kind) {
  statusEl.textContent = message;
  statusEl.className = "status" + (kind ? ` status--${kind}` : "");
}

pasteBtn.addEventListener("click", async () => {
  try {
    const text = await navigator.clipboard.readText();
    if (text) {
      urlInput.value = text.trim();
      urlInput.focus();
    }
  } catch (err) {
    setStatus("Impossible de lire le presse-papiers, collez manuellement.", "error");
  }
});

fetchBtn.addEventListener("click", async () => {
  const url = urlInput.value.trim();
  const audioOnly = document.getElementById("mode-audio").checked;

  if (!url) {
    setStatus("Collez d'abord un lien.", "error");
    return;
  }

  stub.classList.add("stub--hidden");
  fetchBtn.disabled = true;
  setStatus("Récupération en cours… ça peut prendre une minute.");

  try {
    const res = await fetch("/api/download", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, audio_only: audioOnly }),
    });

    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      setStatus(data.error || "Échec de la récupération.", "error");
      return;
    }

    const blob = await res.blob();
    const disposition = res.headers.get("Content-Disposition") || "";
    const match = disposition.match(/filename="?([^"]+)"?/);
    const filename = match ? match[1] : "video";
    const ffmpegAvailable = res.headers.get("X-Ffmpeg-Available") === "1";

    const blobUrl = URL.createObjectURL(blob);
    stubFilename.textContent = filename;
    stubLink.href = blobUrl;
    stubLink.download = filename;
    stub.classList.remove("stub--hidden");

    if (ffmpegAvailable) {
      setStatus("Prêt. Touchez « Télécharger » ci-dessous.", "ok");
    } else {
      setStatus(
        "Prêt (qualité standard — installez ffmpeg sur le serveur pour la meilleure qualité).",
        "ok"
      );
    }
  } catch (err) {
    setStatus("Erreur réseau, réessayez.", "error");
  } finally {
    fetchBtn.disabled = false;
  }
});

urlInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") fetchBtn.click();
});
