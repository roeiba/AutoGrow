/**
 * Professional logging utility for frontend
 */

const LOG_LEVELS = {
  DEBUG: 0,
  INFO: 1,
  WARN: 2,
  ERROR: 3,
}

class Logger {
  constructor(context = 'App') {
    this.context = context
    this.level = import.meta.env.DEV ? LOG_LEVELS.DEBUG : LOG_LEVELS.INFO
  }

  _log(level, emoji, message, ...args) {
    if (level < this.level) return

    const timestamp = new Date().toISOString()
    const prefix = `[${timestamp}] ${emoji} [${this.context}]`

    switch (level) {
      case LOG_LEVELS.DEBUG:
        console.debug(prefix, message, ...args)
        break
      case LOG_LEVELS.INFO:
        console.info(prefix, message, ...args)
        break
      case LOG_LEVELS.WARN:
        console.warn(prefix, message, ...args)
        break
      case LOG_LEVELS.ERROR:
        console.error(prefix, message, ...args)
        break
    }
  }

  debug(message, ...args) {
    this._log(LOG_LEVELS.DEBUG, '🔍', message, ...args)
  }

  info(message, ...args) {
    this._log(LOG_LEVELS.INFO, 'ℹ️', message, ...args)
  }

  success(message, ...args) {
    this._log(LOG_LEVELS.INFO, '✅', message, ...args)
  }

  warn(message, ...args) {
    this._log(LOG_LEVELS.WARN, '⚠️', message, ...args)
  }

  error(message, ...args) {
    this._log(LOG_LEVELS.ERROR, '❌', message, ...args)
  }

  websocket(message, ...args) {
    this._log(LOG_LEVELS.DEBUG, '🔌', message, ...args)
  }

  api(message, ...args) {
    this._log(LOG_LEVELS.DEBUG, '🌐', message, ...args)
  }

  progress(message, percent, ...args) {
    this._log(LOG_LEVELS.INFO, '📊', `${message} (${percent}%)`, ...args)
  }
}

export default Logger
