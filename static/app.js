/* RÉUSSITE SCIENCES - APPLICATION */

document.addEventListener("DOMContentLoaded", () => {
  console.log("Réussite Sciences est prêt !");

  const buttons = document.querySelectorAll("[data-action]");

  buttons.forEach((button) => {
    button.addEventListener("click", () => {
      const action = button.dataset.action;
      console.log("Action :", action);
    });
  });
});
