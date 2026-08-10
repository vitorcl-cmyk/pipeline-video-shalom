/**
 * Shalom Showcase Widget -- vitrine reutilizavel de imoveis.
 *
 * Componente vanilla JS (sem dependencias, sem build step) que renderiza
 * cards de imoveis (foto, bairro, tipo, valor, link) a partir de um JSON
 * estatico gerado por scraping periodico (ver /scraper).
 *
 * Feito pra ser plugado em qualquer pagina HTML: este projeto (Shalom
 * Reels), o app de video e a Vitrini Imoveis. Basta incluir o CSS/JS e
 * marcar um container com `data-shalom-showcase`.
 *
 * Uso declarativo:
 *   <div data-shalom-showcase
 *        data-json-url="/listings.json"
 *        data-bairro="Boa Viagem"
 *        data-tipo="Apartamento"
 *        data-limit="6"></div>
 *
 * Uso programatico:
 *   const widget = ShalomShowcase.mount(el, { jsonUrl: "/listings.json" });
 *   widget.setBairro("Boa Viagem");   // filtro contextual (ex.: bairro
 *                                     // pesquisado numa ferramenta de ITBI)
 *
 * Atualizar todos os widgets montados na pagina de uma vez (util quando o
 * host nao guarda a referencia da instancia):
 *   ShalomShowcase.setBairroGlobal("Boa Viagem");
 *
 * O filtro inicial tambem pode vir da URL: ?bairro=Boa+Viagem
 */
(function (global) {
  "use strict";

  var instances = [];

  // Mapa de acentuacao pt-BR pra comparacao de bairro/tipo tolerante a
  // grafia (o texto raspado do site pode nao bater 100% com o texto vindo
  // da ferramenta de ITBI).
  var ACCENT_MAP = {
    "á": "a", "à": "a", "ã": "a", "â": "a", "ä": "a",
    "é": "e", "è": "e", "ê": "e", "ë": "e",
    "í": "i", "ì": "i", "î": "i", "ï": "i",
    "ó": "o", "ò": "o", "õ": "o", "ô": "o", "ö": "o",
    "ú": "u", "ù": "u", "û": "u", "ü": "u",
    "ç": "c", "ñ": "n"
  };
  var ACCENT_RE = new RegExp("[" + Object.keys(ACCENT_MAP).join("") + "]", "g");

  function normalize(str) {
    return (str || "")
      .toString()
      .trim()
      .toLowerCase()
      .replace(ACCENT_RE, function (ch) {
        return ACCENT_MAP[ch] || ch;
      });
  }

  function formatValor(listing) {
    if (listing.valor_formatado) return listing.valor_formatado;
    var n = Number(listing.valor);
    if (!isFinite(n) || n <= 0) return "Consulte";
    try {
      return n.toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
    } catch (e) {
      return "R$ " + n;
    }
  }

  function readUrlBairro() {
    try {
      var params = new URLSearchParams(global.location.search);
      return params.get("bairro") || null;
    } catch (e) {
      return null;
    }
  }

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function Widget(container, options) {
    this.container = container;
    this.options = Object.assign(
      {
        jsonUrl: container.dataset.jsonUrl || "listings.json",
        bairro: container.dataset.bairro || readUrlBairro() || "",
        tipo: container.dataset.tipo || "",
        limit: container.dataset.limit ? parseInt(container.dataset.limit, 10) : 0,
        emptyMessage: container.dataset.emptyMessage || "Nenhum imovel encontrado para esse filtro.",
        errorMessage: container.dataset.errorMessage || "Nao foi possivel carregar a vitrine no momento.",
        title: container.dataset.title || ""
      },
      options || {}
    );
    this.listings = null;
    this.container.classList.add("shalom-showcase");
    instances.push(this);
    this.refresh();
  }

  Widget.prototype.setBairro = function (bairro) {
    this.options.bairro = bairro || "";
    this.render();
  };

  Widget.prototype.setTipo = function (tipo) {
    this.options.tipo = tipo || "";
    this.render();
  };

  Widget.prototype.destroy = function () {
    var idx = instances.indexOf(this);
    if (idx >= 0) instances.splice(idx, 1);
    this.container.innerHTML = "";
    this.container.classList.remove("shalom-showcase");
  };

  Widget.prototype.refresh = function () {
    var self = this;
    self.container.innerHTML = '<div class="shalom-showcase-loading">Carregando imoveis...</div>';

    return fetch(self.options.jsonUrl, { cache: "no-store" })
      .then(function (res) {
        if (!res.ok) throw new Error("HTTP " + res.status);
        return res.json();
      })
      .then(function (data) {
        self.listings = Array.isArray(data) ? data : data.listings || [];
        self.render();
      })
      .catch(function (err) {
        self.listings = [];
        self.container.innerHTML =
          '<div class="shalom-showcase-error">' + self.options.errorMessage + "</div>";
        if (global.console) console.error("[ShalomShowcase] falha ao carregar " + self.options.jsonUrl, err);
      });
  };

  Widget.prototype._filtered = function () {
    var listings = this.listings || [];
    var bairro = normalize(this.options.bairro);
    var tipo = normalize(this.options.tipo);

    var filtered = listings.filter(function (item) {
      var matchesBairro = !bairro || normalize(item.bairro).indexOf(bairro) !== -1;
      var matchesTipo = !tipo || normalize(item.tipo) === tipo;
      return matchesBairro && matchesTipo;
    });

    if (this.options.limit) filtered = filtered.slice(0, this.options.limit);
    return filtered;
  };

  Widget.prototype._card = function (listing) {
    var card = el("a", "shalom-showcase-card");
    card.href = listing.link || "#";
    card.target = "_blank";
    card.rel = "noopener noreferrer";

    var figure = el("div", "shalom-showcase-photo");
    if (listing.photo) {
      var img = document.createElement("img");
      img.src = listing.photo;
      img.alt = listing.title || listing.bairro || "Imovel";
      img.loading = "lazy";
      figure.appendChild(img);
    }
    card.appendChild(figure);

    var body = el("div", "shalom-showcase-body");

    var badges = el("div", "shalom-showcase-badges");
    if (listing.tipo) badges.appendChild(el("span", "shalom-showcase-badge", listing.tipo));
    if (listing.bairro) badges.appendChild(el("span", "shalom-showcase-badge shalom-showcase-badge-bairro", listing.bairro));
    body.appendChild(badges);

    if (listing.title) body.appendChild(el("h3", "shalom-showcase-title", listing.title));
    body.appendChild(el("p", "shalom-showcase-valor", formatValor(listing)));

    card.appendChild(body);
    return card;
  };

  Widget.prototype.render = function () {
    var listings = this._filtered();
    this.container.innerHTML = "";

    if (this.options.title) {
      this.container.appendChild(el("h2", "shalom-showcase-heading", this.options.title));
    }

    if (!listings.length) {
      this.container.appendChild(el("div", "shalom-showcase-empty", this.options.emptyMessage));
      return;
    }

    var grid = el("div", "shalom-showcase-grid");
    var self = this;
    listings.forEach(function (listing) {
      grid.appendChild(self._card(listing));
    });
    this.container.appendChild(grid);
  };

  function mount(container, options) {
    if (typeof container === "string") container = document.querySelector(container);
    if (!container) throw new Error("[ShalomShowcase] container nao encontrado");
    return new Widget(container, options);
  }

  function autoInit() {
    document.querySelectorAll("[data-shalom-showcase]").forEach(function (container) {
      if (!container.dataset.shalomShowcaseMounted) {
        container.dataset.shalomShowcaseMounted = "true";
        mount(container);
      }
    });
  }

  function setBairroGlobal(bairro) {
    instances.forEach(function (instance) {
      instance.setBairro(bairro);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", autoInit);
  } else {
    autoInit();
  }

  global.ShalomShowcase = {
    mount: mount,
    autoInit: autoInit,
    setBairroGlobal: setBairroGlobal
  };
})(window);
