# Estudo de viabilidade — Busca de imóveis por região no mapa / raio, com filtros

Data: 2026-08-16

## 1. Pedido

Avaliar a viabilidade de uma funcionalidade que permita pesquisar imóveis anunciados
(com endereço completo) dentro de:

- uma região desenhada livremente no mapa (polígono), ou
- um nome de rua + raio de distância,

com filtros (tipo, preço, quartos, área etc.), cruzando anúncios de portais como
**ImovelWeb**, **ZAP Imóveis**, **Chaves na Mão**, **OLX** e similares.

Esse repositório hoje contém o "Reels Imobiliário" (gerador de vídeos a partir de
fotos de imóveis) e faz parte de um conjunto maior de apps da Shalom (hub, admin,
etc. — ver outros branches do projeto). A funcionalidade pedida seria um **novo
módulo**, não uma extensão do pipeline de vídeo.

## 2. Resumo executivo

| Parte da ideia | Viabilidade |
|---|---|
| Busca por região desenhada no mapa (polígono) ou rua+raio, com filtros, **sobre uma base de imóveis própria** (ex.: os imóveis captados/anunciados pela Shalom) | **Alta.** Solução padrão (PostGIS + geocoding + Leaflet/Mapbox), poucas semanas de trabalho. |
| Agregar automaticamente anúncios do **ImovelWeb, ZAP, Chaves na Mão, OLX** via scraping para alimentar essa busca | **Baixa/arriscada.** Tecnicamente possível, mas contraria os Termos de Uso das quatro plataformas, tem alto custo de manutenção (anti-bot) e risco jurídico crescente no Brasil (LGPD/ANPD), além de essas mesmas empresas venderem esse dado agregado como produto (DataZap). |
| Agregar dados desses portais via **integração oficial** | **Média, mas errada direção.** As APIs/feeds XML que essas empresas oferecem são para *publicar* seus próprios anúncios nos portais (sentido inverso ao que foi pedido), não para consultar/baixar o catálogo inteiro de terceiros. Não há API pública de busca agregada. |

**Recomendação:** construir a funcionalidade (mapa com polígono, rua+raio, filtros)
sobre a **base de imóveis própria da Shalom**. Isso entrega valor real, é 100%
legal e reaproveita o padrão de arquitetura que também serviria, no futuro, para
uma eventual camada de agregação via parcerias oficiais — não via scraping direto
dos 4 portais concorrentes.

## 3. Por que scraping dos 4 portais é a parte problemática

### 3.1 Termos de uso proíbem explicitamente

- Grupo OLX (dono de **OLX**, **ZAP Imóveis** e **VivaReal**) tem termos que proíbem
  uso de robôs/crawlers e cópia/reprodução de conteúdo do site para uso em outro
  lugar sem autorização prévia ([Termos e Condições OLX Brasil](https://assets.zap.com.br/publicidade/termos-e-condicoes-olx-brasil-incorporadoras.pdf),
  [Termos Grupo Zap](https://www.grupozap.com/v1.0.0/terms.html)).
- O próprio Grupo OLX **vende** esse tipo de dado agregado como produto próprio, o
  "**DataZap**" ([Termos de uso DataZap](https://grupoolx.com.br/datazap-termos-de-uso)) —
  ou seja, um agregador de anúncios via scraping estaria replicando (sem
  autorização) um produto que a empresa já comercializa, o que aumenta a chance de
  ação de bloqueio técnico e/ou notificação extrajudicial/judicial.
- Existem projetos open-source e serviços comerciais (Apify) fazendo scraping
  desses portais hoje, o que mostra que é *tecnicamente* possível, mas não indica
  que seja seguro para uso comercial contínuo — são projetos pessoais/pontuais,
  não produtos com SLA.

### 3.2 Nenhum dos 4 portais oferece API pública de *busca* agregada

O que existe é o oposto do que precisamos: APIs/feeds XML/JSON para que uma
**imobiliária publique seus próprios imóveis** nesses portais automaticamente
(ex.: [API de importação de anúncios da OLX](https://developers.olx.com.br/anuncio/api/home.html),
[integração XML do ImovelWeb/Navent](https://open-docs.navent.com/bra/pase-a-produccion-xml/)).
Não há endpoint documentado para "buscar todos os imóveis à venda num polígono"
across portais — isso só existe internamente, como produto pago (DataZap).

### 3.3 Barreiras técnicas anti-scraping

- Cloudflare/anti-bot, rate limiting, necessidade de renderizar JS (Playwright em
  vez de simples requests), captchas.
- Layout muda com frequência → scraper quebra e exige manutenção contínua (custo
  recorrente, não um trabalho de "uma vez só").
- Seria necessário rotacionar IPs/proxies residenciais para não ser bloqueado —
  custo mensal e mais uma camada de risco (uso de proxy para burlar bloqueio é
  visto como agravante em disputas de scraping).

### 3.4 Risco jurídico (Brasil, LGPD/ANPD)

- Extrair **dados públicos de negócio** (preço, metragem, características do
  imóvel) tende a ser tratado como legal na jurisprudência, mas **dados pessoais
  visíveis publicamente continuam sendo dados pessoais** sob a LGPD — e anúncios
  de imóvel costumam trazer nome do anunciante/corretor, telefone, CRECI etc.
  Isso exige base legal, finalidade compatível e transparência (art. 7º, §3º da
  LGPD).
- A ANPD colocou **raspagem de dados (data scraping)** no topo da agenda de
  fiscalização para 2025–2026. Ou seja, é uma área sob escrutínio ativo agora,
  não um risco teórico e distante.
- Violação de Termos de Uso não é automaticamente crime, mas abre caminho para
  notificação extrajudicial, bloqueio de acesso e ação cível por concorrência
  desleal/uso não autorizado de base de dados, especialmente vindo de outra
  empresa do setor imobiliário.

**Conclusão dessa parte:** dá para montar um scraper hoje (existe código aberto
fazendo isso), mas não é uma base sólida para um produto comercial contínuo da
Shalom — o custo de manutenção + o risco jurídico/reputacional superam o ganho,
ainda mais quando o objetivo é justamente ser uma imobiliária/prestador de
serviço no mesmo mercado dessas plataformas.

## 4. O que é totalmente viável: busca geográfica sobre base própria

Essa é a parte "de verdade" da funcionalidade — desenhar região no mapa, buscar
por rua+raio, filtrar — e é um problema resolvido, com stack madura.

### 4.1 Modelo de dados

Cada imóvel precisa de:

- endereço completo (rua, número, bairro, cidade, UF, CEP);
- coordenada geográfica (`latitude`/`longitude`), obtida por **geocoding** do
  endereço no cadastro (uma vez, ao criar/editar o imóvel);
- atributos para filtro: tipo, preço, área, quartos, vagas, etc.

Banco recomendado: **PostgreSQL + extensão PostGIS**, que dá suporte nativo a:

- `ST_Contains(poligono, ponto)` → filtro por região desenhada no mapa;
- `ST_DWithin(ponto_rua, ponto_imovel, raio_em_metros)` → filtro por rua + raio;
- índice espacial (`GIST`) para consultas rápidas mesmo com muitos imóveis.

O backend atual já usa SQLAlchemy (`backend/app/database.py`, `models.py`) — dá
para adicionar essas tabelas/colunas no mesmo banco ou em um serviço novo, com
`GeoAlchemy2` para expor os tipos geométricos ao SQLAlchemy.

### 4.2 Geocoding (endereço → coordenada)

Opções:

| Provedor | Custo | Qualidade no Brasil |
|---|---|---|
| Google Geocoding API | Pago por requisição (créditos mensais grátis) | Ótima, referência de mercado |
| Mapbox Geocoding | Pago, plano free generoso | Boa |
| Nominatim (OpenStreetMap) | Gratuito, self-host ou uso público limitado (1 req/s) | Razoável, pode falhar com endereço incompleto |

Como o geocoding roda **uma vez por imóvel cadastrado** (não a cada busca), o
volume é baixo — mesmo a opção paga sai barata.

### 4.3 Desenhar região no mapa

- **Leaflet** + plugin `Leaflet.draw` (gratuito, open-source) ou
- **Mapbox GL JS** + `mapbox-gl-draw` (mais bonito, tem camada free).

O usuário desenha o polígono → front converte para GeoJSON → envia ao backend →
query `ST_Contains`.

### 4.4 Busca por rua + raio

- Geocodificar o texto da rua digitada (mesmo serviço do item 4.2) → obter ponto
  central → consulta `ST_DWithin` com o raio escolhido (slider de km).

### 4.5 Filtros

Filtros convencionais (tipo, faixa de preço, quartos, área, etc.) são apenas
cláusulas `WHERE` adicionais na mesma query — sem complexidade extra.

### 4.6 Esforço estimado (MVP sobre base própria)

| Etapa | Estimativa |
|---|---|
| Modelagem de dados + geocoding no cadastro de imóvel | 3–5 dias |
| Endpoint de busca (polígono e rua+raio) com filtros, PostGIS | 4–6 dias |
| UI do mapa (desenhar região, busca por rua+raio, filtros, lista de resultados) | 6–8 dias |
| Testes, ajustes de UX, deploy | 3–4 dias |
| **Total** | **~3 a 4 semanas**, 1 desenvolvedor full-stack |

Isso assume que já existe (ou existirá em paralelo) um cadastro de imóveis com
endereço — se esse cadastro ainda não existe em nenhum dos outros apps da Shalom,
precisa entrar no escopo também.

## 5. Caminho recomendado para "trazer também os outros portais"

Se o objetivo de negócio é mostrar ao usuário final imóveis de mercado além dos
da própria Shalom, os caminhos **sustentáveis**, em ordem de preferência:

1. **Cadastro manual/curado**: o corretor cola o link do anúncio (ImovelWeb, ZAP,
   OLX, Chaves na Mão) e o sistema extrai endereço/preço via *parsing* pontual
   sob demanda (não crawling em massa), similar a um "salvar favorito" — reduz
   drasticamente volume e risco, e ainda é útil (curadoria de imóveis de
   interesse do cliente).
2. **Parceria oficial** com algum desses grupos (ou provedores de dados como o
   próprio DataZap) para licenciar acesso a um feed agregado — caminho comercial,
   não técnico, mas é o único que remove o risco jurídico por completo.
3. **Descartar a agregação automática dos concorrentes** e focar 100% na base
   própria da Shalom + eventualmente outras imobiliárias parceiras que topem
   compartilhar feed XML (o mesmo padrão que elas já usam para publicar no ZAP/
   ImovelWeb pode, em tese, ser reaproveitado para alimentar um portal próprio,
   com autorização explícita da imobiliária de origem).

O que eu **não recomendo** é construir scraping automatizado e recorrente dos 4
portais como base de um produto comercial da própria Shalom.

## 6. Próximos passos sugeridos

1. Confirmar se já existe (em outro app da Shalom) um cadastro de imóveis com
   endereço — isso define se o MVP começa do zero ou já tem dado para consultar.
2. Decidir o provedor de mapa/geocoding (Google vs Mapbox vs OSM/Nominatim),
   considerando custo esperado de volume de imóveis.
3. Implementar o MVP descrito na seção 4 (busca geográfica sobre base própria).
4. Se a agregação de outros portais continuar sendo prioridade, tratar como
   iniciativa separada, começando pela opção 1 da seção 5 (curadoria manual de
   links), não por scraping em massa.
