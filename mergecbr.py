# -*- coding: utf8 -*-
#!/usr/bin/env python
import os
import zipfile
import logging
import argparse
import shutil
import tempfile
from pprint import pprint as pp
import pkgutil

logging.basicConfig(format="[%(asctime)s] %(levelname)s: %(message)s", level=logging.INFO, datefmt='%H:%M:%S')
log = logging.getLogger('mergeapp')

class Path:
    def __init__(self, root_path):
        self.root_path = root_path
        self._paths = [os.path.join(root_path, path) for path in os.listdir(root_path)]
        self.files = sorted(filter(os.path.isfile, self._paths))
        self.dirs = sorted(filter(os.path.isdir, self._paths))
    
    def root_name(self):
        return self.name(self.root_path)
    
    @classmethod
    def name(klass, path):
        return os.path.basename(path)

    @classmethod
    def _get_prefix(klass, lst):
        list_len = len(str(len(lst)))
        return f"%0{list_len}d_"

    def prefix(self, path):
        src = self.files if os.path.isfile(path) else self.dirs
        return self._get_prefix(src) % src.index(path)

class OptionParser:
    def __init__(self):
        parser = argparse.ArgumentParser(description="Combine multiple CBZ to one file")
        self.parser = parser
        parser.add_argument("-d", "--directory", help="Directory containing CBZ files")
        parser.add_argument("-o", "--output", help="Directory which will contain output CBZ file(s)")
        group = parser.add_mutually_exclusive_group()
        group.add_argument("-v", "--verbose", help="Enable Verbose Mode", action="store_true")
        group.add_argument("-s", "--silent", help="Enable Silent Mode", action="store_true")
        self.add_compressors()

    def add_compressors(self):
        compressors = (
            # module, option name, option value
            ('zlib', 'deflated', zipfile.ZIP_DEFLATED),
            ('bz2',  'bzip',     zipfile.ZIP_BZIP2),
            ('lzma', 'lzma',     zipfile.ZIP_LZMA)
        )
        available_compressors = {name: value for mod, name, value in compressors if pkgutil.find_loader(mod)}
        available_compressors['store'] = zipfile.ZIP_STORED
        if len(available_compressors) > 1:
            self.parser.add_argument("-c", "--compression", help="Compression type", choices=available_compressors.keys(), default="store")
            if "deflated" in available_compressors or "bzip" in available_compressors:
                self.parser.add_argument("-l", "--compresslevel", help="Compression level", choices=range(0,10), type=int, metavar="[0-9]", default=5)
        self.compressors = available_compressors

    def check_compressors(self, args):
        args.compression = self.compressors[getattr(args, 'compression', 'store')]
        if args.compression == "bzip":
            if args.compresslevel == 0:
                args.compresslevel = 1
        elif args.compression != "deflated":
            args.compresslevel = None

    def parse_args(self):
        args = self.parser.parse_args()
        app_args = {}
                
        if args.verbose:
            log.setLevel(logging.DEBUG)
            log.info("Verbose mode activated")
        elif args.silent:
            log.setLevel(logging.CRITICAL)
        
        if not args.directory:
            parent_dir = input(f"Enter Directory [{os.getcwd()}]: ")
            args.directory = parent_dir if os.path.isabs(parent_dir) else os.path.abspath(parent_dir)
        self.check_path(args.directory)

        if not args.output:
            args.output = os.getcwd()
        self.make_path(args.output)

        self.check_compressors(args)
        print(vars(args))
        return vars(args)

    def check_path(self, path):
        if os.path.isdir(path):
            log.debug(f"Parent Directory: {path}")
        else:
            log.error(f'{path} do not exist')
            exit()

    def make_path(self, path):
        try:
            os.makedirs(path, exist_ok=True)
            log.debug(f"Directory {path} created successfully")
        except OSError as error:
            log.error(f"Directory {path} can not be created")


class Comic:
    def __init__(self):
        self.__dict__.update(OptionParser().parse_args())

    def merge_directory(self, directory):
        src_dir = Path(directory)
        with tempfile.TemporaryDirectory() as tmprootdir:
            for file in src_dir.files:
                if not zipfile.is_zipfile(file):
                    continue
                with zipfile.ZipFile(file) as zp:
                    with tempfile.TemporaryDirectory() as tmpdirname:
                        zp.extractall(tmpdirname)
                        for f in Path(tmpdirname).files:
                            shutil.move(f, os.path.join(tmprootdir, src_dir.prefix(file) + Path.name(f)))
            cbz_path = os.path.join(self.output, f'{src_dir.root_name()}.cbz')
            with zipfile.ZipFile(cbz_path, mode='w', compression=self.compression, compresslevel=self.compresslevel) as archive:
                tmppath = Path(tmprootdir)
                for file in tmppath.files:
                    archive.write(file, Path.name(file))

    def merge(self):
        src_dir = Path(self.directory)
        self.merge_directory(self.directory)
        for directory in src_dir.dirs:
            self.merge_directory(directory)

if __name__ == "__main__":
    Comic().merge()