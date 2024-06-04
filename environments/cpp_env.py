#%%
import random
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
from gym import spaces
import copy
import os
import time
NUM_NODES = 25
Side = int(NUM_NODES**0.5)
# num_edges_to_remove = 2
times = 0

def is_connected(matrix):
    graph = nx.from_numpy_array(matrix)
    return nx.is_connected(graph)


class ChinesePostman:
    def __init__(self, num_nodes=NUM_NODES):
        self.num_nodes = num_nodes
        self.side = self.num_nodes**0.5
        self.map = np.zeros((num_nodes, num_nodes))
        self.current_node = random.randint(0, 24)
        self.deopt = self.current_node
        self.num_edges_to_remove = random.randint(8, 10)
        self.traveled = np.zeros((num_nodes, num_nodes))
        self.generate_map()
        self.main_road_matrix = self.map.copy()
        self.need_to_travel = np.sum(self.map > 0) / 2
        self.main_road()
        self.traveled_num =  0
        self.max_episode_steps = 40
        self.step_count = 0
        self.renderction = self.deopt
        self.path = []
        self.done = False
        self.path.append(self.current_node)  
        self.alledge = 0
        self.target_path = None 
        self.map[self.deopt][self.deopt] = 1
        self.traveled[self.deopt][self.deopt] = 1
        self.ok = 0
        self.Gmap =  self.create_networkx_graph()
        self.total_distance = 0

        
        self.traveled_mask = np.ones_like(self.map, dtype=bool)
        np.fill_diagonal(self.traveled_mask, False)
        self.traveled_zero_mask = (self.map == 0) & self.traveled_mask
        self.ok = 0
        self.map_model = np.copy(self.map)
        self.map_model[self.map_zero_mask] = -1
        self.traveled[self.traveled_zero_mask] = -1
        self.map_model[self.deopt][self.deopt] = 1
        self.traveled[self.deopt][self.deopt] = 1
  
    @property
    def observation_space(self):
        observation_space = spaces.Box(low=-1,
                               high=20,
                               shape=(3,self.num_nodes,self.num_nodes), dtype=np.int32)
        # print("test")
        return observation_space

    @property
    def action_space(self):
        action_space = spaces.Discrete(int(self.side*(self.side-1)*2))
        return action_space
    
    def main_road(self):
        for i in range(self.num_nodes):
            for j in range(i+1, self.num_nodes):
                if self.map[i,j] != 0:
                    if np.random.rand() < 0.95 :
                        self.main_road_matrix[i,j] = 1
                    else:
                        self.main_road_matrix[i,j] = 2
                        # print("Need to 2 times: ",i," & ", j)
                    self.main_road_matrix[j, i] = self.main_road_matrix[i, j]
                    
        
    
    def initialize_adjacency_matrix(self):
        # Setup initial connected grid structure
        for i in range(self.num_nodes):
            if i % Side != Side - 1:
                self.map[i][i + 1] = self.map[i + 1][i] = random.randint(10, 10)
            if i < Side * (Side - 1):
                self.map[i][i + Side] = self.map[i + Side][i] = random.randint(10, 10)
        
        self.map_mask = np.ones_like(self.map, dtype=bool)
        np.fill_diagonal(self.map_mask, False)
        self.map_zero_mask = (self.map == 0) & self.map_mask
    def randomly_remove_edges(self):
    
        edges_removed = 0
        while edges_removed < self.num_edges_to_remove:
            existing_edges = np.argwhere(self.map > 0)
            if not existing_edges.size:
                break
            edge_to_remove = existing_edges[np.random.randint(len(existing_edges))]
            # Temporarily remove the edge to test connectivity
            self.map[edge_to_remove[0], edge_to_remove[1]] = 0
            self.map[edge_to_remove[1], edge_to_remove[0]] = 0

            if is_connected(self.map):
                edges_removed += 1  # Successfully removed the edge
            else:
                # Restore the edge if removal breaks the connectivity
                self.map[edge_to_remove[0], edge_to_remove[1]] = 10
                self.map[edge_to_remove[1], edge_to_remove[0]] = 10
    def fix_remove_deges(self):
        # edges_to_remove = [(1, 6), (9, 14), (12, 17), (17, 22),  (19, 24), (5, 6), (6, 7), (7, 8), (15, 16)]
        edges_to_remove = [(3, 4), (7, 8), (12, 13), (12, 13),  (16, 17), (20, 21), (22, 23), (7, 12)]
        for edge in edges_to_remove:
            self.map[edge[0], edge[1]] = self.map[edge[1], edge[0]] = 0

    def generate_map(self):
        self.initialize_adjacency_matrix()
        # self.map = np.copy(self.load_random_array())
        # np.fill_diagonal(self.map, 0)
        self.randomly_remove_edges()
        # self.fix_remove_deges()

    def get_observation(self):
        combined_map = np.concatenate((self.map_model, self.traveled, self.main_road_matrix), axis=0)
        combined_map = combined_map.reshape(3, self.num_nodes, self.num_nodes)
        return combined_map

    def reset(self):
        self.__init__()
        self._rewards = []
        self.traveled[self.deopt][self.deopt] = self.traveled[self.deopt][self.deopt] = 1
        
        combined_map = self.get_observation()
        return combined_map

    def decode_edge_action(self, action):
       
        if action < self.side * (self.side - 1):  # 判斷是不是水平邊
            row = action // (self.side - 1)
            col = action % (self.side - 1)
            node1 = row * self.side + col
            node2 = node1 + 1
        else:  # 垂直邊的處理
            action -= self.side * (self.side - 1)  # 調整邊編號
            row = action // self.side 
            col = action % self.side 
            node1 = row * self.side + col
            node2 = node1 + self.side
        return int(node1), int(node2)
    def determine_closest_node(self, node1, node2):
        
        distance_to_node1 = nx.shortest_path_length(self.Gmap, self.current_node, node1, weight='weight')
        distance_to_node2 = nx.shortest_path_length(self.Gmap, self.current_node, node2, weight='weight')
        
        if distance_to_node1 <= distance_to_node2:
            closer_node, farther_node = node1, node2
            path_distance = distance_to_node1
        else:
            closer_node, farther_node = node2, node1
            path_distance = distance_to_node2
        
        shortest_path = nx.shortest_path(self.Gmap, self.current_node, closer_node, weight='weight')
       
        if len(shortest_path) == 1 or shortest_path[-2] != farther_node:
            # If not, add the farthest node to the path and calculate the additional distance
            additional_path = nx.shortest_path(self.Gmap, shortest_path[-1], farther_node, weight='weight')
            additional_distance = nx.shortest_path_length(self.Gmap, shortest_path[-1], farther_node, weight='weight')
            shortest_path.extend(additional_path[1:])  # Exclude the first element to avoid duplication
            path_distance += additional_distance

        return shortest_path, path_distance
    def update_traveled_edges(self, action):
        """Update the matrix of traveled edges after a valid move."""
        self.traveled[self.current_node][action] += 1
        self.traveled[action][self.current_node] = self.traveled[self.current_node][action]
    def step(self, action):
        done = False
        reward = 0
        action = copy.deepcopy(action[0])
        # print("action",action)
        node1, node2 = self.decode_edge_action(action)
        
        if self.alledge == 1:
            path_distance = nx.shortest_path_length(self.Gmap, self.current_node, self.deopt, weight='weight')
            shortest_path = nx.shortest_path(self.Gmap, self.current_node, self.deopt, weight='weight')
        else:
            shortest_path, path_distance = self.determine_closest_node(node1, node2)
        # print("path",shortest_path)
        # if len(shortest_path) < 2:
        #     return None, -100, True, {"error": "Invalid path length"}
        self.traveled[self.current_node][self.current_node] = 0
        for i in range(len(shortest_path) - 1):
            start_node = shortest_path[i]
            end_node = shortest_path[i+1]
            self.path.append(end_node)
            if self.map[start_node][end_node] > 0:
                if self.traveled[start_node][end_node] == 0:
                    if self.traveled[start_node][end_node] < self.main_road_matrix[start_node][end_node]:
                        # self.traveled_num += 1
                        reward += 20
                    
                
                self.traveled[start_node][end_node] += 1
                self.traveled[end_node][start_node] = self.traveled[start_node][end_node]
                if self.traveled[start_node][end_node] == self.main_road_matrix[start_node][end_node]:
                    self.traveled_num += 1
                    
                #     print("traveled",self.traveled[start_node][end_node] )
                #     print("main_road_matrix",self.main_road_matrix[start_node][end_node])
                    
                
            else:
                reward -= 1000
                print("No this edge")
                done = True
                break
        self.current_node = shortest_path[-1]
        self.renderction = self.current_node
        self.traveled[self.current_node][self.current_node] = 1

        if self.traveled_num == self.need_to_travel and self.alledge == 0:
            with open('test.txt', 'a') as file:
                file.write('1')
            self.alledge = 1
        if self.alledge == 1 and self.deopt == self.current_node:
            reward += 100
            with open('test.txt', 'a') as file:
                file.write('2')
            self.ok = 1 
            done = True
        
        if self.step_count >=40:
            with open('test.txt', 'a') as file:
                file.write('over') 
            done = True
            
        reward -= path_distance
        self.total_distance += path_distance
        self._rewards.append(reward)
        if done:
            info = {"reward": sum(self._rewards),
                    "length": len(self._rewards),
                    "distance":(self.total_distance)}
            # print(info)
            # if (self.total_distance) < 460:
                # self.save_array(self.map)
                
        else:
            info = None
        combined_map = self.get_observation()
        # print(combined_map)
        self.done = done
        return combined_map, reward, done, info

        
    def render(self):
        # input()
        # time.sleep(0.5)
        print("Current path:", self.path)
        if self.done == True:
            print("Current path:", self.path)
        # print(f"Currently at {self.current_node}")
        # print("Need to traverse ",self.need_to_travel," edges, already traversed :",self.traveled_num," edges")

    def close(self):
        print("close")
    def save_array(self, test_data, filename="test_data.npz", expected_dtype=np.float64):
        if test_data.dtype != expected_dtype:
            raise ValueError(f"Data type of the array must be {expected_dtype}, but got {test_data.dtype}.")
        data_dict = {}
        if os.path.exists(filename):
            with np.load(filename, allow_pickle=True) as data:
                data_dict = dict(data)
        # 將新的數據加入字典
        data_dict[f"array_{len(data_dict)}"] = test_data
        # 保存更新後的數據
        np.savez_compressed(filename, **data_dict)

    # 從npz文件中隨機選取一個numpy數組，並檢查數據完整性
    def load_random_array(self, filename="test_data.npz", expected_shape=(25, 25)):
        if not os.path.exists(filename):
            raise FileNotFoundError("The specified file does not exist.")
        with np.load(filename, allow_pickle=True) as data:
            keys = list(data.keys())
            if not keys:
                raise ValueError("No data available in the file.")
            random_key = random.choice(keys)
            random_array = data[random_key]
            if random_array.shape != expected_shape:
                raise ValueError(f"Expected array shape {expected_shape}, but got {random_array.shape}.")
        return random_array

    def create_networkx_graph(self):
        G = nx.Graph()
        for i in range(self.num_nodes):
            for j in range(i + 1, self.num_nodes):
                if self.map[i][j] > 0:
                    G.add_edge(i, j, weight=self.map[i][j])
        return G
    def get_pos(self):
        pos = {i: (i % Side, Side - 1 - i // Side) for i in range(NUM_NODES)}
        Hedges = [(u, v, {'weight': data['weight']}) for u, v, data in self.Gmap.edges(data=True)]
        pos = self.adjust_positions(pos, Hedges )
        print("function pos ",pos)
        return pos
    def adjust_positions(self, pos, edges):
        for edge in edges:
            start, end = int(edge[0]), int(edge[1])
            distance = edge[2]['weight']
            dx, dy = float(pos[end][0] - pos[start][0]), float(pos[end][1] - pos[start][1])
            z = (dx*dx + dy*dy) ** 0.5


            # 計算距離比例因子
            factor = distance / 10  # 假設50是基準距離
            pos[end] = (pos[start][0] + factor * dx/z, pos[start][1] + factor * dy/z)


        return pos    

    def plot_graph(self, G, pos, file_name="graph.png"):
        plt.figure(figsize=(15, 15))
        nx.draw(G, pos, with_labels=True, alpha=0.8, font_size=20, node_size=750, edge_color='black')
        labels = nx.get_edge_attributes(G, 'weight')
        nx.draw_networkx_edge_labels(G, pos, edge_labels=labels, font_color='c', font_size=20)
        plt.savefig(file_name)
        plt.show()
    # def find_untraveled_edges(self):
    #     untraveled_edges = []
    #     for i in range(self.num_nodes):
    #         for j in range(i + 1, self.num_nodes):  # 
    #             if self.map[i][j] > 0 and self.traveled[i][j] == 0:
    #                 untraveled_edges.append((i, j))
    #     return untraveled_edges
    # def print_shortest_path(self, target):
    #     #
    #     if target >= self.num_nodes or target < 0:
    #         return f"Invalid target node: {target}. Node must be between 0 and {self.num_nodes - 1}"
        
    #     if self.current_node == target:
    #         return f"The current node {self.current_node} is the target node."

    #     try:
    #         # 
    #         path = nx.shortest_path(self.Gmap, source=self.current_node, target=target)
    #         if len(path) > 1:
    #             return path[1:]
    #         else:
    #             return path
    #     except nx.NetworkXNoPath:
    #         # 
    #         return f"No path from node {self.current_node} to node {target}."
    # def print_path_to_random_untraveled_edge(self):
    #     # 
    #     untraveled_edges = self.find_untraveled_edges()
    #     if not untraveled_edges:
    #         return self.print_shortest_path(0)

    #     # 
        
    #     random_edge = random.choice(untraveled_edges)
    #     target_node = random.choice(random_edge)  # 
    #     if self.current_node == target_node:
    #         target_node = random_edge[0] if target_node == random_edge[1] else random_edge[1]

    #     other_node = random_edge[0] if target_node == random_edge[1] else random_edge[1]
    #     path = self.print_shortest_path(target_node)
    #     # print(path,"--------------")
    #     if other_node not in path:
    #         path.append(other_node)
    #     # print("The target is :", target_node)
    #     # 
    #     return path
    # def manage_path_to_untraveled_edge(self):
    #     if self.target_path is None or not self.target_path:
    #         # 
    #         path = self.print_path_to_random_untraveled_edge()
    #         if isinstance(path, list):  # 
    #             self.target_path = path
    #         return path
    #     else:
    #         # 
    #         if self.current_node == self.target_path[0]:
    #             self.target_path.pop(0)  # 
    #         if not self.target_path:
    #             path = self.print_path_to_random_untraveled_edge()
    #             if isinstance(path, list):  # 
    #                 self.target_path = path
    #         return self.target_path
        
# cp = ChinesePostman()
# print("------")
# state = cp.reset()
# pos = cp.get_pos()
# # print("pos", pos)
# # print("get pos",cp.get_pos())
# G = cp.create_networkx_graph()
# # print(G.edges(data=True))
# cp.plot_graph(G, pos, "0528.png")
# # print("check",cp.check[1])
# # print("map",cp.map[1])
# # array1 = cp.check[0]
# # array2 = cp.map[0]

# # print(cp.action_space)
# cp.render()
# for _ in range(50):  # Take 10 random steps in the environment
#     print("now is ",cp.renderction)
#     action = int(input("Next will go:"))
#     print("acitno is" ,action)
#     state, reward, done, info= cp.step(action)
#     # print("map",state[0])
#     # print("travel",state[1])
#     # print("treavek is ",state[1])
#     # print("reward is ",reward)
# # 
#     cp.render()
#     if done:
#         print("done")
#         cp.reset()

# Example usage
# cp = ChinesePostman()
# cp.reset()
# G = cp.create_networkx_graph()
# pos = {i: (i % Side, Side - 1 - i // Side) for i in range(NUM_NODES)}
# cp.plot_graph(G, pos, "test2.png")
# print(cp.action_space)
# cp.render()
# for _ in range(50):  # Take 10 random steps in the environment
#     print("now is ",cp.renderction)
#     action = int(input("Next will go:"))
#     state, reward, done, info= cp.step(action)
#     print("map is ",state[0])
#     print("travel is ",state[1])
#     print("Reward is ",reward)
#     cp.render()
#     # print("path:", cp.manage_path_to_untraveled_edge()) 
#     # cp.render()
#     # print(f"Action: Move to {action}, Next state: {state[0]}, Reward: {reward}")
#     if done:
#         print("----Done----")
#         cp.reset()
#         cp.render()
#         G = cp.create_networkx_graph()
#         pos = {i: (i % Side, Side - 1 - i // Side) for i in range(NUM_NODES)}
#         cp.plot_graph(G, pos, "test2.png")
# %%
