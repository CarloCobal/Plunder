from datetime import datetime
from threading import Lock

class Logger(object):
    HEADER = '\033[95m'
    OKGRAY = '\033[0;37m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    _FILE_LOCK = Lock()

    @staticmethod
    def _log_to_file(txt: str) -> None:
        Logger._FILE_LOCK.acquire()
        with open('logs/log.txt', 'a') as fh:
            fh.write(txt + '\n')
        Logger._FILE_LOCK.release()

    @staticmethod
    def debug(txt: str):
        Logger._print('DEBUG', Logger.OKGRAY, txt)

    @staticmethod
    def info(txt: str):
        Logger._print('INFO', Logger.OKCYAN, txt, True)

    @staticmethod
    def warn(txt: str):
        Logger._print('WARN', Logger.WARNING, txt, True)

    @staticmethod
    def error(txt: str):
        Logger._print('ERROR', Logger.FAIL, txt, True)

    @staticmethod
    def _print(flag: str, color: str, msg: str, log_to_file: bool = False) -> None:
        time = datetime.now()
        time = time.strftime('%H:%M:%S')

        basic_string = f'[{time}][{flag}] -> {msg}{Logger.ENDC}'
        colored_string = color + basic_string

        print(colored_string)

        if log_to_file:
            Logger._log_to_file(basic_string)
