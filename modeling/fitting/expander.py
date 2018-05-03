#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.modeling.fitting.expander Contains the ParameterExpander class

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
from collections import OrderedDict

# Import the relevant PTS classes and modules
from .component import FittingComponent
from ...core.basics.log import log
from ...core.tools.utils import lazyproperty, memoize_method
from ...core.tools import sequences
from ...core.tools import nr, numbers, strings, types
from ...core.basics.containers import DefaultOrderedDict
from ...core.tools import formatting as fmt
from ...core.tools.stringify import tostr

# -----------------------------------------------------------------

up = "up"
down = "down"
both = "both"
directions = [up, down, both]

# -----------------------------------------------------------------

class ParameterExpander(FittingComponent):
    
    """
    This class...
    """

    def __init__(self, *args, **kwargs):

        """
        The constructor ...
        :param kwargs:
        :return:
        """

        # Call the constructor of the base class
        super(ParameterExpander, self).__init__(*args, **kwargs)

        # The generation info
        self.info = None

        # The new parameter values
        self.new_parameter_values = DefaultOrderedDict(list)

        # The model parameters
        self.parameters = DefaultOrderedDict(OrderedDict)

    # -----------------------------------------------------------------

    def run(self, **kwargs):

        """
        This function ...
        :param kwargs:
        :return:
        """

        # 1. Call the setup function
        self.setup(**kwargs)

        # 2. Generate the parameter values
        self.generate_parameters()

        # 3. Generate the models
        self.generate_models()

        # 4. Show
        self.show()

        # 7. Set the paths to the input files
        #if self.needs_input: self.set_input()

        # 8. Adjust the ski template
        #self.adjust_ski()

        # 9. Fill the tables for the current generation
        #self.fill_tables()

        # Launch the models
        self.launch()

        # Write
        self.write()

    # -----------------------------------------------------------------

    def setup(self, **kwargs):

        """
        This function ...
        :param kwargs:
        :return:
        """

        # Call the setup function of the base class
        super(ParameterExpander, self).setup(**kwargs)

        # Load the generation info
        self.info = self.fitting_run.get_generation_info(self.config.generation)

    # -----------------------------------------------------------------

    @lazyproperty
    def fitting_run(self):

        """
        This function ...
        :return:
        """

        return self.load_fitting_run(self.config.run)

    # -----------------------------------------------------------------

    @property
    def free_parameter_labels(self):

        """
        This function ...
        :return:
        """

        return self.fitting_run.free_parameter_labels

    # -----------------------------------------------------------------

    @property
    def parameter_ranges(self):

        """
        This function ...
        :return:
        """

        return self.fitting_run.free_parameter_ranges

    # -----------------------------------------------------------------

    @lazyproperty
    def parameter_labels(self):

        """
        This function ...
        :return:
        """

        if self.config.parameters is not None: return self.config.parameters
        else: return self.free_parameter_labels

    # -----------------------------------------------------------------

    @property
    def nparameters(self):

        """
        This function ...
        :return:
        """

        return len(self.parameter_labels)

    # -----------------------------------------------------------------

    @property
    def has_multiple_parameters(self):

        """
        This function ...
        :return:
        """

        return self.nparameters > 1

    # -----------------------------------------------------------------

    @property
    def parameter_units(self):

        """
        This function ...
        :return:
        """

        return self.fitting_run.parameter_units

    # -----------------------------------------------------------------

    def get_parameter_unit(self, label):

        """
        Thisf unction ...
        :param label:
        :return:
        """

        return self.parameter_units[label]

    # -----------------------------------------------------------------

    def has_parameter_unit(self, label):

        """
        This function ...
        :param label:
        :return:
        """

        return label in self.parameter_units and self.parameter_units[label] is not None

    # -----------------------------------------------------------------

    @property
    def initial_parameter_values(self):

        """
        This function ...
        :return:
        """

        return self.fitting_run.first_guess_parameter_values

    # -----------------------------------------------------------------

    @lazyproperty
    def generation(self):

        """
        Thisfunction ...
        :return:
        """

        return self.fitting_run.get_generation(self.config.generation)

    # -----------------------------------------------------------------

    @property
    def grid_settings(self):

        """
        This function ...
        :return:
        """

        return self.fitting_run.grid_settings

    # -----------------------------------------------------------------

    @lazyproperty
    def parameter_scales(self):

        """
        This function ...
        :return:
        """

        # Initialize dictionary for the scales
        scales = dict()

        # Get the scales for each free parameter
        for label in self.free_parameter_labels:
            key = label + "_scale"
            scales[label] = self.grid_settings[key]

        # Return the scales dict
        return scales

    # -----------------------------------------------------------------

    def is_linear(self, label):

        """
        This function ...
        :param label:
        :return:
        """

        return self.parameter_scales[label] == "linear"

    # -----------------------------------------------------------------

    def is_logarithmic(self, label):

        """
        This function ...
        :param label:
        :return:
        """

        return self.parameter_scales[label] == "logarithmic"

    # -----------------------------------------------------------------

    @property
    def parameters_table(self):

        """
        This function ...
        :return:
        """

        return self.generation.parameters_table

    # -----------------------------------------------------------------

    @lazyproperty
    def unique_parameter_values(self):

        """
        This function ...
        :return:
        """

        return self.parameters_table.unique_parameter_values

    # -----------------------------------------------------------------

    @lazyproperty
    def unique_parameter_values_scalar(self):

        """
        This function ...
        :return:
        """

        # Initialize dictionary
        values_scalar = DefaultOrderedDict(list)

        # Loop over the parameters
        for label in self.unique_parameter_values:
            for value in self.unique_parameter_values[label]:
                scalar_value = value.to(self.get_parameter_unit(label)).value
                values_scalar[label].append(scalar_value)

        # Return the scalar values
        return values_scalar

    # -----------------------------------------------------------------

    @memoize_method
    def get_nunique_parameter_values(self, label):

        """
        This function ...
        :param label:
        :return:
        """

        return len(self.unique_parameter_values[label])

    # -----------------------------------------------------------------

    @memoize_method
    def get_sorted_unique_parameter_values_scalar(self, label):

        """
        This function ...
        :param label:
        :return:
        """

        # Get sorted unique values
        return sequences.ordered(self.unique_parameter_values_scalar[label])

    # -----------------------------------------------------------------

    @memoize_method
    def get_lowest_unique_parameter_value_scalar(self, label):

        """
        This function ...
        :param label:
        :return:
        """

        return self.get_sorted_unique_parameter_values_scalar(label)[0]

    # -----------------------------------------------------------------

    @memoize_method
    def get_lowest_unique_parameter_value(self, label):

        """
        This function ...
        :param label:
        :return:
        """

        return self.get_lowest_unique_parameter_value_scalar(label) * self.get_parameter_unit(label)

    # -----------------------------------------------------------------

    @memoize_method
    def get_highest_unique_parameter_value_scalar(self, label):

        """
        This function ...
        :param label:
        :return:
        """

        return self.get_sorted_unique_parameter_values_scalar(label)[-1]

    # -----------------------------------------------------------------

    @memoize_method
    def get_highest_unique_parameter_value(self, label):

        """
        This function ...
        :param label:
        :return:
        """

        return self.get_highest_unique_parameter_value_scalar(label) * self.get_parameter_unit(label)

    # -----------------------------------------------------------------

    @property
    def individuals_table(self):

        """
        This function ...
        :return:
        """

        return self.generation.individuals_table

    # -----------------------------------------------------------------

    @lazyproperty
    def individual_names(self):

        """
        This function ...
        :return:
        """

        return self.individuals_table.individual_names

    # -----------------------------------------------------------------

    @property
    def chi_squared_table(self):

        """
        This function ...
        :return:
        """

        return self.generation.chi_squared_table

    # -----------------------------------------------------------------

    @memoize_method
    def up(self, label):

        """
        This function ...
        :return:
        """

        if types.is_string_type(self.config.direction): return self.config.direction == up
        elif types.is_dictionary(self.config.direction): return self.config.direction[label] == up
        else: raise ValueError("Invalid type for 'direction'")

    # -----------------------------------------------------------------

    @memoize_method
    def down(self, label):

        """
        Thisn function ...
        :return:
        """

        if types.is_string_type(self.config.direction): return self.config.direction == down
        elif types.is_dictionary(self.config.direction): return self.config.direction[label] == down
        else: raise ValueError("Invalid type for 'direction'")

    # -----------------------------------------------------------------

    @memoize_method
    def both(self, label):

        """
        This function ...
        :return:
        """

        if types.is_string_type(self.config.direction): return self.config.direction == both
        elif types.is_dictionary(self.config.direction): return self.config.direction[label] == both
        else: raise ValueError("Invalid type for 'direction'")

    # -----------------------------------------------------------------

    @memoize_method
    def npoints(self, label):

        """
        This function ...
        :param label:
        :return:
        """

        if types.is_integer_type(self.config.npoints): return self.config.npoints
        elif types.is_dictionary(self.config.npoints): return self.config.npoints[label]
        else: raise ValueError("Invalid type for 'npoints'")

    # -----------------------------------------------------------------

    @memoize_method
    def series(self, label):

        """
        This function ...
        :param label:
        :return:
        """

        if self.up(label): return numbers.get_linear_series(self.npoints(label), start=1, step=1)
        elif self.down(label): return numbers.get_linear_series(self.npoints(label), start=-1, step=-1)
        elif self.both(label): return numbers.get_alternating_series(self.npoints(label), start=1)
        else: raise ValueError("Invalid direction")

    # -----------------------------------------------------------------

    def add_new_parameter_value(self, label, value):

        """
        This function ...
        :param label:
        :param value:
        :return:
        """

        # Add unit
        value = value * self.get_parameter_unit(label)

        # Add
        self.new_parameter_values[label].append(value)

    # -----------------------------------------------------------------

    def generate_parameters(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Generating the new parameters values ...")

        # Loop over the parameters
        for label in self.parameter_labels:

            # Linear range
            if self.is_linear(label): self.generate_parameters_linear(label)

            # Logarithmic range
            elif self.is_logarithmic(label): self.generate_parameters_logarithmic(label)

            # Invalid scale
            else: raise ValueError("Invalid scale")

    # -----------------------------------------------------------------

    @memoize_method
    def get_grid_step(self, label):

        """
        This function ...
        :param label: 
        :return: 
        """

        # Get the unique values
        unique_values = self.get_sorted_unique_parameter_values_scalar(label)

        # Determine the step size
        steps = numbers.differences(unique_values)
        return sequences.get_all_close_value(steps)

    # -----------------------------------------------------------------

    def generate_parameters_linear(self, label):

        """
        This function ...
        :param label:
        :return:
        """

        # Inform the user
        log.info("Generating new parameter values for '" + label + "' on a linear scale ...")

        # Determine the step size
        step = self.get_grid_step(label)

        # Show
        log.debug("The step size of the linear grid of '" + label + "' is " + str(step) + " " + tostr(self.get_parameter_unit(label)))

        # Get lowest and highest value
        lowest_value = self.get_lowest_unique_parameter_value_scalar(label)
        highest_value = self.get_highest_unique_parameter_value_scalar(label)

        # Debug
        log.debug("Current lowest value: " + tostr(lowest_value))
        log.debug("Current highest value: " + tostr(highest_value))

        # Add points above the current range
        if self.up(label):

            for i in self.series(label):
                new_value = highest_value + i * step
                self.add_new_parameter_value(label, new_value)

        # Add points below the current range
        elif self.down(label):

            for i in self.series(label):
                new_value = lowest_value + i * step
                self.add_new_parameter_value(label, new_value)

        # Add points both above and below the current range
        elif self.both(label):

            for i, value in zip(self.series(label), sequences.alternate([highest_value, lowest_value], self.config.npoints)):
                new_value = value + i * step
                self.add_new_parameter_value(label, new_value)

        # Invalid direction
        else: raise ValueError("Invalid direction")

    # -----------------------------------------------------------------

    @memoize_method
    def get_grid_factor(self, label):

        """
        This function ...
        :param label:
        :return:
        """

        # Get unique values
        unique_values = self.get_sorted_unique_parameter_values_scalar(label)

        # Determine the factor
        factors = numbers.quotients(unique_values)
        return sequences.get_all_close_value(factors)

    # -----------------------------------------------------------------

    def generate_parameters_logarithmic(self, label):

        """
        This function ...
        :param label:
        :return:
        """

        # Inform the user
        log.info("Generating new parameter values for '" + label + "' on a logarithmic scale ...")

        # Get the grid factor
        factor = self.get_grid_factor(label)

        # Show
        log.debug("The increment of the logarithmic grid of '" + label + "' is a factor of " + str(factor))

        # Get lowest and highest value
        lowest_value = self.get_lowest_unique_parameter_value_scalar(label)
        highest_value = self.get_highest_unique_parameter_value_scalar(label)

        # Debug
        log.debug("Current lowest value: " + tostr(lowest_value))
        log.debug("Current highest value: " + tostr(highest_value))

        # Add points above the current range
        if self.up(label):

            for i in self.series(label):
                new_value = highest_value * factor ** i
                self.add_new_parameter_value(label, new_value)

        # Add points below the current range
        elif self.down(label):

            for i in self.series(label):
                new_value = lowest_value * factor ** i
                self.add_new_parameter_value(label, new_value)

        # Add points both above and below the current range
        elif self.both(label):

            for i, value in zip(self.series(label), sequences.alternate([highest_value, lowest_value], self.config.npoints)):
                new_value = value * factor ** i
                self.add_new_parameter_value(label, new_value)

        # Invalid
        else: raise ValueError("Invalid direction")

    # -----------------------------------------------------------------

    @lazyproperty
    def name_iterator(self):

        """
        This function ...
        :return:
        """

        # Create name iterator, increment
        name_iterator = strings.alphabet_strings_iterator()
        name_iterator.increment_to(self.individual_names)

        # Return
        return name_iterator

    # -----------------------------------------------------------------

    def generate_models(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Generating the new models ...")

        # Generate models with one new parameter value combined with original parameter values
        self.generate_new_old_models()

        # Generate models with all new parameter values
        if self.has_multiple_parameters: self.generate_new_new_models()

    # -----------------------------------------------------------------

    def generate_new_old_models(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Generating models with new and original parameter values ...")

        # Loop over the parameters with new values
        for label in self.parameter_labels: self.generate_new_models_for_parameter(label)

    # -----------------------------------------------------------------

    @memoize_method
    def get_other_parameters(self, label):

        """
        This function ...
        :param label:
        :return:
        """

        # Get labels
        if types.is_string_type(label): labels = [label]
        elif types.is_string_sequence(label): labels = label
        else: raise ValueError("Invalid input")

        # Return other
        return sequences.get_other(self.free_parameter_labels, labels)

    # -----------------------------------------------------------------

    @memoize_method
    def get_grid_points_dict_for_other_parameters(self, label):

        """
        This function ...
        :param label:
        :return:
        """

        # Initialize
        grid_points = OrderedDict()

        # Loop over the other parameters
        for parameter_label in self.get_other_parameters(label): grid_points[parameter_label] = self.get_sorted_unique_parameter_values_scalar(parameter_label)

        # Return
        return grid_points

    # -----------------------------------------------------------------

    def get_grid_points_lists_for_other_parameters(self, label):

        """
        This function ...
        :param label:
        :return:
        """

        # Get dictionary
        grid_points_dict = self.get_grid_points_dict_for_other_parameters(label)

        # Return as lists
        return self.grid_points_to_lists(grid_points_dict)

    # -----------------------------------------------------------------

    def grid_points_to_lists(self, grid_points_dict):

        """
        This function ...
        :param grid_points_dict:
        :return:
        """

        # Convert into lists, and strip units
        grid_points_lists = []

        # Get the labels
        parameter_labels = grid_points_dict.keys()

        # Loop over the free parameters
        for label in parameter_labels:

            # Get the list of scalar values
            #if self.has_parameter_unit(label):
            #    unit = self.get_parameter_unit(label)
            #    values = [value.to(unit).value for value in grid_points_dict[label]]
            #else: values = grid_points_dict[label]

            # Add the list of grid point values
            grid_points_lists.append(values)

        # Return the lists
        return grid_points_lists

    # -----------------------------------------------------------------

    def generate_new_models_for_parameter(self, label):

        """
        This function ...
        :param label: 
        :return: 
        """

        # Debugging
        log.debug("Generating models for the new parameter values of '" + label + "' ...")

        # Loop over the new parameter values
        for value in self.new_parameter_values[label]:

            # Debugging
            log.debug("Generating new models with " + label + " = " + tostr(value) + " ...")

            # Other parameter values
            parameters = self.get_grid_points_dict_for_other_parameters(label)
            other_labels = parameters.keys()
            #print(parameter_labels)

            # Get number of models
            nmodels = 1
            for other_label in other_labels: nmodels *= self.get_nunique_parameter_values(other_label)
            #print(nmodels)

            # Create iterator of combinations
            iterator = sequences.iterate_lists_combinations(*parameters.values())

            # Loop over the grid points of the other parameters
            for index in range(nmodels):

                # The next combination
                other_values = list(iterator.next())  # returns tuple

                # Generate a new individual name
                name = self.name_iterator.next()

                #print(parameters_model)

                # Loop over all the parameters
                #for i in range(len(parameters_model)):

                # Add the parameter value to the dictionary
                self.parameters[label][name] = value.to(self.get_parameter_unit(label)).value
                for other_label, other_value in zip(other_labels, other_values): self.parameters[other_label][name] = other_value

    # -----------------------------------------------------------------

    def generate_new_new_models(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Generating models with all new parameter values ...")

    # -----------------------------------------------------------------

    @lazyproperty
    def new_individual_names(self):

        """
        This function ...
        :return:
        """

        return self.parameters[self.parameters.keys()[0]].keys()

    # -----------------------------------------------------------------

    def show(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Showing ...")

        # Show
        self.show_parameter_values()

        # Show the models
        self.show_models()

    # -----------------------------------------------------------------

    def has_new_parameter_values(self, label):

        """
        This function ...
        :param label:
        :return:
        """

        return label in self.new_parameter_values and len(self.new_parameter_values[label]) > 0

    # -----------------------------------------------------------------

    @memoize_method
    def get_new_parameter_values_above(self, label):

        """
        This function ...
        :param label:
        :return:
        """

        # No new values for this parameter
        if not self.has_new_parameter_values(label): return []

        values = []
        highest = self.get_highest_unique_parameter_value(label)
        for value in self.new_parameter_values[label]:
            if value > highest: values.append(value)
        return values

    # -----------------------------------------------------------------

    @memoize_method
    def get_new_parameter_values_below(self, label):

        """
        This function ...
        :param label:
        :return:
        """

        # No new values for this parameter
        if not self.has_new_parameter_values(label): return []

        values = []
        lowest = self.get_lowest_unique_parameter_value(label)
        for value in self.new_parameter_values[label]:
            if value < lowest: values.append(value)
        return values

    # -----------------------------------------------------------------

    def show_parameter_values(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Showing the parameter values ...")

        # Loop over the free parameters
        for label in self.free_parameter_labels:

            # Get the unit
            unit = self.get_parameter_unit(label)

            print("")
            print(fmt.underlined + fmt.green + label + fmt.reset + " [" + tostr(unit) + "]:")
            print(self.parameter_scales[label])
            print("")

            # Show values below original range
            below = self.get_new_parameter_values_below(label)
            for value in below: print("  " + fmt.cyan + tostr(value.to(unit).value) + fmt.reset)

            # Show original values
            for value in self.get_sorted_unique_parameter_values_scalar(label): print("  " + tostr(value))

            # Show values above original range
            above = self.get_new_parameter_values_above(label)
            for value in above: print("  " + fmt.cyan + tostr(value.to(unit).value) + fmt.reset)

        print("")

    # -----------------------------------------------------------------

    def show_models(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Showing the model parameters ...")

        # Print in columns
        with fmt.print_in_columns() as print_row:

            column_names = ["Individual"] + self.free_parameter_labels
            column_units = [""] + [self.get_parameter_unit(label) for label in self.free_parameter_labels]

            # Show the header
            print_row(*column_names)
            if not sequences.all_none(column_units): print_row(*column_units)

            # Loop over the new individuals
            for name in self.new_individual_names:

                row = []
                row.append(name)

                # Add parameter value
                for label in self.free_parameter_labels: row.append(self.parameters[label][name])

                # Show row
                print_row(*row)

    # -----------------------------------------------------------------

    def launch(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Launching ...")

        # Create manager
        #self.manager = SimulationManager()

        # Run the manager
        #self.manager.run(assignment=assignment, timing=self.timing_table, memory=self.memory_table)

        # status=status, info_tables=[parameters, chi_squared], remotes=remotes, simulations=simulations)

        # Set the actual number of simulations for this generation
        #self.generation_info.nsimulations = self.nmodels

    # -----------------------------------------------------------------



    # -----------------------------------------------------------------

    def write(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing ...")

# -----------------------------------------------------------------
