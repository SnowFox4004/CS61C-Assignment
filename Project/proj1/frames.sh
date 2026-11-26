#!/bin/bash
########################################################################
##
## NAME:        frames.sh
##
## DESCRIPTION: Bash version of frames.csh for CS61C Fall 2020 project 1.
##              Generates up to 90,000 frames and stitches them into a GIF
##              using ppm_tool.py (replaces ImageMagick's `convert`).
##
## USAGE:       ./frames.sh <rootname> <rule> <frames>
## EXAMPLE:     ./frames.sh glider 0x1808 10
##
########################################################################

indir="testInputs"
outdir="studentOutputs"
life="./gameOfLife"
ppm_tool="$(dirname "$0")/ppm_tool.py"

if [ $# -ne 3 ]; then
    echo "Usage: $0 <rootname> <rule> <frames>"
    echo "Example: $0 glider 0x1808 10"
    echo "         This will run Conway's Game of Life simulation $life"
    echo "         with rule 0x1808 on the file $indir/glider.ppm"
    echo "         and write into $outdir/glider/ the files"
    echo "         glider_0x1808_10000.ppm through glider_0x1808_10010.ppm"
    exit 0
fi

rootname="$1"
rule="$2"
nframes="$3"

if [ ! -d "$indir" ]; then
    echo "$indir input directory doesn't exist, exiting..."
    exit 1
fi

if [ ! -f "$indir/$rootname.ppm" ]; then
    echo "$indir/$rootname.ppm initial PPM file doesn't exist, exiting..."
    exit 1
fi

if [ ! -d "$outdir" ]; then
    echo "$outdir output directory doesn't exist, creating..."
    mkdir -p "$outdir" || exit 1
fi

if [ ! -d "$outdir/$rootname" ]; then
    echo "$rootname directory doesn't exist, creating..."
    mkdir -p "$outdir/$rootname" || exit 1
else
    echo "$rootname directory already exists; existing files will not be recomputed"
fi

cp "$indir/$rootname.ppm" "$outdir/$rootname/${rootname}_${rule}_10000.ppm" || exit 1

n=10000
max=$((10000 + nframes))

while [ "$n" -lt "$max" ]; do
    np=$((n + 1))
    report=$((np - 10000))
    if [ -f "$outdir/$rootname/${rootname}_${rule}_${np}.ppm" ]; then
        echo -n "[$report] "
    else
        echo -n "$report "
        "$life" "$outdir/$rootname/${rootname}_${rule}_${n}.ppm" "$rule" \
            > "$outdir/$rootname/${rootname}_${rule}_${np}.ppm" || {
            echo ""
            echo "gameOfLife failed on frame $n" >&2
            exit 1
        }
    fi
    n=$((n + 1))
done
echo ""

echo "Making gif in ${rootname}.gif"
# 等价于: convert -delay 20 -loop 0 -scale 400% $outdir/$1/*.ppm $1.gif
python3 "$ppm_tool" gif -o "${rootname}.gif" -d 10 -l 0 -s 4 "$outdir/$rootname" || {
    echo "GIF generation failed" >&2
    exit 1
}
echo ""