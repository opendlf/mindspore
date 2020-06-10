# Copyright 2020 Huawei Technologies Co., Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
import random
import pytest
import numpy as np
import mindspore.dataset as ds
from mindspore import log as logger

DATASET_FILE = "../data/mindrecord/testGraphData/testdata"


def test_graphdata_getfullneighbor():
    g = ds.GraphData(DATASET_FILE, 2)
    nodes = g.get_all_nodes(1)
    assert len(nodes) == 10
    neighbor = g.get_all_neighbors(nodes, 2)
    assert neighbor.shape == (10, 6)
    row_tensor = g.get_node_feature(neighbor.tolist(), [2, 3])
    assert row_tensor[0].shape == (10, 6)


def test_graphdata_getnodefeature_input_check():
    g = ds.GraphData(DATASET_FILE)
    with pytest.raises(TypeError):
        input_list = [1, [1, 1]]
        g.get_node_feature(input_list, [1])

    with pytest.raises(TypeError):
        input_list = [[1, 1], 1]
        g.get_node_feature(input_list, [1])

    with pytest.raises(TypeError):
        input_list = [[1, 1], [1, 1, 1]]
        g.get_node_feature(input_list, [1])

    with pytest.raises(TypeError):
        input_list = [[1, 1, 1], [1, 1]]
        g.get_node_feature(input_list, [1])

    with pytest.raises(TypeError):
        input_list = [[1, 1], [1, [1, 1]]]
        g.get_node_feature(input_list, [1])

    with pytest.raises(TypeError):
        input_list = [[1, 1], [[1, 1], 1]]
        g.get_node_feature(input_list, [1])

    with pytest.raises(TypeError):
        input_list = [[1, 1], [1, 1]]
        g.get_node_feature(input_list, 1)

    with pytest.raises(TypeError):
        input_list = [[1, 0.1], [1, 1]]
        g.get_node_feature(input_list, 1)

    with pytest.raises(TypeError):
        input_list = np.array([[1, 0.1], [1, 1]])
        g.get_node_feature(input_list, 1)

    with pytest.raises(TypeError):
        input_list = [[1, 1], [1, 1]]
        g.get_node_feature(input_list, ["a"])

    with pytest.raises(TypeError):
        input_list = [[1, 1], [1, 1]]
        g.get_node_feature(input_list, [1, "a"])


def test_graphdata_getsampledneighbors():
    g = ds.GraphData(DATASET_FILE, 1)
    edges = g.get_all_edges(0)
    nodes = g.get_nodes_from_edges(edges)
    assert len(nodes) == 40
    neighbor = g.get_sampled_neighbors(
        np.unique(nodes[0:21, 0]), [2, 3], [2, 1])
    assert neighbor.shape == (10, 9)


def test_graphdata_getnegsampledneighbors():
    g = ds.GraphData(DATASET_FILE, 2)
    nodes = g.get_all_nodes(1)
    assert len(nodes) == 10
    neighbor = g.get_neg_sampled_neighbors(nodes, 5, 2)
    assert neighbor.shape == (10, 6)


def test_graphdata_graphinfo():
    g = ds.GraphData(DATASET_FILE, 2)
    graph_info = g.graph_info()
    assert graph_info['node_type'] == [1, 2]
    assert graph_info['edge_type'] == [0]
    assert graph_info['node_num'] == {1: 10, 2: 10}
    assert graph_info['edge_num'] == {0: 40}
    assert graph_info['node_feature_type'] == [1, 2, 3, 4]
    assert graph_info['edge_feature_type'] == []


class RandomBatchedSampler(ds.Sampler):
    # RandomBatchedSampler generate random sequence without replacement in a batched manner
    def __init__(self, index_range, num_edges_per_sample):
        super().__init__()
        self.index_range = index_range
        self.num_edges_per_sample = num_edges_per_sample

    def __iter__(self):
        indices = [i+1 for i in range(self.index_range)]
        # Reset random seed here if necessary
        # random.seed(0)
        random.shuffle(indices)
        for i in range(0, self.index_range, self.num_edges_per_sample):
            # Drop reminder
            if i + self.num_edges_per_sample <= self.index_range:
                yield indices[i: i + self.num_edges_per_sample]


class GNNGraphDataset():
    def __init__(self, g, batch_num):
        self.g = g
        self.batch_num = batch_num

    def __len__(self):
        # Total sample size of GNN dataset
        # In this case, the size should be total_num_edges/num_edges_per_sample
        return self.g.graph_info()['edge_num'][0] // self.batch_num

    def __getitem__(self, index):
        # index will be a list of indices yielded from RandomBatchedSampler
        # Fetch edges/nodes/samples/features based on indices
        nodes = self.g.get_nodes_from_edges(index.astype(np.int32))
        nodes = nodes[:, 0]
        neg_nodes = self.g.get_neg_sampled_neighbors(
            node_list=nodes, neg_neighbor_num=3, neg_neighbor_type=1)
        nodes_neighbors = self.g.get_sampled_neighbors(node_list=nodes, neighbor_nums=[
            2, 2], neighbor_types=[2, 1])
        neg_nodes_neighbors = self.g.get_sampled_neighbors(
            node_list=neg_nodes[:, 1:].reshape(-1), neighbor_nums=[2, 2], neighbor_types=[2, 2])
        nodes_neighbors_features = self.g.get_node_feature(
            node_list=nodes_neighbors, feature_types=[2, 3])
        neg_neighbors_features = self.g.get_node_feature(
            node_list=neg_nodes_neighbors, feature_types=[2, 3])
        return nodes_neighbors, neg_nodes_neighbors, nodes_neighbors_features[0], neg_neighbors_features[1]


def test_graphdata_generatordataset():
    g = ds.GraphData(DATASET_FILE)
    batch_num = 2
    edge_num = g.graph_info()['edge_num'][0]
    out_column_names = ["neighbors", "neg_neighbors", "neighbors_features", "neg_neighbors_features"]
    dataset = ds.GeneratorDataset(source=GNNGraphDataset(g, batch_num), column_names=out_column_names,
                                  sampler=RandomBatchedSampler(edge_num, batch_num), num_parallel_workers=4)
    dataset = dataset.repeat(2)
    itr = dataset.create_dict_iterator()
    i = 0
    for data in itr:
        assert data['neighbors'].shape == (2, 7)
        assert data['neg_neighbors'].shape == (6, 7)
        assert data['neighbors_features'].shape == (2, 7)
        assert data['neg_neighbors_features'].shape == (6, 7)
        i += 1
    assert i == 40


if __name__ == '__main__':
    test_graphdata_getfullneighbor()
    logger.info('test_graphdata_getfullneighbor Ended.\n')
    test_graphdata_getnodefeature_input_check()
    logger.info('test_graphdata_getnodefeature_input_check Ended.\n')
    test_graphdata_getsampledneighbors()
    logger.info('test_graphdata_getsampledneighbors Ended.\n')
    test_graphdata_getnegsampledneighbors()
    logger.info('test_graphdata_getnegsampledneighbors Ended.\n')
    test_graphdata_graphinfo()
    logger.info('test_graphdata_graphinfo Ended.\n')
    test_graphdata_generatordataset()
    logger.info('test_graphdata_generatordataset Ended.\n')
