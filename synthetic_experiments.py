from risk_averse_matching import hypergraph_matchings as hm
from risk_averse_matching import graph_generator as gg
import os
import time
import pickle

def parse(filename):
    return filename.split('-')

def mkdir_subdirec(sub_direc):
    abs_path = os.getcwd()
    full_path = '{}/{}'.format(abs_path, sub_direc)
    os.makedirs(full_path, exist_ok=True)

def gen_graph_strings():
    graphs = ['erdos', 'barabasi']
    edges = ['bernoulli', 'gaussian']
    param1 = ['uniform', 'gaussian', 'power']
    # param2 is used to set the variances for Gaussian, and probabilities for Bernoulli
    # inorder: variance prop to mean
    # inverse: high mean, low variance and vice versa
    param2 = ['uniform', 'gaussian', 'power', 'inorder', 'inverse']

    results = []
    for g in graphs:
        for e in edges:
            for p1 in param1:
                for p2 in param2:
                    results.append('{}-{}-{}-{}'.format(g, e, p1, p2))
    return results

def gen_params(graph_type=None, edge_distrib=None, param1_distrib=None, param2_distrib=None):
    g = {
        'erdos':{
            'vertices': 6000,
            'p': 0.005
        },
        'barabasi': {
            'vertices': 6000,
            'p': 0.005
        }
    }
    p1 = {
        # bernoulli weight parameter
        'bernoulli': {
            'uniform': {'min': 0, 'max': 1000, 'discrete': True},
            'gaussian': {'mu': 100, 'sigma': 50/3, 'discrete': True, 'min': 0},
            'power': {'alpha': 2, 'max_int': 100, 'discrete': True}
        },
        # gaussian mean parameter
        'gaussian': {
            'uniform': {'min': 0, 'max': 1000, 'discrete': False},
            'gaussian': {'mu': 100, 'sigma': 50/3, 'discrete': False, 'min': 0},
            'power': {'alpha': 2, 'max_int': 1000, 'discrete': False}
        }
    }
    p2 = {
        # bernoulli probability parameter
        'bernoulli': {
            'uniform': {'min': 0, 'max': 1, 'discrete': False},
            'gaussian': {'mu': 0.5, 'sigma': 0.5/3, 'discrete': False, 'min': 0, 'max': 1},
            'power': {'alpha': 2, 'max_int': 1, 'discrete': False},
            'inorder': {},
            'inverse': {}
        },
        # gaussian variance parameter
        'gaussian': {
            'uniform': {'min': 0, 'max': 100, 'discrete': False},
            'gaussian': {'mu': 50, 'sigma': 25/3, 'discrete': False, 'min': 0},
            'power': {'alpha': 2, 'max_int': 50, 'discrete': False},
            'inorder': {},
            'inverse': {}
        }
    }
    graph_vals = g[graph_type] if graph_type else None
    param1_vals = p1[edge_distrib][param1_distrib] if param1_distrib else None
    param2_vals = p2[edge_distrib][param2_distrib] if param2_distrib else None
    return graph_vals, param1_vals, param2_vals

def run_experiment(graph, intervals, edge_distrib, path=None, beta_var=False):
    g = hm.Hypergraph(graph, beta_var, edge_distribution=edge_distrib)
    print(g)

    print('maximum matching')
    _, max_stat = g.max_matching()
    g.print_stats(max_stat)

    print('bounded variance matching')
    beta_thresholds = g.gen_betas(intervals)
    bv_results = []
    for idx, beta in enumerate(beta_thresholds):
        bv_matching, bv_stat = g.bounded_matching(beta)
        bv_results.append(bv_stat)
        if path is not None:
            pickle.dump(bv_matching, open('{}/bv_matchings-{}.pkl'.format(path, idx), 'wb'))
        g.print_stats(bv_stat, beta)
    return max_stat, bv_results

def main():
    intervals = 20
    g_experiments = 4 # number of samples
    p1_experiments = 4 # number of samples
    p2_experiments = 4 # number of samples
    beta_var = True

    graphs = gen_graph_strings() # all combinations of graph parameters
    # total iterations = graph types w/o inorder and inverse param + graph types w/ inorder and inverse param
    #                  = (16 * 4 * 4 * 4) + (16 * 4 * 4 * 1)
    #                  = 1280 iterations
    # Note: takes between ~25-35 secs for each iteration
    # TODO: vary the parameters eg. alpha values
    total_time = 0
    for g_idx, graph_type in enumerate(graphs):
        g, e, p1, p2 = parse(graph_type) # graph parameters
        for g_sample in range(g_experiments):
            g_param, _, _ = gen_params(graph_type=g)
            graph = gg.gen_graph(g, g_param)
            for p1_sample in range(p1_experiments):
                _, p1_param, _ = gen_params(edge_distrib=e, param1_distrib=p1)
                graph_p1 = gg.gen_attrib(graph, e, param1_distrib=p1, param1=p1_param)
                for p2_sample in range(p2_experiments):
                    start = time.time()
                    # skip 'inorder' and 'inverse' after 1 iteration
                    if (p2 == 'inorder' or p2 == 'inverse') and p2_sample > 0:
                        break
                    _, _, p2_param = gen_params(edge_distrib=e, param2_distrib=p2)
                    print(e, p1, p2)
                    graph_p1_p2 = gg.gen_attrib(graph_p1, e, param2_distrib=p2, param2=p2_param)

                    print(g_idx, graph_type, g_sample, p1_sample, p2_sample)
                    print('{} edges in synthethic graph. first edge: {}'.format(len(graph_p1_p2), graph_p1_p2[0]))
                    p1_attrib = 'weight' if e == 'bernoulli' else 'expected_weight'
                    p2_attrib = 'probability' if e == 'bernoulli' else 'variance'
                    avg_p1 = sum(e[p1_attrib] for e in graph_p1_p2)/len(graph_p1_p2)
                    avg_p2 = sum(e[p2_attrib] for e in graph_p1_p2)/len(graph_p1_p2)
                    print('{} avg {} and {} avg {}'.format(avg_p1, p1_attrib, avg_p2, p2_attrib))

                    max_stats, bv_stats = run_experiment(graph_p1_p2, intervals, e, beta_var=beta_var)
                    path = 'data/synthetic-graphs-variance/{}-{}-{}-{}_{}{}{}/'.format(g, e, p1, p2, g_sample, p1_sample, p2_sample) if beta_var else 'data/synthetic-graphs-standard-deviation/{}-{}-{}-{}_{}{}{}/'.format(g, e, p1, p2, g_sample, p1_sample, p2_sample)
                    print('Finished finding bounded variance matchings')
                    mkdir_subdirec(path)
                    f = path + 'max_stats.pkl'
                    pickle.dump(max_stats, open(f, 'wb'))
                    f = path + 'bv_stats.pkl'
                    pickle.dump(bv_stats, open(f, 'wb'))

                    t = time.time() - start
                    total_time += t
                    print('{} sec {} total_time\n'.format(t, total_time))


if __name__ == '__main__':
    main()
