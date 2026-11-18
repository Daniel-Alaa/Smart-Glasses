import os
import xml.etree.ElementTree as ET


def load_kml_locations(kml_path):
    tree = ET.parse(kml_path)
    root = tree.getroot()

    ns = {"kml": "http://www.opengis.net/kml/2.2"}

    locations = {}

    for placemark in root.findall(".//kml:Placemark", ns):
        name_tag = placemark.find("kml:name", ns)
        point_tag = placemark.find(".//kml:Point/kml:coordinates", ns)

        if name_tag is None or point_tag is None:
            continue

        name = name_tag.text.strip().lower()

        lon, lat, *_ = point_tag.text.strip().split(",")

        locations[name] = {
            "coords": (float(lat), float(lon)),
            "aliases": [name]
        }

    return locations


# ----------------------------
# TEST
# ----------------------------
if __name__ == "__main__":

    BASE_DIR = os.path.dirname(__file__)          # navigation_system folder
    PROJECT_ROOT = os.path.dirname(BASE_DIR)      # SmartGlassesProject folder

    kml_file = os.path.join(
        PROJECT_ROOT,
        "New GIU map",
        "new_GIU_map_withBorder.kml"
    )

    print("Path:", kml_file)
    print("Exists:", os.path.exists(kml_file))

    data = load_kml_locations(kml_file)

    print(f"\nLoaded {len(data)} locations")
    for k, v in data.items():
        print(k, "->", v["coords"])