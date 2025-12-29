
# Places Nearby Search Tool (Google Maps)

A command-line tool that searches **Google Maps Places** around user-provided coordinates for selected **categories** (Real Estate Agencies, Associations, Parish Councils, etc.), collects **details**, exports results to **Excel**, and generates an interactive **HTML map**.

> Built for multi-language keyword coverage (EN/PT/ES) to improve recall for associations.

---

## Features

- ✅ Interactive CLI for:
  - Category selection (you can choose multiple)
  - Search radius in meters
  - Inputting one or more coordinates
- 🔎 Uses **Google Places Nearby Search** and **Place Details** to gather:
  - Name, Address, Phone, Website, Lat/Lon, Rating, Total Ratings
- 🧭 Supports multi-language **keywords** for associations (EN/PT/ES)
- 🗂️ Exports to **Excel** (`.xlsx`) with deduplication by Place ID
- 🗺️ Generates an **HTML map** with markers and popups
- ♻️ Efficient pagination handling for up to ~60 results per query

---

## Requirements

- **Python** 3.9+
- Packages:
  - `googlemaps`
  - `pandas`
  - `tqdm`
  - `folium`
- Built-in modules:
  - `time`, `os`

Install dependencies:

```bash
pip install googlemaps pandas tqdm folium
