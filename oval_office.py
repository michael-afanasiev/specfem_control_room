#!/usr/bin/env python

import os
import sys
import errno
import shutil
import subprocess
import argparse
import datetime
import numpy as np

import xml.etree.ElementTree as ET
import components.classes.seismogram as seismogram
import components.classes.cmt_solution as cmt_solution

class ParameterError(Exception):
    pass


class PathError(Exception):
    pass


class MesherNotRunError(Exception):
    pass


class WrongDirectoryError(Exception):
    pass


class colours:
    ylw = '\033[93m'
    blu = '\033[94m'
    rst = '\033[0m'


def print_blu(message):
    print colours.blu + message + colours.rst


def print_ylw(message):
    print colours.ylw + message + colours.rst


def read_parameter_file(filename):
    """
    Little function to read the specfem setup parameter file, and returns a
    dictionary of parameters.

    :filename: path to parameter file.
    """

    # List of required parameters.
    required = ['compiler_suite', 'project_name', 'scratch_path',
                'specfem_root', 'lasif_path', 'iteration_name']

    # Read file, skip lines with #.
    parameters = {}
    file = open(filename, 'r')
    for line in file:
        if line.startswith('#'):
            continue
        fields = line.split()
        parameters.update({fields[0]: fields[1]})

    # Make sure all required parameters are present.
    for param in required:
        if param not in parameters.keys():
            raise ParameterError('Parameter ' + param +
                                 ' not in parameter file.')

    # Fix paths.
    parameters['scratch_path'] = os.path.abspath(parameters['scratch_path'])
    parameters['specfem_root'] = os.path.abspath(parameters['specfem_root'])
    parameters['lasif_path'] = os.path.abspath(parameters['lasif_path'])

    return parameters


def get_iteration_xml_path():
    """
    A little function to grab the iteration xml path from the lasif directory.
    """
    
    # Find iteration xml file.
    iteration_xml_path = os.path.join(p['lasif_path'],
                                      'ITERATIONS/ITERATION_%s.xml'
                                      % (p['iteration_name']))

    if not os.path.exists(iteration_xml_path):
        raise PathError('Your iteration xml file does not exist in the '
                  'location you specified.')
  
    return iteration_xml_path


def safe_copy(source, dest):
    """
    Sets up a file copy that won't fail for a stupid reason.

    :source: Source file.
    :dest: Destination directory.
    """
    source = os.path.join(source)
    dest = os.path.join(dest)

    if (os.path.isdir(source)):
        return
    if not (os.path.isdir(dest)):
        return
    try:
        shutil.copy(source, dest)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise


def safe_sym_link(source, dest):
    """
    Sets up symbolic links that won't fail for a stupid reason.

    :source: Source file.
    :dest: Destination file.
    """

    source = os.path.join(source)
    dest = os.path.join(dest)

    if (os.path.isdir(source)):
        return

    try:
        os.symlink(source, dest)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise


def setup_dir_tree(event_path):
    """
    Sets up the simulation directory strucutre for one event.

    :event_path: Path the forward simulation directory for a specific event.
    """

    mkdir_p(event_path)
    mkdir_p(event_path + '/bin')
    mkdir_p(event_path + '/DATA')
    mkdir_p(event_path + '/OUTPUT_FILES')
    mkdir_p(event_path + '/DATABASES_MPI')
    mkdir_p(event_path + '/DATA/cemRequest')

def find_bandpass_parameters(iteration_xml_path):
    """
    Quickly parses the iteration xml file, to extract the high and lowpass 
    period for filtering purposes.

    :iteration_xml_path: Path the xml file driving the requested iteration.
    """
    
    tree = ET.parse(iteration_xml_path)
    root = tree.getroot()
    for name in root.findall('data_preprocessing'):
        for period in name.findall('highpass_period'):
            highpass_period = period
        for period in name.findall('lowpass_period'):
            lowpass_period = period
    
    return float(highpass_period.text), float(lowpass_period.text)

def find_event_names(iteration_xml_path):
    """
    Quickly parses the iteration xml file and extracts all the event names.

    :iteration_xml_path: Path the xml file driving the requested iteration.
    """

    # Find event names.
    tree = ET.parse(iteration_xml_path)
    root = tree.getroot()
    event_list = []
    for name in root.findall('event'):
        for event in name.findall('event_name'):
            event_list.append(event.text)

    return event_list


def mkdir_p(path):
    """
    Makes a directory and doesn't fail if the directory already exists.

    :path: New directory path.
    """

    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST:
            pass
        else:
            raise


def setup_run():
    """
    Function does a whole bunch of things to set up a specfem run on daint.
    """

    # Find iteration xml file.
    iteration_xml_path = get_iteration_xml_path()
    event_list = find_event_names(iteration_xml_path)

    # Create the forward modelling directories.
    print_ylw('Creating forward modelling directories...')
    for event in event_list:
        event_path = os.path.join(solver_base_path, event)
        setup_dir_tree(event_path)

    # Make master mesh directory.
    mesh_path = os.path.join(solver_base_path, 'mesh')
    setup_dir_tree(mesh_path)

    # Copy over input files.
    print_ylw('Copying initial files...')
    lasif_output = os.path.join(p['lasif_path'], 'OUTPUT')
    for dir in os.listdir(lasif_output):
        for event in event_list:
            if p['iteration_name'] in dir and event in dir:

                event_output_dir = os.path.join(lasif_output, dir)
                for file in os.listdir(event_output_dir):

                    source = os.path.join(event_output_dir, file)
                    dest = os.path.join(solver_base_path, event, 'DATA')
                    safe_copy(source, dest)

                    if event == event_list[0]:

                        source = os.path.join(event_output_dir, file)
                        dest = os.path.join(solver_base_path, 'mesh', 'DATA')
                        safe_copy(source, dest)

    # Copy one instance of forward files to specfem base directory.
    if not os.path.isdir(os.path.join(p['lasif_path'], 'SUBMISSION', 
                                       p['iteration_name'])):
        raise PathError('You have not yet set up a job submission directory '
                        'for this iteration')
    
    source = os.path.join(p['lasif_path'], 'SUBMISSION', p['iteration_name'], 
                          'Par_file')
    dest = os.path.join(p['specfem_root'], 'DATA')
    safe_copy(source, dest)

    # # Change to specfem root directory and compile.
    print_ylw('Compiling...')
    os.chdir(p['specfem_root'])
    with open('compilation_log.txt', 'w') as output:
        proc = subprocess.Popen(['./mk_daint.sh', p['compiler_suite'],
                                'adjoint'], stdout=output, stderr=output)
        proc.communicate()
        proc.wait()

    # Copy binaries to all directories.
    print_ylw('Copying compiled binaries...')
    for event in os.listdir(solver_base_path):
        for binary in os.listdir('./bin/'):

            source = os.path.join('./bin', binary)
            dest = os.path.join(solver_base_path, event, 'bin')
            safe_copy(source, dest)

    print_ylw('Copying compiled parameter file...')
    for event in os.listdir(solver_base_path):
        source = os.path.join('./DATA', 'Par_file')
        dest = os.path.join(solver_base_path, event, 'DATA')
        safe_copy(source, dest)

    # Copy jobarray script to base directory.
    print_ylw('Copying jobarray sbatch script...')
    source = os.path.join(p['lasif_path'], 'SUBMISSION', p['iteration_name'],
                          'jobArray_solver_daint.sbatch')
    dest = solver_root_path
    safe_copy(source, dest)
    log_directory = os.path.join(solver_root_path, 'logs')
    mkdir_p(log_directory)

    # Copy topo_bathy to mesh directory.
    print_ylw('Copying topography information...')
    mesh_data_path = os.path.join(solver_base_path, 'mesh', 'DATA')
    mesh_topo_path = os.path.join(mesh_data_path, 'topo_bathy')
    master_topo_path = os.path.join('./DATA', 'topo_bathy')
    mkdir_p(mesh_topo_path)
    for file in os.listdir(master_topo_path):
        source = os.path.join(master_topo_path, file)
        dest = os.path.join(mesh_topo_path)
        safe_copy(source, dest)

    # Copy submission script to mesh directory.
    source = os.path.join(p['lasif_path'], 'SUBMISSION', p['iteration_name'],
                          'job_mesher_daint.sbatch')
    dest = os.path.join(solver_base_path, 'mesh')
    safe_copy(source, dest)

    print_blu('Done.')


def prepare_solve():
    """
    Sets up symbolic link to generated mesh files.
    """

    print 'Preparing solver directories.'
    for dir in os.listdir(solver_base_path):

        if dir == 'mesh':
            continue

        print_ylw('Linking ' + dir)
        databases_mpi = os.path.join(solver_base_path, 'mesh', 'DATABASES_MPI')
        output_files = os.path.join(solver_base_path, 'mesh', 'OUTPUT_FILES')

        if not os.listdir(databases_mpi):
            raise MesherNotRunError("It doesn't look like the mesher has been \
            run. There are no mesh files in the expected mesh directory.")

        for file in os.listdir(databases_mpi):
            source = os.path.join(databases_mpi, file)
            dest = os.path.join(solver_base_path, dir, 'DATABASES_MPI', file)
            safe_sym_link(source, dest)

        for file in os.listdir(output_files):
            source = os.path.join(output_files, file)
            dest = os.path.join(solver_base_path, dir, 'OUTPUT_FILES')
            safe_copy(source, dest)

    print_blu('Done.')


def submit_mesher():
    """
    Runs over to the meshing directory, and just submits the job.
    """

    mesh_dir = os.path.join(solver_base_path, 'mesh')
    os.chdir(mesh_dir)
    subprocess.Popen(['sbatch', 'job_mesher_daint.sbatch']).wait()


def submit_solver(first_job, last_job):
    """
    Submits the job array script in the solver_root_path directory. Submits
    job array indices first_job to last_job.

    :first_job: The job array index of the first job to submit (i.e. 0)
    :last_job: The job array index of the last job to submit (i.e. n_events-1)
    """

    with open('master_log.txt', 'a') as file:
        file.write("Submitted solver for array jobs %s to %s on "
                   % (first_job, last_job) + str(datetime.datetime.now())
                   + '\n')

    os.chdir(solver_root_path)
    subprocess.Popen(['sbatch', '--array=%s-%s' % (first_job, last_job),
                     'jobArray_solver_daint.sbatch',
                      p['iteration_name']]).wait()

def sync_LASIF_to_scratch():
    """
    Syncs your LASIF directory on /project to /scratch.
    """

    clean_mseed()

    current_dir = os.getcwd()
    print_ylw('Syncing LASIF directory...')
    lasif_dirname = os.path.basename(p['lasif_path'])
    os.chdir(os.path.join(p['lasif_path'], '../'))
    subprocess.Popen(['rsync', '-av', lasif_dirname, p['scratch_path']]).wait()
    os.chdir(current_dir)
    
def sync_scratch_to_LASIF():
    """
    Syncs your lasif mirror on scratch to that on /project.
    """
    
    current_dir = os.getcwd()
    print_ylw('Syncing LASIF directory...')
    lasif_dirname = os.path.basename(p['lasif_path'])
    lasif_project_path = os.path.join(p['lasif_path'], '../')
    os.chdir(p['scratch_path'])
    subprocess.Popen(['rsync', '-av', lasif_dirname, lasif_project_path]).wait()
    os.chdir(current_dir)
    
def process_data(first_job, last_job):
    
    try:
        os.chdir('./data_processing')
    except OSError:
        raise WrongDirectoryError("You're not in the control room directory.")
    
    sync_LASIF_to_scratch()

    lasif_dirname = os.path.basename(p['lasif_path'])
    lasif_scratch_dir = os.path.join(p['scratch_path'], lasif_dirname)
    subprocess.Popen(['sbatch', '--array=%s-%s' % (first_job, last_job),
                      'preprocess_data_parallel.sh', lasif_scratch_dir,
                      p['lasif_path'], p['iteration_name']]).wait()
                      
def distribute_adjoint_sources():
    
    lasif_output_dir = os.path.join(p['lasif_path'], 'OUTPUT')
    os.chdir(os.path.join(solver_base_path))
    for dir in os.listdir('./'):
        print "Distributing... to " + dir
        adjoint_names = []
        mkdir_p(os.path.join(dir, 'SEM'))
        
        adj_src_write_path = os.path.join(dir, 'SEM')

        for output_dir in os.listdir(lasif_output_dir):
            if dir in output_dir:
                for adjoint in os.listdir(os.path.join(lasif_output_dir, 
                                                       output_dir)):
                    adj_src = os.path.join(lasif_output_dir, output_dir, 
                                           adjoint)
                                           
                    if not adjoint.endswith('.adj'):
                        continue
                    
                    safe_copy(adj_src, adj_src_write_path)                
                                               
                    stat_name = os.path.basename(adj_src).split('.')[0]
                    if os.path.basename(stat_name) not in adjoint_names:
                        adjoint_names.append(stat_name)
                
        print "writing station file"
        stations_file = os.path.join(dir, 'DATA', 'STATIONS')    
        adjoint_stat_file = os.path.join(dir, 'DATA', 'STATIONS_ADJOINT')
        write_stations = open(adjoint_stat_file, 'w')
        with open(stations_file, 'r') as input:
            for line in input:
                for adjoint_station_name in adjoint_names:
                    if adjoint_station_name in line:
                        write_stations.write(line)


def destroy_all_but_raw():
    """
    Goes through both the scratch and project lasif directories, and cleans up
    EVERYTHING that is not raw data (meaning: preprocessed data and synthetics).
    """
    
    choice = str(raw_input("WARNING. DANGEROUS. DO YOU WANT TO PROCEED.\n"))
    if choice != 'YES':
        print 'Phew.'
        return
        
    def clean_all_processed_data():
        for dir in os.listdir('./'):
            os.chdir(dir)
            for datadir in os.listdir('./'):
                if 'raw' in datadir:
                    if os.path.exists(os.path.join('raw', 
                        'preprocessedData.tar')):
                        os.remove(os.path.join('raw', 'preprocessedData.tar'))
                if 'raw' not in datadir:
                    if os.path.isdir(datadir):
                        shutil.rmtree(datadir)
                    elif os.path.exists(datadir):
                        os.remove(datadir)

            os.chdir('../')
            
    def clean_all_synthetics():
        for dir in os.listdir('./'):
            os.chdir(dir)
            for datadir in os.listdir('./'):
                if os.path.isdir(datadir):
                    shutil.rmtree(datadir)
                else:
                    os.remove(datadir)     
                
            os.chdir('../')           
            
    os.chdir(os.path.join(p['lasif_path'], 'DATA'))
    clean_all_processed_data()
        
    os.chdir(os.path.join(p['lasif_path'], 'SYNTHETICS'))
    clean_all_synthetics()
        
    lasif_dirname = os.path.basename(p['lasif_path'])
    lasif_scratch_dir = os.path.join(p['scratch_path'], lasif_dirname)
    
    os.chdir(os.path.join(lasif_scratch_dir, 'DATA'))
    clean_all_processed_data()

    os.chdir(os.path.join(lasif_scratch_dir, 'SYNTHETICS'))
    clean_all_synthetics()
    
def unpack_mseed():
    """
    Unpacks the tarred seismogram files for a single event. This is useful for
    using the misfit gui to check things out.
    """
    
    if not args.event_name:
        raise ParameterError("Need to specify event name with this option.")
        
    print "Unpacking data for " + args.event_name
    
    os.chdir(os.path.join(p['lasif_path'], 'DATA'))
    for dir in os.listdir('./'):
        if args.event_name in dir:
            os.chdir(dir)
            for dir2 in os.listdir('./'):
                if os.path.isdir(dir2):
                    os.chdir(dir2)
                    if 'data.tar' in os.listdir('./'):
                        subprocess.Popen(['tar', '-xvf', 'data.tar']).wait()
                        os.remove('data.tar')
                    os.chdir('../')

            os.chdir('../')
            
    os.chdir(os.path.join(p['lasif_path'], 'SYNTHETICS'))
    for dir in os.listdir('./'):
        if args.event_name in dir:
            os.chdir(dir)
            for dir2 in os.listdir('./'):
                if os.path.isdir(dir2):
                    os.chdir(dir2)
                    subprocess.Popen(['tar', '-xvf', 'data.tar']).wait()
                    os.remove('data.tar')
                    os.chdir('../')

            os.chdir('../')
                      
def clean_mseed():
    """
    Goes through both project and scratch LASIF directories, and removes any
    .mseed files. This is useful after looking at misfits with raw .mseeds. Of
    course, the routine also tars everything back up.
    """
    
    current_dir = os.getcwd()
    def clean_mseed_dirtree(tar_file_name):
        for dir in os.listdir('./'):
            os.chdir(dir)
            for datadir in os.listdir('./'):
            
                if os.path.isdir(datadir):
                    os.chdir(datadir)
                    if len(os.listdir('./')) == 0:
                        os.chdir('../')
                        continue
                    if '.mseed' in os.listdir('./')[-1]:
                        subprocess.Popen(['tar -cvf ' + tar_file_name + 
                                          ' *.mseed'], shell=True).wait()
                        for mseed in os.listdir('./'):
                            if 'mseed' in mseed:
                                os.remove(mseed)
                    
                    os.chdir('../')
        
            os.chdir('../')
            
    os.chdir(os.path.join(p['lasif_path'], 'DATA'))
    clean_mseed_dirtree('data.tar');
    
    os.chdir(os.path.join(p['lasif_path'], 'SYNTHETICS'))
    clean_mseed_dirtree('data.tar');
    
    lasif_dirname = os.path.basename(p['lasif_path'])
    lasif_scratch_dir = os.path.join(p['scratch_path'], lasif_dirname)
    
    os.chdir(os.path.join(lasif_scratch_dir, 'DATA'))
    clean_mseed_dirtree('data.tar');
    
    os.chdir(os.path.join(lasif_scratch_dir, 'SYNTHETICS'))
    clean_mseed_dirtree('data.tar');
    
    os.chdir(current_dir)
    
def select_windows(first_job, last_job):
    """
    Selects windows in parallel.
    """
    
    try:
        os.chdir('./inversion_tools')
    except OSError:
        raise WrongDirectoryError("You're not in the control room directory.")
        
    lasif_dirname = os.path.basename(p['lasif_path'])
    lasif_scratch_dir = os.path.join(p['scratch_path'], lasif_dirname)
        
    sync_LASIF_to_scratch()
        
    subprocess.Popen(['sbatch', '--array=%s-%s' % (first_job, last_job),
                      'select_windows_parallel.sh', lasif_scratch_dir, 
                      p['iteration_name']]).wait()
                      
    os.chdir('../')
    with open('master_log.txt', 'a') as file:
        file.write('Selected windows for array jobs %s to %s on '
        % (first_job, last_job) + str(datetime.datetime.now())
        + '\n')

    subprocess.Popen(['rsync', '-av', lasif_scratch_dir, lasif_path]).wait()
    
def build_all_caches():
    """
    Submits a job to build all the LASIF caches. Useful because this can take a
    long time.
    """
    
    # Determine if we can run the script.
    try:
        os.chdir('./components')
    except OSError:
        raise WrongDirectoryError("You're not in the control room directory.")
        
    # # Sync lasif to the scratch directory.
    # sync_LASIF_to_scratch()
    
    # Get lasif scratch directory name.
    lasif_dirname = os.path.basename(p['lasif_path'])
    lasif_scratch_dir = os.path.join(p['scratch_path'], lasif_dirname)
    
    # Submit job.
    subprocess.Popen(['sbatch', 'build_lasif_caches.sbatch', 
                      p['lasif_path'], lasif_scratch_dir]).wait()
                      
    # # Backwards mirror.
    # sync_scratch_to_LASIF()
                          
def process_synthetics(first_job, last_job):
    """
    Runs the parallel process_synthetics functionality in synthetic_processing.

    :first_job: The job array index of the first job to submit (i.e. 0)
    :last_job: The job array index of the last job to submit (i.e. n_events-1)
    """

    try:
        os.chdir('./synthetic_processing')
    except OSError:
        raise WrongDirectoryError("You're not in the control room directory.")

    highpass_period, lowpass_period = find_bandpass_parameters(
                                        get_iteration_xml_path())
                                                
    subprocess.Popen(['sbatch', '--array=%s-%s' % (first_job, last_job),
                      'process_synthetics_parallel.sh', solver_base_path,
                      p['lasif_path'], str(lowpass_period), 
                      str(highpass_period)]).wait()
                                        
    os.chdir('../')
    with open('master_log.txt', 'a') as file:
        file.write("Ran convolution with stf for array jobs %s to %s on "
                   % (first_job, last_job) + str(datetime.datetime.now())
                   + '\n')


parser = argparse.ArgumentParser(description='Assists in the setup of'
                                 'specfem3d_globe on Piz Daint')
parser.add_argument('-f', type=str, help='Simulation driver parameter file.',
                    required=True, metavar='parameter_file_name',
                    dest='filename')
parser.add_argument('--setup_run', action='store_true',
                    help='Setup the directory tree on scratch for one '
                    'iteration. Requires a param file.')
parser.add_argument('--prepare_solve', action='store_true',
                    help='Symbolically links the mesh files to all forward '
                    'directories.')
parser.add_argument('--submit_mesher', action='store_true',
                    help='Runs the mesher in the "mesh" directory.')
parser.add_argument('--submit_solver', action='store_true',
                    help='Submit the job array script for the current '
                    'iteration.')
parser.add_argument('--process_synthetics', action='store_true',
                    help='Process synthetic siesmograms.')
parser.add_argument('--sync_lasif', action='store_true',
                    help='Sync lasif directory from /project to /scratch')
parser.add_argument('--process_data', action='store_true',
                    help='Process rawData.tar files on scratch.')
parser.add_argument('--clean_mseed', action='store_true',
                    help='Delete all .mseed files on project and scratch')
parser.add_argument('--destroy_all_but_raw', action='store_true',
                    help='Delete all .mseed files on project and scratch')
parser.add_argument('--unpack_mseed', action='store_true',
                    help='Unpack tarred seismograms for a given event')
parser.add_argument('--select_windows', action='store_true',
                    help='Unpack tarred seismograms for a given event')                    
parser.add_argument('--build_all_caches', action='store_true',
                    help='Build all cache files for LASIF in serial')                                        
parser.add_argument('--event_name', type=str, help='Event name for use with '
                    '--unpack_mseed')                               
parser.add_argument('--distribute_adjoint_sources', 
                    action='store_true')
parser.add_argument('-fj', type=str, help='First index in job array to submit',
                    metavar='first_job', dest='first_job')
parser.add_argument('-lj', type=str, help='Last index in job array to submit',
                    metavar='last_job', dest='last_job')

args = parser.parse_args()
if args.submit_solver and args.first_job is None and args.last_job is None:
    parser.error('Submitting the solver required -fj and -lj arguments.')
if args.process_synthetics and args.first_job is None and args.last_job is None:
    parser.error('Processing synthetics requires -fj and -lj arguments.')
if args.process_data and args.first_job is None and args.last_job is None:
    parser.error('Processing data requires -fj and -lj arguments.')
if args.select_windows and args.first_job is None and args.last_job is None:
    parser.error('Selecting windows requires -fj and -lj arguments.')

p = read_parameter_file(args.filename)

# Construct full run path.
solver_base_path = os.path.join(p['scratch_path'], p['project_name'],
                                p['iteration_name'])
solver_root_path = os.path.join(p['scratch_path'], p['project_name'])
mkdir_p(solver_base_path)

if args.setup_run:
    setup_run()
elif args.prepare_solve:
    prepare_solve()
elif args.submit_mesher:
    submit_mesher()
elif args.submit_solver:
    submit_solver(args.first_job, args.last_job)
elif args.process_synthetics:
    process_synthetics(args.first_job, args.last_job)
elif args.process_data:
    process_data(args.first_job, args.last_job)
elif args.sync_lasif:
    sync_LASIF()
elif args.clean_mseed:
    clean_mseed()
elif args.destroy_all_but_raw:
    destroy_all_but_raw()
elif args.unpack_mseed:
    unpack_mseed()
elif args.distribute_adjoint_sources:
    distribute_adjoint_sources()
elif args.select_windows:
    select_windows(args.first_job, args.last_job)
elif args.build_all_caches:
    build_all_caches()
