import os
import time
import fileinput
from datetime import datetime
from subprocess import call, Popen, run, STDOUT, check_output, TimeoutExpired
import subprocess
from threading import Timer
from shutil import copyfile, rmtree
import pandas as pd
from hyperopt import STATUS_OK
import math

global timelim
timelim = None


global timelim
timelim = None

def inputHp2mf6(inputHp):
    global cwd
    global namefile
    global initsol
    global SOLNUM
    with open(os.path.join(cwd, 'imsfiles', 'solnum.txt'), 'r+') as f:
        SOLNUM = int(f.read())
        f.seek(0)
        f.truncate()
        f.write(str(SOLNUM+1))
    with open(os.path.join(cwd, 'imsfiles', ('ims_{}.ims'.format(SOLNUM))), 'w') as file:
        # write options block
        file.write('BEGIN OPTIONS\n')
        file.write(f'PRINT_OPTION ALL\nNO_PTC {inputHp[0]}\nATS_OUT_MAXIMUM_FRACTION {inputHp[1]}\n')
        file.write('END OPTIONS\n')

        # write NONLINEAR BLOCK
        file.write('BEGIN NONLINEAR\n')
        file.write(f'OUTER_DVCLOSE {inputHp[2]}\nOUTER_MAXIMUM {inputHp[3]}\n')
        # write out all the options under under_relaxation
        [file.write(f'{k.upper()} {val}\n') for k,val in inputHp[4].items()]
        # write out all the options under backtracking_number
        [file.write(f'{k.upper()} {val}\n') for k,val in inputHp[5].items()]
        file.write('END NONLINEAR\n')

        # write LINEAR block
        file.write('BEGIN LINEAR\n')
        file.write(f'INNER_MAXIMUM {inputHp[6]}\nINNER_DVCLOSE {inputHp[7]}\n')
        file.write(f'INNER_RCLOSE{inputHp[8]}\nLINEAR_ACCELERATION {inputHp[9]}\n')
        # write out all the options under relaxation_factor
        [file.write(f'{k.upper()} {val}\n') for k,val in inputHp[10].items()]        
        # write out all the options under preconditioner_drop_tolerance
        [file.write(f'{k.upper()} {val}\n') for k,val in inputHp[11].items()]        
        # write out all the options under number_orthogonalizations
        [file.write(f'{k.upper()} {val}\n') for k,val in inputHp[12].items()]        
        file.write(f'SCALING_METHOD{inputHp[13]}\REORDERING_METHOD {inputHp[14]}\n')
        file.write('END LINEAR\n')
        
    # print('[INFO] pulling nwt from', os.path.join(cwd, 'nwts', ('nwt_{}.nwt'.format(SOLNUM))))
    return os.path.join(cwd, 'nwts', ('nwt_{}.ims'.format(SOLNUM)))

def inputHp2nwt(inputHp):
    global cwd
    global namefile
    global initsol
    global SOLNUM
    with open(os.path.join(cwd, 'nwts', 'solnum.txt'), 'r+') as f:
        SOLNUM = int(f.read())
        f.seek(0)
        f.truncate()
        f.write(str(SOLNUM+1))
    with open(os.path.join(cwd, 'nwts', ('nwt_{}.nwt'.format(SOLNUM))), 'w') as file:
        file.write(('{} {} {} {} {} {} {} {} CONTINUE {} {} {} {} {} {} {} {}'.format(inputHp[1], inputHp[2], int(inputHp[3]), inputHp[4], inputHp[0]['linmeth'], inputHp[5],
                   inputHp[6], inputHp[7], inputHp[8], inputHp[9], inputHp[10], inputHp[11],
                   inputHp[12], int(inputHp[13]), inputHp[14], inputHp[15])) + '\n')
    if inputHp[0]['linmeth'] == 1:
        with open(os.path.join(cwd, 'nwts', ('nwt_{}.nwt'.format(SOLNUM))), 'a') as file:
           file.write(('{} {} {} {} {}'.format(int(inputHp[0]['maxitinner']), inputHp[0]['ilumethod'], int(inputHp[0]['levfill']),
                      inputHp[0]['stoptol'], int(inputHp[0]['msdr']))))
    elif inputHp[0]['linmeth'] == 2:
        with open(os.path.join(cwd, 'nwts', ('nwt_{}.nwt'.format(SOLNUM))), 'a') as file:
           file.write(('{} {} {} {} {} {} {} {} {} {}'.format(inputHp[0]['iacl'], inputHp[0]['norder'], int(inputHp[0]['level']),
                      int(inputHp[0]['north']), inputHp[0]['iredsys'], inputHp[0]['rrctols'],
                      inputHp[0]['idroptol'], inputHp[0]['epsrn'], inputHp[0]['hclosexmd'],
                      int(inputHp[0]['mxiterxmd']))))
    # print('[INFO] pulling nwt from', os.path.join(cwd, 'nwts', ('nwt_{}.nwt'.format(SOLNUM))))
    return os.path.join(cwd, 'nwts', ('nwt_{}.nwt'.format(SOLNUM)))


def trials2csv(trials):
    global cwd
    global namefile
    df = pd.DataFrame(trials.results).drop('loss', axis=1)
    df.to_csv(os.path.join(cwd, 'nwt_performance.csv'))

def runModel(pathtosol, initsol):
    global cwd
    global namefile
    global timelim
    copyfile(pathtosol, os.path.join(cwd, initsol))
    last_line = ""
    run_command = ""
    use_timer = True
    use_next = False
    with open(os.path.join(cwd, 'run.sh')) as f:
        for line in f:
            if use_next:
                run_command = line
                use_next = False
            elif line.startswith('# Run Command:'):
                use_next = True
            last_line = line
    try:
        timelim = float(last_line) * 60
        print(f'[INFO] Timeout for model run is set to {timelim / 60} minutes')
    except Exception as e:
        timelim = None
        use_timer = False
        print('[INFO] No timeout set for model run')
    print(f'[INFO] Using run command: {run_command.strip()}')
    print(f'[INFO] Starting run out of {cwd}')

    try:
        modflowProcess = run(run_command.strip().split(' '), cwd = cwd, capture_output = True, timeout = timelim)
        print(str(modflowProcess.stdout, 'utf-8'), '\n', str(modflowProcess.stderr, 'utf-8'))
        print("[INFO] Successful termination of trial")
        return True
    except TimeoutExpired:
        print('[WARNING] Time Limit reached, terminating run')
        return False

def getdata(mf6=False):
    # mf6 (bool) True indicates read MF6 output, False indicates read NWT output
    global cwd
    global namefile
    global listfile
    mbline, timeline, iterline = '', '', ''
    mbfound = False
    for line in reversed(open(os.path.join(cwd, listfile), 'r') .readlines()):
        if 'Error in Preconditioning' in line:
            return 999999, -1, 999999
        if 'PERCENT DISCREPANCY' in line.upper() and mbfound == False:
            mbfound = True
            mbline = line
        if mf6 is False:
            # only get runtime from LST file if NWT - for MF6, need to read mfsim.list
            if 'elapsed run time' in line.lower():
                timeline = line
        #TODO: is there an OUTER ITERATIONS line in MF6?
        if 'OUTER ITERATIONS' in line.upper():
            iterline = line
            break
    if mf6 is True:
        # special case to read elapsed time from mfsim.lst if MF6 model (that filename cannot change)
        mf6lst = reversed(open('mfsim.lst', 'r').readlines())
        try:
            timeline = [i for i in mf6lst if 'elapsed run time' in i.lower()][0]
        except:
            pass
    if timeline == '':
        return 999999, -1, 999999

    for val in mbline.split(' '):
        try:
            mass_balance = float(val)
            break
        except:
            pass
    foundmin, foundsec, foundhour = False, False, False
    min, sec, hrs, days = 0, 0, 0, 0
    for val in reversed(timeline.split(' ')):
        if foundsec == False:
            try:
                sec = float(val)
                foundsec = True
            except:
                pass
        elif foundmin == False:
            try:
                min = float(val)
                foundmin = True
            except:
                pass
        elif foundhour == False:
            try:
                hrs = float(val)
                foundhour = True
            except:
                pass
        else:
            try:
                days = float(val)
                break
            except:
                pass

    sec_elapsed = days * 24 * 3600 + hrs * 3600 + min * 60 + sec
    if sec_elapsed == 0:
        print('[ERROR] bad run')
        return 999999, -1, 999999
    for val in iterline.split(' '):
        try:
            iterations = float(val)
            break
        except:
            pass
    try:
        print('[MASS BALANCE]:', mass_balance)
        print('[SECONDS]:', sec_elapsed)
        print('[TOTAL ITERATIONS]:', iterations)
        return sec_elapsed, iterations, mass_balance
    except:
        print('[ERROR] bad run')
        return 999999, -1, 999999

def objective(inputHp, mf6=False):
    global cwd
    global namefile
    global listfile
    global initsol
    global timelim
    eval_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cwd = os.path.join(os.sep + os.path.join(*os.getcwd().split(os.sep)[0:-1]), os.path.join('NWT_SUBMIT','PROJECT_FILES'))
    for file in os.listdir(cwd):
        if mf6:
            namefile = 'mfsim.nam'
        else:
            if file.endswith('.nam') & file != 'mfsim.nam':
                namefile = file
        elif file.endswith('.list') or file.endswith('.lst') and 'mfsim' not in file:
            listfile = file
        elif file.endswith('.nwt'):
            initsol = file
        elif file.endswith('.ims'):
            initsol = file
    
    for line in open(os.path.join(cwd, namefile)).readlines():
        for e in line.strip().split(' '):
            if e.lower().endswith('.list') or e.endswith('.lst'):
                listfile = e.strip()
            elif e.lower().endswith('.nwt'):
                initsol = e.strip()
            elif e.lower().endswith('.ims'):
                initsol = e.strip()

    if mf6:
        pathtosol = inputHp2mf6(inputHp)
    else:
        pathtosol = inputHp2nwt(inputHp)
    if not runModel(pathtosol, initsol):
        ret_dict = {'loss': 999999999999,
                    'status':  STATUS_OK,
                    'eval_time': eval_time,
                    'mass_balance': 999999,
                    'sec_elapsed': timelim,
                    'iterations': -1,
                    'NWT Used': pathtosol,
                    'finish_time': finish_time}
        if mf6:
            junk = ret_dict.pop('NWT Used') 
            ret_dict['IMS Used'] = pathtosol
        return ret_dict

    sec_elapsed, iterations, mass_balance = getdata()
    if mass_balance == 999999:
        loss = 999999999999
    else:
        loss = math.exp(mass_balance ** 2) * sec_elapsed
    finish_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    ret_dict = {'loss': loss,
                'status':  STATUS_OK,
                'eval_time': eval_time,
                'mass_balance': mass_balance,
                'sec_elapsed': sec_elapsed,
                'iterations': iterations,
                'NWTUsed': pathtosol,
                'finish_time': finish_time}
    if mf6:
        junk = ret_dict.pop('NWT Used') 
        ret_dict['IMS Used'] = pathtosol
    return ret_dict