# -*- coding: utf-8 -*-
"""Run example isotherm calculation with HKUST1 framework."""
from __future__ import absolute_import
from __future__ import print_function
import os
import sys
import click

from aiida.engine import run
from aiida.common import NotExistent
from aiida.plugins import DataFactory, WorkflowFactory
from aiida.orm import Code, Dict, Float, Int, Str, SinglefileData

# Workchain objects
IsothermWorkChain = WorkflowFactory('lsmo.isotherm')  # pylint: disable=invalid-name

# Data objects
CifData = DataFactory('cif')  # pylint: disable=invalid-name
NetworkParameters = DataFactory('zeopp.parameters')  # pylint: disable=invalid-name


@click.command('cli')
@click.argument('raspa_code_label')
@click.argument('zeopp_code_label')
def main(raspa_code_label, zeopp_code_label):
    """Prepare inputs and submit the Isotherm workchain.
    Usage: verdi run run_isotherm_hkust1.py raspa@localhost network@localhost"""

    builder = IsothermWorkChain.get_builder()

    builder.metadata.label = "test"

    builder.raspa_base.raspa.code = Code.get_from_string(raspa_code_label)
    builder.zeopp.code = Code.get_from_string(zeopp_code_label)

    options = {
        "resources": {
            "num_machines": 1,
            "tot_num_mpiprocs": 1,
        },
        "max_wallclock_seconds": 1 * 60 * 60,
        "withmpi": False,
    }

    builder.raspa_base.raspa.metadata.options = options
    builder.zeopp.metadata.options = options

    builder.structure = CifData(file=os.path.abspath('data/HKUST-1.cif'), label="HKUST1")
    builder.molecule = Str('co2')
    builder.forcefield = Str('UFF-TraPPE')
    builder.structure_radii = Str('UFF')
    builder.temperature = Float(400)           # Higher temperature will have less adsorbate and it is faster
    builder.zeopp_volpo_samples = Int(1000)    # Default: 1e5 *NOTE: default is good for standard real-case!
    builder.zeopp_block_samples = Int(10)      # Default: 100
    builder.raspa_widom_cycles = Int(100)      # Default: 1e5
    builder.raspa_gcmc_init_cycles = Int(10)   # Default: 1e3
    builder.raspa_gcmc_prod_cycles = Int(100)  # Default: 1e4
    builder.pressure_range = List(list=[0.01, 10])

    run(builder)

if __name__ == '__main__':
    main()  # pylint: disable=no-value-for-parameter

# EOF
