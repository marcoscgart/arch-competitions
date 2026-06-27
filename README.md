# 🏛 Arch Competitions Tracker

Painel de concursos internacionais de Arquitetura e Archviz, atualizado automaticamente via GitHub Actions.

## Como funciona

```
GitHub Actions (todo dia às 08:00 UTC)
    └─ scripts/scraper.py
         ├─ Raspa competitions.archi
         ├─ Raspa Buildner
         └─ Salva competitions.json
              └─ index.html lê o JSON e renderiza o painel
```

## Deploy no GitHub Pages

1. Crie um repositório público no GitHub (ex: `arch-competitions`)
2. Faça upload de todos os arquivos deste projeto
3. Vá em **Settings → Pages**
4. Em **Source**, selecione `Deploy from a branch`
5. Escolha `main` e pasta `/ (root)` → **Save**
6. Aguarde ~1 min. Seu site estará em:
   `https://<seu-usuario>.github.io/arch-competitions`

## Rodar o scraper manualmente

Na aba **Actions** do repositório, clique em **Atualizar concursos** → **Run workflow**.

## Adicionar concursos manualmente

Edite `competitions.json` e adicione um objeto no array `competitions`:

```json
{
  "title": "Nome do concurso",
  "org": "Organizador",
  "type": "archviz",
  "deadline": "DD/MM/YYYY",
  "registration": "DD/MM/YYYY",
  "prize": "€5,000",
  "location": "Concept",
  "lang": "English",
  "url": "https://...",
  "desc": "Descrição curta do concurso.",
  "source": "manual"
}
```

**Tipos válidos:** `archviz` · `conceito` · `estudantil` · `open`

## Adicionar mais fontes de scraping

Edite `scripts/scraper.py` e adicione uma função similar a `scrape_competitions_archi()`,
chamando-a dentro de `main()`. O formato de saída deve seguir o mesmo schema do JSON.

## Estrutura do projeto

```
arch-competitions/
├── index.html              # Painel visual
├── competitions.json       # Dados dos concursos (gerado pelo scraper)
├── scripts/
│   └── scraper.py          # Script de coleta
└── .github/
    └── workflows/
        └── scrape.yml      # Agendamento automático (cron diário)
```
