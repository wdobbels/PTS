#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.core.tools.terminal Provides functions for interacting with the terminal (launching commands and getting output).

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
from cStringIO import StringIO
import sys
import subprocess

# Import the relevant PTS classes and modules
from . import filesystem as fs
from . import introspection

# -----------------------------------------------------------------

class Capturing(list):

    """
    This class ...
    """

    def __init__(self, pipe):

        """
        This function ...
        :param pipe:
        """

        self._pipe = pipe
        super(Capturing, self).__init__()

    # -----------------------------------------------------------------

    def __enter__(self):

        self._stdout = self._pipe
        sys.stdout = self._stringio = StringIO()
        return self

    # -----------------------------------------------------------------

    def __exit__(self, *args):

        self.extend(self._stringio.getvalue().splitlines())
        del self._stringio    # free up some memory
        sys.stdout = self._stdout

# -----------------------------------------------------------------

def is_existing_executable(name):

    """
    This function ...
    :param name:
    :return:
    """

    import os

    try:
        dvnll = open(os.devnull)
        subprocess.Popen(name, stdout=dvnll, stderr=dvnll).communicate()
        return True
    except: return False

# -----------------------------------------------------------------

def executable_path(name, no_pexpect=False):

    """
    This function ...
    :param name:
    :param no_pexpect:
    :return:
    """

    if no_pexpect: output = execute_no_pexpect("which " + name)
    else: output = execute("which " + name)
    return output[0]

# -----------------------------------------------------------------

def make_executable(filepath):

    """
    This fucntion ...
    :param filepath:
    :return:
    """

    # Make executable
    subprocess.call("chmod +rx " + filepath, shell=True)

# -----------------------------------------------------------------

def run_script(filepath, options="", output=True, show_output=False, timeout=None, expect=None, no_pexpect=False):

    """
    This function ...
    :param filepath:
    :param options:
    :param output:
    :param show_output:
    :param timeout:
    :param expect:
    :param cwd:
    :return:
    """

    # Determine the path of the directory where the script is
    dir_path = fs.directory_of(filepath)
    filename = fs.name(filepath)

    make_executable(filepath)
    if no_pexpect: return execute_no_pexpect("./" + filename + " " + options, output=output, show_output=show_output, cwd=dir_path)
    else: return execute("./" + filename + " " + options, output=output, show_output=show_output, timeout=timeout, expect=expect, cwd=dir_path)

# -----------------------------------------------------------------

def execute_no_pexpect(command, output=True, show_output=False, cwd=None):

    """
    This function ...
    :param command:
    :param output:
    :param show_output:
    :param cwd:
    :return:
    """

    output = subprocess.check_output(command, shell=True, stderr=sys.stderr, cwd=cwd)
    if output: return output.split("\n")[:-1]

    #import os

    #if show_output: pipe = sys.stdout
    #else: pipe = subprocess.PIPE

    # Capture the output
    #with Capturing(pipe) as lines:

        #subprocess.call(command, shell=True, stdout=pipe, stderr=sys.stderr, cwd=cwd)
        #if output: return lines

# -----------------------------------------------------------------

def execute(command, output=True, show_output=False, timeout=None, expect=None, cwd=None):

    """
    This function ...
    :return:
    """

    # Import here to accomodate fresh python installations
    import pexpect

    # Create the process
    child = pexpect.spawn(command, timeout=timeout, cwd=cwd)

    # If the output has to be shown on the console, set the 'logfile' to the standard system output stream
    # Otherwise, assure that the logfile is set to 'None'
    if show_output: child.logfile = sys.stdout
    else: child.logfile = None

    # Expect
    if expect is not None: child.expect(expect)
    else: child.expect(pexpect.EOF)

    # Set the log file back to 'None'
    child.logfile = None

    # Ignore the first and the last line (the first is the command itself, the last is always empty)
    if output: return child.before.replace('\x1b[K', '').split("\r\n")[1:-1]

# -----------------------------------------------------------------

def execute_lines_no_pexpect(*args, **kwargs):

    """
    This function ...
    :param args:
    :param kwargs:
    :return:
    """

    output = kwargs.pop("output", True)
    show_output = kwargs.pop("show_output", False)
    cwd = kwargs.pop("cwd", None)

    # Remember the output lines
    lines = []

    # Check if all strings
    for line in args: assert isinstance(line, basestring)

    # Execute the lines
    for line in args: lines += execute_no_pexpect(line, show_output=show_output, cwd=cwd)

    # Return output
    if output: return lines

# -----------------------------------------------------------------

def execute_lines_expect_clone(*args, **kwargs):

    """
    This function ...
    :param args:
    :param kwargs:
    :return:
    """

    # Import our own copy of pexpect because we cannot interact with the process otherwise
    from . import expect

    # Get arguments
    output = kwargs.pop("output", True)
    show_output = kwargs.pop("show_output", False)
    timeout = kwargs.pop("timeout", None)
    cwd = kwargs.pop("cwd", None)

    # Execute first line
    assert isinstance(args[0], basestring)
    child = expect.spawn(args[0], timeout=timeout, cwd=cwd)

    # If the output has to be shown on the console, set the 'logfile' to the standard system output stream
    # Otherwise, assure that the logfile is set to 'None'
    if show_output: child.logfile = sys.stdout
    else: child.logfile = None

    # Loop over the lines
    for line in args[1:]:

        # Just a command where completion is expected
        if isinstance(line, basestring):

            # Send the command
            child = child.sendline(line)
            # child.expect()
            # child.expect("$", timeout=timeout)

        # Tuple: something is expected and must be filled in
        elif isinstance(line, tuple):

            # Expect
            if len(line) == 3 and line[2]:

                # index = self.ssh.expect([self.ssh.PROMPT, line[0]]) # this is not working, why?
                index = child.expect(["$", line[0]], timeout=timeout)
                if index == 0: pass
                elif index == 1: child.sendline(line[1])
                # eof = self.ssh.prompt()
            else:
                # self.ssh.expect(line[0])
                # self.ssh.sendline(line[1])
                child.expect(line[0], timeout=timeout)
                child.sendline(line[1])

        # Invalid
        else: raise ValueError("Lines must be strings or tuples")

    # Expect
    child.expect(expect.EOF)

    # Set the log file back to 'None'
    child.logfile = None

    # Return the output
    if output: return child.before.split("\r\n")[1:-1]

# -----------------------------------------------------------------

def execute_lines(*args, **kwargs):

    """
    This function ...
    :return:
    """

    # Import here to accomodate fresh python installations
    import pexpect

    # Get arguments
    output = kwargs.pop("output", True)
    show_output = kwargs.pop("show_output", False)
    timeout = kwargs.pop("timeout", None)
    cwd = kwargs.pop("cwd", None)

    # Execute first line
    assert isinstance(args[0], basestring)
    child = pexpect.spawn(args[0], timeout=timeout, cwd=cwd)

    # If the output has to be shown on the console, set the 'logfile' to the standard system output stream
    # Otherwise, assure that the logfile is set to 'None'
    if show_output: child.logfile = sys.stdout
    else: child.logfile = None

    # Loop over the lines
    for line in args[1:]:

        # Just a command where completion is expected
        if isinstance(line, basestring):

            # Send the command
            child = child.sendline(line)
            #child.expect()
            #child.expect("$", timeout=timeout)

        # Tuple: something is expected and must be filled in
        elif isinstance(line, tuple):

            # Expect
            if len(line) == 3 and line[2]:

                # index = self.ssh.expect([self.ssh.PROMPT, line[0]]) # this is not working, why?
                index = child.expect(["$", line[0]], timeout=timeout)
                if index == 0: pass
                elif index == 1: child.sendline(line[1])
                # eof = self.ssh.prompt()
            else:

                #self.ssh.expect(line[0])
                #self.ssh.sendline(line[1])
                child.expect(line[0], timeout=timeout)
                child.sendline(line[1])

        # Invalid
        else: raise ValueError("Lines must be strings or tuples")

    # Expect
    child.expect(pexpect.EOF)

    # Set the log file back to 'None'
    child.logfile = None

    # Return the output
    if output: return child.before.split("\r\n")[1:-1]

# -----------------------------------------------------------------

def remove_aliases_and_variables_with_comment(comment):

    """
    This function ...
    :param comment:
    :return:
    """

    # First make backup
    #fs.copy_file(introspection.shell_configuration_path(), fs.home(), new_name="backup_profile")

    # Lines to keep
    lines = []

    remove_next = False
    for line in fs.read_lines(introspection.shell_configuration_path()):

        if comment in line:
            remove_next = True
        elif remove_next:
            if line.strip() == "": remove_next = False
            else: pass
        else: lines.append(line)

    # Write lines
    fs.write_lines(introspection.shell_configuration_path(), lines)

# -----------------------------------------------------------------

def add_to_path_variable(value, comment=None, in_shell=False):

    """
    This function ...
    :param value:
    :param comment:
    :param in_shell:
    :return:
    """

    add_to_environment_variable("PATH", value, comment=comment, in_shell=in_shell)

# -----------------------------------------------------------------

def add_to_environment_variable(variable_name, value, comment=None, in_shell=False):

    """
    This function ...
    :param variable_name:
    :param value:
    :param comment:
    :param in_shell:
    :return:
    """

    # Determine command
    export_command = "export " + variable_name + "=" + value + ":$PATH"

    # Define lines
    lines = []
    lines.append("")
    if comment is not None: lines.append("# " + comment)
    lines.append(export_command)
    lines.append("")

    # Add lines
    fs.append_lines(introspection.shell_configuration_path(), lines)

    # Run export path in the current shell to make variable visible
    if in_shell:
        #subprocess.call(export_command, shell=True) #execute(export_command) # not always working?
        subprocess.call("source " + introspection.shell_configuration_path(), shell=True)

# -----------------------------------------------------------------

def define_alias(name, alias_to, comment=None, in_shell=False):

    """
    This function ...
    :param name:
    :param alias_to:
    :param comment:
    :param in_shell:
    :return:
    """

    # Generate the command
    alias_command = 'alias ' + name + '="' + alias_to + '"'

    # Define lines
    lines = []
    lines.append("")
    if comment is not None: lines.append("# " + comment)
    lines.append(alias_command)
    lines.append("")

    # Add lines
    fs.append_lines(introspection.shell_configuration_path(), lines)

    # Execute in shell
    if in_shell:
        #execute(alias_command) # not always working?
        subprocess.call("source " + introspection.shell_configuration_path(), shell=True)

# -----------------------------------------------------------------
