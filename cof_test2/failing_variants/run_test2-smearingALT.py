from aiida.common.example_helpers import test_and_get_code  # noqa
from aiida.orm.data.base import Float
from aiida.work.run import submit
from ase.io import read
from glob import glob
from os import path
from aiida_lsmo_workflows.cellopt_charges import Cp2kCellOptDdecWorkChain
ParameterData = DataFactory('parameter')
StructureData = DataFactory('structure')

# Test the codes and specify the nodes and walltime
cp2k_code = test_and_get_code('cp2k-5.1@gacrux', expected_code_type='cp2k')
ddec_code = test_and_get_code('ddec@fidis', expected_code_type='ddec')
cp2k_options = {
    "resources": {
        "num_machines": 7,
    },
    "max_wallclock_seconds": 72 * 60 * 60,
    }
ddec_options = {
    "resources": {
        "num_machines": 1,
    },
    "max_wallclock_seconds": 24 * 60 * 60,
    "withmpi": False,
    }

# Set the settings for CP2K

''' First CELL_OPT (Stage1), hardcoded
params_dict = {
        'MOTION':{
            'CELL_OPT': {
                'MAX_ITER': 20,
                'KEEP_ANGLES' : True,
            },
        },
}
'''
params_dict = {
    'FORCE_EVAL': {
        'DFT': {
            'MGRID': {
                'CUTOFF':     1000,                                             # STD=600
                },
            'SCF': {
                'EPS_SCF': 1.0E-5,
                'MAX_SCF': 2000,
                'MAX_ITER_LUMO': 10000,
                'ADDED_MOS': 1000,
                'SMEAR': {
                    '_': 'ON',
                    'METHOD': 'FERMI_DIRAC',
                    'ELECTRONIC_TEMPERATURE': '[K] 300',
                    },
                'DIAGONALIZATION': {
                    '_': True,
                    'ALGORITHM': 'STANDARD'
                    },
                'OT': {
                    '_': False,
                    },
                'OUTER_SCF': {
                    '_': False,
                    },
                'MIXING': {
                    '_': True,
                    'METHOD': 'BROYDEN_MIXING',
                    'ALPHA': 0.2,                                               # STD=0.4
                    'NBROYDEN': 8,
                    },
                },
            },
        },
    'MOTION': {
        'MD': {
            'ENSEMBLE': 'NPT_F',                    #main options: NVT, NPT_F
            'STEPS': 0,                             #default: 3                 # STD=100
            'TIMESTEP': '[fs] 0.5',                 #default: [fs] 0.5
            'TEMPERATURE': '[K] 400',               #default: [K] 300
            'DISPLACEMENT_TOL': '[angstrom] 1.0',   #default: [bohr] 100
            'THERMOSTAT' : {
                'REGION': 'GLOBAL',                 #default: GLOBAL
                'TYPE': 'CSVR',
                'CSVR': {
                    'TIMECON': 0.1,                 #default: 1000, use: 0.1 for equilibration, 50~100 for production
                },
            },
            'BAROSTAT': {                           #by default the barosthat uses the same thermo as the partricles
                'PRESSURE': '[bar] 1.0',            #default: 0.0
                'TIMECON': '[fs] 500',              #default: 1000, good for crystals
            },
        },
        'CELL_OPT': {
            'OPTIMIZER': 'LBFGS',                    #default: BFGS
            'LBFGS' : {
                'TRUST_RADIUS': '[angstrom] 0.2',     #default: None            # STD=0.5
            },
            'MAX_ITER': 1000,
            'KEEP_ANGLES' : False,
        },
    },
}
cp2k_parameters = ParameterData(dict=params_dict)

# Using lists to specify the IDs
ids=['13161N2','18081N2','18082N2'] #12Mar, 7cpus@gacrux

all_structures = [ "/home/daniele/Documents/CoRE-COFs/cifs/{}.cif".format(x) for x in ids]
# Submit the calculations
for s in all_structures:
    print('SUBMITTING: %s '%s)
    s_ase = read(s)
    structure = StructureData(ase=s_ase)
    structure.label = s.split('/')[-1].split('.')[0]
    structure.store()
    submit(Cp2kCellOptDdecWorkChain,
        structure=structure,
        cp2k_code=cp2k_code,
        cp2k_parameters=cp2k_parameters,
        _cp2k_options=cp2k_options,
        ddec_code=ddec_code,
        _ddec_options=ddec_options,
        _label='test2-smearingALT',
        _guess_multiplicity=True,
        min_cell_size=Float(5.0)
        )