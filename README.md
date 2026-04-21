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
- `data/neighborhoods.json` is already checked in with example values so the site works immediately.
- The Python script uses neighborhood center points plus a radius instead of exact official boundaries.
- Rent values are mock but realistic estimates for 1-bedroom apartments.

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

## Metrics Included

The script computes counts and densities per square kilometer for:

- Food & drink
- Nightlife
- Grocery stores
- Green space
- Transit access

## Data Notes

- Source: OpenStreetMap via OSMnx
- Neighborhoods: NoMa, Navy Yard, U Street, Dupont Circle, Georgetown
- Geometry model: center point plus radius
- Output format: JSON only
