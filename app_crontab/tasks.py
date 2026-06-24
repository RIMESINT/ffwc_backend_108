# app_crontab/tasks.py
import subprocess
import logging
from celery import shared_task
from celery_progress.backend import ProgressRecorder

logger = logging.getLogger(__name__)

@shared_task(bind=True)
def run_crontab_script_async(self, label, command_args):
    """
    Background worker process to execute scripts out of the app_crontab tree
    without causing Gunicorn request gateway timeouts.
    """
    progress_recorder = ProgressRecorder(self)
    logger.info(f"System automation request initiated for component: {label}")
    progress_recorder.set_progress(10, 100, description=f"Spawning environment container for {label}...")

    try:
        progress_recorder.set_progress(40, 100, description="Executing command string parameters...")
        
        # Execute shell script or management command directly
        result = subprocess.run(
            command_args,
            capture_output=True,
            text=True,
            check=True
        )
        
        progress_recorder.set_progress(100, 100, description="Process executed successfully.")
        return {
            'status': 'SUCCESS',
            'message': f"Successfully executed: {label}",
            'stdout': result.stdout,
            'stderr': result.stderr
        }
    except subprocess.CalledProcessError as e:
        logger.error(f"Automation component failure for {label}. Exit code: {e.returncode}")
        progress_recorder.set_progress(100, 100, description="Execution failed.")
        return {
            'status': 'FAILURE',
            'message': f"Process terminated with exit code {e.returncode}.",
            'stdout': e.stdout,
            'stderr': e.stderr
        }
    except Exception as e:
        logger.exception(f"Unexpected operational fault executing {label}")
        progress_recorder.set_progress(100, 100, description="System runtime fault.")
        return {
            'status': 'FAILURE',
            'message': f"Internal error: {str(e)}",
            'stdout': '',
            'stderr': str(e)
        }