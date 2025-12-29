import googlemaps
import pandas as pd
import time
import os
import folium
from tqdm import tqdm

# === Config ===
API_KEY =   # kept as in your file
gmaps = googlemaps.Client(key=API_KEY)

OUTPUT_FOLDER = r"C:"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# === Category catalog ===
# Keep "Real Estate Agencies" and add associations (now including Parish Councils & Livestock Associations).
# For associations, use multi-language keywords (EN/PT/ES).
CATEGORIES = {
    "1": {
        "label": "Real Estate Agencies",
        "keywords": ["real estate agency"],  # we'll also use type
        "place_type": "real_estate_agency",
    },
    "2": {
        "label": "Land Associations",
        "keywords": [
            "land association", "associação de proprietários rurais", "asociación de propietarios rurales",
            "associação de proprietários de terra", "asociación de propietarios de tierras",
            "associação de terras", "asociación de tierras"
        ],
        "place_type": None,
    },
    "3": {
        "label": "Hunting Associations",
        "keywords": [
            "hunting association", "clube de caça", "associação de caça",
            "asociación de caza", "sociedad de cazadores", "federación de caza"
        ],
        "place_type": None,
    },
    "4": {
        "label": "Farming Associations",
        "keywords": [
            "farming association", "associação de agricultores", "cooperativa agrícola",
            "asociación de agricultores", "cooperativa agraria", "sindicato agrícola"
        ],
        "place_type": None,
    },
    "5": {
        "label": "Fishing Associations",
        "keywords": [
            "fishing association", "associação de pesca", "clube de pesca",
            "asociación de pesca", "sociedad de pescadores", "federación de pesca"
        ],
        "place_type": None,
    },
    "6": {
        "label": "Parish Councils (Juntas de Freguesia)",
        "keywords": [
            "junta de freguesia", "união de freguesias", "parish council",
            # Spanish variants (less common for PT context but harmless for ES coordinates):
            "junta parroquial", "concejo parroquial"
        ],
        "place_type": None,  # no reliable dedicated type; keywords give better recall
    },
    "7": {
        "label": "Livestock Associations",
        "keywords": [
            "livestock association", "cattle association", "beef association",
            "associação de gado", "associação de produtores de gado",
            "associação de bovinos", "associação pecuária", "associação de criadores",
            "asociación de ganaderos", "asociación ganadera", "asociación de bovinos"
        ],
        "place_type": None,
    },
}

def print_category_menu():
    print("\n📚 Available categories:")
    for k, v in CATEGORIES.items():
        print(f"  [{k}] {v['label']}")
    print("You can pick multiple separated by commas (e.g., 1,3,5).")

def get_category_selection():
    print_category_menu()
    raw = input("Select category(ies): ").strip()
    if not raw:
        return []
    choices = [c.strip() for c in raw.split(",") if c.strip() in CATEGORIES]
    return choices

def get_points():
    points = []
    print("📌 Enter coordinates (latitude and longitude). Type 'done' to finish.")
    while True:
        lat_input = input("Latitude: ")
        if lat_input.lower() == 'done':
            break
        lon_input = input("Longitude: ")
        if lon_input.lower() == 'done':
            break
        try:
            lat = float(lat_input)
            lon = float(lon_input)
            points.append((lat, lon))
        except ValueError:
            print("❌ Invalid coordinates. Please enter numeric values.")
    return points

def fetch_place_details(pid):
    """Fetch place details (fields we need)."""
    try:
        details = gmaps.place(
            place_id=pid,
            fields=[
                "name", "formatted_address", "formatted_phone_number",
                "website", "geometry", "rating", "user_ratings_total"
            ]
        )["result"]
        return {
            "Name": details.get("name"),
            "Address": details.get("formatted_address"),
            "Phone": details.get("formatted_phone_number"),
            "Website": details.get("website"),
            "Latitude": details.get("geometry", {}).get("location", {}).get("lat"),
            "Longitude": details.get("geometry", {}).get("location", {}).get("lng"),
            "Rating": details.get("rating"),
            "Total Ratings": details.get("user_ratings_total"),
        }
    except Exception as e:
        print(f"   ⚠️ Error fetching details for {pid}: {e}")
        return None

def search_places_generic(lat, lon, radius, keywords, place_type=None, category_label=""):
    """
    Search by a list of keywords (or type when available).
    Handles pagination (next_page_token) to collect more results.
    """
    results = []
    seen = set()

    def run_query(keyword_or_none):
        try:
            kwargs = {
                "location": (lat, lon),
                "radius": radius,
            }
            if place_type:
                kwargs["type"] = place_type
            if keyword_or_none:
                kwargs["keyword"] = keyword_or_none

            response = gmaps.places_nearby(**kwargs)
        except Exception as e:
            print(f"⚠️ Search error ({keyword_or_none}): {e}")
            return []

        data = response.get("results", [])
        token = response.get("next_page_token")

        out = list(data)

        # Up to 2 extra pages (Google may return up to ~60 results)
        for _ in range(2):
            if not token:
                break
            time.sleep(2.0)  # Google requires ~2s before using page_token
            try:
                response = gmaps.places_nearby(page_token=token)
                out.extend(response.get("results", []))
                token = response.get("next_page_token")
            except Exception as e:
                print(f"⚠️ Pagination error: {e}")
                break

        return out

    # With type (real estate): one call is enough
    if place_type:
        batches = [run_query(keywords[0] if keywords else None)]
    else:
        # Associations: iterate keywords to broaden coverage
        batches = []
        for kw in keywords:
            batches.append(run_query(kw))
            time.sleep(0.3)  # small pause to be gentle on quotas

    # Aggregate
    for batch in batches:
        for place in batch or []:
            pid = place.get("place_id")
            if not pid or pid in seen:
                continue
            seen.add(pid)
            details = fetch_place_details(pid)
            if not details:
                continue
            record = {
                "Place ID": pid,
                **details,
                "Category": category_label,
                "Search Origin": f"{lat}, {lon}",
            }
            results.append(record)
            time.sleep(0.1)  # brief pause between detail calls

    return results

def generate_map(data, output_html):
    if data.empty:
        print("⚠️ No data to render on the map.")
        return

    # Initial viewport
    first_lat = data.iloc[0]["Latitude"]
    first_lon = data.iloc[0]["Longitude"]
    m = folium.Map(location=[first_lat, first_lon], zoom_start=12)

    # Markers
    for _, row in data.iterrows():
        popup_txt = f"{row.get('Name','')}<br>{row.get('Address','')}"
        if "Category" in data.columns:
            popup_txt += f"<br><b>{row.get('Category','')}</b>"
        folium.Marker(
            location=[row["Latitude"], row["Longitude"]],
            popup=popup_txt,
            tooltip=row.get("Address", "")
        ).add_to(m)

    m.save(output_html)
    print(f"🗺️ HTML map saved to: {output_html}")

def normalize_for_filename(text):
    return (
        text.lower()
        .replace(" ", "_")
        .replace("/", "-")
        .replace(",", "")
    )

def main():
    print("🏠 Search Tool — Agencies & Associations")

    # Category selection
    choices = get_category_selection()
    if not choices:
        print("❌ No category selected. Exiting.")
        return

    # Radius
    try:
        radius = int(input("📏 Enter search radius in meters (e.g., 30000): "))
    except ValueError:
        print("❌ Invalid radius. It must be an integer.")
        return

    # Search points
    points = get_points()
    if not points:
        print("❌ No coordinates provided. Exiting.")
        return

    all_results = []

    # For each point and selected category
    for lat, lon in tqdm(points, desc="🔄 Searching points", unit="point"):
        for c in choices:
            meta = CATEGORIES[c]
            cat_label = meta["label"]
            results = search_places_generic(
                lat=lat,
                lon=lon,
                radius=radius,
                keywords=meta["keywords"],
                place_type=meta["place_type"],
                category_label=cat_label
            )
            all_results.extend(results)

    # Final DataFrame
    df = pd.DataFrame(all_results)
    if df.empty:
        print("\n⚠️ No results found.")
        return

    # Dedupe by Place ID
    df.drop_duplicates(subset="Place ID", inplace=True)

    # Output file names
    if len(choices) == 1 and CATEGORIES[choices[0]]["label"] == "Real Estate Agencies":
        excel_name = f"real_estate_agencies_{radius}m.xlsx"
        html_name = f"real_estate_map_{radius}m.html"
    else:
        cats_name = "_".join([normalize_for_filename(CATEGORIES[c]["label"]) for c in choices])
        excel_name = f"places_{cats_name}_{radius}m.xlsx"
        html_name = f"map_{cats_name}_{radius}m.html"

    output_excel = os.path.join(OUTPUT_FOLDER, excel_name)
    df.to_excel(output_excel, index=False)
    print(f"\n✅ Excel file saved to: {output_excel}")
    print(f"🔢 Total unique places found: {len(df)}")

    output_map = os.path.join(OUTPUT_FOLDER, html_name)
    generate_map(df, output_map)

if __name__ == "__main__":
    main()
