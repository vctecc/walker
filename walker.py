import osmnx as ox
import os
import networkx as nx
import random
import folium
import json
import multiprocessing
from geopy.geocoders import Nominatim

GRAPH_FILE = "moscow_sao_graph.graphml"
NODES_FILE = "valid_end_nodes.json"

if os.path.exists(NODES_FILE):
    with open(NODES_FILE) as file:
        nodes = json.load(file)
else:
    if os.path.exists(GRAPH_FILE):
        print("Загружаем граф САО из файла...")
        G = ox.load_graphml(GRAPH_FILE)
    else:
        print("Скачиваем граф для САО Москвы...")
        sao_boundary = "Северный административный округ, Москва, Россия"
        G = ox.graph_from_place(sao_boundary, network_type="walk")
        ox.save_graphml(G, GRAPH_FILE)
    nodes = list(G.nodes)

geolocator = Nominatim(user_agent="route_generator")
location = geolocator.geocode("Москва, Флотская 34к1")
if location:
    start_lat, start_lon = location.latitude, location.longitude
    start_node = ox.nearest_nodes(G, start_lon, start_lat)
else:
    print("Ошибка: не удалось определить координаты адреса.")
    exit()


def check_node(node):
    min_length = 1000  # 2 км
    max_length = 5000  # 5 км
    dist = nx.shortest_path_length(G, start_node, node, weight="length")
    return node if min_length <= dist <= max_length else None


def find_near_nodes():
    valid_end_nodes = []

    num_workers = 4
    total_nodes = len(nodes)
    progress_step = total_nodes // 50

    with multiprocessing.Pool(num_workers) as pool:
        for i, node in enumerate(pool.imap_unordered(check_node, nodes)):
            if node:
                valid_end_nodes.append(node)

            if i % progress_step == 0:
                print(f"Прогресс: {int((i / total_nodes) * 100)}%")

    with open(NODES_FILE, "w") as f:
        json.dump(valid_end_nodes, f)
    print(f"Найдено и сохранено {len(valid_end_nodes)} подходящих нод.")


def cal_test(points: int):
    route = [start_node]

    waypoints = random.sample(nodes, points)
    for waypoint in waypoints:
        segment = nx.shortest_path(G, route[-1], waypoint, weight="length")
        route.extend(segment[1:])

    route_back = nx.shortest_path(G, route[-1], start_node, weight="length")
    route.extend(route_back[1:])

    route_coords = [(G.nodes[node]['y'], G.nodes[node]['x']) for node in route]
    m = folium.Map(location=route_coords[0], zoom_start=15)

    folium.PolyLine(route_coords, color="blue", weight=5, opacity=0.7).add_to(m)

    start_coords = (G.nodes[start_node]['y'], G.nodes[start_node]['x'])
    folium.Marker(start_coords, icon=folium.Icon(color="green")).add_to(m)

    end_node = waypoints[-1]
    end_coord = (G.nodes[end_node]['y'], G.nodes[end_node]['x'])
    folium.Marker(end_coord, icon=folium.Icon(color="red")).add_to(m)

    coords = [(G.nodes[node]['y'], G.nodes[node]['x']) for node in waypoints[:-1]]
    icon_color = "orange"
    for i, coord in enumerate(coords):
        folium.Marker(coord, icon=folium.Icon(color=icon_color)).add_to(m)

    m.save("random_walk_route.html")
    print("✅ Маршрут сохранён в 'random_walk_route.html'")


if __name__ == "__main__":
    # cal_test(4)
    find_near_nodes()
