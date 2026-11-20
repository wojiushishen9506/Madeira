#!/usr/bin/env python3
"""App translations (app/Madeira/Localizable.xcstrings).

Checks the app catalog, the Simplified Chinese coverage of the settings data and the
placement of the interface language selector. These are source checks, separate from
compiling the catalogs or changing languages on a device.
"""
from pathlib import Path
import json, re, sys

root = Path(__file__).resolve().parents[2]
app = root / 'app/Madeira'
failures = 0


def check(condition, label):
    global failures
    print(('PASS: ' if condition else 'FAIL: ') + label)
    if not condition:
        failures += 1


catalog = json.loads((app / 'Localizable.xcstrings').read_text(encoding='utf-8'))
project = (app.parent / 'Madeira.xcodeproj/project.pbxproj').read_text(encoding='utf-8')
languages = ['de', 'es', 'ko', 'pt-BR', 'ru']

check(project.count('A1009C03 /* Localizable.xcstrings in Resources */') == 2 and
      project.count('A2009C03 /* Localizable.xcstrings */') == 3, 'the catalog is in the app resources')
regions = re.search(r'knownRegions = \((.*?)\);', project, re.S)
check(regions is not None and all(l in regions.group(1) for l in ['de', 'es', 'ko', '"pt-BR"', 'ru']), 'the project knows the languages')
check(catalog.get('sourceLanguage') == 'en', 'English is the source language')

# The calls whose first argument SwiftUI reads as a LocalizedStringKey, and L("...")
# (Library.swift) for texts built in code: notes, picker titles, statuses, errors.
pattern = re.compile(r'\b(?:Text|Button|Label|Toggle|Section|Picker|navigationTitle|LabeledContent|TextField|Link|NavigationLink|'
                     r'Stepper|Menu|ShareLink|alert|confirmationDialog|SecureField|ContentUnavailableView|DisclosureGroup|ProgressView|L|LF)'
                     r'\(\s*"((?:[^"\\]|\\.)*)"')
compat_labels = re.compile(r'\bcompatLabel\(\s*"((?:[^"\\]|\\.)*)",\s*"((?:[^"\\]|\\.)*)"')
literals = set()
for swift in app.glob('*.swift'):
    source = swift.read_text(encoding='utf-8')
    candidates = pattern.findall(source)
    for title, note in compat_labels.findall(source):
        candidates.extend((title, note))
    for candidate in candidates:
        text = re.sub(r'\\\([^()"]*\)', '%@', candidate)
        text = re.sub(r'\\u\{([0-9A-Fa-f]+)\}', lambda x: chr(int(x.group(1), 16)), text)
        literals.add(re.sub(r'\\(["\\nt\'])', lambda x: {'n': '\n', 't': '\t'}.get(x.group(1), x.group(1)), text))

strings = catalog['strings']
# An Int interpolation is keyed %lld by SwiftUI, a String one %@; the source scan sees both as %@.
def shape(key):
    return key.replace('%lld', '%@')
stale = [k for k, v in strings.items() if v.get('extractionState') != 'manual' and shape(k) not in literals]
check(not stale, 'original translated texts are still in the app' + (f' (stale: {stale[:5]})' if stale else ''))
missing = [(k, l) for k, v in strings.items() for l in languages
           if l == 'zh-Hans' or len(v.get('localizations', {})) > 1
           if not v.get('localizations', {}).get(l, {}).get('stringUnit', {}).get('value')]
check(not missing, 'every catalog entry has Simplified Chinese and existing language sets are complete'
      + (f' (missing: {missing[:5]})' if missing else ''))
broken = []
for k, v in strings.items():
    for l, localization in v.get('localizations', {}).items():
        t = localization['stringUnit']['value']
        if re.findall(r'\]\((https?://[^)]+)\)', k) != re.findall(r'\]\((https?://[^)]+)\)', t) or \
                k.count('\n') != t.count('\n') or k.endswith(' ') != t.endswith(' ') or \
                sorted(re.findall(r'%(\d)\$(?:@|lld)', t)) != [str(i + 1) for i in range(shape(k).count('%@'))] or \
                k.count('%%') != t.count('%%'):
            broken.append((k[:30], l))
check(not broken, 'links, line breaks and trailing spaces survive' + (f' ({broken[:5]})' if broken else ''))

config = (app / 'ConfigCatalog.generated.swift').read_text(encoding='utf-8')
quoted = r'"(?:[^"\\]|\\.)*"'
option_copy = set()
for row in (line for line in config.splitlines() if 'ConfigOption(' in line):
    option_copy.update(map(json.loads, re.findall(r'\b(?:title|category|note):\s*(' + quoted + ')', row)))
    choices = row.split('choices: ', 1)[1].split('], sources:', 1)[0]
    option_copy.update(map(json.loads, re.findall(r',\s*(' + quoted + ')', choices)))
option_copy.discard('')
missing_options = sorted(option_copy - strings.keys())
check(not missing_options, 'advanced settings titles, choices, categories and descriptions are translated'
      + (f' (missing: {missing_options[:5]})' if missing_options else ''))

settings = (app / 'SettingsPages.swift').read_text(encoding='utf-8')
onboarding = (app / 'Onboarding.swift').read_text(encoding='utf-8')
root_view = (app / 'MadeiraApp.swift').read_text(encoding='utf-8')
check('var title: LocalizedStringKey' in settings and '[(LocalizedStringKey?, [Page])]' in settings
      and 'func primary(_ title: LocalizedStringKey' in onboarding and 'detail: LocalizedStringKey' in onboarding,
      'settings titles and first-run controls use localizable SwiftUI keys')
check(all('MadeiraLanguagePicker()' in source for source in (settings, onboarding))
      and root_view.count('@AppStorage(MadeiraLanguage.key)') == 2 and '.environment(\\.locale, language.locale)' in root_view,
      'both language selectors use the same saved preference as the app locale')
check(all(key in strings for key in [
    'Interface language', 'System language', 'Get started', 'Skip setup', 'Set up JIT',
    'Getting games', 'Running games', 'Memory and sync', 'Runtimes',
    'Remove from library', 'Game executable not found.',
    'The game stopped with Windows error 0x%@.',
    'The program passed an invalid parameter to the Windows C runtime.',
]), 'key first-run, settings and library strings are in the catalog')
print(f'{len(strings)} catalog entries')

# Not a failure (other threads add texts every day), but listed so they can be translated:
# texts in Text("...")/L("...") and the like that the catalog does not have yet. A text with
# a call inside an interpolation, or with no letters, is left out.
shapes = {shape(k) for k in strings}
untranslated = sorted(t for t in literals if t not in shapes and re.search(r'[A-Za-z]{2}', t)
                      and not re.search(r'\\\(', t))
print(f'NOTE: {len(untranslated)} texts in the app have no translation yet (they show in English):')
for t in untranslated:
    print('  - ' + t.replace('\n', '\\n'))

print('FAIL' if failures else 'PASS')
sys.exit(1 if failures else 0)
