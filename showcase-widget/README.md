# Shalom Showcase Widget

Vitrine de imóveis reutilizável: cards com foto, bairro, tipo, valor e link,
alimentados por um JSON estático (gerado pelo scraper em [`/scraper`](../scraper)).
Vanilla JS, sem dependências e sem build step — pensado pra ser incluído em
qualquer página HTML: este projeto (Shalom Reels), o app de vídeo e a
Vitrini Imóveis.

## Instalação

Copie os dois arquivos pro app que vai usar o widget e inclua no HTML:

```html
<link rel="stylesheet" href="shalom-showcase.css" />
<script src="shalom-showcase.js"></script>
```

## Uso declarativo (auto-init)

```html
<div
  data-shalom-showcase
  data-json-url="/listings.json"
  data-title="Imóveis em destaque"
  data-limit="6"
></div>
```

Qualquer elemento `[data-shalom-showcase]` presente na página é montado
automaticamente no `DOMContentLoaded`.

Atributos `data-*` aceitos: `json-url`, `bairro`, `tipo`, `limit`, `title`,
`empty-message`, `error-message`.

## Uso programático

```js
const widget = ShalomShowcase.mount("#vitrine", {
  jsonUrl: "/listings.json",
  title: "Imóveis no bairro pesquisado",
});

widget.setBairro("Boa Viagem");
widget.setTipo("Apartamento");
widget.destroy(); // remove e desmonta
```

## Filtro contextual por bairro (integração com ITBI)

O caso de uso principal: uma ferramenta de consulta de ITBI pesquisa um
bairro, e a vitrine mostra só os imóveis daquele bairro. Três formas de
alimentar esse contexto, do mais simples ao mais integrado:

1. **Link direto** — a ferramenta de ITBI só precisa linkar/redirecionar
   pra página que tem o widget com `?bairro=Boa+Viagem` na URL. O widget lê
   o parâmetro sozinho no mount.
2. **Global, sem guardar referência** — se a ferramenta de ITBI e o widget
   estão na mesma página (ex.: embutido num painel), chame
   `ShalomShowcase.setBairroGlobal("Boa Viagem")` depois da busca. Atualiza
   todos os widgets montados na página.
3. **Referência direta** — quem chamou `ShalomShowcase.mount(...)` guarda o
   retorno e chama `widget.setBairro(...)` quando quiser.

A comparação de bairro é por substring, sem distinção de maiúsculas/acentos
(`normalize()` no `shalom-showcase.js`), já que o texto raspado do site pode
não bater exatamente com o texto vindo da ferramenta de ITBI.

## Schema do JSON

O widget aceita tanto um array quanto um objeto com a chave `listings`
(o segundo é o formato produzido pelo scraper, que também carrega metadados
como `generated_at`):

```json
{
  "generated_at": "2026-08-10T12:00:00Z",
  "source": "shalomconsultoria.com.br",
  "listings": [
    {
      "id": "apto-boa-viagem-123",
      "title": "Apartamento 3 quartos com vista mar",
      "photo": "https://www.shalomconsultoria.com.br/fotos/123-capa.jpg",
      "bairro": "Boa Viagem",
      "tipo": "Apartamento",
      "valor": 850000,
      "valor_formatado": "R$ 850.000",
      "link": "https://www.shalomconsultoria.com.br/imovel/123"
    }
  ]
}
```

Campos obrigatórios pro card renderizar de forma útil: `bairro`, `tipo`,
`valor` (ou `valor_formatado`), `link`. `photo` e `title` são opcionais mas
recomendados. Campos extras no JSON são ignorados — o schema pode evoluir
sem quebrar o widget.

## Reuso em outros projetos

Este diretório é deliberadamente autocontido (2 arquivos, sem imports de
outras partes do repo) pra poder ser copiado ou publicado como pacote
separado depois. Ao plugar no app de vídeo ou na Vitrini Imóveis:

- Sirva o `listings.json` gerado pelo scraper como arquivo estático (mesmo
  domínio evita CORS; se for cross-origin, garanta que o servidor libera
  `Access-Control-Allow-Origin` pra leitura do JSON).
- Ajuste as variáveis CSS (`--shalom-showcase-accent`, `--card-bg`,
  `--card-border`, `--text-color`, `--text-muted`) pra casar com o tema de
  cada app, ou deixe os fallbacks default.
