import logging

from datetime import datetime
from extract import extract
from load import load
from transform import transform

logger = logging.getLogger(__name__)

def main():

    logger.info("Starting ETL process...")

    batch_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    load(extract(), batch_id)

    transform(batch_id)

    logger.info("ETL process completed successfully.")


if __name__ == "__main__":
    main()