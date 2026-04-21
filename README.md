# DC Neighborhood Compare

Static Astro site for comparing popular Washington, DC neighborhoods for college graduates moving to the city.

## Architecture

The app stays fully static:

```text
Python script -> data/neighborhoods.json -> Astro frontend
```

There is no backend API. The Python script precomputes metrics from OpenStreetMap and writes them into JSON that Astro reads at build time.

## Project Structure

```text
/
|-- .github/
|   `-- workflows/
|       |-- deploy.yml
|       `-- update-data.yml
|-- data/
|   `-- neighborhoods.json
|-- scripts/
|   `-- build_neighborhood_data.py
|-- src/
|   |-- components/
|   |   |-- Comparison.astro
|   |   |-- InfoPanel.astro
|   |   `-- MapSection.astro
|   `-- pages/
|       `-- index.astro
|-- astro.config.mjs
`-- package.json
```

## Local Setup

### 1. Install frontend dependencies

```sh
npm install
```

### 2. Optional: build fresh neighborhood data

Create a Python environment and install OSM tooling:

```sh
python -m venv .venv
.venv\Scripts\activate
pip install osmnx pandas geopandas shapely pyproj
python scripts/build_neighborhood_data.py
```

Notes:
- `data/neighborhoods.json` is already checked in so the site works immediately.
- The Python script uses neighborhood center points plus a radius instead of exact official boundaries.
- Rent values are still curated estimates in the current script.

### 3. Run the Astro app

```sh
npm run dev
```

Then open `http://localhost:4321`.

### 4. Create a production build

```sh
npm run build
npm run preview
```

## GitHub Pages Hosting

This repo is configured for a project page at:

```text
https://colesmacmillan.github.io/dc-neighborhood-compare
```

If you rename the repository, update `base` in `astro.config.mjs` to match the new repo name.

## Data Refresh

The site shows a visible `Data last updated` timestamp pulled from `data/neighborhoods.json`.

Two GitHub Actions workflows support refreshes:

- `Deploy to GitHub Pages`: deploys the current site after pushes to `main`
- `Update Neighborhood Data`: regenerates `data/neighborhoods.json` from the Python script

`Update Neighborhood Data` works in two ways:

- Manual refresh: `GitHub -> Actions -> Update Neighborhood Data -> Run workflow`
- Monthly refresh: the workflow is scheduled to run automatically once a month

If you want to stop monthly refreshes later:

- Go to `GitHub -> Actions -> Update Neighborhood Data`
- Open the workflow menu
- Click `Disable workflow`

Important:

- Scheduled workflows in public repositories can be automatically disabled by GitHub after 60 days of no repository activity
- OpenStreetMap metrics refresh automatically through the script
- Rent values now adjust monthly using Zillow Research ZORI proxy geographies such as ZIP codes and county-level series
- Those rent values are still approximate neighborhood proxies, not exact listing-level neighborhood averages

## Metrics Included

The script computes counts and densities per square kilometer for:

- Food & drink
- Nightlife
- Grocery stores
- Green space
- Transit access

## Data Notes

- Source: OpenStreetMap via OSMnx
- Neighborhoods: Navy Yard, NoMa, Foggy Bottom, Adams Morgan, Arlington, Ballston, Dupont Circle
- Geometry model: center point plus radius
- Output format: JSON only
