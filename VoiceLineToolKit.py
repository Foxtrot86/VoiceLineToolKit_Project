import sys

from UI import *
from Class_functions import Logs, Configuration
# INIT APP
log = Logs()
config = Configuration(logs=log)
config.import_settings()
try:
    if config.config["Settings"]["reset_logs"]:
        log.clear_logs()
except Exception as e:
    log.write_log(f"WARN: Checking reset_logs settings:  {e}")

log.create_instance()
config = Configuration(logs=log)
config.import_settings()
initial_status = set_debug_status(log)

if __name__ == '__main__':
    app = QApplication(sys.argv)

    apply_style(app)

    intro_window = IntroWindow(status=initial_status)
    intro_window.show()

    app.exec()
    sys.exit()
