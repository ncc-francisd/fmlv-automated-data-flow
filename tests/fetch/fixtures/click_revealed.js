// External on purpose — see the comment in click_revealed.html.
document.getElementById("technical").addEventListener("click", async () => {
  const response = await fetch("spec_payload.json");
  const spec = await response.json();
  document.getElementById("panel").textContent = spec.line;
});

document.getElementById("decoy").addEventListener("click", () => {
  document.getElementById("panel").textContent = ["the", "wrong", "panel"].join(" ");
});
