import os
import requests

def fetch_osm_data():
    osm_path = os.path.join(os.path.dirname(__file__), "iit_ism_dhanbad.osm")
    # IIT (ISM) Dhanbad coordinates: ~23.814 N, 86.441 E
    # Bounding box covers IIT (ISM) campus and surrounding Dhanbad roads (Police Line Rd, Saraidheela Rd, Sardar Patel Nagar)
    bbox = "23.805,86.430,23.825,86.455"
    overpass_urls = [
        "https://overpass-api.de/api/interpreter",
        "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter"
    ]
    query = f"""[out:xml][timeout:35];
(
  way["highway"]({bbox});
  node(w);
  relation["highway"]({bbox});
);
out body;
>;
out skel qt;"""

    for url in overpass_urls:
        try:
            print(f"Attempting to fetch OSM data from {url}...")
            resp = requests.post(url, data={"data": query}, timeout=30)
            if resp.status_code == 200 and len(resp.content) > 10000:
                with open(osm_path, "wb") as f:
                    f.write(resp.content)
                print(f"Successfully downloaded OSM road data ({len(resp.content)} bytes) to {osm_path}")
                return True
            else:
                print(f"Response status: {resp.status_code}, length: {len(resp.content)}")
        except Exception as e:
            print(f"Error querying {url}: {e}")
            
    print("Could not retrieve online OSM data; will fallback to calibrated road network.")
    return False

if __name__ == "__main__":
    fetch_osm_data()
