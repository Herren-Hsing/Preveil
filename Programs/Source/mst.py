import sys
import os
import subprocess
import itertools
import random
import re
from logger import print_to_log
from cdp2adp import cdp_rho
import numpy as np
from mbi import FactoredInference, Dataset, Domain
from scipy import sparse
from disjoint_set import DisjointSet
import networkx as nx
import itertools
from scipy.special import logsumexp
import argparse

prng = np.random.default_rng()

#-----------------------------add--------------------------------
PATH_MPC = "../../mp-spdz-0.3.8/"
PATH_RESULT = "../../mp-spdz-0.3.8/"
PATH_RESULT2 = "./"
PROTOCOL = "mascot"
#-------------------------------------------------------------

#-----------------------------add--------------------------------
def read_final_results(file_path):
    with open(file_path, 'r') as file:
        content = file.read()
    
    start_index = content.find('Final:') + len('Final:') + 1
    if start_index == -1:
        return np.array([])
    
    final_data = content[start_index:]
    final_data = re.findall(r'\[([^]]*)\]', final_data)
    final_numbers = []
    for item in final_data:
        try:
            number = float(item.strip())
            final_numbers.append(number)
        except ValueError as e:
            continue
    return np.array(final_numbers)
#-------------------------------------------------------------
def MST(alice,bob, epsilon, delta):
    rho = cdp_rho(epsilon, delta)
    sigma = np.sqrt(3/(2*rho))
    cliques_1 = [(col,) for col in alice.domain]
    print_to_log(f"cliques_1:",cliques_1)
    cliques_2 = list(itertools.combinations(alice.domain, 2))
    print_to_log(f"cliques_2:", cliques_2)    

    log1 = measure(alice,bob, cliques_1, sigma)
    log2 = measure(alice,bob,cliques_2,sigma)
    print_to_log(f"measure succeed!")
    print_to_log(f"compress succeed!")
    cliques = select(alice,rho/3.0, log1,log2)
    log3 = measure(alice,bob, cliques, sigma)
    engine = FactoredInference(data.domain, iters=5000)
    est = engine.estimate(log1 + log3)
    synth = est.synthetic_data()
    return synth

def measure(alice,bob, cliques, sigma, weights=None):
    if weights is None:
        weights = np.ones(len(cliques))
    weights = np.array(weights) / np.linalg.norm(weights)
    measurements = []
    for proj, wgt in zip(cliques, weights):
        alice_x = alice.project(proj).datavector()
        bob_x = bob.project(proj).datavector()
        # Generate alice_y and bob_y
        alice_y = alice_x + np.random.normal(loc=0, scale=sigma/(wgt*np.sqrt(2)), size=alice_x.size)
        bob_y = bob_x + np.random.normal(loc=0, scale=sigma/(wgt*np.sqrt(2)), size=alice_x.size)
        num_workloads = len(alice_y)
        # print_to_log the shape and type of alice_y and bob_y
        print_to_log("Shape of alice_y: ", np.shape(alice_y))
        print_to_log("Shape of bob_y: ", np.shape(bob_y))
        #-----------------------------add--------------------------------

        with open(PATH_MPC+'Player-Data/Input-P0-0', 'w') as outfile:
            outfile.write('\n'.join(str(num) for num in alice_y))
        with open(PATH_MPC+'Player-Data/Input-P1-0', 'w') as outfile:
            outfile.write('\n'.join(str(num) for num in bob_y))
        run_cmd = "cd "+ PATH_MPC +" && Scripts/compile-run.py -E " + str(PROTOCOL) + " /home/judy/Preveil/Programs/Source/safe_addition.mpc " + str(num_workloads) + " > "+ PATH_RESULT2 +"mpc_out.txt"
        os.system(run_cmd)
        output_file_path = PATH_RESULT + "mpc_out.txt"
        with open(output_file_path, 'r') as file:
            content = file.read()
        print_to_log(content)
        #-------------------------------------------------------------
        results_array = read_final_results(output_file_path)
        print_to_log("results_array",results_array)
        y= results_array
        print_to_log("y",y)
        Q = sparse.eye(y.size)
        measurements.append( (Q, y, sigma/wgt, proj) )
    return measurements

def select(alice,rho, measurement_log_1,measurement_log_2,cliques=[]):
    engine_1 = FactoredInference(alice.domain, iters=1000)
    est_1 = engine_1.estimate(measurement_log_1)
   
    weights = {}
    candidates = list(itertools.combinations(alice.domain.attrs, 2))
    print_to_log(f"candidates:",candidates)
    i = 0
    for a, b in candidates:
        xhat = est_1.project([a, b]).datavector()
        print_to_log(f"a, b: {a}, {b}, xhat shape: {xhat.shape}")
        
        y = measurement_log_2[i][1]
        i = i + 1
        xhat = est_1.project([a, b]).datavector()
        weights[a,b] = np.linalg.norm(xhat - y, 1)

    T = nx.Graph()
    T.add_nodes_from(data.domain.attrs)
    ds = DisjointSet()

    for e in cliques:
        T.add_edge(*e)
        ds.union(*e)

    r = len(list(nx.connected_components(T)))
    epsilon = np.sqrt(8*rho/(r-1))
    for i in range(r-1):
        candidates = [e for e in candidates if not ds.connected(*e)]
        wgts = np.array([weights[e] for e in candidates])
        idx = np.argmax(wgts)
        e = candidates[idx]
        T.add_edge(*e)
        ds.union(*e)

    return list(T.edges)

def default_params():
    params = {}
    params['dataset'] = '../data/adult.csv'
    params['domain'] = '../data/adult-domain.json'
    params['epsilon'] = 1.0
    params['delta'] = 1e-9
    params['degree'] = 2
    params['num_marginals'] = None
    params['max_cells'] = 10000
    params['save'] = '../data/final.csv'
    params['csv_path1'] = '../data/alice_adult.csv'
    params['json_path1'] = '../data/alice_adult-domain.json'
    params['csv_path2'] = '../data/bob_adult.csv'
    params['json_path2'] = '../data/bob_adult-domain.json'
    params['result_value'] = '../data/result.txt'
    return params


if __name__ == '__main__':

    description = ''
    formatter = argparse.ArgumentDefaultsHelpFormatter
    parser = argparse.ArgumentParser(description=description, formatter_class=formatter)
    parser.add_argument('--dataset', help='dataset to use')
    parser.add_argument('--domain', help='domain to use')
    parser.add_argument('--epsilon', type=float, help='privacy parameter')
    parser.add_argument('--delta', type=float, help='privacy parameter')
    parser.add_argument('--degree', type=int, help='degree of marginals in workload')
    parser.add_argument('--num_marginals', type=int, help='number of marginals in workload')
    parser.add_argument('--max_cells', type=int, help='maximum number of cells for marginals in workload')
    parser.add_argument('--save', type=str, help='path to save synthetic data')
    parser.add_argument('--csv_path1', type=str, help='path to alice csv file')
    parser.add_argument('--json_path1', type=str, help='path to alice json file')
    parser.add_argument('--csv_path2', type=str, help='path to bob csv file')
    parser.add_argument('--json_path2', type=str, help='path to bob json file')
    parser.add_argument('--result_value', type=str, help='path to result value file')
    
    
    parser.set_defaults(**default_params())
    args = parser.parse_args()
    
    alice = Dataset.load(args.csv_path1, args.json_path1)
    bob = Dataset.load(args.csv_path2, args.json_path2)
    data = Dataset.load(args.dataset, args.domain)

    workload = list(itertools.combinations(data.domain, args.degree))
    workload = [cl for cl in workload if data.domain.size(cl) <= args.max_cells]
    if args.num_marginals is not None:
        workload = [workload[i] for i in prng.choice(len(workload), args.num_marginals, replace=False)]

    synth = MST(alice, bob, args.epsilon, args.delta)
  
    if args.save is not None:
        synth.df.to_csv(args.save, index=False)
 
    errors = []
    for proj in workload:
        X = data.project(proj).datavector()
        Y = synth.project(proj).datavector()
        e = 0.5*np.linalg.norm(X/X.sum() - Y/Y.sum(), 1)
        errors.append(e)
    print_to_log('Average Error: ', np.mean(errors))
    avg_error = np.mean(errors)
    with open(args.result_value, 'w') as f:
        f.write(f'{avg_error}')