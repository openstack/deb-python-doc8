# Copyright (C) 2014 Ivan Melnikov <iv at altlinux dot org>
#
# Author: Joshua Harlow <harlowja@yahoo-inc.com>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


"""Check documentation for simple style requirements.

What is checked:
    - invalid rst format - D000
    - lines should not be longer than 79 characters - D001
      - RST exception: line with no whitespace except in the beginning
      - RST exception: lines with http or https urls
      - RST exception: literal blocks
      - RST exception: rst target directives
    - no trailing whitespace - D002
    - no tabulation for indentation - D003
    - no carriage returns (use unix newlines) - D004
"""

import argparse
import collections
import logging
import os
import sys

if __name__ == '__main__':
    # Only useful for when running directly (for dev/debugging).
    sys.path.insert(0, os.path.abspath(os.getcwd()))
    sys.path.insert(0, os.path.abspath(os.path.join(os.pardir, os.getcwd())))

import six
from six.moves import configparser
from stevedore import extension

from doc8 import checks
from doc8 import parser as file_parser
from doc8 import utils
from doc8 import version

FILE_PATTERNS = ['.rst', '.txt']
MAX_LINE_LENGTH = 79
CONFIG_FILENAMES = [
    "doc8.ini",
    "tox.ini",
    "pep8.ini",
    "setup.cfg",
]


def split_set_type(text):
    return set([i.strip() for i in text.split(",") if i.strip()])


def merge_sets(sets):
    m = set()
    for s in sets:
        m.update(s)
    return m


def extract_config(args):
    parser = configparser.RawConfigParser()
    read_files = []
    if args['config']:
        for fn in args['config']:
            with open(fn, 'r') as fh:
                parser.readfp(fh, filename=fn)
                read_files.append(fn)
    else:
        read_files.extend(parser.read(CONFIG_FILENAMES))
    if not read_files:
        return {}
    cfg = {}
    try:
        cfg['max_line_length'] = parser.getint("doc8", "max-line-length")
    except (configparser.NoSectionError, configparser.NoOptionError):
        pass
    try:
        cfg['ignore'] = split_set_type(parser.get("doc8", "ignore"))
    except (configparser.NoSectionError, configparser.NoOptionError):
        pass
    try:
        cfg['ignore_path'] = split_set_type(parser.get("doc8",
                                                       "ignore_path"))
    except (configparser.NoSectionError, configparser.NoOptionError):
        pass
    try:
        cfg['allow_long_titles'] = parser.getboolean("doc8",
                                                     "allow-long-titles")
    except (configparser.NoSectionError, configparser.NoOptionError):
        pass
    try:
        cfg['sphinx'] = parser.getboolean("doc8", "sphinx")
    except (configparser.NoSectionError, configparser.NoOptionError):
        pass
    try:
        cfg['verbose'] = parser.getboolean("doc8", "verbose")
    except (configparser.NoSectionError, configparser.NoOptionError):
        pass
    try:
        extensions = parser.get("doc8", "extensions")
        extensions = extensions.split(",")
        extensions = [s.strip() for s in extensions if s.strip()]
        if extensions:
            cfg['extension'] = extensions
    except (configparser.NoSectionError, configparser.NoOptionError):
        pass
    return cfg


def fetch_checks(cfg):
    base = [
        checks.CheckValidity(cfg),
        checks.CheckTrailingWhitespace(cfg),
        checks.CheckIndentationNoTab(cfg),
        checks.CheckCarriageReturn(cfg),
        checks.CheckMaxLineLength(cfg),
    ]
    mgr = extension.ExtensionManager(
        namespace='doc8.extension.check',
        invoke_on_load=True,
        invoke_args=(cfg.copy(),),
    )
    addons = []
    for e in mgr:
        addons.append(e.obj)
    return base + addons


def setup_logging(verbose):
    if verbose:
        level = logging.DEBUG
    else:
        level = logging.ERROR
    logging.basicConfig(level=level,
                        format='%(levelname)s: %(message)s', stream=sys.stdout)


def main():
    parser = argparse.ArgumentParser(
        prog='doc8',
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    default_configs = ", ".join(CONFIG_FILENAMES)
    parser.add_argument("paths", metavar='path', type=str, nargs='*',
                        help=("Path to scan for doc files"
                              " (default: current directory)."),
                        default=[os.getcwd()])
    parser.add_argument("--config", metavar='path', action="append",
                        help="User config file location"
                             " (default: %s)." % default_configs,
                        default=[])
    parser.add_argument("--allow-long-titles", action="store_true",
                        help="Allow long section titles (default: False).",
                        default=False)
    parser.add_argument("--ignore", action="append", metavar="code",
                        help="Ignore the given error code(s).",
                        type=split_set_type,
                        default=[])
    parser.add_argument("--no-sphinx", action="store_false",
                        help="Do not ignore sphinx specific false positives.",
                        default=True, dest='sphinx')
    parser.add_argument("--ignore-path", action="append", default=[],
                        help="Ignore the given directory or file (globs"
                             " are supported).", metavar='path')
    parser.add_argument("--max-line-length", action="store", metavar="int",
                        type=int,
                        help="Maximum allowed line"
                             " length (default: %s)." % MAX_LINE_LENGTH,
                        default=MAX_LINE_LENGTH)
    parser.add_argument("-e", "--extension", action="append",
                        metavar="extension",
                        help="Check file extensions of the given type"
                             " (default: %s)." % ", ".join(FILE_PATTERNS),
                        default=list(FILE_PATTERNS))
    parser.add_argument("-v", "--verbose", dest="verbose", action='store_true',
                        help="Run in verbose mode.", default=False)
    parser.add_argument("--version", dest="version", action='store_true',
                        help="Show the version and exit.", default=False)
    args = vars(parser.parse_args())
    if args.get('version'):
        print(version.version_string())
        return 0
    args['ignore'] = merge_sets(args['ignore'])
    cfg = extract_config(args)
    args['ignore'].update(cfg.pop("ignore", set()))
    if 'sphinx' in cfg:
        args['sphinx'] = cfg.pop("sphinx")
    args['extension'].extend(cfg.pop('extension', []))
    args['ignore_path'].extend(cfg.pop('ignore_path', []))
    args.update(cfg)
    setup_logging(args.get('verbose'))

    print("Scanning...")
    files = collections.deque()
    ignored_paths = args.pop('ignore_path')
    files_ignored = 0
    files_selected = 0
    file_iter = utils.find_files(args.pop('paths', []),
                                 args.pop('extension', []), ignored_paths)
    for filename, ignoreable in file_iter:
        if ignoreable:
            files_ignored += 1
            if args.get('verbose'):
                print("  Ignoring '%s'" % (filename))
        else:
            files_selected += 1
            files.append(file_parser.parse(filename))
            if args.get('verbose'):
                print("  Selecting '%s'" % (filename))

    ignoreables = frozenset(args.pop('ignore', []))
    error_counts = {}
    while files:
        f = files.popleft()
        if args.get('verbose'):
            print("Validating %s" % f)
        for c in fetch_checks(args):
            try:
                # http://legacy.python.org/dev/peps/pep-3155/
                check_name = c.__class__.__qualname__
            except AttributeError:
                check_name = ".".join([c.__class__.__module__,
                                       c.__class__.__name__])
            error_counts.setdefault(check_name, 0)
            try:
                extension_matcher = c.EXT_MATCHER
            except AttributeError:
                pass
            else:
                if not extension_matcher.match(f.extension):
                    if args.get('verbose'):
                        print("  Skipping check '%s' since it does not"
                              " understand parsing a file with extension '%s'"
                              % (check_name, f.extension))
                    continue
            try:
                reports = set(c.REPORTS)
            except AttributeError:
                pass
            else:
                reports = reports - ignoreables
                if not reports:
                    if args.get('verbose'):
                        print("  Skipping check '%s', determined to only"
                              " check ignoreable codes" % check_name)
                    continue
            if args.get('verbose'):
                print("  Running check '%s'" % check_name)
            if isinstance(c, checks.ContentCheck):
                for line_num, code, message in c.report_iter(f):
                    if code in ignoreables:
                        continue
                    if args.get('verbose'):
                        print('    - %s:%s: %s %s'
                              % (f.filename, line_num, code, message))
                    else:
                        print('%s:%s: %s %s'
                              % (f.filename, line_num, code, message))
                    error_counts[check_name] += 1
            elif isinstance(c, checks.LineCheck):
                for line_num, line in enumerate(f.lines_iter(), 1):
                    for code, message in c.report_iter(line):
                        if code in ignoreables:
                            continue
                        if args.get('verbose'):
                            print('    - %s:%s: %s %s'
                                  % (f.filename, line_num, code, message))
                        else:
                            print('%s:%s: %s %s'
                                  % (f.filename, line_num, code, message))
                        error_counts[check_name] += 1
            else:
                raise TypeError("Unknown check type: %s, %s"
                                % (type(c), c))
    total_errors = sum(six.itervalues(error_counts))
    print("=" * 8)
    print("Total files scanned = %s" % (files_selected))
    print("Total files ignored = %s" % (files_ignored))
    print("Total accumulated errors = %s" % total_errors)
    if error_counts:
        print("Detailed error counts:")
        for check_name in sorted(six.iterkeys(error_counts)):
            check_errors = error_counts[check_name]
            print("    - %s = %s" % (check_name, check_errors))
    if total_errors:
        return 1
    else:
        return 0


if __name__ == "__main__":
    sys.exit(main())
