# -*- coding: utf-8 -*-

from __future__ import absolute_import

from aiida.common import AttributeDict
from aiida.engine import WorkChain, ToContext
from aiida.plugins import CalculationFactory, DataFactory
from aiida_cp2k.workchains import Cp2kMultistageWorkChain
from aiida_ddec.workchains import Cp2kDdecWorkChain

DdecCalculation = CalculationFactory('ddec')  # pylint: disable=invalid-name
CifData = DataFactory('cif')  # pylint: disable=invalid-name
ZeoppCalculation = CalculationFactory("zeopp.network")  # pylint: disable=invalid-name
NetworkParameters = DataFactory("zeopp.parameters")  # pylint: disable=invalid-name

zeopp_parameters_default = NetworkParameters(dict={ #Default parameters for microporous materials
    'ha': 'DEF',                   # Using high accuracy (mandatory!)
    'res': True,                   # Max included, free and incl in free sphere
    'sa': [1.86, 1.86, 100000],    # Nitrogen probe to compute surface
    'vol': [0.0, 0.0, 1000000],    # Geometric pore volume
    'volpo': [1.86, 1.86, 100000], # Nitrogen probe to compute PO pore volume
    'psd': [1.2, 1.2, 10000]       # Small probe to compute the pore size distr
})

class ZeoppMultistageDdecWorkChain(WorkChain):
    """A workchain that combines: Zeopp + Cp2kMultistageWorkChain + Cp2kDdecWorkChain + Zeopp"""

    @classmethod
    def define(cls, spec):
        """Define workflow specification."""
        super(ZeoppMultistageDdecWorkChain, cls).define(spec)

        spec.expose_inputs(ZeoppCalculation,
            namespace='zeopp',
            exclude=['parameters','structure'])
        spec.input('zeopp.parameters',
            valid_type=NetworkParameters,
            default=zeopp_parameters_default,
            required=False,
            help='parameters for zeo++')
        spec.input('structure',
            valid_type=CifData,
            help='input structure')
        spec.expose_inputs(Cp2kMultistageWorkChain,
            exclude=['structure'])
        spec.expose_inputs(Cp2kDdecWorkChain,
            exclude=['cp2k_base'])

        spec.outline(
            cls.run_zeopp_before,
            cls.run_cp2kmultistage,
            cls.run_cp2kddec,
            cls.run_zeopp_after,
            cls.return_results)

        spec.expose_outputs(ZeoppCalculation,
            namespace='zeopp_before_opt',
            include=['output_parameters'])

        spec.expose_outputs(ZeoppCalculation,
            namespace='zeopp_after_opt',
            include=['output_parameters'])

        spec.expose_outputs(Cp2kMultistageWorkChain,
            exclude=['output_structure'])
        spec.expose_outputs(Cp2kDdecWorkChain,
            include=['structure_ddec'])

    def run_zeopp_before(self):
        """ un Zeo++ for the starting structure"""
        #Merging all inputs
        zeopp_inp = AttributeDict(self.exposed_inputs(ZeoppCalculation, 'zeopp'))
        zeopp_inp['parameters'] = self.inputs.zeopp.parameters
        zeopp_inp['structure'] = self.inputs.structure

        running_zeopp = self.submit(ZeoppCalculation, **zeopp_inp)
        self.report("Running Zeo++ calculation <{}>".format(running_zeopp.pk))
        return ToContext(zeopp_before=running_zeopp)

    def run_zeopp_after(self):
        """Run Zeo++ for the starting structure"""
        #Merging all inputs
        zeopp_inp = AttributeDict(self.exposed_inputs(ZeoppCalculation, 'zeopp'))
        zeopp_inp['parameters'] = self.inputs.zeopp.parameters
        zeopp_inp['structure'] = self.ctx.cp2k_ddec_wc.outputs.structure_ddec

        running_zeopp = self.submit(ZeoppCalculation, **zeopp_inp)
        self.report("Running Zeo++ calculation <{}>".format(running_zeopp.pk))
        return ToContext(zeopp_after=running_zeopp)

    def run_cp2kmultistage(self):
        """Run CP2K-Multistage"""
        cp2k_ms_inputs = AttributeDict(self.exposed_inputs(Cp2kMultistageWorkChain))
        cp2k_ms_inputs['structure'] = self.inputs.structure.get_structure()

        running = self.submit(Cp2kMultistageWorkChain, **cp2k_ms_inputs)
        return ToContext(ms_wc=running)

    def run_cp2kddec(self):
        """Pass the Cp2kMultistageWorkChain outputs as inputs for
        Cp2kDdecWorkChain: cp2k_base (metadata), cp2k_params, structure and WFN.
        """
        cp2k_ddec_inputs = AttributeDict(self.exposed_inputs(Cp2kDdecWorkChain))
        cp2k_ddec_inputs['cp2k_base'] = self.exposed_inputs(Cp2kMultistageWorkChain)['cp2k_base']
        cp2k_ddec_inputs['cp2k_base']['cp2k']['parameters'] = self.ctx.ms_wc.outputs.last_input_parameters
        cp2k_ddec_inputs['cp2k_base']['cp2k']['structure'] = self.ctx.ms_wc.outputs.output_structure
        cp2k_ddec_inputs['cp2k_base']['cp2k']['parent_calc_folder'] = self.ctx.ms_wc.outputs.remote_folder

        running = self.submit(Cp2kDdecWorkChain, **cp2k_ddec_inputs)
        return ToContext(cp2k_ddec_wc=running)

    def return_results(self):
        """Return exposed outputs"""
        self.out_many(self.exposed_outputs(self.ctx.ms_wc, Cp2kMultistageWorkChain))
        self.out_many(self.exposed_outputs(self.ctx.cp2k_ddec_wc, Cp2kDdecWorkChain))
        self.out_many(self.exposed_outputs(self.ctx.zeopp_before, ZeoppCalculation, namespace='zeopp_before_opt'))
        self.out_many(self.exposed_outputs(self.ctx.zeopp_after, ZeoppCalculation, namespace='zeopp_after_opt'))
        self.report("WorkChain terminated correctly")
