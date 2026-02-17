import os
import argparse

from kotonebot.devtools.resgen.codegen import EntityGenerator
from kotonebot.devtools.resgen.runner import generate_resources

OUTPUT_IMG_DIR = './iaa/res'                  # 处理后的图片存放处
OUTPUT_CODE_FILE = './iaa/tasks/R.py'             # 生成的代码文件


class IaaGenerator(EntityGenerator):
    def __init__(self, production: bool = False, ide_type: str | None = None, default_variant: str = ''):
        path_transformer = lambda p: f'sprite_path("{os.path.relpath(p, OUTPUT_IMG_DIR).replace(os.sep, "/")}")'
        super().__init__(production, ide_type, path_transformer, default_variant=default_variant)

    def render_header(self):
        super().render_header()
        self.writer.write("from iaa.utils import sprite_path")


def ide_type_detection() -> str:
    import psutil
    try:
        me = psutil.Process()
        while True:
            parent = me.parent()
            if parent is None:
                break
            name = parent.name().lower()
            if 'code' in name or 'cursor' in name:
                return 'vscode'
            if 'pycharm' in name:
                return 'pycharm'
            me = parent
    except:  # noqa: E722
        pass
    return 'vscode'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--production', action='store_true', help='No docstrings')
    parser.add_argument('--ide', default=None)
    args = parser.parse_args()

    ide = args.ide or ide_type_detection()

    result = generate_resources(
        output_code_file=OUTPUT_CODE_FILE,
        output_img_dir=OUTPUT_IMG_DIR,
        generator_factory=lambda default_variant: IaaGenerator(
            production=args.production,
            ide_type=ide,
            default_variant=default_variant,
        ),
    )
    print(f"Scanning {result.root_scan_path}...")
    if result.variant_names is not None:
        print(f"Variant enabled: {result.variant_names}")
    print(f"Parsed files: {result.parsed_file_count}")
    print(f"Resources: {result.resource_count}")
    print("Done!")

if __name__ == "__main__":
    main()
