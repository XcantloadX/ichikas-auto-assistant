from tools.build import BuildConfig
from tools.build.cli import main

CONFIG = BuildConfig(
    name='iaa',
    collect_packages=['kaa'],
    extra_hidden_imports=['plyer.platforms.win.notification'],
    runtime_copy=[
        ('assets', 'assets'),
        ('iaa/res', 'assets/res_compiled'),
    ],
)

if __name__ == '__main__':
    main(CONFIG)
