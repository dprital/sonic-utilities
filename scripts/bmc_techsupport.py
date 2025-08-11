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

            * Blocking action till we get the file or having ERROR or Timeout

            * It is invoked with the parameter '-m c'
              E.g.: python3 /usr/local/bin/bmc_techsupport -m c -p <path> -t <task-id> -- to collect log dump

    Basically, in the generate_dump script we will call the first method
    at the beginning of its process and the second method towards the end of the process.
"""


import argparse
import os
import sonic_platform
import time


TIMEOUT_FOR_GET_BMC_DEBUG_LOG_DUMP_IN_SECONDS = 60
SYSLOG_IDENTIFIER = "bmc_techsupport"
log = sonic_platform.syslogger.SysLogger(SYSLOG_IDENTIFIER)


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
            log.log_info("Triggering BMC debug log dump Redfish task")
            (ret, (task_id, err_msg)) = self.bmc.trigger_bmc_debug_log_dump()
            if ret != 0:
                log.log_error(f'Failed to trigger BMC debug log dump: {err_msg}')
                raise Exception(err_msg)

            log.log_info(f'Successfully triggered BMC debug log dump - Task-id: {task_id}')
        except Exception as e:
            log.log_error(f'Failed to trigger BMC debug log dump - {str(e)}')
        finally:
            print(f'{task_id}')

    def extract_debug_dump_file(self, task_id, filepath):
        '''
            Extract BMC debug log dump and save running task id
        '''
        try:
            if task_id is None or task_id == BMCDebugDumpExtractor.INVALID_TASK_ID:
                raise Exception(f'Invalid Task-ID')
            log_dump_dir = os.path.dirname(filepath)
            log_dump_filename = os.path.basename(filepath)
            if not log_dump_dir or not log_dump_filename:
                raise Exception(f'Invalid given filepath: {filepath}')

            start_time = time.time()
            log.log_info("Collecting BMC debug log dump")
            ret, err_msg = self.bmc.get_bmc_debug_log_dump(task_id=task_id, filename=log_dump_filename, path=log_dump_dir,
                                                           timeout=TIMEOUT_FOR_GET_BMC_DEBUG_LOG_DUMP_IN_SECONDS)
            end_time = time.time()
            duration = end_time - start_time
            if ret != 0:
                log.log_error(f'BMC debug log dump does not finish within {TIMEOUT_FOR_GET_BMC_DEBUG_LOG_DUMP_IN_SECONDS} seconds: {err_msg}')
                raise Exception(err_msg)
            log.log_info(f'Finished successfully collecting BMC debug log dump. Duration: {duration} seconds')
        except Exception as e:
            log.log_error(f'Failed to collect BMC debug log dump - {str(e)}')


def main(mode, task_id, filepath):
    try:
        extractor = BMCDebugDumpExtractor()
        if extractor.bmc is None:
            raise Exception('BMC instance is not available')
    except Exception as e:
        log.log_error(f'Failed to initialize BMCDebugDumpExtractor: {str(e)}')
        if mode == 'trigger':
            print(f'{BMCDebugDumpExtractor.INVALID_TASK_ID}')
        return
    if mode == 'trigger':
        extractor.trigger_debug_dump()
    elif mode == 'collect':
        extractor.extract_debug_dump_file(task_id, filepath)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BMC tech-support generator script.")
    # Add the arguments
    parser.add_argument('-m', '--mode', choices=['collect', 'trigger'], required=True,
                        help="Mode of operation: 'collect' for collecting debug dump or 'trigger' for triggering debug dump task.")
    parser.add_argument('-p', '--path', help="Path to save the BMC debug log dump file.")
    parser.add_argument('-t', '--task', help="Task-ID to monitor and collect the debug dump from.")

    # Parse the arguments
    args = parser.parse_args()

    # Handle the arguments
    mode = args.mode
    task_id = args.task
    filepath = args.path

    main(mode, task_id, filepath)
