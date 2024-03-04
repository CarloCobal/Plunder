import sys

sys.path.append('../')

from logger import Logger

Logger.info('info msg')
Logger.debug('debug msg')
Logger.error('error msg')
Logger.warn('warn msg')
