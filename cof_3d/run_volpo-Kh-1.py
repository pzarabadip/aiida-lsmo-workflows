import os
from aiida.common.example_helpers import test_and_get_code
from aiida.orm import DataFactory
from aiida.orm.data.base import Float
from aiida.orm.calculation.work import WorkCalculation
from aiida.work.run import submit
from aiida_lsmo_workflows.volpo_Kh import VolpoKh
ParameterData = DataFactory('parameter')
StructureData = DataFactory('structure')
SinglefileData = DataFactory('singlefile')
CifData = DataFactory('cif')

def dict_merge_ez(dict1, dict2):
    sumdicts = dict1.copy()
    sumdicts.update(dict2)
    return sumdicts

# Test the codes and specify the nodes and walltime
zeopp_code = test_and_get_code('zeopp@deneb', expected_code_type='zeopp.network')
raspa_code = test_and_get_code('raspa@deneb', expected_code_type='raspa')

zeopp_options = {
    "resources": {
        "num_machines": 1,
        "tot_num_mpiprocs": 1,
    },
    "max_wallclock_seconds": 3 * 60 * 60,
    "withmpi": False,
    }
raspa_options = {
    "resources": {
        "num_machines": 1,
        "tot_num_mpiprocs": 1,
    },
    "max_wallclock_seconds": 72 * 60 * 60,
    "withmpi": False,
    }

# Settings for Zeopp and Raspa (Widom calculation)
zeopp_probe_radius_co2_trappe = Float(1.525)
zeopp_probe_radius_n2_trappe = Float(1.655)
zeopp_atomic_radii_file = SinglefileData(file=os.path.abspath("./UFF.rad"))
raspa_params_dict = {
        "GeneralSettings":
        {
        "NumberOfCycles"                   : 100000,
        "PrintPropertiesEvery"             : 1000,  # info on henry coeff
        "Forcefield"                       : "LSMO_UFF-TraPPE",
        "CutOff"                           : 12.0,
        "ExternalTemperature"              : 300.0,
        },
}
raspa_co2_dict = {
        "Component":
        [{
        "MoleculeName"                     : "CO2",
        "MoleculeDefinition"               : "TraPPE",
        "WidomProbability"                 : 1.0,
        }],
}
raspa_n2_dict = {
        "Component":
        [{
        "MoleculeName"                     : "N2",
        "MoleculeDefinition"               : "TraPPE",
        "WidomProbability"                 : 1.0,
        }],
}
# Take the structures from a RobustGeoOptDdec calculation ans submit
with open('3dN.list') as f:
    ids=f.read().splitlines()
#ids = ['09000N']
prevWorkflow = '3DCOFs-600K-OptAngles'
for id in ids:
    q = QueryBuilder()
    q.append(StructureData, filters={'label': id}, tag='inp_struct')
    q.append(WorkCalculation, filters={'label':prevWorkflow},
                              output_of='inp_struct', tag='wf')
    q.append(CifData, edge_filters={'label': 'output_structure'},
                      output_of='wf')
    q.order_by({WorkCalculation:{'ctime':'desc'}})
    structure = q.all()[0][0] #take the last
    # Run for CO2, using UFF-TraPPE force field
    submit(VolpoKh,
        structure=structure,
        zeopp_code=zeopp_code,
        _zeopp_options=zeopp_options,
        zeopp_probe_radius=zeopp_probe_radius_co2_trappe,
        zeopp_atomic_radii=zeopp_atomic_radii_file,
        raspa_code=raspa_code,
        raspa_parameters=ParameterData(dict=dict_merge_ez(raspa_params_dict,raspa_co2_dict)),
        _raspa_options=raspa_options,
        _raspa_usecharges=True,
        _label='volpo-Kh-CO2-test1',
        )
    # Run for N2, using UFF-TraPPE force field
    submit(VolpoKh,
        structure=structure,
        zeopp_code=zeopp_code,
        _zeopp_options=zeopp_options,
        zeopp_probe_radius=zeopp_probe_radius_co2_trappe, #THIS IS A MISTAKE!!!!!!!!!!!!!
        zeopp_atomic_radii=zeopp_atomic_radii_file,
        raspa_code=raspa_code,
        raspa_parameters=ParameterData(dict=dict_merge_ez(raspa_params_dict,raspa_n2_dict)),
        _raspa_options=raspa_options,
        _raspa_usecharges=True,
        _label='volpo-Kh-N2-test1',
        )