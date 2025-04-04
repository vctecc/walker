import osmnx as ox
import os
from networkx import MultiDiGraph
import networkx as nx
import random
import folium
import json
import multiprocessing
from geopy.geocoders import Nominatim

GRAPH_FILE = "moscow_sao_graph.graphml"
NODES_FILE = "valid_end_nodes.json"
sao_boundary = "Северный административный округ, Москва, Россия"
start_address = "Москва, Флотская 34к1"


def load_graph(graph_file: str, boundary: str) -> MultiDiGraph:
    if os.path.exists(graph_file):
        print("Загружаем граф САО из файла...")
        return ox.load_graphml(graph_file)

    print("Скачиваем граф для САО Москвы...")
    graph = ox.graph_from_place(boundary, network_type="walk")
    ox.save_graphml(graph, graph_file)
    return graph


def get_location(address: str) -> tuple:
    geolocator = Nominatim(user_agent="route_generator")
    location = geolocator.geocode(address)
    return location.latitude, location.longitude


def check_node(node, graph, start_node):
    min_length = 1000  # 2 км
    max_length = 5000  # 5 км
    dist = nx.shortest_path_length(graph, start_node, node, weight="length")
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


def create_route(points: int):
    graph = load_graph(GRAPH_FILE, sao_boundary)
    start_lon, start_lat = get_location(start_address)
    if not start_lon:
        print("Ошибка: не удалось определить координаты адреса.")
        return

    start_node = ox.nearest_nodes(graph, start_lon, start_lat)
    route = [start_node]

    nodes = list(graph.nodes)
    waypoints = random.sample(nodes, points)
    for waypoint in waypoints:
        segment = nx.shortest_path(graph, route[-1], waypoint, weight="length")
        route.extend(segment[1:])

    route_back = nx.shortest_path(graph, route[-1], start_node, weight="length")
    route.extend(route_back[1:])

    route_coords = [(graph.nodes[node]['y'], graph.nodes[node]['x']) for node in route]
    m = folium.Map(location=route_coords[0], zoom_start=15)

    folium.PolyLine(route_coords, color="blue", weight=5, opacity=0.7).add_to(m)

    start_coords = (graph.nodes[start_node]['y'], graph.nodes[start_node]['x'])
    folium.Marker(start_coords, icon=folium.Icon(color="green")).add_to(m)

    end_node = waypoints[-1]
    end_coord = (graph.nodes[end_node]['y'], graph.nodes[end_node]['x'])
    folium.Marker(end_coord, icon=folium.Icon(color="red")).add_to(m)

    coords = [(graph.nodes[node]['y'], graph.nodes[node]['x']) for node in waypoints[:-1]]
    icon_color = "orange"
    for i, coord in enumerate(coords):
        folium.Marker(coord, icon=folium.Icon(color=icon_color)).add_to(m)

    m.save("random_walk_route.html")
    print("✅ Маршрут сохранён в 'random_walk_route.html'")


if __name__ == "__main__":
    create_route(4)
    # find_near_nodes()
