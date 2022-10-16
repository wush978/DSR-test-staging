import logging

formatter = (
    '[%(asctime)s] p%(process)s {%(pathname)s:%(lineno)d} ' +
    '%(levelname)s - %(message)s'
)


def init_logging():
    logging.basicConfig(
        format=formatter,
        datefmt='%Y-%m-%d %H:%M:%S',
        level=logging.INFO,
    )
