import math
import networkx as nx

# ─────────────────────────────────────────────
# ALL LOCATIONS — Extracted from UPDATED_GIU_map.kmz
# Coordinates are real GPS centroids from KML polygons/points
# ─────────────────────────────────────────────

LOCATIONS = {
    "a building": {
        "coords": (30.004529, 31.699829),
        "aliases": ["a", "a block", "building a", "the a building", "hey building"]
    },
    "s building": {
        "coords": (30.004109, 31.699800),
        "aliases": ["s", "s block", "building s", "the s building", "as building", "es building"]
    },
    "m building": {
        "coords": (30.004163, 31.700646),
        "aliases": ["m", "m block", "building m", "the m building", "i'm building", "am building", "em building"]
    },
    "c building": {
        "coords": (30.004798, 31.698654),
        "aliases": ["c", "c block", "building c", "the c building", "see building"]
    },
    "basketball court": {
        "coords": (30.004551, 31.700537),
        "aliases": ["basketball", "bball", "the basketball court"]
    },
    "tennis court": {
        "coords": (30.004764, 31.700899),
        "aliases": ["tennis", "the tennis court"]
    },
    "football field": {
        "coords": (30.005066, 31.701192),
        "aliases": ["football", "soccer", "football field", "soccer field", "the football field"]
    },
    "food court": {
        "coords": (30.004704, 31.702319),
        "aliases": ["foodcourt", "food", "food area", "the food court"]
    },
    "panorama": {
        "coords": (30.004133, 31.701478),
        "aliases": ["panorama restaurant", "the panorama", "poanorama", "panaroma"]
    },
    "padel": {
        "coords": (30.004579, 31.701493),
        "aliases": ["padel court", "the padel"]
    },
    "cafeteria": {
        "coords": (30.004910, 31.701530),
        "aliases": ["cafe", "caf", "the cafeteria"]
    },
    "supermarket": {
        "coords": (30.004997, 31.701649),
        "aliases": ["super", "market", "shop", "the supermarket"]
    },
    "boosters": {
        "coords": (30.005126, 31.701794),
        "aliases": ["booster", "boosters cafe", "the boosters"]
    },
    "main gate": {
        "coords": (30.003721, 31.700807),
        "aliases": ["gate", "the gate", "entrance", "main entrance", "the main gate"]
    },
    "foodcourt gate": {
        "coords": (30.004341, 31.702135),
        "aliases": ["food court gate", "the foodcourt gate", "food gate", "second gate", "other gate", "back gate"]
    },
}

# ─────────────────────────────────────────────
# WAYPOINTS — Internal path junctions
# Real coords from KML, used for routing only
# NOT spoken as destinations
# ─────────────────────────────────────────────

WAYPOINTS = {
    "wp_m_stairs":   (30.004059, 31.701144),   # M Stairs
    "wp_s_stairs":   (30.003843, 31.700237),   # S Stairs
    "wp_green1":     (30.004260, 31.701292),   # green 1 — path junction near panorama
    "wp_green3":     (30.004763, 31.701262),   # green 3 — path junction near tennis/cafeteria
    "wp_green4":     (30.004679, 31.701424),   # green 4 — path junction near padel
    "wp_green_area": (30.004555, 31.701578),   # green area — central junction
    "wp_essen":      (30.004076, 31.701652),   # essen area junction
}

# ─────────────────────────────────────────────
# UTILITIES
# ─────────────────────────────────────────────

def _haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def _bearing(lat1, lon1, lat2, lon2):
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dlam = math.radians(lon2 - lon1)
    x = math.sin(dlam) * math.cos(phi2)
    y = math.cos(phi1)*math.sin(phi2) - math.sin(phi1)*math.cos(phi2)*math.cos(dlam)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def _turn_instruction(prev_bearing, next_bearing):
    diff = (next_bearing - prev_bearing + 360) % 360
    if diff < 30 or diff > 330:
        return "straight"
    elif diff < 180:
        return "right"
    else:
        return "left"


# ─────────────────────────────────────────────
# BUILD WALKABLE GRAPH
# Based on real campus layout from KML
# ─────────────────────────────────────────────

def _build_graph():
    G = nx.Graph()

    all_nodes = {}
    for name, data in LOCATIONS.items():
        all_nodes[name] = data["coords"]
    for name, coords in WAYPOINTS.items():
        all_nodes[name] = coords

    for name, coords in all_nodes.items():
        G.add_node(name, coords=coords)

    def add_edge(a, b):
        ca, cb = all_nodes[a], all_nodes[b]
        dist = _haversine(ca[0], ca[1], cb[0], cb[1])
        G.add_edge(a, b, weight=dist)

    # ── LOWER CAMPUS (A, S, M, C buildings + main gate) ──
    add_edge("main gate",        "m building")
    add_edge("main gate",        "wp_s_stairs")
    add_edge("wp_s_stairs",      "s building")
    add_edge("wp_s_stairs",      "a building")
    add_edge("s building",       "a building")
    add_edge("s building",       "m building")
    add_edge("a building",       "m building")
    add_edge("c building",       "a building")
    add_edge("c building",       "s building")

    # ── M STAIRS — connects lower campus to upper campus ──
    add_edge("m building",       "wp_m_stairs")
    add_edge("wp_m_stairs",      "wp_green1")

    # ── UPPER CAMPUS PATHS (via green areas) ──
    # Green 1 is the main junction after M stairs
    add_edge("wp_green1",        "panorama")
    add_edge("wp_green1",        "basketball court")
    add_edge("wp_green1",        "wp_green3")

    # Basketball court connects to tennis court
    add_edge("basketball court", "tennis court")

    # Green 3 is junction near tennis court / cafeteria area
    add_edge("wp_green3",        "tennis court")
    add_edge("wp_green3",        "wp_green4")
    add_edge("wp_green3",        "football field")

    # Green 4 connects padel area
    add_edge("wp_green4",        "padel")
    add_edge("wp_green4",        "wp_green_area")

    # Central green area — main upper campus junction
    add_edge("wp_green_area",    "padel")
    add_edge("wp_green_area",    "cafeteria")
    add_edge("wp_green_area",    "supermarket")

    # Panorama connects via essen to food court area
    add_edge("panorama",         "wp_essen")
    add_edge("wp_essen",         "food court")
    add_edge("wp_essen",         "foodcourt gate")

    # Upper cluster connections
    add_edge("cafeteria",        "supermarket")
    add_edge("supermarket",      "boosters")
    add_edge("boosters",         "food court")
    add_edge("football field",   "food court")
    add_edge("football field",   "boosters")

    return G, all_nodes


GRAPH, ALL_COORDS = _build_graph()


# ─────────────────────────────────────────────
# ROUTE GENERATION
# Converts node path → spoken step instructions
# No compass directions — only left/right/straight
# ─────────────────────────────────────────────

def _generate_instructions(path):
    if len(path) < 2:
        return []

    steps = []
    destination = path[-1]
    prev_bearing = None

    for i in range(len(path) - 1):
        curr_node = path[i]
        next_node = path[i + 1]

        ca = ALL_COORDS[curr_node]
        cb = ALL_COORDS[next_node]
        dist = round(_haversine(ca[0], ca[1], cb[0], cb[1]))
        brg = _bearing(ca[0], ca[1], cb[0], cb[1])

        # Skip very short internal waypoint hops from spoken output
        is_waypoint = next_node.startswith("wp_")

        if prev_bearing is None:
            turn_phrase = "Walk straight"
        else:
            turn = _turn_instruction(prev_bearing, brg)
            if turn == "straight":
                turn_phrase = "Continue straight"
            elif turn == "left":
                turn_phrase = "Turn left"
            else:
                turn_phrase = "Turn right"

        prev_bearing = brg

        # Don't add a step for waypoint hops — just update bearing
        if is_waypoint:
            continue

        if next_node == destination:
            steps.append(f"{turn_phrase} and walk about {dist} meters. You will arrive at {destination}.")
        else:
            steps.append(f"{turn_phrase} and walk about {dist} meters toward {next_node}.")

    return steps


def get_route(origin, destination):
    if origin not in GRAPH or destination not in GRAPH:
        return None
    try:
        path = nx.shortest_path(GRAPH, origin, destination, weight="weight")
    except nx.NetworkXNoPath:
        return None
    return _generate_instructions(path)


def get_route_distance(origin, destination):
    if origin not in GRAPH or destination not in GRAPH:
        return None
    try:
        return nx.shortest_path_length(GRAPH, origin, destination, weight="weight")
    except nx.NetworkXNoPath:
        return None


def get_location_names():
    return list(LOCATIONS.keys())


def resolve_location(user_input):
    user_input = user_input.lower().strip()
    if user_input in LOCATIONS:
        return user_input
    for name, data in LOCATIONS.items():
        if user_input in data["aliases"]:
            return name
    for name in LOCATIONS:
        if user_input in name or name in user_input:
            return name
    input_words = set(user_input.split())
    for name in LOCATIONS:
        name_words = set(name.split())
        if input_words & name_words:
            return name
    return None

# ─────────────────────────────────────────────
# INTERFACE CONTRACT
# ─────────────────────────────────────────────

def get_next_instruction(current_node: str, destination: str, heading: float) -> str:
    """
    Returns the first navigation instruction from current_node to destination.
    heading (float): current compass bearing in degrees — reserved for future
    turn refinement once real IMU is integrated.
    Called by decision/logic.py in the main pipeline.
    """
    if current_node == destination:
        return f"You are already at {destination}."

    route = get_route(current_node, destination)

    if not route:
        return f"No route found from {current_node} to {destination}."

    return route[0]

# ─────────────────────────────────────────────
# QUICK TEST
# ─────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        ("tennis court", "panorama"),
        ("s building",   "food court"),
        ("main gate",    "boosters"),
        ("m building",   "cafeteria"),
        ("a building",   "football field"),
        ("c building",   "food court"),
        ("panorama",     "tennis court"),
    ]
    for origin, dest in tests:
        steps = get_route(origin, dest)
        dist  = get_route_distance(origin, dest)
        print(f"\n{origin.upper()} → {dest.upper()}  ({int(dist)}m)")
        if steps:
            for i, s in enumerate(steps, 1):
                print(f"  Step {i}: {s}")
        else:
            print("  NO ROUTE FOUND")