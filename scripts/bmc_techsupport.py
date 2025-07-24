#!/usr/bin/env python3

"""
bmc_techsupport script.
    This script is invoked by the generate_dump script for BMC techsupport fetching

    The usage of this script is divided into two parts:

        1. Triggering BMC debug log dump Redfish task

            * In this case the script, triggers a POST request to BMC to start
              collecting debug log dump

            * In this script we will print the new task-id to the console output to collect
              the debug log dump once the task-id has finished

            * This step is non-blocking

            * It is invoked with the parameter '-m t'
              E.g.: python3 /usr/local/bin/bmc_techsupport -m t  -- to start triggering log dump

        2. Collecting BMC debug log dump

            * In this step we will wait for the task-id to finish if it has not
              finished

            * Blocking action till we get the file or having ERROR - Timeout is 120 seconds

            * It is invoked with the parameter '-m c'
              E.g.: python3 /usr/local/bin/bmc_techsupport -m c -p <path> -t <task-id> -- to collect log dump

    Basically, in the generate_dump script we will call the first method
    at the beginning of its process and the second method towards the end
    of the process, or use the wrapper method for a single call approach.
"""

import syslog
import argparse
import os
import sonic_platform
import time

def parse_file_path(filepath):
    '''
    Returns a tuple (parent_dir, filename) based on the given filepath
    E.g.:
        filepath = '/path/to/your/file.txt'
        returns ('/path/to/your', 'file.txt')
    '''
    directory = os.path.dirname(filepath)
    filename = os.path.basename(filepath)
    return directory, filename


class BMCDebugDumpExtractor:

    INVALID_TASK_ID = '-1'

    def __init__(self):
        platform = sonic_platform.platform.Platform()
        chassis = platform.get_chassis()
        self.bmc = chassis.get_bmc()

    def trigger_debug_dump(self):
        '''
        Trigger BMC debug log dump and prints the running task id to the console output 
        '''
        task_id = BMCDebugDumpExtractor.INVALID_TASK_ID
        try:
            syslog.syslog(syslog.LOG_INFO, f'Triggering BMC debug log dump Redfish task')
            (ret, (task_id, err_msg)) = self.bmc.trigger_bmc_debug_log_dump()
            if ret != 0:
                syslog.syslog(syslog.LOG_ERR, f'Fail to trigger BMC debug log dump: {err_msg}')
                raise Exception(err_msg)

            syslog.syslog(syslog.LOG_INFO, f'Successfully triggered  BMC debug log dump - Task-id: {task_id}')
        except Exception as e:
            syslog.syslog(syslog.LOG_ERR, f'Failed to trigger BMC debug log dump - {str(e)}')
        finally:
            print(f'{task_id}')

    def extract_debug_dump_file(self, task_id, filepath):
        '''
            Extract BMC debug log dump and save running task id
        '''
        try:
            log_dump_dir, log_dump_filename = parse_file_path(filepath)
            if not log_dump_dir or not log_dump_filename:
                raise Exception(f'Invalid given filepath: {filepath}')

            if task_id == BMCDebugDumpExtractor.INVALID_TASK_ID:
                raise Exception(f'Invalid Task-ID')

            start_time = time.time()
            syslog.syslog(syslog.LOG_INFO, f'Collecting BMC debug log dump')
            timeout = 360
            ret, err_msg = self.bmc.get_bmc_debug_log_dump(task_id=task_id, filename=log_dump_filename, path=log_dump_dir, timeout=timeout)
            end_time = time.time()
            duration = end_time - start_time
            if ret != 0:
                syslog.syslog(syslog.LOG_ERR, f'BMC debug log dump does not finish within {timeout} seconds: {err_msg}')
                raise Exception(err_msg)

            syslog.syslog(syslog.LOG_INFO, f'BMC debug log dump takes {duration} seconds to complete')

            if duration > 120:
                syslog.syslog(syslog.LOG_ERR, f'BMC debug log dump exceeds 120 seconds')

            syslog.syslog(syslog.LOG_INFO, f'Finished successfully collecting BMC debug log dump.')
        except Exception as e:
            syslog.syslog(syslog.LOG_ERR, f'Failed to collect BMC debug log dump - {str(e)}')


def main(mode, task_id, filepath):
    extractor = BMCDebugDumpExtractor()
    if mode == 't':
        extractor.trigger_debug_dump()
    elif mode == 'c':
        extractor.extract_debug_dump_file(task_id, filepath)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BMC tech-support generator script.")
    # Add the arguments
    parser.add_argument('-m', '--mode', choices=['c', 't'], required=True, help="Mode of operation: 'c' for collecting debug dump or 't' for triggering debug dump task.")
    parser.add_argument('-p', '--path', help="Optional path to the file.")
    parser.add_argument('-t', '--task', help="Task-ID to collect the debug dump from")

    # Parse the arguments
    args = parser.parse_args()

    # Handle the arguments
    mode = args.mode
    task_id = args.task
    filepath = args.path

    main(mode, task_id, filepath)
