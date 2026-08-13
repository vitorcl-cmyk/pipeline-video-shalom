// Checagem simples de "está no ar?" para cada card do hub.
// Usa fetch em modo no-cors: nao da pra ler o status/corpo da resposta,
// mas se a promise resolve (em vez de rejeitar/estourar timeout), o
// host respondeu -- suficiente para uma bolinha de status.
(function () {
  "use strict";

  const CHECK_TIMEOUT_MS = 6000;

  function checkOne(el) {
    const url = el.dataset.check;
    el.classList.add("hub-status-checking");

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), CHECK_TIMEOUT_MS);

    fetch(url, { mode: "no-cors", signal: controller.signal, cache: "no-store" })
      .then(() => {
        el.classList.remove("hub-status-checking");
        el.classList.add("hub-status-online");
        el.title = "Respondendo";
      })
      .catch(() => {
        el.classList.remove("hub-status-checking");
        el.classList.add("hub-status-offline");
        el.title = "Sem resposta (rede pode estar bloqueando essa porta)";
      })
      .finally(() => clearTimeout(timer));
  }

  document.querySelectorAll("[data-check]").forEach(checkOne);
})();
