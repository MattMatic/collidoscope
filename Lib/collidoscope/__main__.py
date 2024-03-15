from collidoscope import Collidoscope
from argparse import ArgumentParser, FileType
import tqdm
import re
import sys


def designspace_location(loc):
    if not loc:
        return None
    m = re.findall(r"(\w+)=([\.\d]+)[\s,]*", loc)
    if not m:
        raise ValueError(f"Cannot parse location '{loc}'")
    return {axis: float(value) for axis, value in m}


parser = ArgumentParser()
parser.add_argument("input",
                    help="font file to process", metavar="OTF")
parser.add_argument('-c', type=int, default=3, dest="context",
                    help="number of glyphs to process", metavar="CONTEXT")
parser.add_argument('--no-faraway', action='store_false', dest="faraway",
                    help="don't check for interactions between non-adjacent glyphs")
parser.add_argument('--no-marks', action='store_false', dest="marks",
                    help="don't check for interactions between marks")
parser.add_argument('--no-bases', action='store_false', dest="bases",
                    help="don't check for interactions between bases")
parser.add_argument('--no-adjacent-clusters', action='store_false', dest="adjacent_clusters",
                    help="don't check for interactions between glyphs in adjacent clusters")
parser.add_argument('--cursive', action='store_true', dest="cursive",
                    help="check for interactions between paths without anchors")
parser.add_argument('--area', type=int, default=0, dest="area",
                    help="check for interactions of size >=area%% between paths")
parser.add_argument('--scale-factor', dest="scale_factor",
                    help="Scale glyphs before checking", metavar="SCALE", default=1.0)
parser.add_argument('--location', dest="location",
                    help="Designspace location", metavar="LOCATION", type=designspace_location)
parser.add_argument('--jalt', action='store_true', dest="feat_jalt",
                    help="(OT Feature) enable justification alternatives")
parser.add_argument('--swsh', action='store_true', dest="feat_swsh",
                    help="(OT Feature) enable swash")
parser.add_argument('--no-kern', action='store_true', dest="feat_kern_off",
                    help="(OT feature) disable kerning")

parser.add_argument('-r', dest="range",
                    help="Comma-separated list of Unicode ranges", metavar="RANGE")

parser.add_argument('-t', dest="text",
                    help="Text to check", metavar="TEXT")

parser.add_argument('-f', dest="file", type=FileType('r', encoding="UTF-8"),
                    help="File of lines to check (UTF-8)", metavar="FILE")

parser.add_argument('-o', dest="output", type=FileType('w', encoding="UTF-8"), default="report.html",
                    help="Output report file", metavar="FILE")


args = parser.parse_args()

report = args.output

fontfilename = args.input

c = Collidoscope(fontfilename, {
        "faraway": args.faraway,
        "adjacent_clusters": args.adjacent_clusters,
        "cursive": args.cursive,
        "area":    args.area / 100,
        "marks":   args.marks,
        "bases":   args.bases
    },
    scale_factor = float(args.scale_factor),
    location = args.location
)


import itertools

report.write('''
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8"> 
    <title></title>
<style>
body{
 font-family:'Calibri'
}
.cards {
 display: grid;
 grid-template-columns: repeat(auto-fill, 300px);
 grid-auto-rows: auto;
 grid-gap: 1rem;
 font-family:'%s'; font-size:24pt;
 }
svg { transform: scaleY(-1); }
.card {
 border: 2px solid #e7e7e7;
 border-radius: 4px;
 padding: .5rem;
}
.count {
 font-family:'Calibri';
 color:red;
 font-size:10pt;
}
.line {
 font-family:'Calibri';
 color:orange;
 font-size:10pt;
}
</style>
</head>

<body>
<h1>Collision Report</h1>
<h2>%s</br>%s</h2>
''' %  (c.ttfont["name"].getDebugName(1), c.ttfont["name"].getDebugName(6), c.ttfont["name"].getDebugName(5)))

report.write('''<pre>%s</pre></br>''' % (str(sys.argv[1:])))
report.write('''<div class="cards">''')

codepoints = c.ttfont.getBestCmap().keys()
codepointfilter = []


counter = 0
counterhit = 0

def gen_texts(codepoints):
    print("Generating text...")
    combinations = []
    texts = []

    count = 1
    for i in range(0,args.context):
        combinations.append(codepoints)
        count = count * len(codepoints)

    for element in itertools.product(*combinations):
        text = "".join(map(chr, element))
        texts.append(text)
    print("Done")
    return texts

if args.text:
    texts = [args.text]
elif args.file:
    texts = [ x.rstrip() for x in args.file.readlines()]
elif args.range:
    for r in args.range.split(","):
        if "-" in r:
            first, last = r.split("-")
            codepointfilter.extend(range(int(first, 16),int(last,16)+1))
        else:
            codepointfilter.append(int(r,16))
    codepoints = list(filter(lambda x: x in codepointfilter, codepoints))
    texts = gen_texts(codepoints)
else:
    print("Testing ALL GLYPHS AGAINST ALL GLYPHS - you may want to specify a -r range e.g. -r 0620-064A")
    texts = gen_texts(codepoints)

c.prep_shaper()

features = {'kern':True}
if args.feat_jalt:
    features['jalt'] = True
if args.feat_kern_off:
    features['kern'] = False
if args.feat_swsh:
    features['swsh'] = True


pbar = tqdm.tqdm(texts)
for text in pbar:
    counter = counter + 1
    pbar.set_description(text.ljust(26))
    glyphs = c.get_glyphs(text, None, features)
    cols = c.has_collisions(glyphs)
    if cols:
        counterhit = counterhit + 1
        cols = c.draw_overlaps(glyphs, cols, "preserveAspectRatio=\"xMidYMax\" width=250 height=150")
        report.write("<div class=\"card\"><span class=\"count\">%d</span><span class=\"line\"> @%d</span> %s %s</div> \n" % (counterhit, counter, text, cols))
        report.flush()

report.write('''
</div>
</body>
</html>
''')

print("Output written on %s" % args.output.name)
print("Number of hits = %d" % counterhit)
# hbfont = prep_shaper(fontfilename)
# glyphs = get_glyphs(hbfont, font, "ۍ", anchors)
# print(has_collisions(glyphs, 1, {
#         "faraway": False,
#         "cursive": False,
#         "area":    0.4
#     }))
