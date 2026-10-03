#!/usr/bin/env python3
"""Prépare le projet Android de Sonder Studio (utilisé par .github/workflows/apk.yml).
   python3 apk_build.py prepare  -> copie l'app web dans www/ et lit la version
   python3 apk_build.py patch    -> signature, version, icônes, couleurs du projet android/
"""
import os, re, sys, shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
WEB_FILES = ['index.html', 'manifest.webmanifest', 'icon-192.png', 'icon-512.png']

def version():
    html = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
    m = re.search(r"const VERSION = '([^']+)'", html)
    return m.group(1) if m else '0'

def prepare():
    www = os.path.join(ROOT, 'www')
    shutil.rmtree(www, ignore_errors=True); os.makedirs(www)
    for f in WEB_FILES:
        src = os.path.join(ROOT, f)
        if os.path.exists(src): shutil.copy(src, www)
    if not os.path.exists(os.path.join(www, 'index.html')):
        sys.exit("index.html absent à la racine du dépôt")
    v = version()
    env = os.environ.get('GITHUB_ENV')
    if env:
        with open(env, 'a') as fh: fh.write(f"STUDIO_VERSION={v}\n")
    print('Version du studio :', v)

def sub(path, pattern, repl, count=1, required=True):
    s = open(path, encoding='utf-8').read()
    n = re.subn(pattern, repl, s, count=count, flags=re.S)
    if required and n[1] == 0: sys.exit(f"Motif introuvable dans {path} : {pattern}")
    open(path, 'w', encoding='utf-8').write(n[0])

def icons(res):
    try:
        from PIL import Image
    except ImportError:
        print('Pillow absent : icône par défaut conservée'); return
    src = Image.open(os.path.join(ROOT, 'icon-512.png')).convert('RGBA')
    bg = src.getpixel((6, 6))
    dens = {'mdpi': 1, 'hdpi': 1.5, 'xhdpi': 2, 'xxhdpi': 3, 'xxxhdpi': 4}
    for d, k in dens.items():
        folder = os.path.join(res, f'mipmap-{d}'); os.makedirs(folder, exist_ok=True)
        s = round(48 * k)
        ic = src.resize((s, s), Image.LANCZOS)
        ic.save(os.path.join(folder, 'ic_launcher.png')); ic.save(os.path.join(folder, 'ic_launcher_round.png'))
        f = round(108 * k)  # icône adaptative : 108 dp, zone visible ~72 dp
        fg = Image.new('RGBA', (f, f), (0, 0, 0, 0)); inner = src.resize((round(f * .86), round(f * .86)), Image.LANCZOS)
        fg.paste(inner, ((f - inner.width) // 2, (f - inner.height) // 2), inner)
        fg.save(os.path.join(folder, 'ic_launcher_foreground.png'))
    hexbg = '#%02x%02x%02x' % bg[:3]
    bgxml = os.path.join(res, 'values', 'ic_launcher_background.xml')
    open(bgxml, 'w').write(f'<?xml version="1.0" encoding="utf-8"?>\n<resources>\n    <color name="ic_launcher_background">{hexbg}</color>\n</resources>\n')
    for x in ['drawable-v24/ic_launcher_foreground.xml', 'drawable/ic_launcher_background.xml']:
        p = os.path.join(res, x)
        if os.path.exists(p): os.remove(p)
    # écran de démarrage : fond sombre + icône
    for root, _, files in os.walk(res):
        if 'splash.png' in files:
            p = os.path.join(root, 'splash.png'); w, h = Image.open(p).size
            sp = Image.new('RGBA', (w, h), (20, 24, 29, 255)); m = round(min(w, h) * .32); ic = src.resize((m, m), Image.LANCZOS)
            sp.paste(ic, ((w - m) // 2, (h - m) // 2), ic); sp.convert('RGB').save(p)
    print('Icônes générées, fond', hexbg)

def patch():
    app = os.path.join(ROOT, 'android', 'app')
    gradle = os.path.join(app, 'build.gradle')
    run = int(os.environ.get('RUN_NUMBER', '1'))
    v = version()
    sub(gradle, r'versionCode \d+', f'versionCode {100 + run}')
    sub(gradle, r'versionName "[^"]*"', f'versionName "{v}"')
    signing = '''    signingConfigs {
        release {
            storeFile file("../../sonder-release.keystore")
            storePassword System.getenv("SONDER_KEYSTORE_PASSWORD")
            keyAlias "sonder"
            keyPassword System.getenv("SONDER_KEYSTORE_PASSWORD")
        }
    }
    buildTypes {
        release {
            signingConfig signingConfigs.release
'''
    sub(gradle, r'    buildTypes \{\n        release \{\n', signing)
    res = os.path.join(app, 'src', 'main', 'res')
    styles = os.path.join(res, 'values', 'styles.xml')
    sub(styles, r'(<style name="AppTheme.NoActionBar"[^>]*>)', r'\1\n        <item name="android:windowBackground">#14181d</item>')
    icons(res)
    print(f'Projet Android prêt : version {v}, code {100 + run}')

if __name__ == '__main__':
    {'prepare': prepare, 'patch': patch}.get(sys.argv[1] if len(sys.argv) > 1 else '', lambda: sys.exit(__doc__))()
