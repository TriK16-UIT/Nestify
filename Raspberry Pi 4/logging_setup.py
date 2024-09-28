import logging
import os 
from datetime import datetime
from config import LOGS_PATH

if not os.path.exists(LOGS_PATH):
    os.makedirs(LOGS_PATH)

log_filename = datetime.now().strftime("%Y-%m-%d_%H-%M-%S.log")
log_filepath = os.path.join(LOGS_PATH, log_filename)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filepath),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)