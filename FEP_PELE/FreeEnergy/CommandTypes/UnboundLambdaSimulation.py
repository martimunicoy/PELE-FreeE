# -*- coding: utf-8 -*-


# Python imports
import sys


# FEP_PELE imports
from FEP_PELE.FreeEnergy.Command import Command
from FEP_PELE.FreeEnergy import Constants as co

from FEP_PELE.Utils.InOut import clear_directory
from FEP_PELE.Utils.InOut import join_splitted_models
from FEP_PELE.Utils.InOut import remove_splitted_models
from FEP_PELE.Utils.InOut import deleteAllFilesWithExtension

from FEP_PELE.TemplateHandler import Lambda
from FEP_PELE.TemplateHandler.AlchemicalTemplateCreator import \
    AlchemicalTemplateCreator

from FEP_PELE.PELETools.PELERunner import PELERunner
from FEP_PELE.PELETools.ControlFileCreator import \
    ControlFileFromTemplateCreator
from FEP_PELE.PELETools import PELEConstants as pele_co


# Script information
__author__ = "Marti Municoy"
__license__ = "GPL"
__version__ = "1.0.1"
__maintainer__ = "Marti Municoy"
__email__ = "marti.municoy@bsc.es"


# Class definitions
class UnboundLambdaSimulation(Command):
    def __init__(self, settings):
        self._name = co.COMMAND_NAMES_DICT["UNBOUND_LAMBDA_SIMULATION"]
        Command.__init__(self, settings)
        self.directions = co.DOUBLE_WIDE_SAMPLING_DIRECTIONS
        self.path = self.settings.calculation_path + 'unbound/'

    @property
    def name(self):
        return self._name

    def run(self):
        print("###########################")
        print(" Unbound Lambda Simulation")
        print("###########################")

        print(" - Calculating energy differences for each delta lambda")

        alchemicalTemplateCreator = AlchemicalTemplateCreator(
            self.settings.initial_template,
            self.settings.final_template,
            self.settings.atom_links)

        clear_directory(self.path)

        if (self.settings.splitted_lambdas):
            delta_energies = self._run_with_splitted_lambdas(
                alchemicalTemplateCreator)
        else:
            delta_energies = self._run(alchemicalTemplateCreator,
                                       self.settings.lambdas,
                                       Lambda.DUAL_LAMBDA)

        print("   Done")

        join_splitted_models(self.path, co.PDB_OUT_NAME.format('*'))
        remove_splitted_models(self.path, co.PDB_OUT_NAME.format('*'))
        deleteAllFilesWithExtension(self.path, 'conf')
        deleteAllFilesWithExtension(self.path, 'txt')

        print(" - Relative Unbound Free Energy prediction " +
              "{:.2f} kcal/mol".format(sum(delta_energies)))

    def _run(self, alchemicalTemplateCreator, lambdas, lambdas_type, num=0,
             constant_lambda=None):
        delta_energies = []

        atoms_to_minimize = self._getAtomIdsToMinimize(
            alchemicalTemplateCreator)

        runner = PELERunner(self.settings.serial_pele,
                            number_of_processors=1)

        for lambda_ in Lambda.IterateOverLambdas(lambdas, lambdas_type):
            self._createAlchemicalTemplate(alchemicalTemplateCreator,
                                           lambda_, constant_lambda)

            initial_energy = self._minimize(alchemicalTemplateCreator, runner,
                                            lambda_)

            final_energies, directions = self._calculateEnergeticDifference(
                alchemicalTemplateCreator, lambda_, constant_lambda, num,
                atoms_to_minimize)

            for final_energy, direction in zip(final_energies, directions):
                delta_energies.append(co.DIRECTION_FACTORS[direction] *
                                      (final_energy - initial_energy))

        return delta_energies

    def _minimize(self, alchemicalTemplateCreator, runner, lambda_):

        clear_directory(self.settings.minimization_path)

        self._writeMinimizationControlFile(alchemicalTemplateCreator,
                                           lambda_)

        try:
            output = runner.run(self.settings.minimization_path +
                                co.MINIMIZATION_CF_NAME)
        except SystemExit as exception:
            print("UnboundLambdasSimulation error: \n" + str(exception))
            sys.exit(1)

        for line in output.split('\n'):
            if line.startswith(pele_co.ENERGY_RESULT_LINE):
                energy = float(line.strip().split()[-1])
                break
        else:
            print("Error: energy calculation failed")

        return energy

    def _calculateEnergeticDifference(self, alchemicalTemplateCreator,
                                      lambda_, constant_lambda, num,
                                      atoms_to_minimize):

        delta_lambda = lambda_.get_delta()

        runner = PELERunner(self.settings.serial_pele,
                            number_of_processors=1)

        energies = []

        for direction in self.directions:
            lambda_name = str(round(lambda_.value, 3)) + \
                co.DIRECTION_TO_CHAR[direction]

            dir_factor = co.DIRECTION_FACTORS[direction]
            value = lambda_.value + dir_factor * delta_lambda
            shifted_lambda = Lambda.Lambda(value, lambda_type=lambda_.type)

            self._createAlchemicalTemplate(alchemicalTemplateCreator,
                                           shifted_lambda, constant_lambda)

            pdb_name = self.path + co.PDB_OUT_NAME.format(str(lambda_.value) +
                                                          'c')

            logfile_name = self.path + co.LOGFILE_NAME.format(lambda_name)

            trajectory_name = self.path + co.PDB_OUT_NAME.format(lambda_name)

            self._writeRecalculationControlFile(
                self.settings.pp_control_file,
                pdb_name,
                logfile_name,
                trajectory_name,
                atoms_to_minimize,
                self.path + co.SINGLE_POINT_CF_NAME.format(lambda_name))

            output = runner.run(self.path +
                                co.SINGLE_POINT_CF_NAME.format(lambda_name))

            for line in output.split('\n'):
                if line.startswith(pele_co.ENERGY_RESULT_LINE):
                    energies.append(float(line.strip().split()[-1]))
                    break
            else:
                print("Error: energy calculation failed")
                print(output)

        return energies, self.directions

    def _writeMinimizationControlFile(self, alchemicalTemplateCreator,
                                      lambda_):
        cf_creator = ControlFileFromTemplateCreator(
            self.settings.min_control_file)

        if (alchemicalTemplateCreator.explicit_is_final):
            input_pdb = self.settings.final_ligand_pdb
        else:
            input_pdb = self.settings.initial_ligand_pdb

        cf_creator.replaceFlag("INPUT_PDB_NAME", input_pdb)
        cf_creator.replaceFlag("SOLVENT_TYPE", self.settings.solvent_type)
        cf_creator.replaceFlag("LOG_PATH", self.settings.minimization_path +
                               co.SINGLE_LOGFILE_NAME)
        cf_creator.replaceFlag("TRAJECTORY_PATH",
                               self.path +
                               co.PDB_OUT_NAME.format(str(lambda_.value) +
                                                      'c'))

        cf_creator.write(self.settings.minimization_path +
                         co.MINIMIZATION_CF_NAME)

    def _writeRecalculationControlFile(self, template_path, pdb_name,
                                       logfile_name,
                                       trajectory_name, atoms_to_minimize,
                                       output_path):
        builder = ControlFileFromTemplateCreator(template_path)

        builder.replaceFlag("INPUT_PDB_NAME", pdb_name)
        builder.replaceFlag("SOLVENT_TYPE", self.settings.solvent_type)
        builder.replaceFlag("LOG_PATH", logfile_name)
        builder.replaceFlag("TRAJECTORY_PATH", trajectory_name)
        builder.replaceFlag("ATOMS_TO_MINIMIZE",
                            "\"" + '\", \"'.join(atoms_to_minimize) + "\"")

        builder.write(output_path)
