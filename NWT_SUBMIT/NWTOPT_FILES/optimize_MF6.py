import os
import time
import fileinput
import numpy as np
from subprocess import call
from shutil import copyfile, rmtree
import argparse
import pandas as pd
from hyperopt import fmin, rand, atpe, tpe, hp, STATUS_OK, Trials
from hyperopt.mongoexp import MongoTrials
import objective
from functools import partial

cwd = os.getcwd()
# print(cwd[0:-12])
# for file in os.listdir(os.path.join(cwd[0:-12], 'PROJECT_FILES')):
#     if file.endswith('.nam'):
#         namefile = file

try:
    os.mkdir(os.path.join(os.path.join(cwd[0:-12], 'PROJECT_FILES'), 'nwts'))
except:
    rmtree(os.path.join(os.path.join(cwd[0:-12], 'PROJECT_FILES'), 'nwts'))
    os.mkdir(os.path.join(os.path.join(cwd[0:-12], 'PROJECT_FILES'), 'nwts'))

hparams = [
    #OPTIONS PARAMETERS
    hp.choice('no_ptc',
        [
            'first','all'
        ]), #0
    hp.uniform('ats_outer_maximum_fraction', 0.0, 0.5), #1
    #NONLINEAR PARAMETERS 
    hp.uniform('outer_dvclose', .001, 5.), #2
    hp.quniform('outer_maximum', 1, 500, 1), #3
    hp.choice('under_relaxation', #4
        [
            {'under_relaxation':'none'},
            {'under_relaxation': 'simple',
                'under_relaxation_gamma': hp.uniform('under_relaxation_gamma',0.01,1),

            },
            {'under_relaxation': 'cooley',
                'under_relaxation_gamma': hp.uniform('under_relaxation_gamma',0.0,1)

            },
            {'under_relaxation': 'dbd',
                'under_relaxation_gamma': hp.uniform('under_relaxation_gamma',0.0,1),
                'under_relaxation_theta': hp.uniform('under_relaxation_theta',0.2,0.99),
                'under_relaxation_kappa': hp.uniform('under_relaxation_kappa',0.03,0.3),
                'under_relaxation_momentum': hp.uniform('under_relaxation_momentum',0.03,0.3)

            }
        ]),
    hp.choice('backtracking_number', #5
        [
            {'backtracking_number': 0},
            {'backtracking_number': hp.quniform(1,20,1),
                'backtracking_tolerance': hp.loguniform('backtracking_tolerance', np.log(1.0), np.log(1.0e6)),
                'backtracking_reduction_factor': hp.uniform('backtracking_reduction_factor', 0.1, 0.3),
                'backtracking_residual_limit': hp.uniform('backtracking_residual_limit', 5, 100)                
            }
        ]),
    #LINEAR PARAMETERS 
    hp.quniform('inner_maximum', 40, 650, 1),#6
    hp.uniform('inner_dvclose', 1.0e-7, 1.0),#7
    hp.uniform('inner_rclose', 1.0e-1, 1.0e7),#8
    # NOTE: skipping rclose_option because very units dependent
    hp.choice('linear acceleration', [ #9
        'CG', 'BICGSTAB'
    ]),
    hp.choice('relaxation_factor', #10
        [
            {'relaxation_factor':0.0},
            {'relaxation_factor':hp.uniform('relaxation_factor',0.9,1.0)}
        ]),
    
    hp.choice('preconditioner_drop_tolerance', #11
        [
            {'preconditioner_drop_tolerance':0.0},
            {'preconditioner_drop_tolerance':hp.uniform('preconditioner_drop_tolerance',1e-5, 1e-3),
            'preconditioner_levels':hp.quniform('preconditioner_levels',6,9,1),
            }
        ]),
    hp.choice('number_orthogonalizations', #12
        [
            {'number_orthogonalizations':0},
            {'number_orthogonalizations':hp.quniform('number_orthogonalizations',14,10,1)
            }
        ]),
    hp.choice('scaling_method', #13
        [
            'none','diagonal','polcg','l2norm'
        ]),
    hp.choice('reordering_method', #14
        [
            'none','rcm','md'
        ])
]

def trials2csv(trials):
    df = pd.DataFrame(trials, columns=['result'])
    df.to_csv(os.path.join(os.getcwd(), 'nwt_performance.csv'))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Pull NWTs from DB')
    parser.add_argument('--ip', metavar='N', type=str, help='ip address of DB')
    parser.add_argument('--port', type=str, help='port of DB')
    parser.add_argument('--key', type=str, help='key of job you want to pull')
    parser.add_argument('--random', type=bool, required=False, default=False)
    parser.add_argument('--trials', type=int, help='num trials you would like to run')
    parser.add_argument('--mf6', type=bool, required=False, default=False,
                        help='flag for MODFLOW6 if True, else MODFLOW-NWT.')
    
    args = parser.parse_args()
    trials = MongoTrials('mongo://'+ args.ip + ':'+ args.port + '/db/jobs', exp_key=args.key)
    try:
        os.remove(os.path.join(os.getcwd(), 'nwts/imsnum.txt'))
    except:
        pass
    with open(os.path.join(os.getcwd(), 'nwts/imsnum.txt'), 'w+') as f:
        f.write('0')
    if args.random == False:
        print('TPE Run')
        bestHp = fmin(fn=objective.objective,
                      space=hparams,
                      max_queue_len=3,
                      algo=tpe.suggest,
                      max_evals=args.trials,
                      trials=trials)
    else:
        bestRandHp = fmin(fn=objective.objective,
                      space=hparams,
                      max_queue_len=3,
                      algo=rand.suggest,
                      max_evals=args.trials,
                      trials=trials)
