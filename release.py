from tools.build.release import ReleaseConfig
from tools.build.release_cli import main

CONFIG = ReleaseConfig(name='iaa')

if __name__ == '__main__':
    main(CONFIG)
