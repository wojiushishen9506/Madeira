#!/usr/bin/env python3
"""Check the Madeira target's Swift types without building its native libraries."""
import re
import subprocess
from pathlib import Path


root = Path(__file__).resolve().parents[2]
project = (root / 'app/Madeira.xcodeproj/project.pbxproj').read_text()
phase = project.split('/* Begin PBXSourcesBuildPhase section */', 1)[1].split('};', 1)[0]
names = re.findall(r'/\* ([^*\n]+\.swift) in Sources \*/', phase)
tracked = subprocess.check_output(['git', 'ls-files', 'app/Madeira'], cwd=root, text=True).splitlines()
swift_files = []
for name in names:
    relative = f'app/Madeira/{name}'
    if relative in tracked:
        swift_files.append(relative)
        continue
    matches = [path for path in tracked if Path(path).name == name]
    if len(matches) != 1:
        raise SystemExit(f'Madeira target: expected one source for {name}: {matches}')
    swift_files.append(matches[0])
if 'app/Madeira/Library.swift' not in swift_files or 'app/Madeira/MadeiraApp.swift' not in swift_files:
    raise SystemExit('The Madeira app sources could not be located')
missing = [path for path in swift_files if not (root / path).is_file()]
if missing:
    raise SystemExit(f'Madeira target: missing Swift sources: {missing}')

sdk = subprocess.check_output(['xcrun', '--sdk', 'iphoneos', '--show-sdk-path'], text=True).strip()
subprocess.run([
    'xcrun', 'swiftc', '-typecheck', '-module-name', 'Madeira', '-swift-version', '5',
    '-sdk', sdk, '-target', 'arm64-apple-ios18.0', '-DDEBUG', '-enable-bare-slash-regex',
    '-enable-experimental-feature', 'DebugDescriptionMacro', '-Xcc', '-DDEBUG=1',
    '-import-objc-header', 'app/Madeira/Madeira-Bridging-Header.h', *swift_files,
], cwd=root, check=True)
