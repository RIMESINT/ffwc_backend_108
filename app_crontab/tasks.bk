# app_crontab/tasks.py
import subprocess
import logging
import time
from datetime import datetime
from celery import shared_task
from celery_progress.backend import ProgressRecorder

logger = logging.getLogger(__name__)

@shared_task(bind=True)
def run_crontab_script_async(self, label, command_args):
    """
    Safely executes external crontab bash scripts and Django commands 
    inside a background Celery worker thread, embedding detailed 
    tracing and completion diagnostics into the output payload.
    """
    progress_recorder = ProgressRecorder(self)
    logger.info(f"Pipeline job execution triggered for component: {label}")
    progress_recorder.set_progress(10, 100, description=f"Initializing workspace container for {label}...")

    # Start tracing timers
    start_time = time.time()
    start_dt = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 1. Build the Execution Trace Header
    trace_header = (
        f"============================================================\n"
        f"--- PROCESS TRACE INITIATED ---\n"
        f"Target:  {label}\n"
        f"Command: {' '.join(command_args)}\n"
        f"Started: {start_dt}\n"
        f"============================================================\n\n"
    )

    try:
        progress_recorder.set_progress(40, 100, description=f"Spawning runtime subprocess...")
        
        # Execute process and capture text stdout/stderr logs
        result = subprocess.run(
            command_args, 
            capture_output=True, 
            text=True, 
            check=True
        )
        
        # End tracing timers
        end_time = time.time()
        elapsed = round(end_time - start_time, 2)
        end_dt = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 2. Build the Success Completion Footer
        trace_footer = (
            f"\n\n============================================================\n"
            f"--- PROCESS COMPLETED SUCCESSFULLY ---\n"
            f"Ended:   {end_dt}\n"
            f"Elapsed: {elapsed} seconds\n"
            f"Exit:    Code {result.returncode}\n"
            f"============================================================"
        )
        
        final_stdout = trace_header + (result.stdout if result.stdout else "No standard output produced by the script.") + trace_footer
        final_stderr = result.stderr if result.stderr else "No error diagnostics recorded."
        
        progress_recorder.set_progress(100, 100, description=f"Execution successful!")
        return {
            'status': 'SUCCESS',
            'message': f"Successfully executed {label}.",
            'stdout': final_stdout,
            'stderr': final_stderr
        }
        
    except subprocess.CalledProcessError as e:
        # Capture failure timers
        end_time = time.time()
        elapsed = round(end_time - start_time, 2)
        end_dt = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        logger.error(f"Pipeline component process failure for {label}. Exit Code: {e.returncode}")
        
        # 3. Build the Failure Completion Footer
        trace_footer = (
            f"\n\n============================================================\n"
            f"--- PROCESS TERMINATED WITH ERRORS ---\n"
            f"Ended:   {end_dt}\n"
            f"Elapsed: {elapsed} seconds\n"
            f"Exit:    Code {e.returncode}\n"
            f"============================================================"
        )
        
        final_stdout = trace_header + (e.stdout if e.stdout else "No standard output produced before failure.") + trace_footer
        final_stderr = (e.stderr if e.stderr else "No error diagnostics recorded.")
        
        progress_recorder.set_progress(100, 100, description=f"Execution failed with exit code {e.returncode}.")
        return {
            'status': 'FAILURE',
            'message': f"Command failed with exit code {e.returncode}.",
            'stdout': final_stdout,
            'stderr': final_stderr
        }
        
    except Exception as e:
        # Capture crash timers
        end_time = time.time()
        elapsed = round(end_time - start_time, 2)
        end_dt = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        logger.exception(f"Unexpected operational crash running {label}")
        
        # 4. Build the Critical Crash Footer
        trace_footer = (
            f"\n\n============================================================\n"
            f"--- CRITICAL SYSTEM CRASH ---\n"
            f"Ended:     {end_dt}\n"
            f"Elapsed:   {elapsed} seconds\n"
            f"Exception: {str(e)}\n"
            f"============================================================"
        )
        
        final_stdout = trace_header + "Process crashed before executing standard standard output." + trace_footer
        final_stderr = f"CRITICAL EXCEPTION:\n{str(e)}"
        
        progress_recorder.set_progress(100, 100, description="Process execution error.")
        return {
            'status': 'FAILURE',
            'message': f"Internal crash: {str(e)}",
            'stdout': final_stdout,
            'stderr': final_stderr
        }