"""Optional design export, not needed to run the bank.
Requires fontTools, CairoSVG and the DejaVu fonts installed on Linux.
"""
from pathlib import Path
import json
import cairosvg
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.transformPen import TransformPen

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'frontend/public/brand-assets'


def outline(font_path, text, tracking=0, slant=0):
    font = TTFont(font_path)
    glyphs, cmap = font.getGlyphSet(), font.getBestCmap()
    paths, bounds, advance = [], [], 0
    for letter in text:
        glyph = glyphs[cmap[ord(letter)]]
        pen, box = SVGPathPen(glyphs), BoundsPen(glyphs)
        transform = (1, 0, slant, 1, 0, 0)
        glyph.draw(TransformPen(pen, transform))
        glyph.draw(TransformPen(box, transform))
        paths.append((pen.getCommands(), advance))
        bounds.append((box.bounds[0]+advance, box.bounds[1], box.bounds[2]+advance, box.bounds[3]))
        advance += glyph.width + tracking
    return paths, (min(b[0] for b in bounds), min(b[1] for b in bounds), max(b[2] for b in bounds), max(b[3] for b in bounds))


MARK, MB = outline('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 'B')
WORD, WB = outline('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 'bank', tracking=-35)


def fitted(paths, bounds, x, y, height, color):
    x0, y0, x1, y1 = bounds
    scale = height/(y1-y0)
    content = ''.join(f'<path d="{path}" transform="translate({advance} 0)"/>' for path,advance in paths)
    return f'<g fill="{color}" transform="matrix({scale:.8f} 0 0 {-scale:.8f} {x-x0*scale:.6f} {y+y1*scale:.6f})">{content}</g>', (x1-x0)*scale


def currency_mark(x, y, height, color):
    path = 'M2 0H17C24 0 27 3.5 27 8C27 11.5 25 14 22.5 15.3C26 16.6 28 19.5 28 23C28 28.5 24 32 17 32H2Q0 32 0 30V2Q0 0 2 0Z M9 6C5 6 5 12 9 12H17C21 12 21 6 17 6Z M9 20C5 20 5 26 9 26H18C22 26 22 20 18 20Z'
    return f'<g data-mark="B-modular" transform="translate({x} {y}) scale({height/32})"><path fill="{color}" fill-rule="evenodd" d="{path}"/></g>'


def icon(size=64, round=False):
    bg = '<circle cx="32" cy="32" r="32" fill="#ffdd2d"/>' if round else '<rect width="64" height="64" rx="16" fill="#ffdd2d"/>'
    height = 38
    width = 28*height/32
    mark = currency_mark((64-width)/2, 13, height, '#111111')
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 64 64" role="img" aria-label="B bank — монограмма"><title>B bank — монограмма</title>{bg}{mark}</svg>'


def lockup(inverse=False):
    height, word_h = 176, 79
    word_w = (WB[2]-WB[0])*word_h/(WB[3]-WB[1])
    width = 24*2 + 128 + 26 + word_w
    bg = f'<rect width="{width:.2f}" height="176" fill="#111111"/>' if inverse else ''
    symbol = icon().split('</title>',1)[1].rsplit('</svg>',1)[0]
    symbol = f'<g transform="translate(24 24) scale(2)">{symbol}</g>'
    letters, _ = fitted(WORD, WB, 178, (height-word_h)/2, word_h, '#ffdd2d' if inverse else '#111111')
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.2f}" height="176" viewBox="0 0 {width:.2f} 176" role="img" aria-label="B bank"><title>B bank — единый логотип</title>{bg}{symbol}{letters}</svg>'


if __name__ == '__main__':
    ASSETS.mkdir(parents=True, exist_ok=True)
    (ASSETS/'b-symbol.svg').write_text(icon())
    (ASSETS/'b-round.svg').write_text(icon(512, True))
    word, width = fitted(WORD, WB, 0, 0, 52, '#111111')
    (ASSETS/'b-bank-wordmark.svg').write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.2f}" height="52" viewBox="0 0 {width:.2f} 52" role="img" aria-label="bank"><title>bank — надпись логотипа</title>{word}</svg>')
    (ASSETS/'b-bank-logo.svg').write_text(lockup())
    (ASSETS/'b-bank-inverse.svg').write_text(lockup(True))
    inner = lockup().split('</title>',1)[1].rsplit('</svg>',1)[0]
    large = currency_mark(1340, 540, 680, '#e5bf00')
    cover = '<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" viewBox="0 0 1920 1080"><title>B bank — обложка презентации</title><rect width="1920" height="1080" fill="#ffdd2d"/><g transform="translate(72 115) scale(2.35)">'+inner+'</g>'+large+'</svg>'
    (ASSETS/'b-bank-presentation.svg').write_text(cover)
    for target in ['favicon.svg', 'logo.svg']:
        (ROOT/'frontend/public'/target).write_text(icon())
    source = {'mark': {'font':'Original modular geometry', 'slant':0, 'style':'two rounded blocks', 'bar':{'x_fraction':.5,'top_fraction':-.15,'bottom_fraction':1.15,'width_fraction':.078}, 'paths':MARK, 'bounds':MB}, 'wordmark': {'text':'bank', 'font':'DejaVu Sans Bold', 'paths':WORD, 'bounds':WB}, 'palette': {'yellow':'#FFDD2D', 'black':'#111111'}, 'rule':'Upright modular B without crossbars. The wordmark spells bank only.'}
    (ROOT/'design/brand-outlines.json').write_text(json.dumps(source, ensure_ascii=False, indent=2))
    for svg,png,width in [('b-bank-logo.svg','logo-primary.png',1800), ('b-round.svg','logo-round.png',1024), ('b-bank-inverse.svg','logo-inverse.png',1800), ('b-bank-presentation.svg','presentation-cover.png',1920)]:
        cairosvg.svg2png(url=str(ASSETS/svg), write_to=str(ASSETS/png), output_width=width)
    print('SVG masters and consistent PNG exports updated.')
