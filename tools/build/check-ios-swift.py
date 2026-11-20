#!/usr/bin/env python3
"""Check the Madeira target's Swift types without building its native libraries."""
import re
import subprocess
from pathlib import Path


root = Path(__file__).resolve().parents[2]
project = (root / 'app/Madeira.xcodeproj/project.pbxproj').read_text()
phase = project.split('/* Begin PBXSourcesBuildPhase section */', 1)[1].split('};', 1)[0]
swift_names = re.findall(r'/\* ([^/]+\.swift) in Sources \*/', phase)
paths = subprocess.check_output(['git', 'ls-files', 'app/Madeira'], cwd=root, text=True).splitlines()
swift_files = []
for name in swift_names:
    matches = [path for path in paths if Path(path).name == name]
    if len(matches) != 1:
        raise SystemExit(f'Madeira target: expected one source for {name}: {matches}')
    swift_files.append(matches[0])
if 'app/Madeira/Library.swift' not in swift_files or 'app/Madeira/MadeiraApp.swift' not in swift_files:
    raise SystemExit('The Madeira app sources could not be located')

sdk = subprocess.check_output(['xcrun', '--sdk', 'iphoneos', '--show-sdk-path'], text=True).strip()
subprocess.run([
    'xcrun', 'swiftc', '-typecheck', '-module-name', 'Madeira', '-swift-version', '5',
    '-sdk', sdk, '-target', 'arm64-apple-ios18.0', '-DDEBUG', '-enable-bare-slash-regex',
    '-enable-experimental-feature', 'DebugDescriptionMacro', '-Xcc', '-DDEBUG=1',
    '-import-objc-header', 'app/Madeira/Madeira-Bridging-Header.h', *swift_files,
], cwd=root, check=True)
